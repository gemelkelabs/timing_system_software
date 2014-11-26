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
from datetime import datetime
from datetime import date   
import pdb
import colorama
colorama.init(strip=False)

import msgpack
import msgpack_numpy


import simplejson
import XTSMobjectify
import DataBomb
import InfiniteFileStream
msgpack_numpy.patch()#This patch actually changes the behavior of "msgpack"
#specifically, it changes how, "encoding='utf-8'" functions when unpacking
import XTSM_Server_Objects
import file_locations


import numpy
from enthought.traits.api import HasTraits
from enthought.traits.api import Int as TraitedInt
from enthought.traits.api import Str as TraitedStr

import collections
DEBUG = True
      
NUM_RETAINED_XTSM=10



#port = 8083
#wsport = 8084
#udpbport = 8085

        
class Experiment_Sync_Group(HasTraits):
    """
    A class to hold experiment sychronization data - this is the core
    organizational element, holding the current shotnumber, the active_xtsm
    generator, and the last several compiled xtsm objects ()
    """
    active_xtsm = TraitedStr('<XTSM></XTSM>')
    last_successful_xtsm = TraitedStr('<XTSM></XTSM>')
    shotnumber = TraitedInt(0)
    # note: last element is compiled_xtsm, defined by class below
    def __init__(self,server, data_context_name):
        if DEBUG: print "class Experiment_Sync_Group, func __init__"
        self.server=server
        self.data_context_name = data_context_name
    def _active_xtsm_changed(self, old, new): 
        pass
        #if DEBUG: print "class Experiment_Sync_Group, func _active_xtsm_changed"
        #msg = {"active_xtsm_post":str(new),"data_context":self.data_context_name}
        #json = simplejson.dumps(msg, ensure_ascii = False).encode('utf8')
        #self.server.broadcast(json)
    def _shotnumber_changed(self, old, new): 
        pass
        #if DEBUG: print "class Experiment_Sync_Group, func _shotnumber_changed"
        #msg = {"shotnumber":str(new),"data_context":self.data_context_name}
        #json = simplejson.dumps(msg, ensure_ascii = False).encode('utf8')
    def __flush__(self):
        if DEBUG: print "class Experiment_Sync_Group, func __flush__"
        lsx=open(file_locations.file_locations['last_xtsm'][uuid.getnode()]+"last_xtsm.xtsm","w")
        lsx.write(self.last_successful_xtsm)
        lsx.close()
        self.compiled_xtsm.flush()
        self.compiled_xtsm.filestream.__flush__() 
    def __getstate__(self):
        if DEBUG: print "class Experiment_Sync_Group, func __getstate__"       

    class XTSM_stack(collections.OrderedDict):
        """
        A class to hold a stack of compiled XTSM objects and manage their
        storage and retrieval - for simplicity we subclass the orderedDict class
        in collections.  This is extended with an infinite filestream, into which
        the oldest xtsm objects are serialized for storage in this messagepack 
        format as shotnumber:xtsm entries.
        """
        filestream = InfiniteFileStream.Filestream({"file_root_selector":"xtsm_feed"})
        packer = msgpack.Packer()
        def __init__(self):
            collections.OrderedDict.__init__(self)
            self.archived={}
            self.timeadded={}
        def __del__(self):
            self.flush()
        def __getstate__(self):
            print 'andhere'
            
        def update(self,*args,**kwds):
            """
            inserts another element - should be shotnumber:xtsm pair 
            """
            collections.OrderedDict.update(self,*args,**kwds)
            for elm in args:
                self.archived.update({elm.keys()[0]:False})       
            for elm in args:
                self.timeadded.update({elm.keys()[0]:time.time()})
            while len(self)>NUM_RETAINED_XTSM:
                self.heave()
            #pdb.set_trace()                
            
        def archive(self):
            """
            checks if any elements are currently archivable, and archives them
            if any have not yet been archived, and are active
            but exceed the archive_timeout, they are forced deactive and archived.  
            
            """
            #pdb.set_trace() #Check to see if "self has elm" in it.
            for elm in self:
                if not self[elm].isActive(): 
                    self._archive_elm(elm)
                    continue
                if (time.time()-self.timeadded[elm]) > self.archive_timeout:
                    self._archive_elm(elm)
                    self[elm].deactivate(params={"message":"This element was deactivated when timed out from XTSM_Stack"})
                    continue        
                
        def _archive_elm(self,elm):
            """
            stores an element to disk in the infinite filestream - does not check
            if element is active - that is duty of caller
            """
            if type(elm)==type(0):
                elm=(elm,self[elm])
            self._write_out(elm)
            self.archived[elm[0]] = True  
            
        def _write_out(self,elm):
            """
            stores an element to disk in the infinite filestream 
            """
            sn = None
            try:
                sn = elm[1].XTSM.getItemByFieldValue("Parameter","Name","shotnumber").Value.PCDATA
            except:
                pdb.set_trace()
                pass
            self.filestream.write_file(self.packer.pack({elm[0]:elm[1].XTSM.write_xml()}),
                                       comments='',
                                       prefix=str('XTSM_SN'+str(sn))+'_',
                                         extension='.txt')
            
        def heave(self):
            """
            removes the oldest element from the stack (FIFO-style), archiving
            it if it has not already been - in this case, the element is removed
            even if it has active listeners; they are removed too, to avoid memory leaks.
            """
            heavethis = self.popitem(last=False)
            if heavethis[1].isActive():
                heavethis[1].deactivate(params={"message":"This element was deactivated when heaved from XTSM_Stack"})
            if not self.archived[heavethis[0]]:
                self._write_out(heavethis)
                
        def flush(self):
            """
            heaves all elements from stack, saving to disk if necessary
            """
            while len(self)>0:
                self.heave()
                                
    compiled_xtsm = XTSM_stack()        
        
        
