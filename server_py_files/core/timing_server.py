# -*- coding: utf-8 -*-
"""
Python twisted server, implements an HTTP socket-server and command queue to
execute python commands, parse XTSM, and manage data in user-specific contexts.  

Created on Thu May 16 18:24:40 2013
           
This software is described at
https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Python_server

TODO:
    permit standard command library calls with POST payloads on websocket
    connections (for faster exchanges on standard calls) ?
    is this done and working ?
    redirect stdio to console
    execute command queue items on schedule
    queue in databomb upkeep (links and storage)
    
@author: Nate, Jed
"""


import uuid
import time
import sys
import inspect
import pickle
import types
import collections
import subprocess
import io
import os
import platform #Access to underlying platform’s identifying data
from datetime import datetime
from datetime import date   
import pdb
import __main__ as main
import colorama
colorama.init(strip=False)
import textwrap
import pickle
#import roperdarknoise as rdn
import pstats

import msgpack
import msgpack_numpy
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketClientFactory
from autobahn.twisted.websocket import WebSocketClientProtocol
from autobahn.twisted.websocket import connectWS
from autobahn.twisted.websocket import listenWS
from twisted.internet import wxreactor
from twisted.internet import defer
from twisted.internet.protocol import DatagramProtocol
wxreactor.install()
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet import task
from lxml import etree
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO
import wx
import wx.html
from enthought.traits.api import HasTraits
from enthought.traits.api import Int as TraitedInt
from enthought.traits.api import Str as TraitedStr

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet import error

import simplejson
import socket
import XTSMobjectify
import DataBomb
import InfiniteFileStream
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking
import XTSM_Server_Objects
import XTSM_Transforms
import live_content
import xstatus_ready
import file_locations
import server_initializations
import glab_instrument
import script_server

import matplotlib as mpl
import matplotlib.pyplot as plt 
import hdf5_liveheap
import gc

import numpy as np
import scipy
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import timing_diagram
import data_gui
import GPIB_control
import getopt
import commands
import sync
#import objgraph
#from IPy import IP
from scipy.optimize import curve_fit

def tracefunc(frame, event, arg, indent=[0]):
      global DEBUG_LINENO, TRACE_IGNORE
      try: 
          filename = frame.f_globals["__file__"]
          if filename.count("C:\\wamp\\vortex\\WebSocketServer\\DataBomb")==0:
              return tracefunc
      except: return
      for ti in TRACE_IGNORE: 
          if frame.f_code.co_name==ti: return
      DEBUG_LINENO+=1
      if event == "call":
          indent[0] += 2
          print "-" * indent[0] + "> call function", \
          frame.f_code.co_name, str(DEBUG_LINENO)
      elif event == "return":
          print "<" + "-" * indent[0], "exit function", frame.f_code.co_name
          indent[0] -= 2
      return tracefunc

DEBUG_LINENO = 0      
DEBUG_TRACE = False
TRACE_IGNORE=["popexecute","getChildNodes","getItemByFieldValue"]
MAX_SCRIPT_SERVERS = 2
DEBUG = True
      
if DEBUG_TRACE: sys.settrace(tracefunc)


try:
    port = int(sys.argv[1])
    wsport = int(sys.argv[2])
    udpbport = int(sys.argv[2])
except IndexError:
    port = 8083
    wsport = 8084
    udpbport = 8085


    
class MulticastProtocol(DatagramProtocol):
    """
    Protocol to handle UDP multi-receiver broadcasts - used for servers
    to announce their presence to one another through periodic pings
    """
    resident=True
    def startProtocol(self):
        """
        Join the multicast address
        """
        interface_ = ""
        if socket.gethostbyname(socket.gethostname()) == '10.1.1.124':
            interface_ = '10.1.1.124'
        self.transport.joinGroup("228.0.0.5", interface=interface_)

    def send(self,message):
        """
        sends message on udp broadcast channel
        """
        self.transport.write(message, ("228.0.0.5", udpbport))

    def datagramReceived(self, datagram_, address):
        """
        called when a udp broadcast is received
        """
        #if DEBUG: print "Datagram received from "+ repr(address) 
        datagram = simplejson.loads(datagram_)
        if not hasattr(datagram,'keys'):
            if DEBUG: print "unknown UDP message:\n", datagram
            pdb.set_trace()
            return
        if 'loop_started' in datagram.keys():
            return
        if 'shotnumber_started' in datagram.keys():
            #dc.get('_exp_sync').shotnumber = datagram['shotnumber_started']
            #return
            self.server.pxi_time = float(datagram['time'])
            self.server.pxi_time_server_time = float(datagram['time']) - float(time.time())#Make this so that it synchronizes the clocks CP

            msg = {"data_context": 'PXI',
                   "shotnumber":datagram['shotnumber_started']}
            msg = simplejson.dumps(msg, ensure_ascii = False).encode('utf8')
            self.server.broadcast(msg)             
            if DEBUG: print datagram
            
            self.server.active_parser_ip = datagram['server_ip_in_charge']#Make this so that it synchronizes the clocks CP
            self.server.active_parser_port = datagram['server_port_in_charge']#Make this so that it synchronizes the clocks CP
            dc = self.server.command_library.__determineContext__({'data_context':'PXI'})       
            if not dc.dict.has_key('_exp_sync'):
                 exp_sync = sync.Experiment_Sync_Group(self.server, dc.name)
                 dc.update({'_exp_sync':exp_sync})
            dc.get('_exp_sync').shotnumber = int(datagram['shotnumber_started'])
            print "Shot started:", datagram['shotnumber_started'], "pxi_time:", self.server.pxi_time, "time.time():", float(time.time())
            return
            
        
        if 'fake_shotnumber_started' in datagram.keys():
            if self.server.ip == '10.1.1.124':
                return
            print datagram
            msg = {"data_context": datagram['data_context'],
                   "shotnumber":datagram['fake_shotnumber_started']}
            msg = simplejson.dumps(msg, ensure_ascii = False).encode('utf8')
            self.server.broadcast(msg)   
            dc = self.server.command_library.__determineContext__(datagram)       
            if not dc.dict.has_key('_exp_sync'):
                 exp_sync = sync.Experiment_Sync_Group(self.server, dc.name)
                 dc.update({'_exp_sync':exp_sync})
            dc.get('_exp_sync').shotnumber = int(datagram['fake_shotnumber_started'])
            if DEBUG: print "Fake Shot started:", datagram['fake_shotnumber_started'], "pxi_time:", datagram['time'], "time.time():", float(time.time())
            dc.update({'Test_instrument':glab_instrument.Glab_Instrument(params={'server':self.server,'create_example_pollcallback':True})})
            return
        
        try:
            datagram["server_ping"] 
        except KeyError:
            if DEBUG: print "unknown UDP message:\n", datagram
            return
        ping_command = commands.ServerCommand(self.server, self.server.catch_ping, datagram)
        self.server.command_queue.add(ping_command)
    
class HTTPRequest(BaseHTTPRequestHandler):
    """
    A class to handle HTTP request interpretation
    """
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()
    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

        
class WSClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        self.in_use = True
        self.id = uuid.uuid4()
        if DEBUG: print("class WSClientProtocol, func onConnect. : {0}".format(response.peer)), "ID:", self.id
        self.time_of_creation = time.time()
        self.connection = self.factory.connection
        self.connection.protocol = self
        self.server = self.factory.connection_manager.server
        self.connection_manager = self.factory.connection_manager

    def onOpen(self):
        if DEBUG: print("class WSClientProtocol, func onOpen.")
        self.connection.ip = self.transport.getPeer().host
        self.connection.port = self.transport.getPeer().port
        self.connection.connection_manager.connectLog(self)
        self.connection.on_open()

    def onMessage(self, payload, isBinary):
        if DEBUG: print "class WSClientProtocol, func onMessage"
        self.log_message()
        self.connection.last_message_time = time.time()
        msg_command = commands.ServerCommand(self.server, self.connection.on_message, payload, isBinary, self)
        self.server.command_queue.add(msg_command)
        


    def log_message(self):
        headerItemsforCommand=['host','origin']
        self.request = {k: self.http_headers[k] for k in headerItemsforCommand if k in self.http_headers}
        self.ctime = time.time()        
        self.request.update({'ctime':self.ctime})
        self.request.update({'timereceived':time.time()})
        self.request.update({'write':self.sendMessage})
        self.request.update({'protocol':self})
        # record where this request is coming from
        self.factory.connection_manager.elaborateLog(self,self.request)

    def onClose(self, wasClean, code, reason):
        if DEBUG: print("class WSClientProtocol, func onClose. {0}".format(reason))
        try:
            self.connection.on_close()
        except AttributeError:
            self.is_open_connection = False
            pass
                          
        

