# -*- coding: utf-8 -*-
"""
Created on Tue May 21 15:19:04 2013

@author: Nate

This module defines a 'live heap' data class, which is essentially a stack
of like data items held in RAM, which are synchronously written out to an 
element in an hdf5 data file when the stack reaches a certain size.  
It is meant to provide transparent access to a heap of similar data taken
while some set of parameters is varied.  An example might be a series of 
images, each of which was taken at the end of a timing sequences generating
a BEC in an apparatus; each image corresponds to a specific iteration of the
experiment, labeled by a shotnumber.  As this data is accumulated, it can
be added to the live_heap, which manages the storage to disk by itself, and
retains the latest portion in RAM ready for analysis in a transparent way.
Ideally, the user does not need to be aware where the data currently resides.     
"""

import numpy,uuid,operator,os,time
import tables, pdb

class DataHeap():
    
    def __init__(self, options={}):
        """
        constructor for datastore - should open or create an hdf5 file on disk
        to attach to - filepath should provide the path
        """
        #path = "c:\\wamp\\vortex\\Python Interpreter\\glds"
        path = "c:\\wamp\\www\\data_storage"
        self.options={"filepath":path + '\\' + str(uuid.uuid4()) + ".h5", 
                 "title":"Untitled" }
        self.options.update(options)
        self.id=str(uuid.uuid4())
        file_name = self.options["filepath"]
        self.h5=tables.open_file(file_name,
                                 mode="a",
                                 title=self.options["title"],
                                 driver="H5FD_SEC2",
                                 NODE_CACHE_SLOTS=0)
        #pdb.set_trace()
        try:
            self.fileaccessgroup=self.h5.get_node("/","fa")    
            self.fatable=self.h5.get_node("/fa","access")    
        except tables.NoSuchNodeError:    
            self.fileaccessgroup=self.h5.create_group('/','fa','fileaccessgroup')
            self.fatable = self.h5.create_table(self.fileaccessgroup, 'access', self.AccessRecord , "Acess Records")
        self.handles=[]        
        self.__record_action__("file opened")
    