class DataContext(XTSM_Server_Objects.XTSM_Server_Object):
    """
    A dataContext object stores variable definitions for a Python session
    in a sheltered scope, roughly one for each user, such that independent
    data analysis and experiment control sessions can be run without interferences
    
    .dict contains dictionary of variables and values
    """
    def __init__(self, name, server):
        if DEBUG: print "class DataContext, function __init__", 'name:', name
        self.dict = {"__context__":name}
        self.name = name
        self.server = server
        #Create DataBombCatcher
        d = DataBomb.DataBombCatcher(params={"server":self.server})
        self.dict.update({'_bombstack':d})
        #Create DataBombDispatcher
        d = DataBomb.DataBombDispatcher(params={"server":self.server}) 
        self.dict.update({'databomb_dispatcher':d})       
        #Create DataListenerManager
        d = DataBomb.DataListenerManager()
        self.dict.update({'data_listener_manager':d}) 

    def _close(self):
        pass
 
    def update(self,data):
        """
        updates a variable or variables according to a dictionary of new values
        """
        self.dict.update(data)
    def get(self,variablename):
        return self.dict[variablename]
    def __getitem__(self,vname):
        return self.get(vname)
    def xstatus(self):
        stat = '<DataContext><Name>' + self.name + '</Name>'
        for var in self.dict:
            try:
                stat +='<Variable>'
                stat += '<Name>'
                stat += var
                stat += '</Name>'
                stat += '<Type>'
                stat += '<![CDATA['
                stat += str(type(self.dict[var]))
                stat += ']]></Type>'
                stat += '<Value>'
                stat += '<![CDATA['
                stat += str(self.dict[var])[0:25]
                stat += ']]>'
                stat += '</Value>'
                stat += '</Variable>'
            except:
                stat += '<Unknown></Unknown>'
        stat += '</DataContext>'
        return stat
    def __flush__(self):
        for item in self.dict:
            try:
                self.dict[item].__flush__()
                self.dict[item].flush()
            except AttributeError:
                pass
        XTSM_Server_Objects.XTSM_Server_Object.__flush__(self)
        