class WSServerProtocol(WebSocketServerProtocol):
    """
    This is the websocket protocol - it defines the server's response to
    bidirectional open-port websocket communications.  This is useful for
    on-demand server-push and low-connection-overhead comm.
    
    added by NDG on 3-25-14, most methods not yet finished
    """
    resident=True
    bidirectional=True
    def onConnect(self, request):
        pass
        self.in_use = True
        self.id = uuid.uuid4()
        if DEBUG: print("class WSServerProtocol, func onConnect. : {0}".format(request.peer)), "ID:", self.id
        self.time_of_creation = time.time()
        self.server = self.factory.connection_manager.server
        self.connection_manager = self.factory.connection_manager

    def onOpen(self):
        pass
        if DEBUG: print("class WSServerProtocol, func onOpen.")
        #if not (self.transport.getPeer().host == '10.1.1.112' or self.transport.getPeer().host == '10.1.1.124' or self.transport.getPeer().host == '10.1.1.178'):
        #    pdb.set_trace()
        #if self.transport.getPeer().port == '8087':
        #print self.transport.getPeer().host
        #pdb.set_trace()
        if str(self.transport.getPeer().host) == '127.0.0.1':
            new_connection = WebSocketConnection()
            new_connection.is_open_connection = True
            new_connection.server = self.factory.server
            new_connection.connection_manager = self.factory.connection_manager
            new_connection.protocol = self
            new_connection.port = self.transport.getPeer().port
            new_connection.ip = self.transport.getPeer().host
            self.connection = new_connection
            self.connection.protocol = self
            self.connection_manager.connectLog(self) 
            self.connection.last_message_time = time.time()
            self.connection.on_open()
            return
        new_peer = PeerServer()
        new_peer.is_open_connection = True
        new_peer.server = self.factory.server
        new_peer.connection_manager = self.factory.connection_manager
        new_peer.protocol = self
        new_peer.port = self.transport.getPeer().port
        new_peer.ip = self.transport.getPeer().host
        self.connection = new_peer
        self.connection.protocol = self
        self.connection_manager.connectLog(self) 
        self.connection.last_message_time = time.time()
        self.connection.on_open()
   

        #peer = self.transport.getPeer()
        #self.factory.isConnectionOpen = True
        #self.connection_manager.add_peer_server_as_server(peer)
        #try:
        #    self.factory.openConnections.update({self.ConnectionUID:self})
       # except AttributeError: 
        #    self.factory.openConnections = {self.ConnectionUID:self}
        
        #Moved to add_peer_server in class Client Manager/PeerServer
        #self.ctime = time.time()
        #peer = self.transport.getPeer()
        #self.peer ='%s:%s' % (p.host,p.port)
        #self.ConnectionUID = uuid.uuid1().__str__()
        #self.clientManager.add_peer_server(peer)
        #pdb.set_trace()
        #try:
        #    self.factory.openConnections.update({self.ConnectionUID:self})
        #except AttributeError: 
        #    self.factory.openConnections = {self.ConnectionUID:self}
        #self.clientManager.connectLog(self)

    def failHandshake(self,code=1001,reason='Going Away'):
        pass        
            
    def onMessage(self, payload, isBinary):
        if DEBUG: print"class WSServerProtocol, func onMessage."
        if DEBUG and not isBinary and len(payload) < 10000: print payload
        self.connection.last_connection_time = time.time()
        self.log_message()
        self.connection.last_message_time = time.time()
        msg_command = commands.ServerCommand(self.server, self.connection.on_message, payload, isBinary, self)
        self.server.command_queue.add(msg_command)

    def log_message(self):
        headerItemsforCommand=['host','origin']
        self.request = {k: self.http_headers[k] for k in headerItemsforCommand if k in self.http_headers}
        self.ctime = time.time()        
        self.request.update({'ctime':self.ctime})
        self.request.update({'timereceived':time.time()})
        self.request.update({'write':self.sendMessage})
        self.request.update({'protocol':self})
        # record where this request is coming from
        self.factory.connection_manager.elaborateLog(self,self.request)

    #Moved to function in GlabClient
    """
    def onBinaryMessage(self,payload_):
        payload = msgpack.unpackb(payload_)
        print "---------Data Below!-------------"
        print payload

    #def giveit(self):
    #    self.sendMessage("adsdasd")

    def onTextMessage(self,payload):
        print "------------"
        print payload
        # we will treat incoming websocket text using the same commandlibrary as HTTP        
        # but expect incoming messages to be JSON data key-value pairs
        try:
            data = simplejson.loads(payload)
        except simplejson.JSONDecodeError:
            self.transport.write("The server is expecting JSON, not simple text")
            print "The server is expecting JSON, not simple text"
            self.transport.loseConnection()
            return False
        # if someone on this network has broadcast a shotnumber change, update the shotnumber in
        # the server's data contexts under _running_shotnumber
        #pdb.set_trace()        
        if hasattr(data, "shotnumber"):
            pdb.set_trace() # need to test the below
            #for dc in self.parent.dataContexts:
                #dc['_running_shotnumber']=data['shotnumber']
        data.update({'request':self.request})
        data.update({'socket_type':"Websocket"})
        SC=SocketCommand(params=data, request=self.request, CommandLibrary=self.server.commandLibrary)
        try:
            #self.commandQueue.add(SC)
            self.server.commandQueue.add(SC)
        #except AttributeError:
        #    self.commandQueue=CommandQueue(SC)
        except:
            self.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")
    """    
    def onClose(self, wasClean, code, reason):
        if DEBUG: print("class WSServerProtocol, func onClose. {0}".format(reason))
        try:
            self.connection.on_close()
        except AttributeError:
            self.is_open_connection = False
            pass
        #self.transport.loseConnection()
        #del self.server
        #Does this work?? 


            
        
#class EchoProtocol(protocol.Protocol):
#    """
#    A simple example protocol to echo requests back on HTTP
#    """
#    def connectionMade(self):
#        p=self.transport.getPeer()
#        self.peer ='%s:%s' % (p.host,p.port)
#        print  datetime.now(), ":Connected from", self.peer
#    def dataReceived(self,data):
#        print data
#        self.transport.write('You Sent:\n')
#        self.transport.write(data)
#        self.transport.loseConnection()
#    def connectionLost(self,reason):
#        print datetime.now() , ":Disconnected from %s: %s" % (self.peer,reason.value)
             
        
class CommandProtocol(protocol.Protocol):
    """
    This is the protocol to handle incoming socket commands; it is here to
    listen on a socket, and insert command requests into a command queue - if 
    the request is valid, it will eventually be executed by the queue 
    """
    resident=False
    bidirectional=False
    def connectionMade(self):
        self.ctime = time.time()
        p = self.transport.getPeer()
        self.peer ='%s:%s' % (p.host,p.port)
        self.ConnectionUID = uuid.uuid1().__str__()
        if DEBUG: print "class CommandProtocol, function connectionMade. uid:", self.ConnectionUID
        try:
            self.factory.openConnections.update({self.ConnectionUID:self})
        except AttributeError:
            pdb.set_trace()
        if DEBUG: print "Connected from", self.peer, "at", datetime.now()
        self.factory.connection_manager.connectLog(self)
        self.server = self.factory.connection_manager.server
        self.alldata = ''
    
    def provide_console(self):
        if DEBUG: print "class CommandProtocol, function provide_console"
        """
        default face of server when contacted with a get request
        """
        #self.transport.write("this is a running XTSM server\n\r\n\r")
        #pdb.set_trace()
        self.transport.write("<XML>"+self.factory.parent.xstatus()+"</XML>")
        self.transport.loseConnection()
    
    def dataReceived(self,data):
        """
        Algorithm called each time a data fragment (packet typ <1300 bytes) is taken in on socket
        If last packet in message, records the requested command in the queue
        """
        if DEBUG: print "class CommandProtocol, function dataReceived"
        if data[6:12] == "status":
            print self.server.xstatus()
            self.transport.write("<XML>"+self.server.xstatus()+"</XML>")
            self.transport.loseConnection()
            return
        if DEBUG and len(data) < 10000: print "data:", data
        # on receipt of the first fragment determine message length, extract header info
        # NOTE: this can only handle header lengths smaller than the fragment size - 
        # the header MUST arrive in the first fragment
        # append the new data 
        self.alldata += data
        if u"?console" in data: self.provide_console()
        #requests = 0   #For use with priorities
        if not hasattr(self,'mlength'):
            # attempt to extract the header info with the current message subset
            try:            
                self.dataHTTP = HTTPRequest(self.alldata)
                self.boundary = self.dataHTTP.headers['content-type'].split('boundary=')[-1]
                fb = data.find('--' + self.boundary) # find the first used boundary string
                if fb == -1:
                    return # if there is none, the header must not be complete
                # if there is a boundary, header must be complete; get header data
                self.mlength = fb + int(self.dataHTTP.headers.dict['content-length'])
                headerItemsforCommand = ['host','origin','referer']
                self.request = {k: self.dataHTTP.headers[k] for k in headerItemsforCommand if k in self.dataHTTP.headers}
                self.request.update({'ctime':self.ctime,'protocol':self})
                # record where this request is coming from
                self.factory.connection_manager.elaborateLog(self,self.request)
            except: return  # if unsuccessful, wait for next packet and try again
        
        # if we made it to here, the header has been received
        # if the entirety of message not yet received, append this fragment and continue
        if self.mlength > len(self.alldata):
            return
        # if we have made it here, this is last fragment of message       
        # mark the 'all data received' time
        self.request.update({'timereceived':time.time()})
        # strip multipart data from incoming HTTP request
        kv = [datas.split('name="')[-1].split('"\n\r\n\r') for datas in self.alldata.split('--'+self.boundary+'--')]
        self.params = {k:v.rstrip() for k,v in kv[:-1]}
        # insert request, if valid, into command queue (persistently resides in self.Factory)  
        #pdb.set_trace()
        #SC=SocketCommand(self.params,self.request)
        SC=commands.SocketCommand(self.params,self.request, self.server.command_library)#CP 2014-10-28
        try:
            self.factory.connection_manager.server.command_queue.add(SC)
            #self.factory.commandQueue.add(SC)
        except AttributeError:
            if DEBUG: print 'Failed to insert SocketCommand in Queue, No Queue'
            raise
            #self.factory.commandQueue=CommandQueue(SC)
        except:
            if DEBUG: print "Error No command included in request", SC
            msg = {'Not_Command_text_message':'Failed to insert SocketCommand in Queue, reason unknown','terminator':'die'}
            self.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
            if DEBUG: print 'Failed to insert SocketCommand in Queue, reason unknown'
            self.transport.loseConnection()
            raise
    # close the connection - should be closed by the command execution
    # self.transport.loseConnection()
    def connectionLost(self,reason):   
        if DEBUG: print "class CommandProtocol, function connectionLost"   
        try:
            del self.factory.openConnections[self.ConnectionUID]
        except KeyError:
            pass
        if DEBUG: print datetime.now(), "Disconnected from %s: %s" % (self.peer,reason.value)

        
