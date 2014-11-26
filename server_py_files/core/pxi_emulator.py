# -*- coding: utf-8 -*-
"""
Created on Tue Mar 25 22:01:55 2014

@author: Nate
"""

import httplib, mimetypes, numpy, time, pdb
import msgpack, msgpack_numpy
msgpack_numpy.patch()
import profile

from twisted.internet.protocol import DatagramProtocol
import simplejson
import socket
import sys
shotnumber = 1
DEBUG = True
udpbport = 8085

from twisted.internet import reactor
from twisted.internet import task
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketClientFactory
from autobahn.twisted.websocket import WebSocketClientProtocol
from autobahn.twisted.websocket import connectWS
from autobahn.twisted.websocket import listenWS
from twisted.internet.protocol import DatagramProtocol
import twisted.internet.error
from twisted.python import log

from twisted.internet import stdio
from twisted.protocols import basic
from twisted.internet import error
import os
import colorama
from StringIO import StringIO
log.startLogging(sys.stdout)
   
websocket_speed_test_start = 0   
   
class CommandLibrary():
    """
    The Command Library contains all methods a server can execute in response
    to an HTTP request; the command is specified by name with the 
    "IDLSocket_ResponseFunction" parameter in an HTTP request
    Note: it is the responsibility of each routine to write responses
    _AND CLOSE_ the initiating HTTP communication using
    params>request>protocol>loseConnection()
    """
    def __init__(self):
        if DEBUG: print "class CommandLibrary, func __init__"
        self.factory = None
        self.multicast = None
        
    def start_fake_shot(self):
        if DEBUG: print "class PXI_emulator.CommandLibrary, func start_fake_shot"
        global shotnumber
        msg = {'fake_shotnumber_started':shotnumber,
               'time':time.time(),
                'server_ip_in_charge':'10.1.1.124',
                'data_context':'PXI_emulator',
                'server_port_in_charge':'8083'}
        msg = simplejson.dumps(msg, ensure_ascii = False).encode('utf8')
        self.multicast.protocol.send(msg)
        shotnumber+=1
        
    def request_active_xtsm(self):
        if DEBUG: print "class PXI_emulator.CommandLibrary, func request_active_xtsm"
        global shotnumber
        #pdb.set_trace()
        msg = {'IDLSocket_ResponseFunction': 'compile_active_xtsm',
               'shotnumber': shotnumber,
                'Labview Version':'1.0',
                'data_context':'PXI_emulator',
                'terminator':'die'}
        msg = simplejson.dumps(msg, ensure_ascii = False).encode('utf8')
        self.factory.protocol.sendMessage(msg, isBinary=False)


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
        if DEBUG: print "class PXI_emulator.MulticastProtocol, func startProtocol"
        interface_ = ""
        if socket.gethostbyname(socket.gethostname()) == '10.1.1.124':
            interface_ = '10.1.1.124'
        self.transport.joinGroup("228.0.0.5", interface=interface_)

    def send(self,message):
        """
        sends message on udp broadcast channel
        """
        if DEBUG: print "class PXI_emulator.MulticastProtocol, func send"
        self.transport.write(message, ("228.0.0.5", udpbport))

    def datagramReceived(self, datagram_, address):
        """
        called when a udp broadcast is received
        """
        #if DEBUG: print "Datagram received from "+ repr(address) 
        datagram = simplejson.loads(datagram_)
        if hasattr(datagram, 'has_key'):
            if datagram.has_key('server_ping'):
                return
        else:
            if DEBUG: print "class PXI_emulator.MulticastProtocol, func datagramReceived"
            if DEBUG and len(payload) < 10000: print datagram
        

        
class MyClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        if DEBUG: print("class PXI_emulator.MyClientProtocol, func onConnect. : {0}".format(response.peer))
        self.factory.protocol = self

    def onOpen(self):
        if DEBUG: print("class PXI_emulator.MyClientProtocol, func onOpen.")

    def onMessage(self, payload_, isBinary):
        if DEBUG: print "class PXI_emulator.MyClientProtocol, func onMessage"
        payload = simplejson.loads(payload_)
        if DEBUG: print payload.keys()
        if DEBUG and len(str(payload)) < 10000: print payload
        if payload.has_key('sending'):
            self.factory.command_library.start_fake_shot()

    def onClose(self, wasClean, code, reason):
        if DEBUG: print("class PXI_emulator.MyClientProtocol, func onClose. {0}".format(reason))
                          
        