class glab_datastore():
    """
    This class wraps the pytables module to provide a data storage vehicle
    a single datastore is intended to interface with a single .hdf5 file
    on disk.
    Multiple live stacks can heave data into the same datastore.  
    """    
    def __init__(self, options={}):
        """
        constructor for datastore - should open or create an hdf5 file on disk
        to attach to - filepath should provide the path
        """
        #path = "c:\\wamp\\vortex\\Python Interpreter\\glds"
        path = "c:\\wamp\\www\\data_storage"
        self.options={"filepath":path + '\\' + str(uuid.uuid4()) + ".h5", 
                 "title":"Untitled" }
        self.options.update(options)
        self.id=str(uuid.uuid4())
        file_name = self.options["filepath"]
        self.h5=tables.open_file(file_name,
                                 mode="a",
                                 title=self.options["title"],
                                 driver="H5FD_SEC2",
                                 NODE_CACHE_SLOTS=0)
        #pdb.set_trace()
        try:
            self.fileaccessgroup=self.h5.get_node("/","fa")    
            self.fatable=self.h5.get_node("/fa","access")    
        except tables.NoSuchNodeError:    
            self.fileaccessgroup=self.h5.create_group('/','fa','fileaccessgroup')
            self.fatable = self.h5.create_table(self.fileaccessgroup, 'access', self.AccessRecord , "Acess Records")
        self.handles=[]        
        self.__record_action__("file opened")
        
    def __del__(self):
        """
        destructor for the datastore; meant to ensure file is flushed and
        closed on termination
        """
        self.__record_action__('file closed')
        self.h5.close()
        for hind in xrange(len(self.handles)):
            self.handles[hind].close()
        print "file "+self.options["filepath"]+" closed"

    def __record_action__(self, action):
        """
        records a file access action
        """
        facreaterec=self.fatable.row
        facreaterec['timestamp']=time.time()
        facreaterec['computerid']=os.environ['COMPUTERNAME']
        facreaterec['datastoreid']=self.id
        facreaterec['action']=action
        facreaterec.append()
        
    def flush(self):
        """
        flushes pending write requests to disk
        """
        self.__record_action__("file flush")        
        self.h5.flush()        
        
    def __str__(self):
        """
        string function output
        """
        return self.h5.__str__()
        
    def view(self):
        """
        launches a viewer to browse contents of associated hdf file
`        """
        pass
    
    def get_handle(self,element_id,element_structure):
        """
        links an element in the datastore to a liveheap by returning a handle
        corresponding to the provided element id.  id can be a string providing
        path to element in hdf5 style, or...
        if element does not exist, or an existing element has the wrong structure,
        creates a new element with _x appended to name
        """
        def exit_this(h):
            """
            exit routine - record action and return a data handle
            """
            t=self.dataHandle(h)
            self.handles.append(t)
            self.__record_action__("issued handle for "+str(element_id))
            return t
        # first create a numpy structured array as a descriptor for the table elements
        eparts = element_id.rsplit("/",1)
        des = numpy.empty(1,dtype=[
                ("shotnumber",numpy.int64),
                ("repnumber",numpy.int64),
                (eparts[1],element_structure.dtype, element_structure.shape)
                ])
        # now try to create or open the table, else looking for first unused name of type
        for ind in xrange(-1,1000):
            try: 
                h = self.h5.getNode(element_id+("_"+str(ind))*(ind>0))
                if h.dtype==des.dtype:
                    exit_this(h)
            except tables.exceptions.NoSuchNodeError: 
                where = "/"+eparts[0]
                name = eparts[1]+("_"+str(ind))*(ind>0)
                h = self.h5.create_table(where, name, description=des.dtype)
                return exit_this(h)

    def load_from_filestore(self,directory,tablename="Untitled",limit=None,dtype=numpy.float32):
        """
        Not intended to be used often - loads individual files from a directory
        and stores them in a named table in the datastore - unfinished
        """
        hh=None
        for dirname, dirnames, filenames in os.walk(directory):
            num=0
            # print path to all subdirectories first.
            for subdirname in dirnames:
                print os.path.join(dirname, subdirname)    
            # import data and append to an image stack.
            imgs=[]
            names=[]
            for filename in filenames:
                print os.path.join(dirname, filename)
                try: 
                    imgs.append(numpy.loadtxt(os.path.join(dirname, filename),dtype=dtype))
                    names.append(os.path.join(dirname, filename))
                    num+=1
                    if num>=limit:
                        return numpy.dstack(imgs)        
                    #del(imgs[0])
                except: 
                    print 'failed'
                if hh==None:
                    hh=self.get_handle("/"+tablename,imgs[0])

                try: hh.append(imgs[-1],num,0)
                except: pass
                
            return numpy.dstack(imgs)

    class dataHandle():
        """
        Provides access to an element in the datastore; primary means of 
        interface to data
        """
        def __init__(self,element):        
            self.table=element
            self.dataname=element.name.rsplit("_",1)[0]
            self.status="open"
            
        def append(self,data,shotnumber,repnumber):
            """
            adds data to this table in file.
            """
            if self.status=="open":
                row=self.table.row
                row['shotnumber']=shotnumber
                row['repnumber']=repnumber
                row[self.dataname]=data
                row.append()
            else: raise self.ClosedHandleError()

        def close(self):
            self.status="closed"
        
        class ClosedHandleError(Exception):
            def __str__(self): return "The corresponding file was closed" 
    
    class AccessRecord(tables.IsDescription):
        """
        structure for records of file access in associated h5 file
        """
        timestamp      = tables.FloatCol()   # timestamp of operation
        computerid     = tables.StringCol(36)  # name of machine performing op
        datastoreid    = tables.StringCol(36)  # type of action taken
        action         = tables.StringCol(36)  # type of action taken
        
        