class ConnectionManager(XTSM_Server_Objects.XTSM_Server_Object):
    """
    The client manager retains a list of recent clients, their IP addresses,
    and can later be used for permissioning, etc...
    """
    def __init__(self, server):
        self.server = server
        self.id = uuid.uuid4()
        self.maintenance_period = 5
        self.peer_servers = {}
        self.script_servers = {}
        self.default_websocket_connections = {}
        self.data_gui_servers = {}
        self.TCP_connections = {}
        
        maintenance_command = commands.ServerCommand(self.server, self.periodic_maintainence)
        self.server.reactor.callLater(self.maintenance_period,
                                      self.server.command_queue.add,
                                      maintenance_command)
        # setup the websocket server services

        #self.wsfactory.protocol.commandQueue = self.commandQueue
        #self.wsfactory.protocol.clientManager = self.clientManager
        
        

        address = "ws://localhost:" + str(wsport)
        self.wsServerFactory = WebSocketServerFactory(address, debug=True)
        self.wsServerFactory.setProtocolOptions(failByDrop=False)
        #self.wsServerFactory.parent = self
        self.wsServerFactory.protocol = WSServerProtocol
        self.wsServerFactory.connection_manager = self
        self.wsServerFactory.server = self.server
        listenWS(self.wsServerFactory)
        # listen on standard TCP port
        #global port
        #self.laud = self.server.reactor.listenTCP(port, self.wsServerFactory)
        
    def is_connections_closed(self):
        if DEBUG: print "Checking connections"
        #pdb.set_trace()
        for key in self.peer_servers.keys():
            if self.peer_servers[key].protocol.state != self.peer_servers[key].protocol.STATE_CLOSED:
                return False
        for key in self.script_servers.keys():
            if self.script_servers[key].protocol.state != self.script_servers[key].protocol.STATE_CLOSED:
                return False
        return True    

       
    def identify_client(self,protocol):
        """
        attempts to identify a client by the connection protocol 
        
        resident protocols are identified by the ip:port string
        non-resident (ephemoral) protocols are identified by ip address and
        header info
        """
        if protocol.resident:
            return protocol.peer
        #pdb.set_trace()
        
    def connectLog(self,protocol):
        return # temporary disable
        #pdb.set_trace()
        pid = self.identify_client(protocol)
        try:
            self.clients[pid].connectLog()
        except KeyError:
            self.clients.update({pid:self.client(params={"protocol":protocol})})

    def elaborateLog(self,protocol,request):
        return # temporary disable
        pid = self.identify_client(protocol)
        try:
            self.clients[pid].elaborateLog()
        except KeyError:
            self.clients.update({pid:self.client(params={"protocol":protocol})})
        
    def update_client_roles(self,request,role):
        """
        keeps list of clients by 'role' the role is ascribed by the caller
        
        if peer is a request object, the ip:port will be determined, and if 
        request is an emphemeral TCP port, will ...
        
        """
        return
        #pdb.set_trace() #commend out by JZ on 10/3/14
        if not self.client_roles.has_key(request['protocol'].peer):
            self.client_roles.update({request['protocol'].peer:{role:time.time()}})
        else:
            self.client_roles[request['protocol'].peer].update({role:time.time()})
    role_timeouts={}
    def periodic_maintainence(self):
        """
        performs periodic maintenance on connection data with clients
        """
        if not hasattr(self,'peer_servers'):
            return
        for key in self.peer_servers.keys():
            if DEBUG: print self.peer_servers[key].last_broadcast_time
            if self.peer_servers[key].is_open_connection == False:
                continue
            if (time.time() - self.peer_servers[key].last_broadcast_time) > 30:
                if DEBUG: print ("Shutting down inactive peer_server:",
                       self.peer_servers[key].name,
                       self.peer_servers[key].server_id,
                       'Last Broadcast time:',
                       str(time.time() -float(self.peer_servers[key].last_broadcast_time)),
                       'seconds ago')
                self.peer_servers[key].close()
                #del self.peer_servers[key]
        return # temporary disable
        self.__periodic_maintenance__()
#        for peer in self.client_roles:
#            for role in self.client_roles[peer]:
#                try: 
#                    if (time-time()-self.client_roles[peer][role])>self.role_timeouts[role]:
#                        del self.client_roles[peer][role]
#                except KeyError: pass
    def xstatus(self):
        stat='<Clients>'
        try:
            statd=''
            for client in self.clients:
                statd += '<Client>'
                statd += '<Name>'
                statd += socket.gethostbyaddr(client.split(":")[0])[0]
                statd += '</Name>'
                statd += '<IP>'
                statd += client
                statd += '</IP>'
                statd += '<Referer>'
                statd += (self.clients[client])['referer']
                statd += '</Referer>'
                statd += '<LastConnect>'
                statd += str(round(-(self.clients[client])['lastConnect']
                                + time.time()))
                statd += '</LastConnect>'
                statd += '</Client>'
            stat+=statd
        except:
            stat+='<Updating></Updating>'
        stat+='</Clients>'
        return stat
    

    def add_peer_server(self, ping_payload):
        """
        Adds a peer server to the the Connection Manager for the main server.
        """
        if DEBUG: print "In class ClientManager, function, add_peer_server()"
        if ping_payload != None:
            new_peer = PeerServer()
            new_peer.is_open_connection = False
            new_peer.server = self.server
            new_peer.connection_manager = self
            new_peer.open_connection(ping_payload)
        else:
            raise
 

    def add_data_gui_server(self, commands=None):
        """
        Adds a script server to the the Connection Manager for the main server.
        This is a barebones server whose only purpose is to execute little
        scripts that cannot be allowed to hog resources of the main server.
        There should be no more than ~16 script servers
        """
        if len(self.data_gui_servers) > 0:
            return
        if DEBUG: print "In class ConnectionManager, function, add_data_gui_server()"
        new_data_gui_server = DataGUIServer()
        new_data_gui_server.is_open_connection = False
        new_data_gui_server.server = self.server
        new_data_gui_server.connection_manager = self
        new_data_gui_server.open_connection()

    def add_script_server(self, commands=None):
        """
        Adds a script server to the the Connection Manager for the main server.
        This is a barebones server whose only purpose is to execute little
        scripts that cannot be allowed to hog resources of the main server.
        There should be no more than ~16 script servers
        """
        if DEBUG: print "In class ConnectionManager, function, add_script_server()"
        new_script_server = ScriptServer()
        new_script_server.is_open_connection = False
        new_script_server.server = self.server
        new_script_server.connection_manager = self
        if commands != None:
            new_script_server.commands_when_ready = commands
        new_script_server.open_connection()
        
    def command_script_server(self, commands=None):
        for key in self.script_servers.keys():
            if DEBUG: print "in use:", self.script_servers[key].in_use
            if self.script_servers[key].in_use == False:
                if commands != None:
                    self.script_servers[key].in_use = True
                    self.script_servers[key].commands_when_ready = commands
                    script_information = {'script_body':commands['script_body'],
                                          'context': commands['context']}
                    self.server.send(simplejson.dumps(script_information), self.script_servers[key])
                    return
        
        #Past here, all script servers are in use
        global MAX_SCRIPT_SERVERS
        if len(self.script_servers) < MAX_SCRIPT_SERVERS:
            self.add_script_server(commands)
        else:
            #print "Too Many Script_Servers. Killing oldest and using its resources."
            pdb.set_trace()
            pass
            
        return None      
            
            
    def catch_ping(self, ping_payload):
        if not self.is_known_server(ping_payload):
            #Not known server. Add a new PeerServer
            #foreign_address = "ws://" + str(ping_payload['server_ip']) + ":" + str(ping_payload['server_port'])
            self.add_peer_server(ping_payload)
        
        
    def send(self,data, address,isBinary=False):
        #address can be the following: shadow, analysis, ip, ip:port styrings and numbers, peer_server object, ''ws://localhost:8086''
        if DEBUG: print "In class ConnectionManager, function, send()"
        if address.__class__.__name__ == 'ScriptServer':
            address.protocol.sendMessage(data,isBinary)
            if DEBUG: print "Just Sent to ScriptServer:"
            if DEBUG and len(data) < 10000: print data
            return True
        if address.__class__.__name__ == 'DataGUIServer':
            address.protocol.sendMessage(data,isBinary)
            if DEBUG: print "Just Sent to DataGUIServer:"
            #if DEBUG and not isBinary and len(data) < 10000: print data
            return True
        if address.__class__.__name__ == 'WebSocketConnection':
            address.protocol.sendMessage(data,isBinary)
            if DEBUG:
                print "Just Sent to a default WebSocketConnection:"
                if hasattr(data,'keys'): print data.keys()
            if DEBUG and not isBinary and len(data) < 10000: print data
            return True
        if address.__class__.__name__ == 'PeerServer':
            address.protocol.sendMessage(data,isBinary)
            if DEBUG: print "Just Sent to PeerServer,", address, address.ip, address.id, ":"
            if DEBUG and len(data) < 10000: print data
            return True
        if address == 'active_parser':
            if DEBUG: print "-----------act---------"
            for key in self.peer_servers:
                if self.peer_servers[key].ip == self.server.active_parser_ip:
                    self.peer_servers[key].protocol.sendMessage(data,isBinary)
                    if DEBUG: print "Just Sent to active_parser:"
                    if DEBUG and len(data) < 10000: print data
                    return True
        # Only thing left is assuming that the address is an ip address.
        #try:
        #    IP(address)
        #except ValueError:
        #    raise
            #Invalid IP address - NB: "4" is a valid ip address, the notation is that it pads 0's
        #address is a valid ip address now.
        for peer in self.peer_servers.keys():
            if self.peer_servers[peer].ip == address:
                p = self.peer_servers[peer].protocol
                p.sendMessage(data,isBinary)
                #p.sendMessage(simplejson.dumps({'Not_Command_text_message':'hi','terminator':'die'}, ensure_ascii = False).encode('utf8'))
                if not isBinary:
                    if DEBUG: print "Just Sent to " + address + ":"
                    if DEBUG and len(data) < 10000: print data
                else:
                    if DEBUG: print "Just Sent (binary) to " + address + ":"
                    d = msgpack.unpackb(data)
                    if 'databomb' in d:
                        if DEBUG: print "-A lot of databomb data here-"
                    else:
                        if DEBUG: print "Just Sent to " + address + ":"
                        if DEBUG and len(d) < 10000: print d
                return True
        for ss in self.script_servers.keys():
            if self.script_servers[ss].ip == address:
                p = self.script_servers[ss].protocol
                if DEBUG: print p.sendMessage(data,isBinary)
                if DEBUG: print "Just Sent to " + address + ":"
                if DEBUG and len(data) < 10000: print data
                return True
        if DEBUG: print "Not Sent!"
        return False
        
    def is_known_server(self,ping_payload):
        #pdb.set_trace()
        #print self.peer_servers
        #if DEBUG: print "in isKnownServer"
        #print payload['server_id']
        found = False
        '''
        if ping_payload['server_ip'] == '10.1.1.178':
            return True
        if ping_payload['server_ip'] == '10.1.1.124':
            return True
        if ping_payload['server_ip'] == '10.1.1.136':
            return True
        
        if DEBUG: print "Peer Servers:"
        for key in self.peer_servers:
            pass
            if DEBUG: print self.peer_servers[key].ip:
        '''
        
        for key in self.peer_servers:
            #print self.peer_servers[key].ip
            '''
            directory = dir(self.peer_servers[key])
            for d, v in enumerate(directory):
                print directory[d], getattr(self.peer_servers[key],str(directory[d]))
            '''
            if self.peer_servers[key].ip == ping_payload['server_ip']:
                found = True
                '''
                There will be two peer server instances for this server.
                (both client and server is a peer_server instance)
                '''
                self.peer_servers[key].server_id = ping_payload['server_id']
                self.peer_servers[key].last_broadcast_time = time.time()
                self.peer_servers[key].server_time = ping_payload['server_time']
                self.peer_servers[key].ping_payload = ping_payload
                if self.peer_servers[key].is_open_connection == False:
                    self.peer_servers[key].reconnect(ping_payload)
                #if DEBUG: print "Known Server"
        #if DEBUG: print "Unknown Server"
        return found
        
    def announce_data_listener(self,params):
        if DEBUG: print "class connection_manager, function announce_data_listener"
        #pdb.set_trace() #commend out by JZ on 10/3/14
        return
        announcement = {"IDLSocket_ResponseFunction":"announce_listener",
                        #"shotnumber":"",
                        "ip_address":'10.1.1.124',
                        "server_id":self.server.id,
                        "instrument_of_interest":"ccd_camera",
                        "terminator":"die"}
        announcement.update(params)
        for i in self.connections:
            #pdb.set_trace()
            #self.connections[i].sendMessage(simplejson.dumps(announcement))
            self.connections[i].sendMessage(simplejson.dumps(announcement),isBinary=False)
        
        