class MyServerProtocol(WebSocketServerProtocol):

    def onConnect(self, request):
        if DEBUG: print("class PXI_emulator.MyServerProtocol, func onConnect: {0}".format(request.peer))
        self.factory.protocol = self
        
    def onOpen(self):
        if DEBUG: print("class PXI_emulator.MyServerProtocol, func onOpen")
        
    def onMessage(self, payload_, isBinary):
        if DEBUG: print "class PXI_emulator.MyServerProtocol, func onMessage"
        #self.log_message()
        payload = simplejson.loads(payload_)
        global websocket_speed_test_start
        if payload.has_key('websocket_speed_test_start'):
            websocket_speed_test_start = time.time()
        if payload.has_key('websocket_speed_test_start'):
            websocket_speed_test_start = time.time()
        if DEBUG and len(payload) < 10000: print payload
        
    def onClose(self, wasClean, code, reason):
        if DEBUG: print("class PXI_emulator.MyServerProtocol, func onClose: {0}".format(reason))
        #server_shutdown()

    def check_for_main_server():
        global time_last_check
        global time_now
        time_last_check = time_now
        time_now = time.time()
        #print time_last_check, time_now, last_connection_time
        if (time_now - last_connection_time) > 1100000 and (time_now - time_last_check) < 11:
            server_shutdown()
        
    def server_shutdown():
        if DEBUG: print "----------------Shutting Down PXI_emulator Now!----------------"
        reactor.callLater(0.01, reactor.stop)

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
        po = sys.stdout
        sys.stdout = rbuffer
        err = False
        try:
            #exec(line,globals(),locals())
            exec line in globals(),locals()
        except Exception as e:
            err = e
        sys.stdout = po
        print '>u> ' + line
        if err:
            out = self.pre_e + str(e) + self.post_e
        else:
            out = rbuffer.getvalue()
        if out != "":
            print '>s> ' + out




def main():
    
    global command_library
    command_library = CommandLibrary()
    address = "ws://" + 'localhost'
    keyboard = Keyboard_Input()
    stdio.StandardIO(keyboard)
    multicast = reactor.listenMulticast(udpbport, 
                                        MulticastProtocol(),
                                        listenMultiple=True) 
    
    factory = WebSocketClientFactory(address + ":8084", debug = False)
    factory.setProtocolOptions(failByDrop=False)
    factory.protocol = MyClientProtocol
    try:
        connectWS(factory)
        command_library.factory = factory
        command_library.multicast = multicast
        factory.command_library = command_library
    except twisted.internet.error.CannotListenError:
        print "Can't listen"
        #server_shutdown()
    
if __name__ == '__main__':
    main()

'''
factory = WebSocketServerFactory(address + ":9084", debug = False)
factory.setProtocolOptions(failByDrop=False)
factory.protocol = MyServerProtocol
try:
    reactor.listenTCP(9084, factory)
    factory.command_library = command_library
    command_library.factory = factory
except twisted.internet.error.CannotListenError:
    print "Can't listen"
    return
    #server_shutdown()
'''


reactor.run()


#The following was for PXI_emulator through TCP
def send_compile_request(shotnumber=22):
    if DEBUG: print "send_compile_request"
    post_multipart("127.0.0.1:8083",'127.0.0.1:8083'
                    ,[('IDLSocket_ResponseFunction','compile_active_xtsm')
                    ,('shotnumber',str(shotnumber)),('Labview Version','1.0')
                    #,('data_context','default:127.0.0.1'),('terminator','die')],[])
                    ,('data_context','PXI_emulator'),('terminator','die')],[])

def post_multipart(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)
    h = httplib.HTTP(host)
    h.putrequest('POST', selector)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    h.close()
    #errcode, errmsg, headers = h.getreply()
    return #h.file.read()

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\n\r'
    L = []
    L.append('--' + BOUNDARY )
    for (key, value) in fields:
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
        L.append('--' + BOUNDARY + '--')
    #L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
def post_databomb(shotnumber=1):
    """
    Post a fictitious databomb of random data
    """
    msgdict={"sender":"PXI1Slot3/ai0:3","shotnumber":str(int(shotnumber)),"repnumber":-1}
    msgdict.update({"somedata":numpy.random.random(10000)})
    msg=msgpack.packb(msgdict)
    post_multipart("127.0.0.1:8083",'127.0.0.1:8083'
                    ,[('IDLSocket_ResponseFunction','databomb')
                    ,('databomb',msg),('data_context','PXI_emulator'),('terminator','die')],[])
    
def constant_run(delay=2,iter=100):
    global shotnumber
    msg = {'fake_shotnumber_started':shotnumber,
           'time':time.time(),
            'server_ip_in_charge':'10.1.1.124',
            'server_port_in_charge':'8083'}
    for a in range(iter):
        send_compile_request(shotnumber)
        time.sleep(delay)
        #post_databomb(shotnumber)
        print "New Fake shot started. shotnumber =", shotnumber
        post_multipart("127.0.0.1:8083",'127.0.0.1:8083',
                       [('fake_shotnumber_started',str(shotnumber)),
                      ('time',str(time.time())),
                        ('server_ip_in_charge','10.1.1.124'),
                        ('server_port_in_charge','8083'),
                        ('data_context','PXI_emulator'),
                        ('terminator','die')],[])
        shotnumber+=1
        