class glab_liveheap():
    """
    This is the root class for live heaps.
    
    Live heaps are intended to facilitate run-time data collection and analysis,
    providing automated data-storage (holding a specified amount of recent data 
    elements in RAM, and archiving to disk afterward).  Analyses can be run in 
    the form of python scripts stored in an Analysis Library element
    """
    def permanent_id(self, shotnumber, repnumber=1):
        """
        returns a permanent id (resource locator) to retrieve data element with 
        """
        return "method for heap locator not yet written"
        
    def heave(self,heap_index=None):
        """
        this tosses an element from the RAM stack, and writes to disk if
        element is not already marked as archived
        """
        if heap_index==None:
            heap_index=self.stackorders.argmax()
        if not self.archived[heap_index]: pass
        # incomplete - next must send into hdf5 file
    def push(self,element,shotnumber,repnumber):
        """
        this will add an element to the top of the stack; if necessary an existing element
        will be heaved from the bottom of RAM stack to disk/file
        """
        # first determine if any elements must be heaved (possibly to disk) to make room
        mustheave=False
        try:
            pushind=numpy.where(self.stackorders==-1)[0][0]
        except IndexError: 
            pushind=self.stackorders.argmax()
            mustheave=True
        if mustheave:
            self.heave(pushind)
        # next must update the stack element itself
        self.shotnumbers[pushind]=shotnumber
        self.repnumbers[pushind]=repnumber
        self.stack[...,pushind]=element
        
    def getlivedata(self):
        """
        this method returns all data currently in RAM
        """
        pass
    def getdata(self,shotnumbers):
        """
        this method will return data corresponding to a list of shotnumbers
        """
        pass
    def getshotnumbers(self,FILE_PERSIST):
        """
        this method will return all shot numbers present in the file (default), 
        or all live (RAMish) shotnumbers, as specified in the FILE_PERSIST flag
        """
        pass
    def getliveshotnumbers(self):
        """
        this will be supercedeed by a flag on getshotnumbers
        """
        pass
    def __init__(self,options={}):
        """
        Constructor for live heaps
        
        sizeof should be the maximum number of data elements to hold in dynamic memory
        element_structure should be a list of dimensions for each data element
        typecode should be the numpy-supported Python data type for each element
        FILENAME should specify the desired hdf5 file to link to the heap
        GENERATOR ... i forget ...
        DATANAME should specify the desired name of the element        
        """
        # first define default options and override
        default_options={"sizeof":None, "element_structure":(), 
                         "typecode":numpy.dtype("float64"), "filename":None, 
                         "dataname":"untitled_"+str(uuid.uuid1())}
        default_options.update(options)
        # if no stack size given, set RAM size to 10MByte
        if default_options["sizeof"]==None:
            try:
                item_size = default_options["typecode"].itemsize
                ele_struc = default_options["element_structure"]
                size = int((1e+7)/(item_size*reduce(operator.mul,ele_struc)))
                default_options.update({"sizeof":size})
            except TypeError:
                size = int((1e+7)/default_options["typecode"].itemsize)
                default_options.update({"sizeof":size})
        # transfer to attributes of self
        for option in default_options.keys():
            setattr(self,option,default_options.get(option))
        # the data stack for RAM will be created immediately on intialization
        # and never redefined to avoid constant copying or re-reservation
        # a stack order >=0 defines the arrangement, -1 denotes empty element 
        self.stack=numpy.empty(self.element_structure+(self.sizeof,),dtype=self.typecode)
        self.stackorders=numpy.array([-1 for a in xrange(self.sizeof)])
        self.shotnumbers=numpy.array([-1 for a in xrange(self.sizeof)])
        self.repnumbers=numpy.array([-1 for a in xrange(self.sizeof)])
        self.archived=numpy.array([True for a in xrange(self.sizeof)])

# the code below was NDG's impulse on 12/15/13 of how to implement runtime analysis;
# prior to deciding this is better smoothly connected to XTSM

#    class Analysis_Library():
#        """
#        The analysis library provides a framework for running run-time data analysis
#        on a liveheap of data elements; each member of the library is a python function
#        attached to data describing when it should execute.  
#        """
#        def __init__(self, args={}):
#            """
#            Constructor for analysis library
#            
#            Arguments accepted in the args dictionary:
#                DataContext:  reference to a datacontext from which to draw other elements
#                all other items:  all others will be appended to the object by their name; use at own risk
#            """
#            for item in args.iteritems():
#                setattr(self,item[0],item[1])
#            self.members={}
#            return self 
#            
#        def add(self,analyses):
#            """
#            adds an analysis or analyses to the library; provide them as a dictionary of elements
#            """
#            self.members.update(analyses)
#            
#        class Analysis():
#            """
#            The analysis class wraps a function used for data analysis with
#            data about when to execute.
#            """