class GlabClient(XTSM_Server_Objects.XTSM_Server_Object):
    """
    a generic class for clients
    """
    def __init__(self, params={}):
        for key in params:
            setattr(self,key,params[key])
        self.id = str(uuid.uuid1())
        #self.id = str(uuid.uuid4())
        self.protocol_id = None
        self.time_of_creation = time.time()
        self.last_connection_time = None
        self.ip = None
        self.is_open_connection = False
        self.port = None
        
    def __periodic_maintenance__(self):
        """
        flushes old connections and relations
        """
        pass
    
    def log_communication(self,request):
        """
        logs a request
        """
        pass

    def on_close(self):
       self.is_open_connection = False
       
    
    def close(self):
       if DEBUG: print "Shutting down connection:", self.protocol.connection.ip
       self.protocol.sendClose()
       self.protocol.transport.loseConnection()

    def on_open(self):  
        self.last_broadcast_time = time.time()
        pass               
               
    def catch_msgpack_payload(self, payload_, protocol):
        if DEBUG: print "class GlabClient, func catch_msgpack_payload"
        try:
            payload = msgpack.unpackb(payload_)
        except:
            pdb.set_trace()
            raise
        
                    
        SC = commands.SocketCommand(params = payload,
                           request = protocol.request,
                           command_library = self.server.command_library)
        try:
            #self.commandQueue.add(SC)
            #pdb.set_trace()
            if DEBUG: print "adding socket command"
            self.server.command_queue.add(SC)
            if DEBUG: print "added socket command"
        #except AttributeError:
            #    self.commandQueue=CommandQueue(SC)
        except:
            protocol.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")
            raise
        
        #print "class GlabClient, func catch_msgpack_payload - End"
        #print payload

    def catch_json_payload(self, payload_, protocol):
        # we will treat incoming websocket text using the same commandlibrary as HTTP        
        # but expect incoming messages to be JSON data key-value pairs
        try:
            payload = simplejson.loads(payload_)
        except simplejson.JSONDecodeError:
            if DEBUG: print "JSONDecodeError"
            if DEBUG and len(payload) < 10000: print payload
            msg = {'Not_Command_text_message':"The server is expecting JSON, not simple text",'terminator':'die'}
            protocol.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
            if DEBUG: print "The server is expecting JSON, not simple text"
            pdb.set_trace()
            if DEBUG: print payload_
            protocol.transport.loseConnection()
            return False
        # if someone on this network has broadcast a shotnumber change, update the shotnumber in
        # the server's data contexts under _running_shotnumber
        #pdb.set_trace()  
        if 'Not_Command_text_message' in payload:
            if DEBUG: print payload['Not_Command_text_message']
            return
            
        if DEBUG: print "payload:"
        if DEBUG and not len(payload) < 10000: print payload

        '''
        if hasattr(payload, "shotnumber"):
            #pdb.set_trace() # need to test the below
            for dc in self.parent.dataContexts:
                dc['_running_shotnumber']=payload['shotnumber']
        '''
        payload.update({'request':protocol.request})
        #payload.update({'protocol':protocol})
        payload.update({'socket_type':"Websocket"})
        if not payload.has_key('IDLSocket_ResponseFunction'):
            if protocol.request != None:
                #if DEBUG: print "Error No command included in request", payload.keys()
                msg = {'Not_Command_text_message':'No command included in request.','terminator':'die'}
                if protocol.request.has_key("write"):
                    protocol.request["write"](simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
                else:                
                    protocol.transport.write(simplejson.dumps(msg, ensure_ascii = False).encode('utf8'))
                    protocol.transport.loseConnection()
            return None
            
        SC = commands.SocketCommand(params = payload,
                           request = protocol.request,
                           command_library = self.server.command_library)
        try:
            #self.commandQueue.add(SC)
            self.server.command_queue.add(SC)
        #except AttributeError:
            #    self.commandQueue=CommandQueue(SC)
        except:
            protocol.sendMessage("{'server_console':'Failed to insert SocketCommand in Queue, reason unknown'}")
            raise  

               
class TCPConnection(GlabClient):
    def __init__(self):
        ConnectionManager.GlabClient.__init__(self)
        if DEBUG: print "in TCPConnection class, __init__()"
    pass    
   
class WebSocketConnection(GlabClient):
    """
    class to hold data regarding other XTSM servers on network
    when added open web socket. server connects to this peer server.
    Others open with TCP
    """
    
    def __init__(self):
        GlabClient.__init__(self)
        if DEBUG: print "in WebSocketConnection class, __init__()"
        self.server_id = None
        self.name = None
        self.ping_payload = None
        self.last_broadcast_time = 0
        self.protocol = None
        #pdb.set_trace()
    
    def open_connection(self, address):
       self.is_open_connection = True
       self.server_time = time.time()
       self.last_broadcast_time = time.time()

       wsClientFactory = WebSocketClientFactory(address, debug = True)
       wsClientFactory.setProtocolOptions(failByDrop=False)
       wsClientFactory.protocol = WSClientProtocol
       wsClientFactory.connection_manager = self.server.connection_manager
       wsClientFactory.connection = self
       connectWS(wsClientFactory)
        

    def on_message(self, payload, isBinary, protocol):
        if isBinary:
            self.catch_msgpack_payload(payload, protocol)
        else:
            self.catch_json_payload(payload, protocol)
        
    def on_open(self):
        if DEBUG: print "class WebSocketConnection, func on_open. self.id = " + str(self.id)
        self.is_open_connection = True  
        self.last_broadcast_time = time.time()
        self.connection_manager.default_websocket_connections.update({self.id:self})
        self.server.connection_manager.connectLog(self) 
   
class PeerServer(GlabClient):
    """
    class to hold data regarding other XTSM servers on network
    when added open web socket. server connects to this peer server.
    Others open with TCP
    """
    
    def __init__(self):
        GlabClient.__init__(self)
        if DEBUG: print "in PeerServer class, __init__()"
        self.server_id = None
        self.name = None
        self.ping_payload = None
        self.last_broadcast_time = 0
        self.protocol = None
        #pdb.set_trace()
        
    def reconnect(self, ping_payload):
       self.open_connection(ping_payload)
    
    def open_connection(self, ping_payload):
       self.is_open_connection = True
       self.server_id = ping_payload['server_id']
       self.server_name = ping_payload['server_name']
       self.ip = ping_payload['server_ip']
       self.port = ping_payload['server_port']
       try:
           self.server_id_node = ping_payload['server_id_node']
       except:
           pass
       self.server_time = ping_payload['server_time']
       self.last_broadcast_time = time.time()
       # Connect to the peer as a Client
       address = "ws://" + ping_payload['server_ip'] + ":" + ping_payload['server_port']
       #print address
       wsClientFactory = WebSocketClientFactory(address, debug = True)
       wsClientFactory.setProtocolOptions(failByDrop=False)
       wsClientFactory.protocol = WSClientProtocol
       wsClientFactory.connection_manager = self.server.connection_manager
       wsClientFactory.connection = self
       connectWS(wsClientFactory)
        

    def on_message(self, payload, isBinary, protocol):
        if isBinary:
            self.catch_msgpack_payload(payload, protocol)
        else:
            self.catch_json_payload(payload, protocol)
        
    def on_open(self):
        self.is_open_connection = True  
        self.last_broadcast_time = time.time()
        self.connection_manager.peer_servers.update({self.id:self})
        if DEBUG: print "class PeerServer, func on_open. self.id = " + str(self.id)
        self.server.connection_manager.connectLog(self) 
        if DEBUG: print "class PeerServer"
        
       
class ScriptServer(GlabClient):
    def __init__(self):
        GlabClient.__init__(self)
        self.output_from_script = None
        self.in_use = True # Keep as true on initialization so that the
        #server doesn't accidentally  try to hand this server off to two
        #processes when it was just first created.
        if DEBUG: print "in ScriptServer class, __init__()"
    pass
    
    def open_connection(self):
        new_port = 9000 + len(self.connection_manager.script_servers)
        if DEBUG: print "About to open"
        script_server_path = os.path.abspath(script_server.__file__)
        subprocess.Popen(['C:\\Python27\\python.exe',script_server_path]+['localhost',str(new_port)])
        if DEBUG: print "Done Opening"            
        # Connect to the new_script_server
        address = 'ws://localhost:'+str(new_port)
        wsClientFactory = WebSocketClientFactory(address, debug = True)
        wsClientFactory.setProtocolOptions(failByDrop=False)
        wsClientFactory.protocol = WSClientProtocol
        wsClientFactory.connection_manager = self.connection_manager
        wsClientFactory.connection = self
        connectWS(wsClientFactory)  
        self.connection_manager.connectLog(self)  
        self.last_broadcast_time = time.time()
        pass
    
    def on_message(self, payload, isBinary, protocol):
        #pdb.set_trace()
        if isBinary:
            pass
            if DEBUG: print "Binary message received: {0} bytes"#, payload
        else:
            #payload = payload.decode('utf8')
            if DEBUG: print "Text message received in Client ws protocol:",payload
            '''
            self.output_from_script = payload
            self.last_connection_time = None
            if DEBUG: print "Script Finished. Payload:"
            if DEBUG: print payload
            #print "Waiting for server to take my payload and then set script_server.in_use = False"
            if self.output_from_script == '"Script Server Ready!"':
                self.output_from_script = None
                self.in_use = False
                if hasattr(self,'callback_function'):
                    self.in_use = True
                    self.callback_function(self)
            '''
            #script finished. Message is the data.
            data = simplejson.loads(payload)
            self.commands_when_ready['callback_function'](data)

    def on_open(self):
        self.in_use = True
        self.is_open_connection = True
        self.connection_manager.script_servers.update({self.id:self})
        global MAX_SCRIPT_SERVERS
        if len(self.connection_manager.script_servers) < MAX_SCRIPT_SERVERS:
            script_command = commands.ServerCommand(self.server, self.connection_manager.add_script_server)
            reactor.callLater(0.1, self.server.command_queue.add, script_command)
        self.server.connection_manager.connectLog(self)  
        #self.protocol.sendMessage("output_from_script = 'Script Server Ready!'")
        self.last_connection_time = None
        self.output_from_script = None
        self.in_use = False
        if DEBUG: print 'Script Server Ready!'
        if hasattr(self,'commands_when_ready'):
            self.in_use = True
            script_information = {'script_body':self.commands_when_ready['script_body'],
                                  'context': self.commands_when_ready['context']}
            self.server.send(simplejson.dumps(script_information), self)
        
        
class DataGUIServer(GlabClient):
    def __init__(self):
        GlabClient.__init__(self)
        self.output_from_script = None
        self.in_use = True # Keep as true on initialization so that the
        #server doesn't accidentally  try to hand this server off to two
        #processes when it was just first created.
        if DEBUG: print "in DataGUIServer class, __init__()"
    pass
    
    def open_connection(self):
        new_port = 9100 + len(self.connection_manager.data_gui_servers)
        if DEBUG: print "About to open"
        data_gui_path = os.path.abspath(data_gui.__file__)
        subprocess.Popen(['C:\\Python27\\python.exe',data_gui_path]+['localhost',str(new_port)])
        if DEBUG: print "Done Opening"            
        # Connect to the data_gui_
        address = 'ws://localhost:'+str(new_port)
        wsClientFactory = WebSocketClientFactory(address, debug = True)
        wsClientFactory.setProtocolOptions(failByDrop=False)
        wsClientFactory.protocol = WSClientProtocol
        wsClientFactory.connection_manager = self.connection_manager
        wsClientFactory.connection = self
        #connectWS(wsClientFactory)  
        reactor.callLater(1,connectWS,wsClientFactory)
        self.connection_manager.connectLog(self)  
        self.last_broadcast_time = time.time()
        pass
    
    def on_message(self, payload, isBinary, protocol):
        #pdb.set_trace()
        if isBinary:
            pass
            if DEBUG: print "Binary message received: {0} bytes"#, payload
        else:
            #payload = payload.decode('utf8')
            if DEBUG: print "Text message received in Client ws protocol:",payload

    def on_open(self):
        self.in_use = True
        self.is_open_connection = True
        self.connection_manager.data_gui_servers.update({self.id:self})
        self.server.connection_manager.connectLog(self)  
        self.last_connection_time = None
        self.in_use = False
        if DEBUG: print 'In class DataGUIServer, func on_open'
        
     
        
class GlabServerFactory(protocol.Factory):
    """
    creates the 'factory' class that generates protocols which are executed
    in response to incoming HTTP requests
    """

    def associateCommandQueue(self,command_queue):
        self.command_queue = command_queue
    def associateConnectionManager(self,connection_manager):
        self.connection_manager = connection_manager
    def xstatus(self):
        stat=""
        if hasattr(self,'openConnections'):
            stat+="<Connections>"
            try:            
                for connection in self.openConnections:
                    statd=""
                    statd+="<Connection name='"+connection+"'>"
                    statd+="<From><Origin>"+self.openConnections[connection].request['origin']+"</Origin>"
                    statd+="<Referer>"+self.openConnections[connection].request['referer']+"</Referer>"
                    statd+="</From>"
                    statd+="<TimeElapsed>"+str(round(time.time()-self.openConnections[connection].request['ctime']))+"</TimeElapsed>"
                    if self.openConnections[connection].params.has_key('IDLSocket_ResponseFunction'):
                        statd+="<Command>"+self.openConnections[connection].params['IDLSocket_ResponseFunction']+"</Command>"
                    statd+="</Connection>"
                    stat+=statd
            except:
                stat+="<Updating></Updating>"
            stat+="</Connections>"
        return stat

class Keyboard_Input(basic.LineReceiver):
    """
    Keyboard input protocol - for simultaneous input of python commands
    and browsing of server objects while the server is running
    """
    from os import linesep as delimiter # doesn't seem to work
    if os.name=='nt': delimiter="\n"
    def __init__(self):
        self.pre_e=colorama.Style.BRIGHT+ colorama.Back.RED+colorama.Fore.WHITE
        self.post_e=colorama.Fore.RESET+colorama.Back.RESET+colorama.Style.RESET_ALL
#        self.setRawMode()
    def connectionMade(self):
        pass
    def lineReceived(self, line):
        """
        called when a line of input received - executes and prints result
        or passes error message to console
        """
        rbuffer = StringIO()
        po=sys.stdout
        sys.stdout = rbuffer
        err=False
        if not hasattr(self,"dc"):
            self.dc={"self":self.server}
        print "dc:", self.dc
        try: exec(line,self.dc)
        except Exception as e: err=e
        except KeyboardInterrupt : pass
        # remove backeffect on dictionary
        if self.dc.has_key('__builtins__'): 
            del self.dc['__builtins__']
        # update data context
        # remember to restore the original stdout!
        sys.stdout = po
        print '>u> '+line
        if err: out = self.pre_e+str(e)+self.post_e
        else: out = rbuffer.getvalue()
        if out!="": print '>s> ' + out
    def rawDataReceived(self,data):
        print data

class Mediated_StdOut(StringIO):
    """
    class that catches all output, streams into one of several contextual buffers 
    (determined from where the print statement originated)
    and handles printing to consoles
    """
    passthrough=False
    class contextual_buffer():
        """
        a buffer for output separated by context
        """
        def __init__(self,params={}):
            default_params={"lines_retained":20,"linestack":[".\n" for a in range(20)],
                            "prompt":"","display_name":"","bg":colorama.Back.WHITE,
                            "col":colorama.Fore.BLACK,"width":140}
            default_params.update(params)
            for it in default_params: setattr(self,it,default_params[it])
            self.context_col={}
            self.cols=[getattr(colorama.Fore,a) for a in ["BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN"]]
            self.col_inc=0
            self.line_term=colorama.Fore.RESET + colorama.Back.RESET + colorama.Style.RESET_ALL
            self.textwrapper = textwrap.TextWrapper()
        def write(self,s):
            self.textwrapper.width=110
            outs=self.textwrapper.wrap(str(s))
            if self.col=="contextualize":
                col=self.color_by_context(s)
            else: col=self.col
            for out in outs:
                self.linestack.pop(0)
                self.linestack.append(col+str(out).strip()+self.line_term)      
        def dump(self,stream):
            stream.write("-"*10+self.display_name+"-"*10+"\n")
            for a in range(self.lines_retained):
                if self.linestack[a]!="\n": 
                    stream.write(self.linestack[a])
                    if self.linestack[a][-1]!="\n": stream.write("\n")
            stream.write(self.prompt)
        def color_by_context(self,s):
            try: col=self.context_col[inspect.stack()[3][3]]
            except KeyError: 
                self.context_col.update({inspect.stack()[3][3]:self.cols[self.col_inc % len(self.cols)]})
                self.col_inc+=1
                col=self.context_col[inspect.stack()[3][3]]
            return col

    default_params={"prompt":"","display_name":"default","bg":colorama.Back.WHITE,"col":"contextualize"}
    received_params={"prompt":">u> ","display_name":"console","bg":colorama.Back.WHITE,"col":colorama.Fore.BLACK}
    buffers={"default":contextual_buffer(default_params),
             "lineReceived":contextual_buffer(received_params)}
    def write(self,s):
        """
        write routine called by print statements
        """
        if self.passthrough:
            sys.stdout=sys.__stdout__
            print s
            sys.stdout=sys.self
            return            
        cb=self._determine_context_buffer(s)
        cb.write(s)
        self.dump()
        
    def dump(self):
        """
        prints all buffers to console
        """
#        self.partial_in=""
#        for line in sys.stdin: 
#        self.partial_in+=sys.stdin.read(1)
        sys.stdout = sys.__stdout__
        os.system('cls')
        for cb in self.buffers.values():
            cb.dump(sys.stdout)
        sys.stdout = self
        
    def _determine_context_buffer(self,s):
        """
        tries to determine a context from the print statement's calling routine 
        """
        try: return self.buffers[inspect.stack()[2][3]]
        except KeyError: return self.buffers['default']
        
    def __del__(self):
        self.passthrough=True
        os.system('cls')
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__



class GlabPythonManager():
    """
    This is the top-level object; it manages queueing the TCP socket commands,
    and other things as time goes on...
    """
    def __init__(self):
        # intercept print statements
        #sys.stdout = Mediated_StdOut()
        
        if DEBUG: print "debug: GlabPythonManager(), __init__"
        # general identifiers
        self.id = str(uuid.uuid1())
        self.hostid = platform.node()# The computer’s network name

        # create a TCP socket listener (called a factory by twisted)
        self.listener = GlabServerFactory()
        self.listener.openConnections = {}
        self.listener.parent = self

        # tell the twisted reactor what port to listen on and
        # which factory to use for response protocols
        global port
        global wsport        
        self.reactor = reactor
        self.task = task
        try:
            reactor.listenTCP(port, self.listener)
        except error.CannotListenError:
            time.sleep(10)
            reactor.listenTCP(port, self.listener)
        #reactor.addSystemEventTrigger('before','shutdown',server_shutdown)


        # create a Command Queue, Client Manager, and Default Data Context
        self.command_queue = commands.CommandQueue(self)
        self.command_library = commands.CommandLibrary(self)
        self.connection_manager = ConnectionManager(self)
        self.dataContexts = {}
        self.server = self
        self.ip = None
        self.instruments = {}
        self.pxi_time_server_time = 0
        self.active_parser_ip = None
        self.active_parser_port = 0
        self.pxi_time = 0
        self.ALL_DATABOMBS = {}
        self.server.databomblist=[]
        self.databombs_for_data_gui = {}#ALL DATABOMBS
        #if self.ALL_DATABOMBS.len
        
        # associate the CommandProtocol as a response method on that socket
        self.listener.protocol = CommandProtocol

        # associate the Command Queue and ClienManager with the socket listener
        self.listener.associateCommandQueue(self.command_queue)
        self.listener.associateConnectionManager(self.connection_manager)
        
        # create a periodic command queue execution
        self.queueCommand = task.LoopingCall(self.command_queue.popexecute)
        self.queueCommand.start(0.03)
        self.initdisplay()

        
        # setup the udp broadcast for peer discovery
        self.multicast = reactor.listenMulticast(udpbport, 
                                                 MulticastProtocol(),
                                                 listenMultiple=True)
        self.multicast.protocol.server = self 
        

        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)
        #self.clientManager.announce_data_listener(self.data_listener_manager.listeners[i],'ccd_image','rb_analysis')
        
        #self.execu = task.LoopingCall(self.commandLibrary.execute_script)
        #self.period = 5.0
        #self.execu.start(self.period)
        
        self.server_ping_period = 5.0 
        reactor.callWhenRunning(self._init_when_running)

        #Moved into Client Manager CP
        # setup the websocket services
        #self.wsfactory = WebSocketServerFactory("ws://localhost:" + 
        #                                        str(wsport),
        #                                        debug=False)
        #self.wsfactory.setProtocolOptions(failByDrop=False)
        #self.wsfactory.parent = self
        #self.wsfactory.protocol = WSServerProtocol
        #self.wsfactory.protocol.commandQueue = self.commandQueue
        #self.wsfactory.protocol.clientManager = self.clientManager
        

        # run initialization script specific to this machine
        try: 
            init_code = server_initializations.initializations[uuid.getnode()]
            if init_code:
                exec(init_code) in globals(), locals()
        except KeyError:
            if DEBUG: print ("WARNING:: no supplementary server_initialization data",
                   "present for this machine")

        self.keyboard=Keyboard_Input()
        self.keyboard.server=self
        stdio.StandardIO(self.keyboard)

        #Moved into Client Manager CP
        # listen on standard TCP port
        #self.laud = reactor.listenTCP(wsport, self.wsfactory)
        
        #Testing CP 08/2014
        #pdb.set_trace()
        #self.client_factory = WebSocketClientFactory("ws://10.1.1.178:8084", debug = True)
        #self.client_factory.protocol = WSClientProtocol
        #connectWS(self.client_factory)
        
        
        # the display has been disabled due to conflicts and hangs
        #self.refreshdisplay=task.LoopingCall(self.display.refresh)
        #self.refreshdisplay.start(0.5)


    def _init_when_running(self):
        if DEBUG: print "server running"
        self.server.id_node = uuid.getnode()
        self.server.ip = socket.gethostbyname(socket.gethostname())
        self.server.name = socket.gethostname()
        dc_name = 'default:'+str(self.server.ip)
        dc = sync.DataContext(dc_name, self.server)
        self.dataContexts.update({dc_name:dc})
        self.command_queue.add(commands.ServerCommand(self.server, self.connection_manager.add_script_server))
        self.command_queue.add(commands.ServerCommand(self.server, self.connection_manager.add_data_gui_server))
        self.command_queue.add(commands.ServerCommand(self.server, self.server_ping))
        self.ping_data={"server_id":self.id,
                            "server_name":self.name,
                            "server_ip":self.ip,
                            "server_port":str(wsport),
                            "server_id_node":self.id_node,
                            "server_ping":"ping!"}
        self.ping_data.update({"server_time":time.time()})
        ps = PeerServer()
        ps.server = self.server
        ps.connection_manager = self.server.connection_manager
        ps.open_connection(self.ping_data)
        if DEBUG: print ('Listening on ports:',
               str(port), '(standard HTTP),',
               str(wsport) + ' (websocket)',
               str(udpbport) + ' (udp port)')

    def run(self):
        """
        Run the server
        """
        reactor.run()

    def init_GPIB(self, device_address=7):
        '''
        if ip address is not found, run the program "GPIB Configuator" and look
        at ip. Or run "NetFinder" from Prologix
        '''
        self.GPIB_adapter = GPIB_control.PrologixGpibEthernet('10.1.1.113')
        
        read_timeout = 1.0  
        if DEBUG: print "Setting adapter read timeout to %f seconds" % read_timeout
        self.GPIB_adapter.settimeout(read_timeout)
        
        gpib_address = int(device_address)#Scope over Rb exp tektronix 460A
        #gpib_address = int(7)#Scope over Rb exp tektronix 460A
        if DEBUG: print "Using device GPIB address of %d" % gpib_address
        self.GPIB_device = GPIB_control.GpibDevice(self.GPIB_adapter, gpib_address)
        if DEBUG: print "Finished initialization of GPIB controller"
        
        
    
    
    def get_scope_field(self,
                        q1="Data:Source CH1",
                        q2="Data:Encdg: ASCII",
                        #q2="Data:Encdg: SRIbinary",#least significant byte first, signed int
                        q3="Data:Width 2",
                        q4="Data:Start 1",
                        q5="Data:Stop 500",
                        #q6="RS232:BAUD 19200",
                        q7="wfmpre?",
                        #q12="wavfrm?",
                        #q8="*OPC?",
                        q9="curve?",
                        #q10="*OPC?",
                        #q11="*WAI",
                        filename='C:\\Users\\Gemelke_Lab\\Documents\\ScopeTrace\\NewScopeTrace',
                        tdiv=10,
                        vdiv=10,
                        fit='NoFit'):
        '''
        This function pull trace back from Textronix TDS460A. 
        fit= 'SPG', fit with single peak gaussian function, return peak hight, width, and area under peak;
        fit= 'DPG', fit with double peak gaussian function, return peak hight, width, and area under peak;
        tdiv timedivision in ms; vdiv voltage perdivision in mV.
        '''
    
        e1 = time.time()
        if not hasattr(self,'GPIB_device'):
            if DEBUG: print "GPIB device not ready"
            return
     
        self.GPIB_device.write(q1)
