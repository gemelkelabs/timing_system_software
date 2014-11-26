# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 19:53:48 2014

This module contains class definitions to handle data input from experiment
hardware - it allows the XTSM server to attach incoming data 'databombs' to
a list,  filestream them raw to disk, unpack their contents, notify listeners
of their arrival, and create copies and links to the data for other elements

This is managed through two primary classes and their subclasses: 

    DataBombCatcher
        FileStream
        DataBomb
    DataListenerManager
        DataListener
        
@author: Nate
"""
import msgpack, msgpack_numpy, StringIO, sys, time, struct, uuid, io, datetime, os, pdb
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking
from xml.sax import saxutils
import xstatus_ready
import file_locations
import InfiniteFileStream
import simplejson

"""
raw_buffer_folders should contain an entry for the raw data destination folder
keyed by the MAC address of the host computer.  to add an entry for a new
computer, find the MAC address using import uuid / print uuid.getnode()
"""

class DataBomb(xstatus_ready.xstatus_ready):
    """
    The databomb class is meant to implement a socket-based drop of data into
    the XTSM webserver.  Data should arrive as an HTTP post request, with a single
    argument as payload, in the form of a messagepack formatted binary string.
    (The messagepack may contained as many named variables as needed).  The 
    databomb class contains methods for unpacking, and will strip data identifying
    the generator.  This data is used to notify listeners the data is present
    using the DataListenerManager and DataListenerManager.DataListener classes.
    Furthermore, databombs can be automatically streamed to disk as they arrive
    as a means of (vertical) raw data storage.
    """
    def __init__(self,messagepack):
        print "in class Databomb, function __init__"
        if not isinstance(messagepack, str):#Expecting a messagepacked byte string
            pdb.set_trace()
        self.packed_data = messagepack
        self.databomb_init_time = time.time()
        self.raw_links = []
        self.databomb = 0
        self.notify_data = {}
        self.uuid = str(uuid.uuid1())
        
    def unpack(self):
        """
        Unpacks bytes from messagepack into key-value pair data
        in a dictionary; extract sender.  Looks for some optional special fields:
            sender: a string labeling the sender; choosing a unique id is sender's responsibility            
            shotnumber: an integer representing the shotnumber
            repnumber: an integer representing the repetition number
            onunpack: a string of python commands to execute on unpack
        """
        print "in class DataBomb, function unpack"
        #pdb.set_trace()
        self.data = msgpack.unpackb(self.packed_data)
        self.shotnumber = self.data['shotnumber']
        notify_data_elms=['sender','shotnumber','repnumber','server_machine','server_IP_address']
        for elm in notify_data_elms:        
            try: 
                self.notify_data.update({elm:self.data[elm]})
            except KeyError:
                pass
        try: 
            self.unpack_instructions=self.data['onunpack']
            try: 
                rbuffer = StringIO()
                sys.stdout = rbuffer
                exec(self.unpack_instructions,self.data)
                if self.data.has_key('__builtins__'): 
                    del self.data['__builtins__']
                sys.stdout = sys.__stdout__ 
                self.data.update({"onunpack_response":rbuffer.getvalue()})
            except:
                self.data.update({"onunpack_error":True})
        except KeyError:
            pass
        
    def stream_to_disk(self, data, filestream):
        """
        streams bytes out to file object for raw-receipt-storage 
        appends a header to identify the bomb by its uuid, followed by timestamp,
        then raw data in its messagepack byte stream -
        entire object should be unpackable using messagepack unpackb routine
        twice - first to extract 'data' element, then to unpack data
        """   
        print "In class DataBomb, function stream_to_disk"
        to_disk = {'databomb_id': str(self.uuid),
                  'time_packed': str(time.time()),
                  'len_of_packed_data': str(len(self.packed_data)),
                  'shotnumber': self.shotnumber,
                  'packed_data': self.packed_data }
        prefix = 'DB_SN'+str(self.shotnumber)+'_'
        header = {i:to_disk[i] for i in to_disk if i!='packed_data'}
        comments = str(header)
        extension = '.msgp'
        path = filestream.write_file(msgpack.packb(to_disk, use_bin_type=True),
                                     comments=comments,
                                     prefix=prefix,
                                     extension=extension)
        self.raw_links.append(path)
        print "Path:", self.raw_links
        
        
    def deploy_fragments(self,listenerManagers):
        """
        sends individual data elements to destination in XTSM generators;
        intended to establish links to saved raw data, append to horizontal
        stacks as requested in xtsm, and initiate analyses - listeners should
        already have been installed in a manager by the XTSM elements, and
        this deployment should trigger them
        """
        print "in class DataBomb, function deploy_fragments"
        #print "Listeners:", 
        #pdb.set_trace()
        if not hasattr(listenerManagers,'__iter__'):
            listenerManagers = [listenerManagers]
        for fragment in [a for a in self.data.keys() if not self.notify_data.has_key(a)]:
            for listenerManager in listenerManagers:
                self.notify_data.update({"fragmentName":fragment})   
                data = {fragment:self.data[fragment]}
                datalinks = {fragment:[f+"["+fragment+"]" for f in self.raw_links]}
                listenerManager.notify_data_present(self.notify_data,data,datalinks)
        try: 
            del self.notify_data["fragmentName"]
        except KeyError:
            pass
        
    def deploy(self,filestream,listenerManagers):
        """
        streams data to disk, unpacks and deploys fragments
        """
        print "in class DataBomb, function deploy"
        self.unpack()#Make first to extract shotnumber for file ID
        self.stream_to_disk(self.packed_data, filestream)
        self.deploy_fragments(listenerManagers)
                

#This class contains all the Databombs that have been received
class DataBombCatcher(xstatus_ready.xstatus_ready):
    """
    A class to define a list of dataBombs, and organize their deployment
    
    params probably should include an element keyed 'dataListenerManagers'
    with a list of such elements who are sensitive to these bombs
    """
    def __init__(self,params={}):
        defaultparams={ }
        for key in params.keys(): 
            defaultparams.update({key:params[key]})
        for key in defaultparams.keys():
            setattr(self,key,defaultparams[key])   
        self.databombs={}
        self.dataListenerManagers = DataListenerManager()
        params = {'file_root_selector':'raw_buffer_folders'}
        self.filestream = InfiniteFileStream.Filestream(params)
        #self.stream=self.FileStream(params={'file_root_selector':'raw_buffer_folders'})

    def __flush__(self):
        self.filestream.__flush__()
        
    def _close(self):
        pass

    def add(self,bomb):
        """
        adds a bomb to the list - the bomb input is expected to be of the 
        messagepack format.  Returns unique identifier assigned to bomb
        """
        if bomb.__class__!=DataBomb: 
            try: bomb=DataBomb(bomb)
            except: 
                raise self.BadBombError
                return
        self.databombs.update({bomb.uuid:bomb})
        return bomb.uuid
        
    def deploy(self,criteria):
        """
        deploys bombs based on selection criteria, which can be:
            'all' - deploys all bombs in the list
            'next' - deploys one based on a First-In-First-Out (FIFO) model
            uuid - deploys by the unique identifier assigned to the bomb on add
        """
        print "In class DataBombCatcher, function deploy"
        print "criteria:", criteria
        if not hasattr(self,'dataListenerManagers'): self.dataListenerManagers=[]
        def all_c(o):
            for bomb in o.databombs:
                bomb.deploy(o.filestream,self.dataListenerManagers)
            o.databombs=[]
        def next_c(o):
            ind=min([(bomb.databomb_init_time,bomb.uuid) for bomb in o.databombs])[1]
            o.databombs[ind].deploy(o.filestream,self.dataListenerManagers)
            del o.databombs[ind]
        ops={ 'all': all_c, 'next':next_c }
        try: ops[criteria](self)
        except KeyError: 
            try: 
                self.databombs[criteria].deploy(self.filestream,self.dataListenerManagers)
                del self.databombs[criteria]
            except KeyError: raise self.UnknownBombError

    class BadBombError(Exception):
        pass

    class UnknownBombError(Exception):
        pass


        

class DataListenerManager(xstatus_ready.xstatus_ready):
    """
    A class to manage data listeners.
    This is held within a DataContext (DataContext is a dictionary) held by the server.
    It holds a list of all the listeners that are looking to receive databombs. 
    This also holds informatoin on what to do with the listener - within "spawn".
    Also needs to delete the listeners when databombs were received.
    """
    def __init__(self):
        self.listeners={}
        self.instruments={}
        
    def spawn(self,params={}):
        """
        creates a listener for data returned from
        apparatus / input hardware; use when an experiment is defined and expects
        data to be returned and either linked to the generator or processed in some
        way

        arguments passed in by dictionary -
        listen_for - identifies what to listen for as a key-value dictionary of must-haves 
        generator  identify who is listening as ({'fasttag':XXXX, 'xtsm': xtsm_object } for an XTSM element)
        onlink - callback method after data has been linked in to listener
        onattach - callback method after data has been attached to listener
        onclose - callback after item is destroyed 
        """
        print "class DataListenerManager, function spawn"
        defaultparams={'listen_for':{'sender':'',
                                     'shotnumber':-1,
                                     'server_machine':'',
                                     'server_IP_address':'',
                                     'repnumber': None},
                       'timecreated':time.time(),
                       'generator': None,
                       'timeout':360 }
        if params == None:
            params = defaultparams
        for key in params:
            defaultparams.update({key:params[key]})
        #print "Params for listener:", defaultparams
        newguy = self.DataListener(defaultparams)        
        self.listeners.update({newguy.id:newguy})
        
        #This needs to send the soon to be esnding servers  
    
    def notify_data_present(self, generator_info, data, datalinks):
        """
        method for data to announce its presence 
        searches for relevant listeners and links or attaches as desired
        listeners will try to match generator_info (a dictionary) and express interest
        if they do, data will be linked or attached as they request
        """
        #print "in class DataListenerManager, function notify_data_present"
        #print "generator_info", generator_info
        #print "data", "--Bunch of Data--"
        #print "datalinks", datalinks
        for listener in self.listeners.values():
            if listener.query_interest(generator_info):
                #print "a listener is interested in the data"
                #pdb.set_trace()
                (listener.getMethod())(data,datalinks)

    def flush(self):
        """
        Cleans up listener tree by removing listener's who have timed-out or
        reached their designated number of collection events
        """
        for listener in self.listeners.keys():
            if self.listeners[listener].query_dead(): del self.listeners[listener]

    class DataListener(xstatus_ready.xstatus_ready):
        """
        A class of objects that define a 'listener' for data returned from
        apparatus / input hardware; use when an experiment is defined and expects
        data to be returned and either linked to the generator or processed in some
        way
        
        arguments passed in by dictionary of arguments - 
        listen_for - identifies what to listen for as a key-value dictionary of must-haves 
        generator - identifies who is listening as ({'fasttag':XXXX, 'xtsm': xtsm_object } for an XTSM element)
        onlink - callback method after data has been linked in to listener
        onattach - callback method after data has been attached to listener
        onclose - callback after item is destroyed 
        """
        def __init__(self,params={}):
            """
            constructor for class
            """
            print "In class DataListener, function __init__"
            self.sender = None
            self.server = None
            self.id='DL'+str(uuid.uuid1())
            self.listen_for = None
            self.timecreated = None
            self.generator = None
            self.timeout = None
            self.eventcount = None
            defaultparams={'listen_for':{'sender':'','shotnumber':-1,'repnumber': None}
                            , 'timecreated':time.time(), 'generator': None
                            , 'timeout':360, 'eventcount':1 }        
            for key in params.keys():
                defaultparams.update({key:params[key]})
            self.datalinks=[]
            self.expirationtime = time.time() + defaultparams['timeout']
            print "DefaultParams for DataListener:", defaultparams
            for key in defaultparams.keys():
                setattr(self,str(key),defaultparams[key])   
            #pdb.set_trace()
    
        def __del__(self):
            """
            NOTE:  listener must be killed by its owner manager - this is prone to cause memory leak
            """
            if hasattr(self,'onclose'): self.onclose(self)

        def announce_interest(self,address):
            """
            announce to network servers that this element is interested in its data
            Note: add to The databomb dispatcher functionality that will save
            all databombs to disk that haven't been sent.
            A good way of doing this is perhaps within the destrtuctor.
            It chewcks a flag it it was dispatched - this way it might save even
            on a crash.
            """
            print "class DataListener, function announce_interest"
            p = {'listener_id':self.id,
                 'instrument_id':None,
                 'instrument_type':'camera',
                 'connection_id':None,
                 'ip_address':address,
                 'port':None,
                 #'shotnumber':None,
                 'data_type':'image'}
            self.server.announce_data_listener(params=p)
        
        def query_interest(self, generator_id):
            """
            returns true if this listener is interested in data from the 
            provided generator id
             - a match will be flagged if every element in the listener's dictionary
             is matched by the event's generator id dictionary - however the generator
             may provide more info than necessary, and the listener need not specify them all
             - matches are based on a soft comparison; if a string can be converted to a number
             it will be before comparison is made.  
            """
            for key_listening_for in self.listen_for.keys():
                if not (key_listening_for in generator_id):
                    continue
                if self.listen_for[key_listening_for] == generator_id[key_listening_for]:
                    return True
                #try:
                #    listening = float(self.listen_for[key_listening_for])
                #    given = float(generator_id[key_listening_for])
                #    if listening == given:#Not necessary?
                #        return True
                #except AttributeError:#Error Thrown when cannot convert string to float
                #    pass
            return False
            
            """
            This is confusing
            for element in self.listen_for.keys():
                try:  
                    if self.listen_for[element] != generator_id[element]: 
                        try: 
                            if float(self.listen_for[element]) != float(generator_id[element]):
                                return False
                            else:
                                continue                        
                        except:
                            return False
                except KeyError: 
                    return False
            return True
            """
    
        def query_dead(self):
            """
            checks whether listener has passed timeout or has already responded
            to its event(s)
            """
            if self.expirationtime<time.time(): return True
            if self.eventcount<=0: return True
            return False
    
        def attachdata(self,data,datalinks):
            """
            Attaches the data the listener is looking for directly
            """
            self.data=data
            self.eventcount-=1
            if hasattr(self,'onattach'): self.onattach(self)
    
        def linkdata(self,data,datalinks):
            """
            Links the data the listener is looking for - 
            the link should take the form of a string forming a resource locator;
            intended for linking to files (hdf5 via liveheaps, or raw data from bomb file dumps)
            """
            #print "class DataListenerManager, function linkdata"
            self.datalinks.append(datalinks)
            self.eventcount-=1            
            if hasattr(self,'onlink'): self.onlink(self)

        def getMethod(self):
            """
            returns the method, link or attach, for this listener
            """
            try: 
                if self.method=='attach': return self.attachdata
                else: return self.linkdata
            except NameError: return self.linkdata 
            return self.linkdata

import inspect, urllib

class DataBombDispatcher(xstatus_ready.xstatus_ready):
    """
    class to manage the creation and dispatch of databombs,
    handle exceptions and handshaking such that data is (ideally) never lost
    """
    def __init__(self,params={}):
        print "class DataBombDispatcher function __init__"
        defaultparams={ }
        self.instruments_with_destinations = {}
        self.all_requests = {}
        #This sets all the params to be member variables of DataBombDispatcher
        for key in params.keys():
            defaultparams.update({key:params[key]})
        for key in defaultparams.keys():
            setattr(self,key,defaultparams[key])   
        self.databombers={}
        if not hasattr(self, "server"): 
            print "WARNING:: DatabombDispatcher created with no attached server"
            return
        self.server.attach_poll_callback(lambda: True, self.dispatch, 0.05)
        
    def add(self,bomber):
        """
        adds a bomber to the list - the bomber input is expected to be a dictionary.
        Returns unique identifier assigned to bomb
        """         
        print "class DataBombDispatcher, function add" 
        if bomber.__class__!=self.DataBomber: 
            try: 
                bomber=self.DataBomber(bomber)
                bomber.server = self.server
            except: 
                raise self.BadBomberError
                return
        self.databombers.update({bomber.uuid:bomber})
        return bomber.uuid
    
    

    def link_to_instrument(self,params):
        #from params find instruments
    #Then add the ip address to the instruments_with_destinations
    #
        print "class DataBombDispatcher, function link_to_instrument"  
        for key in params.keys():
            setattr(self,key,params[key]) 
        pdb.set_trace()
        self.destinations = [params['ip_address']]
        self.instruments_with_destinations.update(params)
        self.all_requests.update(params)
        
    def delink_to_instrument(self,params):
        pass
    
    def dispatch(self,criteria="all"):
        """
        dispatches bombers based on selection criteria, which can be:
            'all' - deploys all bombs in the list
            'next' - deploys one based on a First-In-First-Out (FIFO) model
            uuid - deploys by the unique identifier assigned to the bomb on add
        """
        #print "class DataBombDispather, function dispatch"
        #for d in self.databombers: delete if bomber has sent
        if len(self.databombers)==0:
            return
        #print "class DataBombDispatcher, function dispatch"
        #print "Length of self.databombers:", len(self.databombers)
        for key in self.databombers.keys():
            if self.databombers[key].is_sent:
                pass
                #del self.databombers[key]
        #This code is confusing. I am just going to send all databombs and then delete them
        """
        def all_c(o):
            for bomber in o.databombers.values():
                print "telling bomber to dispatch"
                bomber.dispatch(['10.1.1.124'])#Fix this
            #o.databombers={} need to delete the bombers more carefully CP
        def next_c(o):
            ind=min([(bomber.timestamp,bomber.uuid) for bomber in o.databombers])[1]
            o.databombers[ind].dispatch()
            del o.databombers[ind]
        ops={ 'all': all_c, 'next':next_c }

        try:
            ops[criteria](self)
        except KeyError: 
            try: 
                self.databombers[criteria].dispatch()
                #del self.databombers[criteria] need to delete the bomber
            except KeyError:
                raise self.UnknownBomberError
        """
        for bomber in self.databombers:
            if self.databombers[bomber].is_sent == True:
                continue
            print "telling bomber to dispatch"
            self.databombers[bomber].dispatch(['10.1.1.124'])#Fix this
            #self.databombers[bomber].dispatch(['10.1.1.112'])#Fix this
        


    class BadBomberError(Exception):
        pass
        
    class DataBomber(xstatus_ready.xstatus_ready):
        """
        a class for contruction and sending of an outgoing databomb 
        """
        def __init__(self,data,destinations=None, server=None):
            """
            constructs an outgoing payload from a dictionary of data
            """
            print "class DataBomber, __init__"
            self.uuid='DBR'+uuid.uuid1().__str__()
            self.server=server
            self.is_sent = False
            try: 
                caller=inspect.stack()[1][3]
            except: 
                caller="Unknown"
            default_data={"generator":caller}
            #data.update({"shotnumber":shotnumber}) Add this
            data.update({"server_IP_address":'10.1.1.178'})
            default_data.update(data)
            data=default_data
            data.update({"packed_time":time.time(),
            "packed_by":str(uuid.getnode())+"_DataBomber_init"})           
            self.data=data            
            #pdb.set_trace()
            # packs data into a msgpack format (binary key-value pairs)
            self.packed_data=msgpack.packb(data, use_bin_type=True)
            self.destinations=destinations
            
        def dispatch(self,destinations_=None):
            print "DataBomber, dispatch"
            """
            sends the payload to the specified destination(s) 
            (as well as any provided at initialization)
            , provided as an ip address string, e.g. "10.1.1.101:8083"
            """
            if not self.server: 
                print "WARNING:: databomber dispatched without an attached server - dispatch ignored"
                return
            if type(destinations_) != type([]):
                destinations_=[destinations_]
            if type(self.destinations) != type([]):
                self.destinations=[self.destinations]
            self.destinations = list(set(self.destinations + destinations_))    
            if not self.destinations[0]:
                #self.destinations=[self.data['destination_priorities'][0]]#Update this to send more
                self.dest_by_priority=True
            flag = False
            for dest in self.destinations:
                if dest != None:
                    flag = True
            if not flag:
                #self.destinations.append("10.1.1.112")#Make this general - to the active_parser - perhaps by adding a Parameter field in the head, next to the shotnumber and building the scope (??)
                self.destinations.append("10.1.1.124")
            if self.server.ip == '10.1.1.178':
                data_context = 'PXI'#Change for generality CP
            if self.server.ip == '10.1.1.124':
                data_context = 'PXI'#Change for generality CP
            if self.server.ip == '10.1.1.112':
                data_context = 'PXI_emulator'#Change for generality CP
            self.destinations = [x for x in self.destinations if x is not None]
            packed_message = msgpack.packb({"IDLSocket_ResponseFunction":'databomb','data_context':data_context,'databomb':self.packed_data}, use_bin_type=True)#self.packed_data
            for dest in self.destinations:
                dest = "10.1.1.124"
                if self.server.ip == '10.1.1.178':
                    dest = "10.1.1.124"
                if self.server.ip == '10.1.1.124':
                    dest = "10.1.1.124"
                if self.server.ip == '10.1.1.112':
                    dest = "10.1.1.112"
                if dest == None:
                    print "No destination"
                    continue
                try: 
                    flag = False
                    flag = self.server.send(packed_message,dest, isBinary=True)
                    if flag:
                        print "dest:", dest
                        print "Databomb Sent!"
                        self.is_sent = True
                    else:
                        print "dest:", dest
                        print "Databomb Not Sent!"
                except:
                    raise