#        e2 = time.time()
#        print 'q1 takes', e2-e1
        
        self.GPIB_device.write(q2)
#        e3 = time.time()
#        print 'q2 takes', e3-e2
        
        self.GPIB_device.write(q3)
#        e4 = time.time()
#        print 'q3 takes', e4-e3
        
        self.GPIB_device.write(q4)
#        e5 = time.time()
#        print 'q4 takes', e5-e4       
        
        self.GPIB_device.write(q5)
#        e6 = time.time()
#        print 'q5 takes', e6-e5
        
#        self.GPIB_device.write(q6)
#        e7 = time.time()
#        print 'q6 takes', e7-e6    
        
        response1=self.GPIB_device.converse(q7)
        response2=self.GPIB_device.converse(q9)
        e2 = time.time()
#        print 'q7,q9 takes', e8-e7
        #print response2


        ystr = response2["curve?"].split(',')
        ystr[0]= ystr[0].split(' ')[1] # separate the word 'CURV' in the first element

        #if DEBUG: print "Data:", ystr
        
        
#        if sys.byteorder != "little": # What does this line means, what is 'little'????
#            print "Error: byte order on this computer not expected. Expected python to be little"
#            pdb.set_trace()

        print "Scope communication took", e2-e1,"s"
        #pdb.set_trace()
        ydata=np.array(ystr,dtype=np.float)

        xdata=np.multiply(np.arange(len(ydata),dtype=np.float),(tdiv*10.0)/500.0) #xdata converted for 10ms/div scale
    
        ydata=np.multiply(ydata,(vdiv*5.0)/2.**15.) #ydata converted for 5mV/div scale, five devisions corresponding to 0~2**15
    
        if fit=='NoFit':
            fig,ax=plt.subplots()
            ax.plot(xdata,ydata)
            ax.set_ylabel('Voltage (mV)')
            ax.set_xlabel('Time (ms)')
            ax.grid(True)
            ax.axis([0,tdiv*10,-vdiv*4.,vdiv*4.])
            ax.xaxis.set_ticks(np.linspace(0,10*tdiv,11))
            plt.show(block=False)
            plt.savefig(filename)
            print "Figure saved. No fitting is performed."
        
        elif fit == 'MolassesTOF':
            def molasses_tof(x,offset,t,a,c):
                '''
                t= kb T /M ; a, amplitude; c, center of peak; offset
                '''
                SIG0=10.**-3
                G=9.8
                T0 = 94.* 10**-3
                return offset + a/np.sqrt(SIG0**2 + t * ((x-c)/1000.)**2) * np.exp(-(G*(T0**2 - ((x-c)/1000.)**2)**2/(8*(SIG0**2+t* ((x-c)/1000.)**2))))
                
            fig,ax=plt.subplots()
            ax.plot(xdata,ydata)
            
            #popt,popv = curve_fit(func, xdata, ydata, (-12.,12.,15.,25.,6.,5.,50.))
            popt,popv = curve_fit(molasses_tof, xdata, ydata, (-32,10.**-4,1,40.))  
            fit = molasses_tof(xdata, *popt)
            ax.plot(xdata, fit, 'r--')
            ax.text(0, 2*vdiv,'Fitting: Single Gaussian. \n'
                    + 'temp = '+str(popt[1]*0.0105)+' K ;\n amplitude = '+str(popt[2])+' mV ; \n center = '+str(popt[3])+'ms.\n')
            
            ax.set_title('Time of Flight')
            ax.grid(True)
            ax.axis([0,tdiv*10,-vdiv*4.,vdiv*4.]) # set the plot range, [xmin, xmax,ymin,ymax]
            ax.set_ylabel('Log Amp Output Voltage (mV)')
            ax.set_xlabel('Time (ms)')
            plt.show(block=False)
            plt.savefig(filename)
        
            
        
        elif fit=='SPG':
            def gaussian(x,offset,w,a,c):
                
                '''
                Define single peak gaussian function, parameters are listed below:
                x, variable; offset; w, 1/sqrt(e) width ; a amplitude of the peak; c, peak center.
                FWHM=2.3548*w
                '''
                return offset + a*np.exp(-(x-c)**2./(2.*w**2.))
            
            
            fig,ax=plt.subplots()
            ax.plot(xdata,ydata)
            
            #popt,popv = curve_fit(func, xdata, ydata, (-12.,12.,15.,25.,6.,5.,50.))
            popt,popv = curve_fit(gaussian, xdata, ydata, (-15,10.,60.,50.))  
            fit = gaussian(xdata, *popt)
            ax.plot(xdata, fit, 'r--')
            ax.text(0, 2*vdiv,'Fitting: Single Gaussian. \n'
                    + 'width = '+str(popt[1])+' ms ;\n amplitude = '+str(popt[2])+' mV ; \n center = '+str(popt[3])+'ms.\n'+'FWHM = '+str(2.3548*popt[1])+'ms.')
            print 'amplitude = ', popt[2], 'mV'
            print 'FWHM = ' , 2.3548*popt[1], 'ms'
            
            ax.set_title('Time of Flight')
            ax.grid(True)
            ax.axis([0,tdiv*10,-vdiv*4.,vdiv*4.]) # set the plot range, [xmin, xmax,ymin,ymax]
            ax.set_ylabel('Log Amp Output Voltage (mV)')
            ax.set_xlabel('Time (ms)')
            plt.show(block=False)
            plt.savefig(filename)
        
        elif fit=='DPG':
            # define the double peak Gaussian fitting function.
            def two_gaussian(x,offset,w1,a1,c1,w2,a2,c2):
                
                '''
                Define two peak gaussian function, parameters are listed below:
                x, variable; offset; w1(w2), 1/sqrt(e) width of first(second) peak; a1(a2) amplitude of the first(second) peak; c1 (c2) peak center.
                FWHM=2.3548*w
                '''
                return offset + a1*np.exp(-(x-c1)**2./(2.*w1**2.)) + a2*np.exp(-(x-c2)**2./(2.*w2**2.))
            
            
            fig,ax=plt.subplots()
            ax.plot(xdata,ydata)
            
            #popt,popv = curve_fit(func, xdata, ydata, (-12.,12.,15.,25.,6.,5.,50.))
            popt,popv = curve_fit(two_gaussian, xdata[15:], ydata[15:], (-10,10.,10.,45,4.,3.,80.)) 
            fit = two_gaussian(xdata[15:], *popt)
            ax.plot(xdata[15:], fit, 'r--')
            ax.axis([0,tdiv*10,-vdiv*4.,vdiv*4.])
            ax.set_title('Time of Flight')
            ax.xaxis.set_ticks(np.linspace(0,10*tdiv,11))
            ax.grid(True)
            ax.text(0, 2*vdiv,'Fitting: Two Gaussian. \n'
                    + 'width1 = '+str(popt[1])+' ms ;\n amplitude1 = '+str(popt[2])+' mV ; \n center1 = '+str(popt[3])+'ms.\n'+ 'FWHM = '+str(2.3548*popt[1])+'ms.')
            ax.text(6*tdiv,2*vdiv,'width2 = '+str(popt[4])+' ms ;\n amplitude2 = '+str(popt[5])+' mV ; \n center2 = '+str(popt[6])+'ms.\n'
                    + 'FWHM = '+str(2.3548*popt[4])+'ms.\n'+'Area: '+str(2.3548*popt[4]*popt[5])+'mV*ms.')
            ax.set_ylabel('Log Amp Output Voltage (mV)')
            ax.set_xlabel('Time (ms)')
            print 'FWHM=', 2.3548*popt[4], 'ms'
            print 'Amplitude=', popt[5], 'mV'
            print 'Area=', 2.3548*popt[4]*popt[5], 'mV*ms'
           
            plt.show(block=False)
            plt.savefig(filename)
           
        # plt.plot(range(len(ydata)),func(range(len(ydata)), 1,1) )
        ydatasave=str(ydata).translate(None,'[]\n')
        savefile=open(filename,'w')
        savefile.write(ydatasave)
        savefile.close()
        print "ASCII data saved"
        print "Figure saved"
        

    def get_spectrum_analyzer_trace(self,filename='C:\\Users\\Gemelke_Lab\\Documents\\SpectrumAnalyzerTrace\\newtrace'):
    
        e1 = time.time()
        if not hasattr(self,'GPIB_device'):
            if DEBUG: print "GPIB device not ready"
            return
        
        q1 = 'FA?'#Specifies start frequency
        q2 = 'FB?'#Specifies stop frequency.
        q3 = 'RL?'#Adjusts the reference level.
        q4 = 'RB?'#Specifies resolution bandwidth
        q5 = 'VB?'#Specifies video bandwidth.
        q6 = 'ST?'#Sweep Time
        q7 = 'LG?'#Log Scale
        q8 = 'AUNITS?'#Specifies amplitude units for input, output, and display
        #q9 = 'TDF B'#Specifies transfer in Binary format
        q9 = 'TDF P'#Specifies transfer in ASCII decimal values in real-number parameter format
        q10 = 'TRA?' # read the trace from analyzer display
        e1 = time.time()
        params = self.GPIB_device.converse([q1,q2,q3,q4,q5,q6,q7,q8,q9])
        e2 = time.time()
        print params
        if DEBUG: print "communication took", e2-e1, "sec"
        
        
        e1 = time.time()
        response = self.GPIB_device.converse([q10])
        e2 = time.time()
        ystr=response['TRA?']
        ydata=np.array([float(s) for s in ystr.split(',')])
        xdata=np.linspace(float(params['FA?']),float(params['FB?']),601)
        
        fig, ax=plt.subplots()
        ax.plot(xdata,ydata)
        ax.set_ylabel(str(params['AUNITS?']))
        ax.set_xlabel('Frequency (Hz)')
        ax.grid(True)
        ax.axis([float(params['FA?']),float(params['FB?']),-100.,0])
        ax.xaxis.set_ticks(np.linspace(float(params['FA?']),float(params['FB?']),11))
        ax.yaxis.set_ticks(np.linspace(-100,0,11))
        ax.text(float(params['FA?']),-10,'Refrence Level:'+str(params['RL?'])+'\n Rsolution Bandwidth:'+str(params['RB?']))
        plt.show(block=False)
        plt.savefig(filename)
        print "Figure saved. No fitting performed."
                
        ydatasave=str(ydata).translate(None,'[]\n')
        savefile=open(filename,'w')
        savefile.write(ydatasave)
        savefile.close()
        print "ASCII data saved"
        print "Figure saved"
        
        if DEBUG: print "communication took", e2-e1, "sec"
        
        
        
       


    def server_shutdown(self):
        port = reactor.listenTCP(portNumber, factory)
        port.stopListening()
        
        connector = reactor.connectTCP(host, port, factory)
        connector.disconnect()

    def announce_data_listener(self,params):
        if DEBUG: print "class server, function announce_data_listener"
        self.connection_manager.announce_data_listener(params)

    def stop(self,dummy=None):
        """
        Exit routine; stops twisted reactor
        """
        if DEBUG: print "Closing Python Manager"
        self.flush_all()
        for key in self.connection_manager.peer_servers.keys():
            self.connection_manager.peer_servers[key].protocol.sendClose()
        for key in self.connection_manager.script_servers.keys():
            self.connection_manager.script_servers[key].protocol.sendClose()
        for key in self.connection_manager.data_gui_servers.keys():
            self.connection_manager.data_gui_servers[key].protocol.sendClose()
        self.close_all()
        #self.connection_manager.laud.loseConnection()
        if DEBUG: print self.connection_manager.is_connections_closed()
        reactor.stop()
        if DEBUG: print "Done"
                
    def flush_all(self):
        for dc in self.dataContexts:
            self.dataContexts[dc].__flush__()

    def close_all(self):
        for dc in self.dataContexts:
            self.dataContexts[dc]._close()

    def server_ping(self):
        """
        sends an identifying message on udp broadcast port
        """
        
        if not hasattr(self,"ping_data"):
            #need to include a list called ping_data - which is updated as needed. by "ping_data fnctions in objects of the server.
        #Nmaely this includes a list of instruments that are attached to the server.
            self.ping_data={"server_id":self.id,
                            "server_name":self.name,
                            "server_ip":self.ip,
                            "server_port":str(wsport),
                            "server_id_node":self.id_node,
                            "server_ping":"ping!"}
        self.ping_data.update({"server_time":time.time()})
        self.multicast.protocol.send(simplejson.dumps(self.ping_data))
        server_command = commands.ServerCommand(self.server, self.server_ping)
        reactor.callLater(self.server_ping_period,
                          self.command_queue.add,
                          server_command)

        
    def is_own_ping_broadcast(self,payload_):
        if payload_['server_id'] == self.id:
            return True
        else:
            return False     
        
        
    def catch_ping(self,payload):
        """
        recieves an identifying message on udp broadcast port from other
        servers, and establishes a list of all other servers
        """    
        
        #print "In GlabPythonManager, pong()"
        #pdb.set_trace()
        #self.peer_servers[payload['server_name']]
        '''
        if self.isOwnPingBroadcast(payload):
            pass
            #print "ignoring own broadcast"
        else:
            #print "ping from a peer server. Giving payload to the Client Manager."
        '''
        self.connection_manager.catch_ping(payload)
            
        #try:
        #    self.clientManager.ping(simplejson.loads(payload))
        #except (AttributeError, KeyError): 
        #    self.clientManager.add_peerServer(simplejson.loads(payload))
        #if not hasattr(self,"server_network"): self.server_network={}
        #self.server_network.update({data['server_id']:data})
            
    def broadcast(self,msg, UDP=False):
        """
        broadcasts a message to all clients connected through the websockets 
        or by udp broadcast (UDP flag) - the latter will reach all listeners
        """
        if DEBUG: print "class GlabPythonManager, function: broadcast"
        if DEBUG and len(msg) < 10000: print "class GlabPythonManager, function: broadcast"
            
        if UDP: 
            self.multicast.protocol.send(msg)
            return
            
        for key, connection in self.connection_manager.default_websocket_connections.iteritems():
            try:
                pass
                self.connection_manager.send(msg,connection)
            except AttributeError:
                if DEBUG: print "Error: Failed to send broadcast"
                pass            
            
        '''
        for key, peer_server in self.connection_manager.peer_servers.iteritems():
            if not peer_server.ip == '10.1.1.112':
                continue
            try:
                self.connection_manager.send(msg,peer_server)
            except AttributeError:
                if DEBUG: print "Error: Failed to send broadcast"
                pass
        '''
        
        
        for key, connection in self.listener.openConnections.iteritems():
            continue
            try:
                if DEBUG: print "broadcasting to the protocol:", connection.ConnectionUID
                connection.transport.write(msg)
            except AttributeError:
                if DEBUG: print "Error: Failed to send broadcast"
                pass
        
        
        #for client in self.wsfactory.openConnections.keys():
        #self.wsfactory.openConnections[client].sendMessage(messagestring)
        
        
    def send(self,data,address,isBinary=False):
        """
        sends data to a specified address, provided as a sting in the form
        ip:port, a server_id string in the form of a uuid1 provided through
        peer discovery, or by role, in the form of a string "role:XXX" where
        XXX is one of:
            
        the send method will be chosen from among existing websocket connection
        if it exists, or establishes one if it does not.  Returns False if
        failed returns data if there was a response
        
        Should look into the client manager for a valid destination.
        If no valid destinations return false
        """
        if DEBUG: print "In class Server, function, send"
        #dest = self.resolve_address(address)
        peer_to_send_message = None
        #or uid in self.clientManager.peer_servers:
        #pdb.set_trace()
        #peer_server = self.clientManager.connections[uid]
        #if peer_server.ip == address:
            #peer_to_send_message = peer_server
        #pdb.set_trace()
        return self.connection_manager.send(data,address,isBinary)
        
        #for client in self.clientManager.connections.keys():
            #pdb.set_trace()
            #self.clientManager.connections[client].sendMessage("------From RBAnalysis---Hi")
    
    def _execute(self, commands):               
        script = commands['script_body']
        context = commands['context']
        old_stdout = sys.stdout
        try:
            capturer = StringIO.StringIO()
            sys.stdout = capturer
            t0=time.time()
            exec script in globals(),context
            t1=time.time()
            context.update({"_starttime":t0,"_exectime":(t1-t0),"_script_console":capturer.getvalue()})
        except Exception as e: 
            context.update({'_SCRIPT_ERROR':e})
            print '_SCRIPT_ERROR'
#          del context['__builtin__']  # removes the backeffect of exec on context to add builtins
        sys.stdout = old_stdout
        print "Context: " + str([context])
        if hasattr(commands, 'callback_function'):
            if commands['callback_function'] != 'None':
                callback = commands['callback_function']
                callback()
        ###    
    
    def execute_script(self, commands):#script_body, context, callback_with_result_function):
        #May want to pass this to a shadow server
        #Add functionality where main server timesout the shadow server if it doesn't return the original secript
        #Now should make a list of shadow servers.
        #Look into specifing which processor the script is launched on
        #Limit number to ~10
        #Keep track in peer_server.
        #dc=self.__determineContext__(params)
        #time = dc.get('time')
        #shotnumber = dc.get('shotnumber')
        #script = dc.get('script_xml')
        #script = "print 'This is script that is executed'"
        #pdb.set_trace()    
        #print "class CommandLibrary, function execute_script"
        
        #script = 'output_from_script = "hi"'
        #script_body = params['script_body']
        #print "script_body:"
        #print script_body
        #self.server.script_queue.add(params)
        #if self.server.clientManager.send("Hi",'ws://localhost:8086'):
        #self.server.send(script,'ws://localhost:8086')
        #wsClientFactory = WebSocketClientFactory(address, debug = True)
        #wsClientFactory.protocol = WSClientProtocol
        #wsClientFactory.clientManager = self
        #connectWS(wsClientFactory)          
        
        #print "class ScriptQueue, function popexecute"
        #print "script_servers:", self.server.clientManager.script_servers
        #print "script_queue =", self.queue
        #commands = {'_execute_script_function':self._execute_script,
        #            'script_body':script_body,
        #            'context': context,
        #            'callback_with_result_function':callback_with_result_function}
        if hasattr(commands, 'ExecuteOnMainServer'):
            if commands['ExecuteOnMainServer'] != 'False':
                self._execute(commands)
                return
        self.server.connection_manager.command_script_server(commands)
        
        '''
        #Need to move this to the conditions on exectuting commands in the queue
        script_server = self.server.connection_manager.get_available_script_server()#Need to call this in order to create script_servers. Returns None when no servers ready     
        self.server.connection_manager.get_available_script_server(callback_function)        
        #print "return from get_avail... ss =", ss
        if script_server == None:
            pass
            #Need to add self back to the queue
            return
        if params['on_main_server'] == True:
            #This should be done in the sheltered scipt environment.
            #Add functionality for timing
            #print "Executing on Main Server"
            code_locals = {}
            #print "print queue[0]:"
            #print self.queue[0]
            #print "compile...."
            #inst = glab_instrument(self.server)
            #inst.name = self.queue[0]['name']
            #if self.queue[0]['name'] == 'CCD':
            ##    Roper_CCD.Princeton_CCD(self.queue[0])
            #self.server.instruments.update({inst.id:inst})
            #try:
            #    code = compile(self.queue.pop()['script_body'], '<string>', 'exec')
            #except:
            #    print "compile unsuccessful"
            #    raise
            #print "compile successful"
            if DEBUG: print "executing"
            script = params['script_body']
            with open(script) as f:
                #Capture std out, look at sheltered script
                code = compile(f.read(), script, 'exec')
                exec(code, globals(), locals())#Copying of variables occur
            if DEBUG: print "done executing"
            return
        else:
            #add functionality for timing
            #self.queue.pop().execute(self.server.commandLibrary)    
            #Trying to connect to a server that is not responsive will restart that server and try to connect again.
            #self.server.clientManager.use_script_server(ss)
            #print "got server"
            self.server.send(params['script_body'], script_server)
            return
        '''
        return
    
    def resolve_address(self,address):
        """
        attempts to resolve a network address string in the form ip:port, 
        a server_id string in the form of a uuid1 provided through peer
        discovery, or by role, in the form of a string "role:XXX" where XXX
        is one of:
            
        returns an ip:port string if successful, "" if not
        """
        return "Not yet functional"
        if type(address)!=type(""): address=str(address)
        if (len(address.split(":"))==2) and (len(address.split("."))==3):
            return address
        if "role:" in address:
            try:
                return self.clients_by_role[address.split("role:")[1]]
            except AttributeError:
                return ""
        
        
    
    class display():
        pass
    class IORedirector(object):
        '''A general class for redirecting I/O to this Text widget.'''
        def __init__(self,text_area):
            self.text_area = text_area
    class StdoutRedirector(IORedirector):
        '''A class for redirecting stdout to this Text widget.'''
        def write(self,str):
            self.text_area.write(str,False)
    def initdisplay(self):
        # try a wx window control pane
        self.displayapp = wx.PySimpleApp()
        # create a window/frame, no parent, -1 is default ID, title, size
        self.displayframe = wx.Frame(None, -1, "HtmlWindow()", size=(1000, 600))
        # call the derived class, -1 is default ID
        self.display=self.HtmlPanel(self.displayframe,-1,self)
        # show the frame
        #self.displayframe.Show(True)
        myWxAppInstance = self.displayapp
        reactor.registerWxApp(myWxAppInstance)
        splash="<html><body><h2>GLab Python Manager</h2></body></html>"
        print self.xstatus()
        print self.xstatus("html")
        self.display.updateHTML(splash+self.xstatus("html"))
        #tried to redirect stdout to tkinter console, not working:
        #sys.stdout = self.StdoutRedirector( self.display.statuswindow )
    def attach_poll_callback(self,poll,callback,poll_time, onTimeFromNow=False):
        """
        attaches a poll-and-callback event mechanism to the main event-loop
        - used by the Glab_instrument class for data read-outs
        poll and callback should be functions or methods, and poll_time is
        a float representing the time in seconds between polls
        
        the task assigned to the polling is stored in a list 'pollcallbacks'
        attached to the server object, and a reference to this task is returned 
        to the caller
        """
        def pollcallback():
            if poll(): 
                callback()
            else:
                return
        #Will this interfere with the CommandQueue executing "compile_active_xtsm"?
        thistask = task.LoopingCall(pollcallback)
        if not hasattr(self, "pollcallbacks"):
            self.pollcallbacks=[]        
        self.pollcallbacks.append(thistask)
        thistask.start(poll_time)
        return thistask
        
    class HtmlPanel(wx.Panel):
        """
        class HtmlPanel inherits wx.Panel and adds a button and HtmlWindow
        """
        def __init__(self, parent, id, owner):
            self.server=owner            
            # default pos is (0, 0) and size is (-1, -1) which fills the frame
            wx.Panel.__init__(self, parent, id)
            self.SetBackgroundColour("red")
            self.html1 = wx.html.HtmlWindow(self, id, pos=(0,30), size=(1000,600))            
            self.btn1 = wx.Button(self, -1, "Stop Twisted Reactor", pos=(0,0))
            self.btn1.Bind(wx.EVT_BUTTON, self.server.stop)            
            self.btn2 = wx.Button(self, -1, "Refresh", pos=(120,0))
            self.btn2.Bind(wx.EVT_BUTTON, self.refresh)
            wx.EVT_CLOSE(self, lambda evt: reactor.stop())
        def refresh(self, event=None):
            self.html1.SetPage(self.server.xstatus("html"))
        def getHTML(self):
            return self.html1.GetParser().GetSource()
        def updateHTML(self,html):
            self.html1.SetPage(html)
            
    def xstatus(self, xformat="xml"):
        """
        Creates a status snap-shot in XML
        """
        stat='<Status>'
        # Server parameters
        stat += '<Server>'
        stat += '<Host>'
        stat += '<Name>'+ socket.gethostname()+  '</Name>'
        stat += '<IP>' + socket.gethostbyname(socket.gethostname()) + '</IP>'
        stat += '</Host>'
        stat += '<Script>' + main.__file__ + '</Script>'
        stat += '<LocalTime>' + time.asctime() + '</LocalTime>'
        stat += '</Server>'
        # Clients
        stat+=self.connection_manager.xstatus()        
        # Active Connections        
        stat+=self.listener.xstatus()
        # Command Queue
        stat+=self.command_queue.xstatus()
        # Data Contexts
        if hasattr(self,'dataContexts'):
            stat+='<DataContexts>'
            for dc in self.dataContexts.values():
                stat+=dc.xstatus()
            stat+='</DataContexts>'
        stat+='</Status>'
        if xformat=="html":
            # the xsl below transforms the status xml into viewable html
            xsltransform='''
            <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
            <xsl:template match="Status"><h4>Status:</h4>
                <div><xsl:apply-templates select="Server" /></div>
                <div><xsl:apply-templates select="Clients" /></div>
                <div><xsl:apply-templates select="Connections" /></div>
                <div><xsl:apply-templates select="Commands" /></div>
                <div><xsl:apply-templates select="DataContexts" /></div>
            </xsl:template>
            <xsl:template match="Server"><table border="1px"><tr><td><b>Server:</b></td><td><xsl:value-of select="./Host/Name"/></td><td><xsl:value-of select="./Host/IP"/>:<xsl:value-of select="./Host/Port"/></td><td><b>Local Time:</b></td><td><xsl:value-of select="./LocalTime"/></td></tr></table></xsl:template>
            <xsl:template match="Clients"><table border="1px"><tr><td><b>Recent Clients:</b></td></tr><xsl:apply-templates select="Client"/></table></xsl:template>
            <xsl:template match="Client"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./IP"/></td><td><xsl:value-of select="./LastConnect"/>(s) ago</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Connections"><table border="1px"><tr><td><b>Open Connections:</b></td></tr><xsl:apply-templates select="Connection"/></table></xsl:template>
            <xsl:template match="Connection"><tr><td><xsl:value-of select="./From/Referer"/></td><td><xsl:value-of select="./Command"/></td><td><xsl:value-of select="./TimeElapsed"/>s</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Commands"><table border="1px"><tr><td><b>Command Queue:</b></td></tr><xsl:apply-templates select="Command"/></table></xsl:template>
            <xsl:template match="Command"><tr><td><xsl:value-of select="./Name"/></td><td><table border='1px'><xsl:apply-templates select="Parameter"/></table></td><td><xsl:value-of select="./TimeElapsed"/>s</td><td><xsl:value-of select="./Referer"/></td></tr></xsl:template>     
            <xsl:template match="Parameter"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./Value"/></td></tr></xsl:template>            
            <xsl:template match="DataContexts"><table border="1px"><tr><td><b>Data Contexts:</b></td></tr><xsl:apply-templates select="DataContext"/></table></xsl:template>
            <xsl:template match="DataContext"><tr><td><xsl:value-of select="./Name"/></td><td><table border='1px'><xsl:apply-templates select="Variable"/></table></td></tr></xsl:template>            
            <xsl:template match="Variable"><tr><td><xsl:value-of select="./Name"/></td><td><xsl:value-of select="./Type"/></td><td><xsl:value-of select="./Value"/></td></tr></xsl:template>
            <xsl:template match="*"><li><i><xsl:value-of select ="local-name()"/>:</i><ul><xsl:apply-templates /></ul></li>
            </xsl:template>
            </xsl:stylesheet>
            '''
            xslt_root = etree.XML(xsltransform)
            transform = etree.XSLT(xslt_root)
            doc = etree.parse(StringIO(stat))
            result_tree = transform(doc)
            stat=str(result_tree)
        return stat

    def __enter__(self):
        return self
        
    def __exit__(self):
        self.save()
        
# do it all:
#with GlabPythonManager() as theBeast:
#    pass
debug=True
active_xtsm = ''

theBeast=GlabPythonManager()
try:
    theBeast.run()
except KeyboardInterrupt:
    pass

