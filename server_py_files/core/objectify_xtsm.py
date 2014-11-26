"""
This software is described in detail at https://amo.phys.psu.edu/GemelkeLabWiki/index.php/Python_parser
         
"""
import copy
import ast  # abstract syntax tree for scripts
import msgpack, msgpack_numpy, struct  # support for messagepack format data
msgpack_numpy.patch()
import gnosis.xml.objectify # standard package used for conversion of xml structure to Pythonic objects, also core starting point for this set of routines
import sys, StringIO, urllib, uuid # standard packages for many things
import inspect, pdb, traceback, code  # used for profiling and debugging this code
import numpy, scipy, math, bisect # math routines 
numpy.set_printoptions(suppress=True,precision=7, threshold='nan')  # sets default printing options for numpy
from bitarray import bitarray # used to manipulate individual bits in arrays without wasting memory by representing bits as bytes
from lxml import html
from xml.sax import saxutils
import io
import time
import hdf5_liveheap, tables
import sheltered_script, live_content, glab_figure, softstring
import XTSM_cwrappers
import simplejson
import collections 
import profile
import pstats
import commands
import sync

#from IPy import IP

DEBUG = False

XO_IGNORE=['PCDATA']  # ignored elements on XML_write operations

class XTSM_core(object):
    """
    Default Class for all elements appearing in an XTSM tree; contains generic methods
    for traversing the XTSM tree-structure, inserting and editing nodes and attributes,
    writing data out to XML-style strings, and performing parsing of node contents in
    python-syntax as expressions
    """
    scope={}  # dictionary of names:values for parsed variables in element's scope  
    scoped=False  # records whether scope has been determined
    scopePeers={} # contains a list of {TargetType,TargetField,SourceField} which are scope-peers, to be found by matching TargetType objects with TargetField's value equal to SourceField's value

    def __init__(self,value=None):
        self._seq=[]
        if value==None:
            self.PCDATA=''
        else:
            self.PCDATA=value
            self._seq={value}
        self.__parent__=None

    def insert(self,node,pos=0):
        "inserts a node node at the position pos into XTSM_core object"
        node.__parent__=self
        if pos < 0: pos=0
        if ((pos=="LAST") or (pos > self._seq.__len__())): pos=self._seq.__len__()
        nodeType=type(node).__name__.split('_XO_')[-1]
        if hasattr(self, nodeType):  # begin insertion process
            if getattr(self,nodeType).__len__() > 1:
                getattr(self,nodeType).append(node)
                getattr(self,'_seq').insert(pos,node)
            else:
                setattr(self,nodeType,[getattr(self,nodeType),node])
                getattr(self,'_seq').insert(pos,node)
        else:
            setattr(self, nodeType, node)
            getattr(self,'_seq').insert(pos,node)
        self.onChange(self)
        return node
        
    def find_closest(self,array1,array2): #LRJ 3-11-2014
        '''
        Returns the indicies of array1 that are closest to the values of array2
        Array1 must be an ordered array
        '''
        idx=array1.searchsorted(array2)
        idx=numpy.clip(idx,1,len(array1)-1)
        left=array1[idx-1]
        right=array1[idx]
        idx-=array2-left<right-array2
        return idx
        
    def getDictMaxValue(self,dictionary): #LRJ 10-23-2013
        """
        Finds and returns the largrest numeric value in a dictionary
        """        
        self.valut=list(dictionary.values())
        return max(self.valut)
    
    def getActiveSequence(self):
        """
        Find and return the active sequence
        """
        for seq in self.getOwnerXTSM().body.Sequence:
            try: 
                if seq.current_value=="active":
                    return seq
            except AttributeError: continue
    
    def addAttribute(self,name,value):
        "adds an (XML) attribute to the node with assigned name and value"
        setattr(self,name,value)
        self.onChange(self)
        return getattr(self,name)
        
    def getOwnerXTSM(self):
        """
        Returns top-level XTSM element
        """
        if self.__parent__:
            return self.__parent__.getOwnerXTSM()
        else:
            return self
            
    def getFirstParentByType(self,tagtype):
        """
        Searches up the XTSM tree for the first ancestor of the type tagtype,
        returning the match, or None if it reaches toplevel without a match
        """
        if self.get_tag()==tagtype:
            return self
        else:
            if self.__parent__:
                return self.__parent__.getFirstParentByType(tagtype)
            else: return None
        
    def getChildNodes(self):
        """
        Returns all XTSM children of the node as a list
        """
        if (type(self._seq).__name__=='NoneType'):
            return []
        child_nodes = [a for a in self._seq if type(a)!=type(u'')]
        return child_nodes
        
    def getDescendentsByTypeRecursively(self,targetType):
        """
        Returns a list of all descendents of given type
        Original implementation by Nate
        """
        
        res=[]
        for child in self.getChildNodes():
            #print self, self.getChildNodes()
            if hasattr(child,'getDescendentsByType'):
                res.extend(child.getDescendentsByType(targetType)) 
        if hasattr(self,targetType): 
            res.extend(getattr(self,targetType))
                    
        #print res
        return res
    
    def getDescendentsByType(self, target_type):
        """
        Returns a list of all descendents of given type.
        """
        #res = self.getDescendentsByTypeRecursively(target_type)
        res2 = self.getDescendentsByTypeIteratively(target_type)
        '''
        if collections.Counter(res) != collections.Counter(res2):
            print target_type
            print 'getDescendentsByTypeRecursively:', res
            print 'getDescendentsByTypeIteratively:', res2
            pdb.set_trace()        
        '''
        return res2
    
    def getDescendentsByTypeIteratively(self, target_type):
        """
        Returns a list of all descendents of given type.
        Implemented without recursion.
        Implemented by CP 2017/09/30
        """
        def iterativeChildren(top_nodes,target_type):
            """
            Helper function to iterate through the child nodes.
            """
            #pdb.set_trace()
            results = []
            nodes = top_nodes
            while True:
                if not nodes:
                    break
                for i, node in enumerate(nodes[:]):
                #iterates over a copy of the nodes list
                    if hasattr(node, 'get_tag'):
                        if(node.get_tag() == target_type ):#or hasattr(node,target_type)
                            results.extend(node)
                    if hasattr(node, 'getChildNodes'):
                        newNodes = node.getChildNodes()
                        nodes.extend(newNodes)
                    nodes.remove(node)
            return results
            
        decendents = iterativeChildren(self.getChildNodes(),target_type)
        return decendents   
    
    def getItemByFieldValue(self,itemType,itemField,itemFieldValue,multiple=False):
        """
        Returns the first XTSM subelement of itemType type with field itemField equal to itemFieldValue
        Note: will search all descendent subelements!
        """
        hits=set()
        if hasattr(self,itemType):
            for item in getattr(self,itemType): # advance to matching element
                if getattr(item,itemField).PCDATA==itemFieldValue:
                    if multiple: hits=hits.union({item})
                    else: return item
        for subelm in self.getChildNodes():
            if not hasattr(subelm,'getItemByFieldValue'): continue
            item=subelm.getItemByFieldValue(itemType,itemField,itemFieldValue,multiple)
            if item!=None and item!={}:
                if multiple: hits=hits.union(item) 
                else: return item
        if multiple: return hits
        else: return None 

    def getItemByFieldValueSet(self,itemType,FieldValueSet):
        """
        Returns all subelements of type which have all given fields with specified values
        FieldValueSet should be a dictionary of field:value pairs
        """
        for step,pair in enumerate(FieldValueSet.items()):
            if step==0: hits=self.getItemByFieldValue(itemType,pair[0],pair[1],True)
            else: hits=hits.intersection(self.getItemByFieldValue(itemType,pair[0],pair[1],True))
            if len(hits)==0: return hits
        return hits.pop()

    def getItemByAttributeValue(self,attribute,Value,multiple=False):
        """
        Returns the first subelement with (non-XTSM) attribute of specified value
        if multiple is true returns a list of all such elements
        """
        hits=set()
        if hasattr(self,attribute):
            if getattr(self,attribute)==Value: 
                if multiple: hits=hits.union({self})
                else: return self
        for subelm in self.getChildNodes():
            a=subelm.getItemByAttributeValue(attribute,Value,multiple) 
            if a: 
                if multiple: hits=hits.union({a})
                else: return a
        if multiple: return hits
        else: return None
                
    def parse(self,additional_scope=None):
        """
        parses the content of the node if the node has only 
        textual content. 
        ->>if it has parsable subnodes, it will NOT parse them -(NEED TO TAG PARSABLE NODES)
        this is done within the node's scope
        side-effect: if scope not already built, will build
        entirely untested
        """
        if (not hasattr(self,'PCDATA')): return None  # catch unparsable
        if (self.PCDATA==None): return None
        if not isinstance(self.PCDATA,basestring): return None
        suc=False        
        try:        # try to directly convert to floating point
            self._parseValue=numpy.float64(self.PCDATA)
            suc=True
        except ValueError:    # if necessary, evaluate as expression
            if (not self.scoped): self.buildScope()  # build variable scope
            if additional_scope!=None:       
                tscope=dict(self.scope.items()+additional_scope.items())
            else: tscope=self.scope
            try: 
                self._parseValue=eval(html.fromstring(self.PCDATA.replace('#','&')).text,globals(),tscope)  # evaluate expression
                suc=True
            except NameError as NE:
                self.addAttribute('parse_error',NE.message)
        if suc:
            if hasattr(self._parseValue,'__len__'):
                if isinstance(self._parseValue,basestring) or len(self._parseValue)<2:
                    self.addAttribute('current_value',str(self._parseValue))
            else: self.addAttribute('current_value',str(self._parseValue))  # tag the XTSM
            return self._parseValue
        else: return None
    
    def buildScope(self):
        """
        constructs the parameter scope of this node as dictionary of variable name, value
        first collects ancestors' scopes starting from eldest
        then collects scopes of peers defined in scopePeers
        then collects parameter children 
        those later collected will shadow/overwrite coincident names
        """
        if self.__parent__: # if there is a parent, get its scope first (will execute recursively up tree)
            self.__parent__.buildScope()
            self.scope.update(self.__parent__.scope) # append parent's scope (children with coincident parameters will overwrite/shadow)
        if (not self.scoped):
            if hasattr(self,'scopePeers'):
                root=self.getOwnerXTSM()
                for peerRelation in self.scopePeers:
                    peerElm=root.getItemByFieldValue(peerRelation[0],peerRelation[1],getattr(self,peerRelation[2]).PCDATA) # loop through scope peers
                    if (peerElm != None):
                        if (not hasattr(peerElm,'scoped')): peerElm.buildScope() # build their scopes if necessary
                        self.scope.update(peerElm.scope) # append their scopes
            if hasattr(self,'Parameter'):
                for parameter in self.Parameter: # collect/parse parameter children
                    if (not hasattr(parameter,'_parseValue')): parameter.Value[0].parse()
                    self.scope.update({parameter.Name.PCDATA: parameter.Value[0]._parseValue})
        self.scoped=True # mark this object as scoped
        return None

    def buildAnalysisScope(self):
        """
        constructs the variable scope of this node as dictionary of variable name, value
        first collects scope as defined in buildScope (same method as used during parse)
        then builds scope from peer Samples, dataNodes and dataLinks
        those later collected will shadow/overwrite coincident names
        
        if this element is not yet scopable due to missing data, will return False
        otherwise on success returns True
        """
        if self.analysisScoped: return True        
        if not self.scoped: self.buildScope()
        self.analysisScope={}
        scopedPeers=[c for c in self.__parent__.getChildNodes() if c.analysisScoped]
        # if a peer is already scoped, copy its scope
        if len(scopedPeers)>0: self.analysisScope.update(scopedPeers[0].analysisScope)
        else:
            for child in [c for c in self.__parent__.getChildNodes() if hasattr(c,"contribute_dataScope")]:
                self.analysisScope.update(c.contribute_dataScope())
        # here need to ask peers for contribution to data scope
        self.analysisScoped=True # mark this object as scoped
        return None

    def get_tag(self):
        """
        returns the tagname of the node
        """
        return type(self).__name__.split('_XO_')[-1]
        
    def set_value(self, value, REWRITE_NDG=False):
        """
        sets the textual value of a node
        """
        if not REWRITE_NDG:
            pos=0
            if (self.PCDATA in self._seq):
                pos=self._seq.index(unicode(str(value)))
                self._seq.remove(unicode(str(value)))
            self._seq.insert(pos,unicode(str(value)))
            self.PCDATA=unicode(str(value))
            self.onChange(self)
            return self
        else:
            pos=0
            if (self.PCDATA in self._seq):
                pos=self._seq.index(self.PCDATA)
                self._seq.remove(self.PCDATA)
            self._seq.insert(pos,unicode(str(value)))
            self.PCDATA=unicode(str(value))
            self.onChange(self)
            return self
            
        
    def generate_guid(self, depth=None):
        """
        generate a unique id number for this element and all descendents to
        supplied depth; if no depth is given, for all descendents.
        if element already has guid, does not generate a new one
        """
        if (not hasattr(self,'guid')):
            self.addAttribute('guid',str(uuid.uuid1()))
        if (depth == None):
            for child in self.getChildNodes(): child.generate_guid(None)
        else:
            if (depth>0):
                for child in self.getChildNodes(): child.generate_guid(depth-1)
        return
    
    def generate_guid_lookup(self,target=True):
        """
        creates a lookup list of guid's for all descendent elements that possess one
        adds the result as an element 'guid_lookup' if target input is default value True
        """
        if hasattr(self,'guid'): 
            guidlist=[self.guid]
        else:
            guidlist=[]
        for child in self.getChildNodes():
            guidlist.extend(child.generate_guid_lookup(False))
        if target: self.guid_lookup=guidlist
        return guidlist
    
    def generate_fasttag(self,running_index,topelem=None):
        """
        creates a lookup index and reference table
        """
        self._fasttag=running_index
        if topelem==None: 
             topelem=self
             topelem._fasttag_dict={running_index:self}
        else: topelem._fasttag_dict.update({running_index:self}) 
        running_index+=1
        for child in self.getChildNodes(): running_index=child.generate_fasttag(running_index,topelem)
        return running_index
    
    def remove_all(self, name):
        delattr(self,name)
        self._seq=[it for it in self._seq if type(it)!=getattr(gnosis.xml.objectify,"_XO_"+name)] 
        self.onChange(self)
        pass

    def remove_node(self,node):
        """
        removes a specified node from the element
        """
        # remove from xml sequence
        self._seq.remove(node)
        # remove from python object attributes
        elmsthistype=getattr(self,node.get_tag())
        # if there's only one and it's this one, delete the attribute
        if (len(elmsthistype)==1):
            if elmsthistype[0]==node: delattr(self,node.get_tag())
            return
        # if there are many, delete the one from list
        for elmthistype in elmsthistype:
            if elmthistype==node:
                getattr(self,node.get_tag()).remove(node)
                return
        

    def onChange(self,elm=None):
        """
        default XTSM onchange element - all parents will be notified of child
        element changes.  In addition, any nodes tagged (using registerListener) 
        as needing notifications of a change on this element
        will have their callback method called
        """
        """
        CP - pertaining to problems updating the GUI after receiving a databomb and inserting a DataLink
        isActive represents if there is any elements that are still waiting on data to come back.
        Check to see if DataLinks are active...
        try .write_xml() on the actual Node that I inserted.
        is the data listener there?
        """
        #pdb.set_trace()
        try: 
            for listener in self._registeredListeners:  
                params = self._registeredListeners[listener]
                del params['method']  # avoids passing the method to itself
                params.update({"changed_element":self})
                params.update({"root_changed_element":elm})
                self._registeredListeners[listener]['method'](params)  # calls the callback associated in the dictionary
        except AttributeError:
            pass
        if self.__parent__:
            return self.__parent__.onChange(elm)
        else:
            return None

    def registerListener(self,listener_callback):
        """
        allows another element to provide a callback mechanism which fires
        whenever this element changes.  argument listener should be a method or
        function which will be executed on the change, or a dictionary, with
        at least one argument called 'method' with value set to the method to be called, 
        and the remaining entries as keyword arguments for the method
        
        returns a unique id for the listener element installed
        
        this is a separate mechanism from installListeners (installListeners is
        used after parsing to install data listeners which attach to incoming
        databomb elements).  registerListener specifically allows one XTSM 
        element to listen for changes on another.
        """
        if type(listener_callback)!=type({}): 
            listener_callback={"method":listener_callback}        
        listener_callback.update({"listener_id":uuid.uuid1()})
        if not hasattr(self,"_registeredListeners"): self._registeredListeners={}
        self._registeredListeners.update({listener_callback['listener_id']:listener_callback})
        return listener_callback['listener_id']

    def deregisterListener(self,listener_id):
        """
        removes a listener from service, using the identifier that was returned
        when the listener was registered - returns a boolean indicating success
        """
        try: del self._registeredListeners[listener_id]
        except AttributeError: return False
        except KeyError: return False
        return True

    def write_xml(self, out=None, tablevel=0, whitespace='True'):
        """
        Serialize an _XO_ object back into XML to stream out; if no argument 'out' supplied, returns string
        If tablevel is supplied, xml will be indented by level.  If whitespace is set to true, original whitespace
        will be preserved.
        """
        global XO_IGNORE
        mode=False
        newline=False
        firstsub=True
        # if no filestream provided, create a stream into a string (may not be efficient)
        if (not out):
            mode=True
            out=StringIO.StringIO()
        # write tag opening
        out.write(tablevel*"  "+"<%s" % self.get_tag())
        # attribute output; ignore any listed in global XO_IGNORE
        for attr in self.__dict__:
            if (isinstance(self.__dict__[attr], basestring)):
                if (attr in XO_IGNORE): continue 
                out.write(' ' + attr + '="' + self.__dict__[attr] + '"')
        out.write('>')
        # write nodes in original order using _XO_ class _seq list
        if self._seq:            
            for node in self._seq:
                if isinstance(node, basestring):
                    if (not whitespace):
                        if node.isspace():
                            pass
                        else: 
                            out.write(node)                            
                    else: out.write(node)
                else:
                    if firstsub:
                        out.write("\n")
                        firstsub=False
                    node.write_xml(out,0 if (tablevel==0) else (tablevel+1),whitespace)
                    newline=True
        # close XML tag
        if newline:
            out.write(tablevel*"  ")
        out.write("</%s>\n" % self.get_tag())
        # if mode is stringy, return string        
        if mode:
            nout=out.getvalue()
            out.close()
            return nout
        return None
        
    def countDescendents(self,tagname):
        """
        Counts number of descendent nodes of a particular type
        """
        cnt=0
        for child in self.getChildNodes():
            cnt+=child.countDescendents(tagname)
        if hasattr(self,tagname):
            return cnt+getattr(self,tagname).__len__()
        else: return cnt
        
    def get_childNodeValue_orDefault(self,tagType,default):
        """
        gets the value of the first child Node of a given tagtype, 
        or returns a default value if the node does not exist
        or if it is empty
        """
        if not hasattr(self,tagType): return default
        val=getattr(self,tagType).PCDATA     
        if val != u'': return val
        else: return default
        
    def installListeners(self,listenerManager):
        """
        runs down the XTSM tree, generating and adding data event listeners
        to the provided manager for all elements which have a 
        __generate_listener__() method defined
        """
        #print "In class XTSM_core, func installListeners"       
        if hasattr(self,"__generate_listener__"):
            params = self.__generate_listener__()
            if params != None:
                listenerManager.spawn(params)
        child_nodes = self.getChildNodes()
        for idx, child in enumerate(child_nodes):
            try:
                child.installListeners(listenerManager)
            except AttributeError:#exceptions.AttributeError: 'int' object has no attribute 'installListeners' Why? CP
                #pdb.set_trace()#It's because install listeners is trying to call, installlisteners on <Script><ScriptOutput><Value>1
                return
                    
        
class XTSM_Element(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class ClockPeriod(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class body(gnosis.xml.objectify._XO_,XTSM_core):
    def parseActiveSequence(self):
        """
        finds/parses SequenceSelector node, identifies active Sequence, initiates subnodeParsing,
        constructs control arrays, returns the ParserOutput node, which is also attached as a 
        subnode to the active Sequence node        
        """
        try:
            if self.SequenceSelector:
                if not hasattr(self.SequenceSelector[0],'current_value'): 
                    self.SequenceSelector[0].parse() # parse SS if not done already
                try:
                    aseq=self.getItemByFieldValue('Sequence','Name',self.SequenceSelector[0].current_value) # identify active sequence by name and begin collection
                    aseq.parse()
                except Exception as Error:
                    print Error
                    print traceback.format_exc()
            elif self.__parent__.SequenceSelector:
                if not hasattr(self.__parent__.SequenceSelector[0],'current_value'): 
                    self.__parent__.SequenceSelector[0].parse() # parse SS if not done already
                try:
                    aseq=self.getItemByFieldValue('Sequence','Name',self.__parent__.SequenceSelector[0].current_value) # identify active sequence by name and begin collection
                    aseq.parse()
                except Exception as Error:
                    print Error
        except Exception as Error:
            print Error
        aseq.addAttribute("current_value","active")
        return aseq.ParserOutput[0]

class TimingProffer():
    """
    A helper class defined to aid XTSM parsing; holds data about request for timing events
    from edges, intervals... Provides methods for compromise timing when requests
    are conflictory or require arbitration of timing resolution, etc...
    """
    data={}  # a dictionary to be filled with arrays for each type of timing request: edge,interval, etc...
    valid_entries={'Edge':0,'Interval':0,'Sample':0} # will hold the number of elements in the array which are currently valid data
    data_per_elem={'Edge':5,'Interval':7,'Sample':7} # the number of elements needed to understand a request: time, value, timing group, channel...
    data_types={'Edge':numpy.float64,'Interval':numpy.float64,'Sample':numpy.float64}  # the data_type to store

    def __init__(self,generator):
        """
        Creates the timingProffer from a root element (such as a sequence)
        """
        # the following loops through all elements defined above as generating
        # proffers, creates a blank array to hold proffer data, stored in data dictionary. Take edges as example,
        # if the sequence has n edges and each edges have 5 parameters, then the array dimension would be n by 5
        for gentype in self.valid_entries.keys():
            self.data.update({gentype:numpy.empty([generator.countDescendents(gentype),self.data_per_elem[gentype]],self.data_types[gentype])})
    
    def insert(self,typename,elem):
        '''
        Inserts a proffer elements
        '''
        try:
            self.data[typename][self.valid_entries[typename]]=elem
            self.valid_entries[typename]=self.valid_entries[typename]+1
        except IndexError:  # Reset index to 0 if index is out of range.
            self.valid_entries[typename] = 0
            self.data[typename][self.valid_entries[typename]]=elem
            self.valid_entries[typename]=self.valid_entries[typename]+1

class Emulation_Matrix():
    """
    A helper class defined to store result of hardware emulation for a sequence
    should follow constructs at line 674 of IDL version
    NOT STARTED
    """
    pass

class GroupNumber(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class ControlData(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM class to store the control arrays generated by the parser
    """

class ParserOutput(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM class to store the control array structure generated by the parser
    """
    def package_timingstrings(self):
        """
        packaging of all group timingstrings into a single timingstring with header
        """
        try: 
            headerLength=80
            bodyLength=sum([(cd.ControlArray.timingstring).shape[0] for cd in self.ControlData])
            num_tg=len(self.ControlData)
            ts=numpy.empty(bodyLength+num_tg*headerLength+1,dtype=numpy.uint8)
            ts[0]=num_tg            
            hptr=1
            ptr=headerLength*num_tg + 1
            for cd in self.ControlData:
                ts[hptr:hptr+headerLength] = cd.ControlArray.generate_package_header()
                hptr+=headerLength
                ts[ptr:ptr+cd.ControlArray.timingstring.shape[0]] = cd.ControlArray.timingstring
                ptr+=cd.ControlArray.timingstring.shape[0]
            # Add in length of entire string to begininning.
            try:
                totalLength = ts.shape
                self.timing_string_ints = ts
                tl=numpy.asarray(totalLength, dtype=numpy.uint64).view('u1')
                ts=numpy.concatenate((tl, ts))
            except OverflowError: return ""  # Overflow error means length of ts is greater than 8 byte integer.
        except AttributeError: return ""
        return ts


class ControlArray(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM class: control arrays generated by the parser
    """
    def construct(self,sequence,channelMap,tGroup):
        """
        constructs the timing control array for a timingGroup in given sequence
        sequence should already have collected TimingProffers
        """
        
        TIMING=False
        timing=[]      
        if TIMING: t0=time.time()
        
        # bind arguments to object
        self.sequence=sequence
        self.channelMap=channelMap
        self.tGroup=tGroup
        del sequence,channelMap,tGroup
        
        
        # get data about the channel, sequence and its clocking channel
        self.get_biographics()
        # locate the edges and intervals for this timing group, generated explicitly or by clocking requests                
        if TIMING: timing.append(("biographics FOR GROUP "+str(self.tGroup),time.time()))        
        self.get_edgeSources()
        if TIMING: timing.append(("get_edge_sources",time.time()))                
        # coerce explicit timing edges to a multiple of the parent clock's timebase
        self.coerce_explicitEdgeSources() #LRJ 3-7-2014, edge coercion will be done inside of construct_denseT so that clockers and outputs agree on times.
        if TIMING: timing.append(("coerce_explicitEdgeSources",time.time()))        
        # create a list of all times an update is needed for this timing group                
        self.construct_denseT()
        if TIMING: timing.append(("construct_denseT",time.time()))        
        # clockstring management: save the current timinggroup's clocking string to the ParserOutput node,
        # also find and eventually insert clocking strings for other timinggroups which should occur on a channel in the current timinggroup
        if not hasattr(self.sequence.ParserOutput,"clockStrings"): self.sequence.ParserOutput.clockStrings={}
        self.sequence.ParserOutput.clockStrings.update({self.tGroup:(self.denseT/self.parentgenresolution).astype('uint64')})
        if TIMING: timing.append(("clock strings updates",time.time()))        
        if self.direction!='INPUT':
            # sort edges and intervals by group index (channel), then by (start)time
            self.sort_edgeSources()
            if TIMING: timing.append(("sort_edgeSources",time.time()))        
            # create a channelData object for every channel; accumulates all edges for each channel
            self.channels={channum:channelData(self,channum) for channum in range(self.numchan)} 
            if TIMING: timing.append(("channel creations",time.time()))        
            # HERE WE NEED TO CONVERT FLAGGED DIGITAL BOARDS INTO SINGLE CHANNEL INTEGER REPRESENTATIONS
            if self.ResolutionBits==1 and hasattr(self.tGroupNode,'ParserInstructions'):
                if self.tGroupNode.ParserInstructions[0].get_childNodeValue_orDefault('RepresentAsInteger','yes').lower() == 'yes':
                    self.repasint=True
                    self.RepresentAsInteger()
                    if TIMING: timing.append(("rep as int",time.time()))        

            # Break these into channel control strings - first determine necessary size and define empty array
        else: 
            self.channels={channum:channelData(self,channum) for channum in range(self.numchan)}
            if TIMING: timing.append(("channel creations",time.time()))        
        self.TimingStringConstruct()
        if TIMING: timing.append(("timing string construct",time.time()))        
        
        if TIMING: 
            prior=t0
            allsteps=[]
            for step in timing:
                allsteps.append((step[0],step[1]-prior))
                prior=step[1]
            print allsteps
        return self

    def get_biographics(self):
        """
        get biographical data about the timing group: number of channels, its clock period, whether it is a delaytrain
        """
                
        self.tGroupNode=self.channelMap.getItemByFieldValue('TimingGroupData','GroupNumber',str(self.tGroup))
        self.clockgenresolution=numpy.float64(self.channelMap.tGroupClockResolutions[self.tGroup])
        self.numchan=int(self.tGroupNode.ChannelCount.PCDATA)
        try: self.range=numpy.float64((self.tGroupNode.Range.PCDATA))
        except AttributeError: self.range=numpy.float64(self.tGroupNode.Scale.PCDATA)
        self.ResolutionBits=int(self.tGroupNode.ResolutionBits.PCDATA)
        # math.ceil returns the smallest integer not less than the argument.         
        self.bytespervalue=int(math.ceil(self.ResolutionBits/8.))
        try: self.direction={"IN":"INPUT","OUT":"OUTPUT"}[str(self.tGroupNode.Direction.PCDATA).upper().strip().split('PUT')[0]]
        except AttributeError: self.direction="OUTPUT"        
        # The following lines introduces the calibrition for the channel value.
        if not self.tGroupNode.DACCalibration.PCDATA==None:
            self.DACCalibration=numpy.float64(self.tGroupNode.DACCalibration.PCDATA) #LRJ 11-8-2013
        else:
            self.DACCalibration= numpy.float64((pow(numpy.float64(2.),numpy.float64(self.ResolutionBits-1))-1)/(self.range/numpy.float64(2.)))
            
        
        if hasattr(self.tGroupNode,'SoftwareTrigger'): self.swTrigger=True 
        if hasattr(self.tGroupNode,'DelayTrain'): self.dTrain=True 
        else: self.dTrain=False
        # if not self-clocked, get data about clocker
        if (self.tGroupNode.ClockedBy.PCDATA != u'self'):
            self.clocksourceNode=self.channelMap.getChannel(self.tGroupNode.ClockedBy.PCDATA)
            self.clocksourceTGroup=self.channelMap.getItemByFieldValue('TimingGroupData'
                                                                  ,'GroupNumber',
                                                                  self.clocksourceNode.TimingGroup.PCDATA)
            self.parentgenresolution=self.channelMap.tGroupClockResolutions[int(self.clocksourceTGroup.GroupNumber.PCDATA)]
            self.bytesperrepeat=4
            if self.ResolutionBits==u'1': self.ResolutionBits=0
        else: 
            self.parentgenresolution=self.clockgenresolution
            self.bytesperrepeat=4
        # Find the end time for the sequence
        if hasattr(self.sequence,'endtime'): self.seqendtime=self.sequence.endtime
        else: self.seqendtime=self.sequence.get_endtime()
        # if delay train group, use ResolutionBits for time-resolution
        try: 
            if self.dTrain: 
                self.bytespervalue=0
                self.bytesperrepeat=int(math.ceil(self.ResolutionBits/8.))
        except AttributeError: pass

    def get_edgeSources(self):
        
        """
        gets all sources of timing edges (Edges, Intervals) for this group from the timing Proffer object
        """
       
        # Find the edge that belongs to this timinggroup        
        if len(self.sequence.TimingProffer.data['Edge'])>0:
            self.groupEdges=(self.sequence.TimingProffer.data['Edge'])[(((self.sequence.TimingProffer.data['Edge'])[:,0]==int(self.tGroup)).nonzero())[0],]
        else: self.groupEdges=self.sequence.TimingProffer.data['Edge']
        # Find the interval that belongs to this timinggroup       
        if len(self.sequence.TimingProffer.data['Interval'])>0:
            self.groupIntervals=(self.sequence.TimingProffer.data['Interval'])[(((self.sequence.TimingProffer.data['Interval'])[:,0]==int(self.tGroup)).nonzero())[0],]
        else: self.groupIntervals=self.sequence.TimingProffer.data['Interval']
        # Find the samples that belong to this timinggroup       
        if len(self.sequence.TimingProffer.data['Sample'])>0:
            self.groupSamples=(self.sequence.TimingProffer.data['Sample'])[(((self.sequence.TimingProffer.data['Sample'])[:,0]==int(self.tGroup)).nonzero())[0],]
        else: self.groupSamples=self.sequence.TimingProffer.data['Sample']
        # transpose to match IDL syntax
        self.groupEdges=self.groupEdges.transpose().astype(numpy.float64) # NDG 051714 to float64
        self.groupIntervals=self.groupIntervals.transpose().astype(numpy.float64) # NDG 051714 to float64
        self.groupSamples=self.groupSamples.transpose().astype(numpy.float64) # NDG 051714 to float64
        # now check if any channels in this timingGroup are claimed as clocks by other timingGroups
        self.cStrings={}  # dictionary of clock times for each channel that clocks another timingGroup
        for channel in range(self.numchan):
            clocker=self.channelMap.isClock(self.tGroup,channel)
            if clocker:
                clockString = numpy.array(self.sequence.ParserOutput.clockStrings[clocker], dtype = 'float64')
                self.cStrings.update({channel:(clockString*numpy.float64(self.clockgenresolution))})
                # REMOVE ALL GROUP EDGES AND GROUP INTERVALS ON CLOCKING CHANNELS HERE

    def coerce_explicitEdgeSources(self):
        """
        coerce explicit timing edges to a multiple of the parent clock's timebase
        (using the parent's resolution allows us to subresolution step.)
        """
        self.lasttimecoerced=numpy.float64(numpy.ceil(numpy.float64(self.seqendtime)/numpy.float64(self.clockgenresolution)))*numpy.float64(self.clockgenresolution)    


    def construct_denseT(self):
        """
        constructs a list of all times an update is necessary on this timing group:
        this could arise from an explicitly defined edge, an update in an interval,
        or from a clocking pulse needed by another channel 
        """
        
        BENCHMARK=False
        if BENCHMARK: 
            t0=time.time()            
            self.construct_denseT_old()
            t1=time.time()
            old_denseT=self.denseT
            print "old denseT: ", t1-t0
            t0=time.time()
        
        # first create a sorted list of all times at beginning or end of interval, at an edge, or beginning or start of sequence
        self.alltimes=numpy.unique(numpy.concatenate([self.groupIntervals[2:4,].flatten(),self.groupEdges[2,],[self.channelMap.hardwaretime.astype(numpy.float64), numpy.float64(self.lasttimecoerced)]]))
        #self.alltimes=XTSM_cwrappers.merge_sorted([self.groupIntervals[2:4,].flatten(),self.groupEdges[2,],numpy.array([self.channelMap.hardwaretime,self.lasttimecoerced],dtype=numpy.float64)])

        # create a list denseT of all update times necessary in the experiment 
        self.denseT=numpy.array([self.channelMap.hardwaretime],dtype=numpy.float64)       
        
        self.groupSamOrInts=numpy.hstack((self.groupIntervals,self.groupSamples))
        # loop through all windows between members of alltimes
        for starttime,endtime in zip(self.alltimes[0:-1],self.alltimes[1:]):
            
            # identify all intervals in this group active in this window
            if self.groupSamOrInts.size!=0:
                pre=(self.groupSamOrInts[2,]<=starttime).nonzero()
                post=(self.groupSamOrInts[3,]>starttime).nonzero()
                if ((len(pre)>0) and (len(post)>0)):
                    aInts=numpy.intersect1d(numpy.array(pre),numpy.array(post))
                    if aInts.size>0:
                        # find compromise timing resolution (minimum requested, coerced to parent clock multiple)
                        Tres=math.ceil(round(min(self.groupSamOrInts[5,aInts])/self.clockgenresolution,3))*self.clockgenresolution
                        # define the times in this window using universal time
                        T=numpy.linspace(starttime,endtime,(endtime-starttime)/Tres+1).astype(numpy.float64)
                        self.denseT=numpy.append(self.denseT,T)
                    else: self.denseT=numpy.append(self.denseT,starttime)   
                else: self.denseT=numpy.append(self.denseT,starttime)
            else: self.denseT=numpy.append(self.denseT,starttime)
        
        # This line add the endtime to the end of the denseT.       
        self.denseT=numpy.append(self.denseT,numpy.float64(self.lasttimecoerced))

        # now incorporate all clockstrings for clock channels:
        # merge all clock update times with denseT from edges and intervals (costly operation)
        if self.dTrain == True:  cind=2
        else:                    cind=0          # Data in delay train cEdges is stored differently.
        allclcks=[]
        for clockChannel in self.cStrings:
            try: 
                allclcks.append(self.cEdges[clockChannel][cind,:])
            except AttributeError: 
                self.cEdges={}
                self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                allclcks.append(self.cEdges[clockChannel][cind,:])
            except KeyError: 
                self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                allclcks.append(self.cEdges[clockChannel][cind,:])
    
        #Build an array indicating the clocking chain for the timing group. 
        #Format is an array of timing group numbers. For example tg 3 would give [2,6,0] which indicates that tg3 is clocked by tg 2 is clocked by tg 6 is clocked by tg 0
        self.channelMap.getClocks()
        try: self.clkchain=numpy.array([self.channelMap.Clocks[self.tGroup][0]],dtype=numpy.float64)
        except KeyError: self.clkchain=numpy.array([],dtype=numpy.float64)
        for elem in range(self.getDictMaxValue(self.channelMap.tGroupClockLevels)-self.channelMap.tGroupClockLevels[self.tGroup]):
            try :
                self.clkchain=numpy.append(self.clkchain,self.channelMap.Clocks[self.clkchain[elem]][0])
            except KeyError :pass
            except IndexError: pass
        # coerce denseT times collected so far repeatedly "on-grid" of each parent clocker
        coer_chain = [numpy.float64(self.channelMap.tGroupClockResolutions[elem]) for elem in self.clkchain]
        coer_chain.insert(0,numpy.float64(self.channelMap.tGroupClockResolutions[self.tGroup]))
        if len(coer_chain)>1:
            coer_chain_red=[ce for ce,cen in zip(coer_chain[0:-1],coer_chain[1:]) if (ce/cen)%numpy.float64(1.0) != numpy.float64(0.0) ]
            coer_chain_red.insert(0,coer_chain[0])
            coer_chain=coer_chain_red
        for coer in coer_chain:
            self.denseT=((self.denseT/numpy.float64(coer)).round())*numpy.float64(coer)

        # the next few lines merge all denseT elements (from intervals and edges on this timing group)
        # with all clocking edges from channels on this timing group that clock another group
        # since denseT itself and each clocker's edges are time-ordered lists, we will use a merging algorithm
        # that is optimized for generating a sorted merged array from presorted arrays. Moreover, its'
        # back-effect on the input arrays is to replace their values (initially times) with their position
        # in the merged output array.
        
        if len(allclcks)>=1:
            allclcks.append(self.denseT)  # adds denseT array to a list of arrays to be merged
            self.denseT=XTSM_cwrappers.merge_sorted(allclcks,track_indices=True)  # calls the efficient c-routine
            del allclcks[-1]  # drop the last element of allclcks which points to the original denseT
        else: self.denseT=XTSM_cwrappers.merge_sorted([self.denseT])  # if there are no clocking channels, we only need to strip duplicates from denseT


        self.allclcks={i:clck for clck,i in zip(allclcks,[cc for cc in self.cStrings])}
            
        if BENCHMARK:
            t1=time.time()
            print "new denseT time:" , t1-t0
            print "equality check", numpy.array_equal(old_denseT, self.denseT)
            print "denseT types old/new:" , old_denseT.dtype, self.denseT.dtype
            if not numpy.array_equal(old_denseT, self.denseT): pass

    def construct_denseT_old(self):
        """
        constructs a list of all times an update is necessary on this timing group:
        this could arise from an explicitly defined edge, an update in an interval,
        or from a clocking pulse needed by another channel 
        """
        
        # first create a sorted list of all times at beginning or end of interval, at an edge, or beginning or start of sequence
        self.alltimes=numpy.unique(numpy.append(self.groupIntervals[2:4,],self.groupEdges[2,]))

        self.alltimes=numpy.unique(numpy.append(self.alltimes,[self.channelMap.hardwaretime,self.lasttimecoerced]))  #LRJ 10-23-2013 replaced 0 with hardware time. 
                
        # create a list denseT of all update times necessary in the experiment 
        # self.denseT=numpy.array([0]) #LRJ replaced 0 with hardwaretime. 
        self.denseT=numpy.array([self.channelMap.hardwaretime],dtype=numpy.float64)       
        # loop through all windows between members of alltimes
        for starttime,endtime in zip(self.alltimes[0:-1],self.alltimes[1:]):
            
            self.groupSamOrInts=numpy.hstack((self.groupIntervals,self.groupSamples))
            # identify all intervals in this group active in this window
            if self.groupSamOrInts.size!=0:
                pre=(self.groupSamOrInts[2,]<=starttime).nonzero()
                post=(self.groupSamOrInts[3,]>starttime).nonzero()
                if ((len(pre)>0) and (len(post)>0)):
                    aInts=numpy.intersect1d(numpy.array(pre),numpy.array(post))
                    if aInts.size>0:
                        # find compromise timing resolution (minimum requested, coerced to parent clock multiple)
                        Tres=math.ceil(round(min(self.groupSamOrInts[5,aInts])/numpy.float64(self.clockgenresolution),3))*numpy.float64(self.clockgenresolution)
                        # define the times in this window using universal time
                        T=numpy.linspace(starttime,endtime,(endtime-starttime)/Tres+1)
                        self.denseT=numpy.append(self.denseT,T)
                    else: self.denseT=numpy.append(self.denseT,starttime)   
                else: self.denseT=numpy.append(self.denseT,starttime)
            else: self.denseT=numpy.append(self.denseT,starttime)
        
        # This line add the endtime to the end of the denseT.       
        self.denseT=numpy.append(self.denseT,self.lasttimecoerced)

        self.denseT=numpy.unique(self.denseT)
        # now incorporate all clockstrings for clock channels:
        # merge all clock update times with denseT from edges and intervals (likely costly operation)
        allclcks=numpy.array([])
        if self.dTrain == True:            # Data in delay train cEdges is stored differently.
            for clockChannel in self.cStrings:
                try: 
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][2,:]])
                except AttributeError: 
                    self.cEdges={}
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][2,:]])
                except KeyError: 
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][2,:]])
        else: # If not a delay train...
                        
            for clockChannel in self.cStrings:
                try: allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][0,:]])
                except AttributeError: 
                    self.cEdges={}
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][0,:]])
                except KeyError: 
                    self.cEdges.update({clockChannel:self.generate_clockEdges(self.cStrings[clockChannel],None,clockChannel)})
                    allclcks=numpy.concatenate([allclcks,self.cEdges[clockChannel][0,:]])
        # choose the unique update times and sort them (sorting is a useful side-effect of the unique function)
             
        try: 
            self.denseT=numpy.unique(numpy.concatenate([allclcks, self.denseT]))          
            #Build an array indicating the clocking chain for the timing group. 
            #Format is an array of timing group numbers. For example tg 3 would give [2,6,0] which indicates that tg3 is clocked by tg 2 is clocked by tg 6 is clocked by tg 0
            self.channelMap.getClocks()
            self.clkchain=numpy.array([self.channelMap.Clocks[self.tGroup][0]])
            for elem in range(self.getDictMaxValue(self.channelMap.tGroupClockLevels)-self.channelMap.tGroupClockLevels[self.tGroup]):
                try :
                    self.clkchain=numpy.append(self.clkchain,self.channelMap.Clocks[self.clkchain[elem]][0])
                except KeyError :pass
                except IndexError: pass
            
            #Coerce all times in denseT to the timing group's own time resolution, its clocker's time resolution, its clocker's clocker's time resolution and so on through the clocking chain
            self.denseT=(self.denseT/self.channelMap.tGroupClockResolutions[self.tGroup]).round()*self.channelMap.tGroupClockResolutions[self.tGroup]           
            for elem in range(len(self.clkchain)):
                self.denseT=((self.denseT/self.channelMap.tGroupClockResolutions[self.clkchain[elem]]).round())*self.channelMap.tGroupClockResolutions[self.clkchain[elem]]
               
            self.denseT=numpy.unique(self.denseT)
            
        except: pass


    def sort_edgeSources(self):
        """
        sort edges and intervals by group index (channel), then by (start)time
        """
        if self.groupEdges.size > 0:
            self.groupEdges=self.groupEdges[:,numpy.lexsort((self.groupEdges[2,:],self.groupEdges[1,:]))] 
        if self.groupIntervals.size > 0:
            self.groupIntervals=self.groupIntervals[:,numpy.lexsort((self.groupIntervals[2,:],self.groupIntervals[1,:]))]
        if self.groupSamples.size > 0:
            self.groupSamples=self.groupSamples[:,numpy.lexsort((self.groupSamples[2,:],self.groupSamples[1,:]))]

    def RepresentAsIntegerOld(self):
        """
        Replaces an N-channel digital group intedge with a single-channel log_2(N)-bit intedge list
        This algorithm assumes the group is digital, channel intedges have no duplications, 
        and that the final edges all coincide - THIS LAST PART IS PROBLEMATIC
        """
        Nchan = len(self.channels)  # number of channels
        Nbitout = math.ceil(Nchan/8.)*8  # number of bits in integer to use
        try:
            dtype = {0:numpy.uint8,8:numpy.uint8,16:numpy.uint16,32:numpy.uint32,64:numpy.uint64}[Nbitout] # data type for output
        except KeyError:
            pass
        # get all update times
        channeltimes = numpy.concatenate([ch.intedges[0,:].astype(numpy.float64) for ch in self.channels.values()])
        # get number of updates for each channel 
        chanlengths = [ch.intedges.shape[1] for ch in self.channels.values()]
        # get whether each channel is a clock channel
        channelclocks = [ch.isclock for ch in self.channels.values()]
        # create a set of ptrs to the update times for each channel
        ptrs = numpy.array([sum(chanlengths[0:j]) for j in range(0,len(chanlengths))])
        # find the final resting places of the pointers

        fptrs = [ptr for ptr in ptrs[1:]]
        # add in end pointer
        fptrs.append(channeltimes.shape[0])
        fptrs = numpy.array(fptrs)
        # create a bit-array to represent all channel outputs
        bits = bitarray([(not bool(ch.intedges[3,0])) for ch in self.channels.values()])
        # create arrays of output times and values for a single channel
        numtimes = len(numpy.unique(channeltimes))
        outvals = numpy.empty(numtimes,dtype=dtype)
        outtimes = numpy.empty(numtimes,dtype=numpy.uint64)
        outptr = 0  # a pointer to the first currently unwritten output element
        
        ### THE FOLLOWING LINES SHOULD NOT BE HERE AS FAR AS I CAN TELL - NDG THEY SHOULD BE REMOVED, and then RETESTED.        
        # fix channels with no edges/intervals to end at the correct time
        index = 0
        final_update = max(channeltimes)
        for i in range(len(channelclocks)):
            index += chanlengths[i] 
            if not channelclocks[i]:
                channeltimes[index - 1] = final_update
        ### NDG 3-11-14                
                
        if hasattr(self.tGroupNode, 'ParserInstructions') and hasattr(self.tGroupNode.ParserInstructions, 'Pulser'):
            if str.upper(str(self.tGroupNode.ParserInstructions.Pulser.PCDATA)) == 'YES': # for automatic pulses
                while not (ptrs == fptrs).all():
                    active = ptrs<fptrs # identify active pointers
                    time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                    #LRJ 10-30-2013 hitstrue disables unused channels
                    lineindex=0
                    hitstrue=[]
                    for ct in channeltimes[ptrs]:
                            if self.channels.values()[lineindex].intedges.shape[1] == 2 and ct==time:
                                hitstrue.append(False)
                            else:
                                hitstrue.append(ct==time)
                            lineindex+=1  
                    hits = [ct == time for ct in channeltimes[ptrs]] # find active pointers
                    bits = bitarray(hitstrue) # assign bits based on whether a matching time was found
                    # populate output arrays
                    outvals[outptr] = numpy.fromstring((bits.tobytes()[::-1]),dtype=dtype)
                    outtimes[outptr] = time
                    # advances pointers if active and hits are both true for that pointer.
                    ptrs += numpy.logical_and(active, hits)
                    outptr += 1
            else: # for alternating rise/fall pulses
                while not (ptrs == fptrs).all():
                    active = ptrs<fptrs # identify active pointers
                    time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                    flips = [ct == time for ct in channeltimes[ptrs]] # find active pointers
                    bits = bits^bitarray(flips) # flip bits where updates dictate using bitwise XOR
                    # populate output arrays
                    outvals[outptr] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
                    outtimes[outptr] = time
                    # advances pointers if active and flips and both true for that pointer.
                    ptrs += numpy.logical_and(active, flips)
                    outptr += 1
                # Now change final values to be zeros.
                bits = bitarray(0 for ch in self.channels.values())
                outvals[-1] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
        else: # for alternating rise/fall pulses
            while not (ptrs == fptrs).all():
                active = ptrs<fptrs # identify active pointers
                time = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                flips = [ct == time for ct in channeltimes[ptrs]] # find pointers that indicates state change             
                bits = bits^bitarray(flips) # flip bits where updates dictate using bitwise XOR
                # populate output arrays
                outvals[outptr] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
                outtimes[outptr] = time
                # advances pointers if active and flips and both true for that pointer.
                ptrs += numpy.logical_and(active, flips)
                outptr += 1
            # Now change final values to be zeros.
            bits = bitarray(0 for ch in self.channels.values())
            outvals[-1] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)            
#        self.rawchannels = self.channels
#        self.channels = {0:channelData(self, 0, times = outtimes, values = outvals)}
#        self.numchan = 1
#        self.bytespervalue = int(Nbitout / 8)
#        self.bytesperrepeat = 0
        return (outvals,outtimes)

    def RepresentAsInteger(self):
        """
        Replaces an N-channel digital group intedge with a single-channel log_2(N)-bit intedge list
        This algorithm assumes the group is digital, channel intedges have no duplications, 
        and that the final edges all coincide - THIS LAST PART IS PROBLEMATIC
        """

        BENCHMARK = False  # setting true benchmarks and compares output of this routine to the old one.

        if BENCHMARK:  t0=time.time()        
        Nchan = len(self.channels)  # number of channels
        Nbitout = math.ceil(Nchan/8.)*8  # number of bits in integer to use
        # get all update times
        #trr=time.time()
        channeltimes = numpy.concatenate([ch.intedges[0,:].astype(numpy.float64) for ch in self.channels.values()])
        #tss=time.time()
        #print "repas concat", tss-trr
        pulse=False
        if hasattr(self.tGroupNode, 'ParserInstructions') and hasattr(self.tGroupNode.ParserInstructions, 'Pulser'):
            if str.upper(str(self.tGroupNode.ParserInstructions.Pulser.PCDATA)) == 'YES': pulse=True
        else: pulse=False
        
        # get number of updates for each channel 
        chanlengths = [ch.intedges.shape[1] for ch in self.channels.values()]
        # get whether each channel is a clock channel
        channelclocks = [ch.isclock for ch in self.channels.values()]
        # create a set of ptrs to the update times for each channel
        ptrs = numpy.array([sum(chanlengths[0:j]) for j in range(0,len(chanlengths))])
        # find the final resting places of the pointers
        fptrs = [ptr for ptr in ptrs[1:]]
        # add in end pointer
        fptrs.append(channeltimes.shape[0])
        fptrs = numpy.array(fptrs)
        final_update = max(channeltimes[fptrs-1])
        # create arrays of output times and values for a single channel
        #trrr=time.time()
        fast_times = numpy.arange(final_update+1)
        #tsss=time.time()
        #print "repas unique", tsss-trrr
        numtimes = len(fast_times)
        
        ### THE FOLLOWING LINES SHOULD NOT BE HERE AS FAR AS I CAN TELL - NDG THEY SHOULD BE REMOVED, and then RETESTED.        
        # fix channels with no edges/intervals to end at the correct time
#        index = 0
#        for i in range(len(channelclocks)):
#            index += chanlengths[i] 
#            if not channelclocks[i]:
#                channeltimes[index - 1] = final_update
        ### NDG 3-11-14                

        bits2 = bitarray([(not bool(ch.intedges[3,0])) for ch in self.channels.values()])        
        seed=0
        if not pulse: bits2.reverse()
        for bit in bits2.tolist(): seed = ((seed << 1) | bit)
        #tr=time.time()
        fast_string=XTSM_cwrappers.repas.repasint(channeltimes.astype(numpy.uint32),seed,PULSER=pulse, DEV=pulse) # development method is currently ~30% faster for typical data
        #ts=time.time()
        #print "repas actual: ", ts-tr
        #t10=time.time()
        if pulse:
            # the following lines reproduce some confusing lines in prior repasint for channels which have only two 
            # update times (previously reasoned to be 'unused' channels - though that is not always the case (clocking channels for unused timinggroups, which need holding values clocked in, for example))  
            # once it is established this routine reproduces the old routine's output, these lines should be removed
            # and the entire timing system retested.
            twoedgechannels=[i for i,p,f in zip(range(0,Nchan),ptrs,fptrs) if f-p==2]
            for twoedgechannel in twoedgechannels:
                changetimeindex1 = channeltimes[ptrs[twoedgechannel]]
                changetimeindex2 = channeltimes[fptrs[twoedgechannel]-1]
                fast_string[changetimeindex1] &= ((1 << (Nchan-twoedgechannel-1))^(2**Nchan-1))
                fast_string[changetimeindex2] &= ((1 << (Nchan-twoedgechannel-1))^(2**Nchan-1))
        #t11=time.time()
        #print "pulse flips", t11-t10


        if BENCHMARK:
            t0=time.time()-t0
            print "new repasint time:" , t0
            t0=time.time()
            outvals=self.RepresentAsIntegerOld()
            t0=time.time()-t0
            print "old repasint time:", t0
            print "equality check:", numpy.array_equal(fast_string,outvals[0])
            if not numpy.array_equal(fast_string,outvals[0]): pdb.set_trace()
            if not numpy.array_equal(fast_times,outvals[1]): pdb.set_trace()

        self.rawchannels = self.channels
        #tq=time.time()
        self.channels = {0:channelData(self, 0, times = fast_times, values = fast_string)}
        #tp=time.time()
        #print "channel creation", tp-tq
        self.numchan = 1
        self.bytespervalue = int(Nbitout / 8)
        self.bytesperrepeat = 0

        return

    def TimingStringConstruct(self):
        """
        Constructs the for this timing group, by defining a place
        in memory, then calling ChannelData elements to construct and fill
        their fragments
        """
        # first reserve a place for the timinstring in memory        
        # calculate the total number of edges on the timingGroup
        if self.direction=='INPUT': 
            self.numalledges=0
        else: self.numalledges=sum([chan.intedges.shape[1] for chan in self.channels.values()])
        # calculate length of control string for entire timing group in bytes
        self.tsbytes=self.numalledges*(self.bytesperrepeat+self.bytespervalue)+4*self.numchan+15  ### last two terms account for header and segment headers
        self.timingstring=numpy.ones(self.tsbytes,numpy.uint8)  # will hold timingstring
        # create the timingstring header
        # First part of the header is the length of the control string for the entire timing group.
        self.timingstring[0:8]=numpy.asarray([self.tsbytes], dtype='<u8').view('u1')
        self.timingstring[8:15]=numpy.append(
                                  numpy.asarray([self.numchan,self.bytespervalue,self.bytesperrepeat], dtype='<u1').view('u1'),
                                  numpy.asarray([self.denseT.size], dtype='<u4').view('u1'))
        self.tsptr=15  # a pointer to the current position for writing data into the timingstring
        self.determine_TS_method()
        # now output each channel's timing string fragment
        for chan in self.channels.values():
            chan.timingstring_construct()
    
    def generate_package_header(self):
        """
        creates the header for this timingstring when all groups' timingstrings are
        packaged together
        """
        headerLength=80
        tsh=numpy.zeros(headerLength,dtype=numpy.uint8) # declare memory for header
        tsh[0:8]=numpy.array([self.timingstring.shape[0]],dtype=numpy.uint64).view(numpy.uint8) # timingstring length in bytes
        tsh[8:16]=numpy.array([self.tGroup],dtype=numpy.uint64).view(numpy.uint8) # timing group number
        tsh[16]={'DigitalOutput':0,'AnalogOutput':1,'DigitalInput':2,'AnalogInput':3,'DelayTrain':4}[self.get_tgType()] # type of hardware interface
#        tsh[17]=  GOING TO IGNORE THESE AS TOO SPECIFIC FOR PARSER TO GENERATE
#        tsh[18]=
        tsh[19:23]=numpy.array([1000./self.clockgenresolution],dtype=numpy.uint32).view(numpy.uint8)
        tsh[23]=hasattr(self,'swTrigger') # whether this group software-triggers acquisition (taken directly from XTSM)
        tsh[24]=self.isSparse # whether the sparse/dense conversion should be run on this data by the acquisition hardware
        tsh[25]=1  #  HEADER VERSION
#        tsh[26:32]= Reserved for future use
        tsh[32:56]=numpy.fromstring(self.tGroupNode.Name[0].PCDATA[0:24].ljust(24,u" "),dtype=numpy.uint8)  # tGroup Name
        tsh[56:80]=numpy.fromstring(self.tGroupNode.ClockedBy[0].PCDATA[0:24].ljust(24,u" "),dtype=numpy.uint8)  # Clock Channel Name
        return tsh        
    '''
    def findNearestValue(self,array,array2):
        
        Returns an edge array with coerced times from denseT that are nearest to an edge's requested time
        This algorithm could be made more efficient by sorting edge_array and matching values starting at the last found value

        idx=array.searchsorted(array2)
        idx=numpy.clip(idx,1,len(array)-1)
        left = array[idx-1]
        right = array[idx]
        idx -= array - left < right - array  
        edge_array=array[idx]                      
            # edge_array[elem]=dense_time_array[abs(edge_array[elem]-dense_time_array).argmin()] #many computations to rewrite group edge array
        return edge_array
        '''

    def get_tgType(self):
        """
        Returns the timing group's type: Analog/Digital,Input/Output,DelayTrain as string
        """
        try: 
            if self.dTrain: return 'DelayTrain'
        except AttributeError: pass
        if self.ResolutionBits>1: rval='Analog'
        else: rval='Digital'
        if self.direction=="OUTPUT": rval+='Output'
        else: rval+="Input"
        return rval
        
    def calculate_numalledges(self):
        """
        Calculate how many edges this timinggroup will have
        """
        self.numalledges=0
        # find out how many edges this timinggroup will have
        for intervalInd in self.groupIntervals[6,]:
            # get the interval, find how many samples it will generate
            interval=self.sequence._fasttag_dict[intervalInd]
            self.numalledges+=interval.expected_samples(self.denseT)
        for sampleInd in self.groupSamples[6,]:
            # get the sample, find how many samples it will generate
            sample=self.sequence._fasttag_dict[sampleInd]
            self.numalledges+=sample.expected_samples(self.denseT)
        # add the number of group edges
        self.numalledges+=self.groupEdges.shape[1]
        # add the number of clocking edges 
        self.numalledges+=sum([len(a) for a in self.cStrings.values()])
        
    def determine_TS_method(self):
        """
        Determines the type of timingstring to output for this group, and tags
        whether group will have sparse timingstring representation using attribute
        self.isSparse
        """
        if self.dTrain:
            self.method='Digital_DelayTrain'
            self.isSparse=False
        else: 
            if self.direction=='INPUT':
                self.method='INPUT'
                self.isSparse=False
                return
            if (self.ResolutionBits>1 and self.bytesperrepeat!=0):
                self.method='Analog_VR'
                self.isSparse=True
            if (self.ResolutionBits==1 and self.bytesperrepeat==0):
                self.method='Digital_R'
                if hasattr(self,'repasint'): self.isSparse=not self.repasint
                else: self.isSparse=True
            
    def generate_clockEdges(self,ctimes,chanObj,channelnumber):
        """
        Generates and returns an edge array corresponding to a clocking string, given the clock times as a 1D numpy array, and a channel object
        """
        # find channel data for this clock: active rise / active fall, pulse-width, delaytrain  
                
        #ctimes=numpy.unique(ctimes)
        ctimes=XTSM_cwrappers.merge_sorted([ctimes])
        if chanObj==None:
            chanObj=self.channelMap.getItemByFieldValueSet('Channel',{'TimingGroup':str(self.tGroup),'TimingGroupIndex':str(channelnumber)})    # find the channel
        if chanObj: 
            try:
                chanObj=chanObj.pop() # if the channels are returned as part of a list, get one channel object from list
            except AttributeError:
                pass # if it doesn't have a 'pop' attribute, then it is simply one channel object.
        aEdge=chanObj.get_childNodeValue_orDefault('ActiveClockEdge','rise')
        pWidth=chanObj.get_childNodeValue_orDefault('PulseWidth','')
        dTrain=self.tGroupNode.get_childNodeValue_orDefault('DelayTrain','No')
        if hasattr(self.tGroupNode, 'ParserInstructions'):
            aPulse = self.tGroupNode.ParserInstructions.get_childNodeValue_orDefault('Pulser','No')
        else:
            aPulse = self.tGroupNode.get_childNodeValue_orDefault('Pulser','No')
        high=1
        low=0
        if not (str.upper(str(dTrain)) == 'YES' or str.upper(str(aPulse)) == 'YES'):  # algorithm for using a standard value,repeat pair
            if pWidth=='':  # if pWidth not defined create bisecting falltimes
                falltimes=(ctimes[0:-1]+ctimes[1:])/numpy.float64(2.)  # creates too few falltimes; need a last fall            
                falltimes=numpy.append(falltimes,[ctimes[-1] + self.channelMap.hardwaretime]) # creates a last fall time a hardwaretime after last rise.
            else: # if pulsewidth defined, use it to create falltimes
                falltimes=numpy.add(ctimes,pWidth)
            if self.ResolutionBits>1: # algorithm for an analog clock channel (should rarely be used)
                high=chanObj.get_childNodeValue_orDefault('HighLevel',numpy.float64(5.))
                low=chanObj.get_childNodeValue_orDefault('HighLevel',numpy.float64(0.))
            if str.upper(aEdge)!='RISE':  # if not rising edge trigger, swap high and low
                low,high=high,low
            intedges=numpy.empty((5,(ctimes.shape[0]*2)),dtype=numpy.float64)
            intedges[3,1::2]=low  # set values
            intedges[3,0::2]=high
            intedges[2,1::2]=falltimes  # set times
            intedges[2,0::2]=ctimes
            intedges[0,1::2]=falltimes  # set time indices 
            intedges[0,0::2]=ctimes           
        
        elif str.upper(str(aPulse)) == 'YES': # algorithm for an automatic pulser which does not require fall times/falls on its own
            intedges = numpy.empty((5, ctimes.shape[0]),dtype=numpy.float64) 
            intedges[3,:] = high  # set all values as high, since they fall automatically
            intedges[2,:] = ctimes  # set reduced times
            intedges[0,:] = ctimes  # set times
            
        else: # algorithm for a delay train pulser (returns only delay count between successive pulses in slot 0, times in slot 2)
            # negative time values (such as for digital clocking channel) appear as ridiculously large positive times.
            # remove the large positive time, offset all times by 2ns, and add in a new start time                   
            delays=ctimes[1:]-ctimes[:-1]
            delays=numpy.append(delays,self.channelMap.hardwaretime) #LRJ 10-29-2013 final delay time set to hardware time
            intedges=numpy.empty((5,ctimes.shape[0]),dtype=numpy.float64)
            intedges[4,:]=-1
            intedges[3,:]=high  # all values for a delay train are irrelevant; a pulse will be issued at time ordinate
            intedges[2,0:]=ctimes  # times are recorded as actual times
            intedges[0,:]=delays
        intedges[4,:]=-1  # denote that these are parser-generated edges       
        #intedges[0,:]=self.tGroup  # set tGroup
        intedges[1,:]=channelnumber  # set channel number
        return intedges

class channelData():
    """
    subclass of ControlArray to store individual channel data
    """
    def __init__(self,parent,channelnumber,times=None,values=None):
        self.channel=channelnumber
        self.parent=parent
               
        if times==None:
            self.clockchans=[parent.channelMap.isClock(parent.tGroup,x) for x in range(parent.numchan)] #LRJ 10-31-2013 create list of clock channels in the active timing group. False for non-clocker channels, clocked timing group number for clock channels
            self.isclock=parent.channelMap.isClock(parent.tGroup,self.channel)
            self.isinput=parent.channelMap.isInput(parent.tGroup,self.channel)            
            # find the channel for data, get biographicals                
            self.chanObj=parent.channelMap.getChannel([parent.tGroup,self.channel])   # find the channel
            if hasattr(self.chanObj,'InitialValue'): self.initval=self.chanObj.InitialValue[0].parse()
            else: self.initval=0
            if hasattr(self.chanObj,'HoldingValue'): 
                if (self.chanObj.HoldingValue[0].parse()!= None):
                    self.holdingval=self.chanObj.HoldingValue[0].parse()
                else:
                    self.holdingval=0
            else: self.holdingval=0
            
             
            # retrieve intedges
            if self.isclock:
                # if this is a clock channel, take the clock edges if already constructed or construct from clockstring
                #t0=time.time()
                try: 
                    if parent.dTrain!=True: self.intedges=self.clock_harvest(parent.cEdges[self.channel],parent.denseT,chan_num=self.channel)
                    else: self.intedges=parent.cEdges[self.channel]
                except (AttributeError,KeyError):
                    self.intedges=parent.generate_clockEdges(parent.cStrings[self.channel],self.chanObj,self.channel)
                #t1=time.time()
                #print "clock harvest: ", t1-t0

            else:
                # for a non-clock channel, start with explicitly defined edges
                # step through each interval, reparse and append data
                #t0=time.time()
                try: 
                    #replace times in groupEdges with the nearest coerced time in denseT using the edge_harvest method of ControlArray
                    edgesonchannel=parent.groupEdges[:,(parent.groupEdges[1,:]==self.channel).nonzero()[0]]                    
                    self.intedges=numpy.empty((5L,edgesonchannel.shape[1]))                    
                    for i in range(edgesonchannel.shape[1]):
                        self.intedges[:,i]=self.parent.sequence._fasttag_dict[edgesonchannel[4,i]].parse_harvest(parent.denseT)
                except IndexError: self.intedges=numpy.empty((5,0))
                try: self.chanIntervals=parent.groupIntervals[:,(parent.groupIntervals[1,:]==self.channel).nonzero()[0]]
                except IndexError: self.chanIntervals=numpy.empty((7,0))
                for intervalInd in self.chanIntervals[6,]:
                   # locate the next interval, reparse for denseT and append
                   interval=parent.sequence._fasttag_dict[intervalInd]
                   try: self.intedges=numpy.hstack((self.intedges,interval.parse_harvest(parent.denseT)))
                   except: pdb.set_trace()
                #t1=time.time()
                #print "harvest: ", t1-t0

            if ((not self.isclock) and (not self.isinput)):
                #t0=time.time()
                # add first and last edge if necessary
                if self.intedges.shape[1]>0:
                    if self.intedges[2,0]!=0:
                        self.intedges=numpy.hstack([numpy.array([[parent.denseT.searchsorted(parent.channelMap.hardwaretime),self.channel,parent.channelMap.hardwaretime,self.initval,-1]]).transpose(),self.intedges])
                    if self.intedges[2,-1]!=parent.lasttimecoerced:
                        self.intedges=numpy.hstack([self.intedges,numpy.array([[parent.denseT.searchsorted(parent.lasttimecoerced),self.channel,parent.lasttimecoerced,self.holdingval,-1]]).transpose()])
                else: 
                    self.intedges=numpy.hstack([numpy.array([[parent.denseT.searchsorted(parent.channelMap.hardwaretime),self.channel,parent.channelMap.hardwaretime,self.initval,-1]]).transpose(),self.intedges]) 
                    self.intedges=numpy.hstack([self.intedges,numpy.array([[parent.denseT.searchsorted(parent.lasttimecoerced),self.channel,parent.lasttimecoerced,self.holdingval,-1]]).transpose()])
                #t1=time.time()
                #print "first/last edge insert: ", t1-t0



                if self.parent.ResolutionBits==1:         # Only remove the repeat values for digital Channel , JZ 08/13/14  
                    self.intedges=numpy.delete(self.intedges,numpy.where(self.intedges[3,:-1]==self.intedges[3,1:])[0]+1,axis=1)            
            
        else:
            #t0=time.time()
            self.intedges=numpy.empty((5,times.shape[0]),dtype=numpy.float64)
            self.intedges[4,:]=-1
            self.intedges[1,:]=self.parent.tGroup
            self.intedges[0,:]=times
            self.intedges[2,:]=self.parent.denseT
            self.intedges[3,:]=values
            #t1=time.time()
        self.intedges=self.intedges[:,self.intedges[2,:].argsort()]  # added 10/8/14 NDG,JZ,CP  to solve missing edge elements which follow an interval in source XTSM
#        try: 
#            if self.chanObj.TimingGroupIndex.PCDATA==u'19': pdb.set_trace() 
#        except: pass          
           #print "times given: ", t1-t0

    def clock_harvest(self,clock_edge_array,dense_time_array,chan_num=None): #LRJ 3-11-2014, NDG 5-16-14        
        """
        Returns an edge array entry with coerced times from denseT that are nearest to an edge's requested time
        """
        
        NEW_VERSION=True        
        
        if NEW_VERSION:
            clock_edge_array[0]=self.parent.allclcks[chan_num]
            clock_edge_array[2]=dense_time_array[self.parent.allclcks[chan_num].astype(dtype=numpy.uint32)]                
        #searchsorted routine on clockedges needs to be time characterized, this algorithm may be inefficient LRJ 3-12-2014
        else:
            idx=dense_time_array.searchsorted(clock_edge_array[2])
            close_array=numpy.isclose(dense_time_array[idx],clock_edge_array[2],0,1e-8) #need a quick way to find lowest tres and replace 1e-8 LRJ 3-12-2014
            if close_array.all(): 
                clock_edge_array[0]=idx                
            else: 
                idx_actual=self.parent.find_closest(dense_time_array,clock_edge_array[2][numpy.where(close_array,0,1).nonzero()])
                clock_edge_array[2][numpy.where(close_array,0,1).nonzero()]=dense_time_array[idx_actual]        
                clock_edge_array[0]=dense_time_array.searchsorted(clock_edge_array[2])        
        return clock_edge_array
            
    def apply_channelTransforms(self):
        """
        Applies XTSM-declared tranformations to the channel output, including declared
        calibrations, min's, and max's, and scales and offsets into integer ranges
        """
        try: 
            if not (self.chanObj.Calibration[0].PCDATA == '' or self.chanObj.Calibration[0].PCDATA == None):
                V=self.intedges[:,3] # the variable V can be referenced in channel calibration formula (eval'd next line)
                self.intedges[:,3]=eval(self.chanObj.Calibration[0].PCDATA)
        except: pass
        minv=maxv=''
        try:
            maxv=self.chanObj.MaxValue[0].parse()
            minv=self.chanObj.MinValue[0].parse()
        except: pass
        if ((minv == '') or (minv == None)): minv = -self.parent.range/numpy.float64(2.)#min(self.intedges[:,3])
        if ((maxv == '') or (maxv == None)): maxv = self.parent.range/numpy.float64(2.)#max(self.intedges[:,3])
        numpy.clip(self.intedges[:,3],max(-self.parent.range/numpy.float64(2.),minv),min(self.parent.range/numpy.float64(2.),maxv),self.intedges[:,3])        
        # scale & offset values into integer ranges
        numpy.multiply(self.parent.DACCalibration,self.intedges[:,3],self.intedges[:,3]) #LRJ 10-15-2013,8*bytespervalue replaced ResolutionBits   
        
    def timingstring_construct(self):
        """
        inserts the timingstring fragment for this channel into the parent ControlArray's existing timingstring at position tsptr;
        also enforces min and max values, channel calibration expressions, and scales to byte-form (these should be split to ancillary methods for maintainability)
        """
        length=self.intedges.shape[1]
        # first a header denoting this channel's length in bytes as 4bytes, LSB leading
        self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+4)]=numpy.asarray([int(length*(self.parent.bytesperrepeat+self.parent.bytespervalue))], dtype='<u4').view('u1')
        self.parent.tsptr+=4
        self.intedges=self.intedges.transpose()
        if length>0 and self.parent.method!="Digital_DelayTrain":
            # Perform channel hardware limit transformations here:
            if not hasattr(self.parent,'repasint'): self.apply_channelTransforms()
            # calculate repeats
            reps=numpy.empty(length,dtype=numpy.int32)
            reps[:-1]=self.intedges[1:,0]-self.intedges[:-1,0]
            reps[-1]=1  # add last repeat of one
            # now need to interweave values / repeats
            # create a numedges x (self.bytespervalue+self.bytesperrepeat) sized byte array
            interweaver=numpy.empty([length,(self.parent.bytesperrepeat+self.parent.bytespervalue)],numpy.byte)
            # load values into first bytespervalue columns. LRJ 10-16-2013-"signed" float value from scaling is cast into Two's Complement U16 
            interweaver[:,0:self.parent.bytespervalue]=numpy.lib.stride_tricks.as_strided(
                numpy.asarray(self.intedges[:,3],dtype='<u'+str(self.parent.bytespervalue)).view('u1'),
                [length,self.parent.bytespervalue],[self.parent.bytespervalue,1])
            try:
                # load repeats into last bytesperrepeat columns
                interweaver[:,self.parent.bytespervalue:(self.parent.bytespervalue+self.parent.bytesperrepeat)]=numpy.lib.stride_tricks.as_strided(
                    numpy.asarray(reps,dtype='<u'+str(self.parent.bytesperrepeat)).view('u1'),
                    [length,self.parent.bytesperrepeat],[self.parent.bytesperrepeat,1])
            except TypeError:
                pass
            # copy into timingstring
            self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+length*(self.parent.bytesperrepeat+self.parent.bytespervalue))]=interweaver.view('u1').reshape(interweaver.shape[0]*(self.parent.bytesperrepeat+self.parent.bytespervalue))
            self.parent.tsptr+=length*(self.parent.bytesperrepeat+self.parent.bytespervalue)
        else: # delay train algorithm
            if length>0:
                self.parent.timingstring[self.parent.tsptr:(self.parent.tsptr+length*(self.parent.bytesperrepeat+self.parent.bytespervalue))]=numpy.asarray((self.intedges[:,0]/self.parent.parentgenresolution).round(), dtype='<u'+str(self.parent.bytesperrepeat)).view('u1')  # NEED THIS ALGORITHM!
                self.parent.tsptr+=length*(self.parent.bytesperrepeat+self.parent.bytespervalue)
                
class Sequence(gnosis.xml.objectify._XO_,XTSM_core):
    def collectTimingProffers(self):
        """
        Performs a first pass through all edges and intervals, parsing and collecting all ((Start/ /End)time/value/channel) entries necessary to arbitrate clocking edges
        """        
        self.TimingProffer=TimingProffer(self)
        if (not hasattr(self,'guid_lookup')): 
            self.generate_guid()            
            self.generate_guid_lookup()
        if (not hasattr(self,'_fasttag_dict')): 
            self.generate_fasttag(0)
        for subsequence in self.SubSequence:
            subsequence.collectTimingProffers(self.TimingProffer)
        return None
        
    def parse(self):
        """
        top-level algorithm for parsing a sequence;
        equivalent to XTSM_parse in IDL code.
        """
        
        # replicate subsequences with iterations specified (also strip any previously generated replications)
        for subseq in self.getDescendentsByType("SubSequence"):
            subseq.dereplicate()        
        for subseq in self.getDescendentsByType("SubSequence"):
            subseq.replicate()
            '''
            filenames = []
            for i in range(1):
                name = 'c:\psu_data\profile_stats_replicate_%d.txt' % i
                profile.runctx('subseq.replicate()',globals(),locals(), filename=name)
            stats = pstats.Stats('c:\psu_data\profile_stats_replicate_0.txt')
            for i in range(0, 1):
                stats.add('c:\psu_data\profile_stats_replicate_%d.txt' % i)
            stats.sort_stats('cumulative')
            stats.print_stats()
            '''
        # get the channelmap node from the XTSM object.
        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
      
        # Add undecleared channels to the ChannelMap node. The following line causes a problem
        #in the postparse step. Since all the undecleared channels are created as nonclock channels, even that the
        #channel is in the clocking group 6 (RIO01sync). Having initial edges on these channels are problematic 
        #at the postparse step, where it combines the timing group RIO01/syn with delaytrain. by JZ 12/18
    
        #cMap.creatMissingChannels()
        
        # Insert a initilization subsequence in the sequence and a holding subsequence
        #self.channelInitilization()
        #self.channelHolding()        
        # Decipher channelMap, get resolutions

        channelHeir=cMap.createTimingGroupHeirarchy()        
        channelRes=cMap.findTimingGroupResolutions()
        
        # collect requested timing edges, intervals, etc...
        self.collectTimingProffers()
        #pdb.set_trace()
        # create an element to hold parser output
        pOutNode=self.insert(ParserOutput())
        # step through timing groups, starting from lowest on heirarchy
        #sorted (channelHeir, key=channelHeir.__getitem__) returns a list of groupnumber in the order of clocklevel, from low to high
        for tgroup in sorted(channelHeir, key=channelHeir.__getitem__):
            cA=pOutNode.insert(ControlData()) # create a control array node tagged with group number
            cA.insert(GroupNumber().set_value(tgroup))
            cA.insert(ControlArray().construct(self,cMap,tgroup))
        return

    def get_starttime(self):
        """
        gets the starttime for the sequence from XTSM tags(a parsed 'StartTime' tag). This method is added on 12/12/13 by JZ.
        """
        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
        ht=cMap.getHardwaretime()        
        
        if hasattr(self,'StartTime'):
            if not self.StartTime[0].PCDATA == None :
                starttime=self.StartTime[0].parse()
                self.starttime=starttime+2*ht
            else: self.starttime=2*ht
        else: self.starttime=2*ht    
        return self.starttime    
    
    def get_endtime(self):
        """
        gets the endtime for the sequence from XTSM tags (a parsed 'EndTime' tag)
        or coerces to final time in edge and intervals, or to default maximum length
        of 100s. Leaving the EndTime node blank will make the endtime equal to the 
        maximum requested time plus twice the resolution of the slowest board.
        """
        maxlasttime=100000 # a default maximum sequence length in ms!!! 
        if hasattr(self,'EndTime'):
            #st=self.get_starttime()
            endtime=self.EndTime[0].parse()
            if ((endtime < maxlasttime) and (endtime > 0)): 
                self.endtime = endtime
            else: 
                if hasattr(self,'TimingProffer'): #LRJ 3-13-2014
                    try: edgeet=self.TimingProffer.data['Edge'][:,2].max()
                    except ValueError: edgeet=0
                    try: int1et=self.TimingProffer.data['Interval'][:,2].max()
                    except ValueError: int1et=0
                    try: int2et=self.TimingProffer.data['Interval'][:,3].max()
                    except ValueError: int2et=0
                    try: sam1et=self.TimingProffer.data['Sample'][:,2].max()
                    except ValueError: sam1et=0
                    try: sam2et=self.TimingProffer.data['Sample'][:,3].max()
                    except ValueError: sam2et=0

                    self.endtime=max(edgeet,int1et,int2et,sam1et,sam2et)+2*self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0].hardwaretime
                else:               
                    self.endtime = maxlasttime
                    self.EndTime[0].addAttribute('parser_error','Invalid value: Coerced to '+str(maxlasttime)+' ms.')
        return self.endtime
                
# The following lines are not used - board initialization and holding values are inserted into intedges now without
# creating explicit edges to do so - the downside of that is that a user does not get feedback from looking at the parsed
# XTSM what values were used.  The reason the following was ultimately dropped was that initial and holding values
# were placed on a delaytrain as well which caused downstream problems in postparsing.  This could easily be avoided
# by not creating edges for a delay train - NDG 4-2014 after conversation with JZ

#    def channelInitilization(self):
#        """
#        At the beginning of the sequence, insert a initilization subsequence to set all the nonclock channel to the initial value at initial time. Added on 12/12/13 by JZ.
#        """
#
#        # First create a initialization subsequence as a instance of SubSequence class.
#        inisequence=SubSequence()
#        st=gnosis.xml.objectify._XO_StartTime()
#        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
#        channelRes=cMap.findTimingGroupResolutions()
#        channelHeir=cMap.createTimingGroupHeirarchy()
#        timesort=[]
#        for s in range(len(channelHeir)):
#            tgadvance=(2**channelHeir[s])*channelRes[s]
#            timesort.append(tgadvance)
#        initime=max(timesort)
#        
#        st.set_value(-initime)
#        inisequence.insert(st)
#        for chan in cMap.Channel:
#            parserEdge=Edge()
#            channelname=OnChannel()
#            time=gnosis.xml.objectify._XO_Time()
#            value=gnosis.xml.objectify._XO_Value()
#            
#            if hasattr(chan,'ChannelName'):
#                channelname.set_value(chan.ChannelName[0].PCDATA)
#                
#            [tg,tgi]=cMap.getChannelIndices(channelname.PCDATA)
#            if ((not cMap.isClock(tg,tgi)) and (not cMap.isInput(tg,tgi))):
#                parserEdge.insert(channelname)
#                time.set_value(0)
#                if hasattr(chan,'InitialValue'):
#                    value.set_value(chan.InitialValue.parse())
#                else: value.set_value(0)
#                parserEdge.insert(time)
#                parserEdge.insert(value)
#                       
#                inisequence.insert(parserEdge)
#            else: continue
#        
#        self.insert(inisequence)
#        
#        return None
#        
#        
#    def channelHolding(self):
#        """
#        At the end of the sequence, insert a holding subsequence to set all the nonclock channel to the holding value at sequence endtime. Added on 12/19/13 by JZ.
#        """
#        holdsequence=SubSequence()
#        st=gnosis.xml.objectify._XO_StartTime()
#        cMap=self.getOwnerXTSM().getDescendentsByType("ChannelMap")[0]
#        endtime=self.get_endtime()
#        st.set_value(endtime)
#        holdsequence.insert(st)
#        
#        for chan in cMap.Channel:
#            parserEdge=Edge()
#            channelname=OnChannel()
#            time=gnosis.xml.objectify._XO_Time()
#            value=gnosis.xml.objectify._XO_Value()
#            
#            if hasattr(chan,'ChannelName'):
#                channelname.set_value(chan.ChannelName[0].PCDATA)
#            
#            [tg,tgi]=cMap.getChannelIndices(channelname.PCDATA)
#            if ((not cMap.isClock(tg,tgi)) and (not cMap.isInput(tg,tgi))):
#                parserEdge.insert(channelname)
#                time.set_value(0)
#                if hasattr(chan,'HoldingValue'):
#                    if not chan.HoldingValue.PCDATA == None:
#                        value.set_value(chan.HoldingValue.parse())
#                    else: value.set_value(0)
#                                                                                             
#                else: value.set_value(0)
#                parserEdge.insert(time)
#                parserEdge.insert(value)
#                       
#                holdsequence.insert(parserEdge)
#            else: continue
#        
#        self.insert(holdsequence)    
#        
#        return None

class SubSequence(gnosis.xml.objectify._XO_,XTSM_core):
    def collectTimingProffers(self,timingProffer):
        """
        Performs a first pass through all edges and intervals, parsing and collecting all ((Start/ /End)time/value/channel) entries 
        necessary to arbitrate clocking edges
        """
        # Find the subsequence starttime and pass it to the subnode edge time,  interval and subsequence starttime, JZ on 12/12/13
        
        starttime=self.get_starttime()
        
        if (hasattr(self,'Edge')):
            for edge in self.Edge:
                timingProffer.insert('Edge',edge.parse_proffer(starttime))
        if (hasattr(self,'Interval')):
            for interval in self.Interval:
                timingProffer.insert('Interval',interval.parse_proffer(starttime)) 
        if (hasattr(self,'Sample')):
            for sample in self.Sample:
                timingProffer.insert('Sample',sample.parse_proffer(starttime)) 
        if (hasattr(self,'SubSequence')):
            for subsequence in self.SubSequence:
                subsequence.collectTimingProffers(timingProffer)
        return None
            
    def get_starttime(self):
        """
        gets the starttime for the subsequence from XTSM tags(a parsed 'StartTime' tag) and add the starttime of its parent, return the absolute starttime . This method is added on 12/12/13 by JZ.
        """
        if hasattr(self,'StartTime'):
            print self.Name.PCDATA
            #pdb.set_trace()
            substarttime=self.StartTime[0].parse()
            try:
                self.starttime=substarttime+self.__parent__.get_starttime()
            except: print 'Subsequence StartTime Ivalid.'    
        return self.starttime

    def replicate(self):
        """
        looks for "Iterations" subelement of SubSequence, and creates a copy
        for each iteration.  
        """
        self.dereplicate()  # remove any previously generated replications
        if not hasattr(self,"Iterate"):
            return
        progenitor_name = self.Name[0].PCDATA
        progenitor_time = self.StartTime[0].parse()
        # create a container subsequence for the iterations of the progenitor subsequence
        container_subsequence = SubSequence()
        namer = copy.deepcopy(self.Name[0])
        namer.set_value("_iterations_of_" + progenitor_name, REWRITE_NDG=True)
        container_subsequence.insert(namer, pos="LAST")
        st = copy.deepcopy(self.StartTime[0])
        st.set_value(u"0", REWRITE_NDG=True)
        container_subsequence.insert(st)
        # create the iterated subsequences
        #pdb.set_trace()
        for iters in self.Iterate:
            try:
                per=iters.Period[0].parse()
            except:
                msg = "Cannot Determine Iteration Period - is Period Element Declared?"
                iters.addAttribute("parser_error", msg)
            iters_num = int(iters.Repetitions[0].parse())
            for it in range(iters_num):
                newsubseq = copy.deepcopy(self)  # create a copy of the current subsequence
                newsubseq.remove_all("Iterate")  # prevent an endless replication loop (wouldn't happen anyway based on calling sequence)
                #newsubseq.remove_all("Name") 
                #newsubseq.insert(Name("_iter_"+str(it)+"_"+progenitor_name))
                if hasattr(newsubseq,"Name"):
                    newsubseq.Name[0].set_value("_iter_"+str(it)+"_"+progenitor_name, REWRITE_NDG=True)
                if hasattr(newsubseq,"StartTime"):
                    newsubseq.StartTime[0].set_value(str(progenitor_time+float(1.+it)*per), REWRITE_NDG=True)  # set successive starttimes
                else: 
                    msg = "Iterations Ignored - Progenitor Subsequence Missing a Start Time"
                    self.addAttribute("parser_error", msg)
                    return
                container_subsequence.insert(newsubseq, pos="LAST")
        # attach the container subsequence to the parent of the progenator
        self.insert(container_subsequence, pos="LAST")

    def dereplicate(self):
        """
        removes the replicated copies of an iterated subsequence
        """
        if not hasattr(self,"SubSequence"): return
        for subseq in self.SubSequence:
            subseq.dereplicate()
            if "_iterations_of_" in subseq.Name[0].PCDATA: self.remove_node(subseq)

# declaring an XTSM Name class was problematic, could probably reinstate this with effort
#class Name(gnosis.xml.objectify._XO_,XTSM_core):
#    def __init__(self, name=None):
#        XTSM_core.__init__(self)
#        if name!=None:
#            self.set_value(name)
#        return None

class ChannelMap(gnosis.xml.objectify._XO_,XTSM_core):
    def getChannelIndices(self,channelName):
        """
        returns the timingGroup number and timingGroup index for a channel of specified name as a pair [tg,tgi]
        """
        if (not hasattr(self,'Channel')): return [-1,-1]
        for chan in self.Channel:
            if hasattr(chan,'ChannelName'):
                if chan.ChannelName[0].PCDATA==channelName: 
                    return [numpy.float64(chan.TimingGroup[0].PCDATA),numpy.float64(chan.TimingGroupIndex[0].PCDATA)]
        else: return [-1,-1]

    def getClocks(self):
        """
        Assembles a list of all clocking channels and stores as self.Clocks
        """
        self.Clocks={}
        for tg in self.TimingGroupData:
            if hasattr(tg,'ClockedBy'):
                clck=self.getChannel(tg.ClockedBy[0].PCDATA)
                if clck != None:
                    self.Clocks.update({int(tg.GroupNumber[0].PCDATA):[int(clck.TimingGroup[0].PCDATA),int(clck.TimingGroupIndex[0].PCDATA)]})
        return

    def isClock(self,timingGroup,channelIndex):
        """
        returns False if channel is not a clock; otherwise returns timingGroup number
        the channel is a clock for
        """
        if (not hasattr(self,'Clocks')):
            self.getClocks()
        for tg,c in self.Clocks.items():
            if c==[timingGroup,channelIndex]:
                return tg
        return False

    def isInput(self,timingGroup,channelIndex):
        """
        returns False if channel is not a sampling input channel and True if it is
        """
        try: 
            if {"IN":"INPUT","OUT":"OUTPUT"}[str(self.getChannel([timingGroup,channelIndex])
                                        .Direction[0].PCDATA).upper().strip().split('PUT')[0]]=='INPUT':
                return True
        except: pass
        try:
            if {"IN":"INPUT","OUT":"OUTPUT"}[self.getTimingGroup(timingGroup)
                                        .Direction[0].PCDATA.upper().strip().split('PUT')[0]]=='INPUT':
                return True
        except: pass
        return False

    def getTimingGroup(self,timingGroupNumber):
        """
        Returns the timing group with specified number
        """
        for group in self.TimingGroupData: 
            if int(group.GroupNumber[0].PCDATA)==int(timingGroupNumber): return group

    def getChannel(self,channelName):
        """
        returns the timingGroup number and timingGroup index for a channel of specified name as a pair [tg,tgi]. Return the channel node, not the index
        """
        if (not hasattr(self,'Channel')): return None
        if isinstance(channelName, basestring):
            for chan in self.Channel:
                if hasattr(chan,'ChannelName'):
                    if chan.ChannelName[0].PCDATA==channelName: 
                        return chan
            else: return None
        elif type(channelName)==type([]):
            for chan in self.Channel:
                try: 
                    if ((int(chan.TimingGroupIndex[0].PCDATA)==int(channelName[1])) 
                        and (int(chan.TimingGroup[0].PCDATA)==int(channelName[0]))):
                        return chan
                except: pass
            return None
        else: return None
        
    def createTimingGroupHeirarchy(self):
        """
        Creates a heirarchy of timing-groups by associating each with a level.
        The lowest level, 0, clocks nothing
        one of level 1 clocks one of level 0        
        one of level 2 clocks one of level 1...etc
        results are stored in the object as attribute tGroupClockLevels,
        which is a dictionary of (timingGroup# : timingGroupLevel) pairs
        """         
        
        tgroups=self.getDescendentsByType('TimingGroupData')
        tGroupClockLevels=numpy.zeros(len(tgroups),numpy.byte)
        bumpcount=1
        while bumpcount!=0:
            maxlevel=max(tGroupClockLevels)
            if maxlevel>len(tgroups): pass #raise exception for circular loop
            bumpcount=0
            tgn=[]
            for s in range(len(tgroups)):
                if hasattr(tgroups[s],"GroupNumber"):
                    gn=int(tgroups[s].GroupNumber[0].PCDATA)
                else: pass
                    # raise 'All timing groups must have groupnumbers; offending <TimingGroupData> node has position '+s+' in channelmap'
                if maxlevel==0: tgn=[tgn,gn]
                if (tGroupClockLevels[s] == maxlevel):
                    if hasattr(tgroups[s],'ClockedBy'): clocksource=tgroups[s].ClockedBy.PCDATA
                    else: pass # raise 'TimingGroup '+gn+' must have a channel as clock source (<ClockedBy> node)' 
                    if (clocksource != 'self'):
                        clockgroup=self.getChannel(clocksource).TimingGroup[0].PCDATA
                        for k in range(len(tgroups)):
                            if tgroups[k].GroupNumber[0].PCDATA==clockgroup: break
                        tGroupClockLevels[k]=maxlevel+1
                        bumpcount+=1
        tGroupNumbers = [int(a.GroupNumber.PCDATA) for a in self.getDescendentsByType('TimingGroupData')]
        self.tGroupClockLevels = dict(zip(tGroupNumbers,tGroupClockLevels)) # dictionary of tg#:tgLevel pairs
        return self.tGroupClockLevels
        
    def findTimingGroupResolutions(self):
        """
        establish clocking resolutions which work for each clocking chain, 
        such that descendents clock at a multiple of their clocker's base frequency
        stores result at self.tGroupClockResolutions
        (first establishes a timingGroup heirarchy if not already existent on node)        
        Untested - should follow block at line 627 in IDL version
        """
        if (not hasattr(self,'tGroupClockLevels')): self.createTimingGroupHeirarchy()
        cl=max(self.tGroupClockLevels.values()) 
        res={}        
        while (cl >=0):
            tgThisLevel=[tg for tg,tgl in self.tGroupClockLevels.items() if tgl==cl]
            for tg in tgThisLevel:
                tgNode=self.getItemByFieldValue('TimingGroupData','GroupNumber',str(tg))
                if hasattr(tgNode,'ClockPeriod'):
                    cpNode=tgNode.ClockPeriod[0]
                    clockperiod=cpNode.PCDATA
                else: 
                    clockperiod=numpy.float64(0.0002)   # add a clockperiod node with default value
                    cpNode=tgNode.insert(ClockPeriod(str(clockperiod)))
                if hasattr(cpNode,'current_value'): 
                    if cpNode.current_value != u'':
                        clockperiod=cpNode.current_value
                if hasattr(tgNode,'ClockedBy'):
                    if tgNode.ClockedBy[0].PCDATA!='self':
                        clocksource=tgNode.ClockedBy[0].PCDATA
                        clockgroup=self.getItemByFieldValue('TimingGroupData','GroupNumber',self.getChannel(clocksource).TimingGroup[0].PCDATA)
                        if hasattr(clockgroup,'ClockPeriod'):
                            if hasattr(clockgroup.ClockPeriod[0],'current_value'):
                                timerperiod=clockgroup.ClockPeriod[0].current_value
                            else: timerperiod=clockgroup.ClockPeriod[0].PCDATA
                        else: timerperiod=numpy.float64(0.0002)
                        clockperiod=numpy.ceil(numpy.float64(clockperiod)/numpy.float64(timerperiod))*numpy.float64(timerperiod)
                if hasattr(tg,'current_value'):
                    tgNode.current_value=str(clockperiod)
                else: tgNode.addAttribute('current_value',str(clockperiod))
                try: res.update({tg:numpy.float64(clockperiod)})  # this needs to be converted to a numeric value, not a string !!!!!
                except ValueError: res.update({tg:numpy.float64(0.0002)})
            cl-=1
        self.tGroupClockResolutions=res
        #self.hardwaretime=self.getDictMaxValue(self.tGroupClockResolutions)
        return res
    
    def getHardwaretime(self):
        """
        This method is used to get the minimum time advance required to syn the level 0 board. Added on 12/19/2013 by JZ.
        """
        channelRes=self.findTimingGroupResolutions()
        channelHeir=self.createTimingGroupHeirarchy()
        timesort=[]
        for s in range(len(channelHeir)):
            tgadvance=(2**channelHeir[s])*channelRes[s]
            timesort.append(tgadvance)
        hardwaretime=max(timesort)
        self.hardwaretime=hardwaretime
        
        return self.hardwaretime
          
    
    def creatMissingChannels(self):
        """
        This methods intends to create undecleared channels for each timing group, including/not including the FPGA board, in the channalmap and assign initial and holding values for them. 
        """
        # First for each TimingGroupData in the channelmap, find its GroupNumber and Channelcount. Count how many channels are in this timing group. 
        # First find the number of timing groups in the channelmap.
        timinggroup=self.getDescendentsByType('TimingGroupData')
        channel=self.getDescendentsByType('Channel')
        
        #The following define all the missing channels and assign default initial and holding values for them, including the channels on the PFGA board.
        for tg in range(len(timinggroup)):
            # Get the timing group number and channelcount in this timinggroup.            
            tgn=int(timinggroup[tg].GroupNumber[0].PCDATA)
            chancount=int(timinggroup[tg].ChannelCount[0].PCDATA)
            for tgi in range(chancount):
                # Check whether this channel has been decleared. If yes, then check the next channel. 
                # If not, then declear this channel with default initial and holding value.              
                for chan in channel:
                    ctg=int(chan.TimingGroup[0].PCDATA)
                    ctgi=int(chan.TimingGroupIndex[0].PCDATA)
                    if [tgn,tgi]==[ctg,ctgi]: break
                else:
                    newchannel=gnosis.xml.objectify._XO_Channel()
                    newname=gnosis.xml.objectify._XO_ChannelName()
                    newtg=gnosis.xml.objectify._XO_TimingGroup()
                    newtgi=gnosis.xml.objectify._XO_TimingGroupIndex()
                    newinival=gnosis.xml.objectify._XO_InitialValue()
                    newholdval=gnosis.xml.objectify._XO_HoldingValue()
                    
                    nm='TG'+str(tgn)+'TGI'+str(tgi)
                    newname.set_value(nm)
                    newtg.set_value(tgn)
                    newtgi.set_value(tgi)
                    newinival.set_value(0)
                    newholdval.set_value(0)
                    
                    newchannel.insert(newname)
                    newchannel.insert(newtg)
                    newchannel.insert(newtgi)
                    newchannel.insert(newinival)
                    newchannel.insert(newholdval)
                    
                    self.insert(newchannel)
        
        return None

class Edge(gnosis.xml.objectify._XO_,XTSM_core):
    scopePeers=[['Channel','ChannelName','OnChannel']]
    def parse_proffer(self,startTime):
        """
        returns parsed values for [[timinggroup,channel,time,edge]]
        times will be returned relative to the provided (numeric) start-time
        unfinished!
        """
        t=self.Time[0].parse()+numpy.float64(startTime)
        self.time=t
        v=self.Value[0].parse()
        self.value=v
        [tg,c]=self.OnChannel[0].getTimingGroupIndex()
        self.channel=c        
        if (not hasattr(self,'guid')):
            self.generate_guid(1)
        if hasattr(self,'_fasttag'): return [tg,c,t,v,self._fasttag]
        else: return [tg,c,t,v,-1]
        
    def parse_harvest(self,dense_time_array):
        '''
        Returns an edge array entry with coerced times from denseT that are nearest to an edge's requested time
        ''' 
        idx=dense_time_array.searchsorted(self.time)
        if dense_time_array[idx]!=self.time: 
            try:
                if abs(dense_time_array[idx]-self.time)>abs(dense_time_array[idx-1]-self.time):
                    idx=idx-1
            except IndexError: pass
        self.Time[0].addAttribute("current_value",str(dense_time_array[idx]))
        self.time=dense_time_array[idx]
        self.value=self.Value[0].parse({'T':self.time,'TI':self.time})
        return numpy.array([idx,self.channel,self.time,self.value,self._fasttag])

'''
class Value(gnosis.xml.objectify._XO_,XTSM_core):
    def __init__(self, value=None):
        XTSM_core.__init__(self, value)
        self.value = value
'''

class Interval(gnosis.xml.objectify._XO_,XTSM_core):
    scopePeers=[['Channel','ChannelName','OnChannel']]
    def parse_proffer(self,startTime):
        """
        returns parsed values for [[timinggroup,channel,starttime,endttime,Vresolution,Tresolution,edge]]
        times will be returned relative to the provided (numeric) start-time
        unfinished!
        """
        st=self.StartTime[0].parse()+numpy.float64(startTime)
        et=self.EndTime[0].parse()+numpy.float64(startTime)
        self.endtime=et
        self.starttime=st
        #v=self.Value[0].parse()
        vres=self.VResolution[0].parse()
        tres=self.TResolution[0].parse()
        [tg,c]=self.OnChannel[0].getTimingGroupIndex()
        self.tg=tg
        self.c=c
        if (not hasattr(self,'guid')):
            self.generate_guid(1)
        if hasattr(self,'_fasttag'): return [tg,c,st,et,vres,tres,self._fasttag]
        else: return [tg,c,st,et,vres,tres,-1]
        
    def expected_samples(self, dense_time_array):
        """
        Returns number of samples interval will generate given a dense time array
        """
        return ((dense_time_array>=self.starttime)&(dense_time_array<=self.endtime)).sum()
        
    def parse_harvest(self, dense_time_array):
        """
        Returns all edges according to times in this interval
        first index (timinggroup number) replaced with time index
        """
        
        startind=dense_time_array.searchsorted(self.starttime)
        endind=dense_time_array.searchsorted(self.endtime)        
        self.T=dense_time_array[startind:(endind+1)]        
        TI=self.T-self.starttime
        self.V=self.Value[0].parse({'T':self.T,'TI':TI})
        numelm=self.T.size
            
        new_array2 = numpy.empty((5,numelm),dtype=numpy.float64) # NDG 051714 to float64
        new_array2[0,:]=numpy.arange(startind,endind+1)
        new_array2[1,:]=self.c
        new_array2[2,:]=self.T
        new_array2[3,:]=self.V
        new_array2[4,:]=self._fasttag
            
        return new_array2
            
    def _figure_autotype(self):
        return "TimeSeries"
    def _figuredata_autogen(self,dataname,figure):
        def gen_x():
            return self.T
        def gen_y():
            return self.V
        return ('gen_'+dataname)()

class Script(gnosis.xml.objectify._XO_,XTSM_core):
    """
    A class for execution of semi-arbitrary scripts
    """
    def _analyze_script(self):
        """
        finds the references to undeclared variables as a dictionary
        of variable:line# pairs and attaches them to self.references
        
        also finds the assignments to new variables as a dictionary
        of variable:[line numbers] pairs
        """
        if not self.scoped: self.buildScope()
        if not hasattr(self,'syn_tree'): self._build_ast()
        sv=self.ScriptVisitor()
        self.assignments={}
        self.references={}
        self.dependencies={}
        try:
            sv.visit(self.syn_tree)
        except AttributeError:
            return
        self.assignments=sv.assignments
        self.references=sv.references
        self.dependencies=sv.references
        #pdb.set_trace()
        for scopeitem in self.scope:
            try:
                del self.dependencies[scopeitem]
            except KeyError:
                pass
        for dep in self.dependencies:
            self.dependencies[dep] = False
            #self.dependencies.update({self.dependencies[dep]:False})
        
    def _find_dependencies(self,server):
        """
        finds XTSM elements which should generate the data needed in dependencies
        - does so by finding one named according to the dependencies found in script.
        Since data will not yet exist, onchange events will be attached to XTSM nodes
        which match by name.  onchange callback "registerData" will be called, which
        looks for a DataLink Attachment, and if present will call DataLink's retrieveData
        command
        
        priority for data will be first to scope elements, then parent, peers,
        children
        """
        self.server = server
        self._analyze_script()
        targs=[self.__parent__,self.__parent__.getChildNodes(),self.getChildNodes()] # possible target nodes
        for dep in self.dependencies:  # foreach dependent find a node with this name and quit
            for targ in targs:
                try: 
                    if dep.upper().strip()==targ.Name.PCDATA.upper().strip(): 
                        self.dependencies.update({self.dependencies[dep]:targ})
                        break
                except AttributeError: pass
        temp_dep = copy.deepcopy(self.dependencies)
        for dep in temp_dep: # check if dependent is an acceptable python module - if so, don't need to listen for it
            if dep.lower().strip() in sheltered_script.ALLOWED_SCRIPT_MODULES:
                self.module_dependents.update({dep.lower.strip():sheltered_script.ALLOWED_SCRIPT_MODULES[dep.lower.strip()]})                
                del self.dependencies[dep]
            if dep == 'self':
                del self.dependencies[dep]#Addded by CP 2014-11-10
            if dep == 'commands':
                del self.dependencies[dep]#Addded by CP 2014-11-10
        if not all(self.dependencies.values()): 
            self.active=False # if any dependencies are missing don't bother executing
            unfound=[d for d in self.dependencies if not self.dependencies[d]]
            self.addAttribute("parser_error","undetermined dependent(s): "+", ".join(unfound))
        print self.dependencies
        if len(self.dependencies)==0: self.execute() # if no dependencies, execute immediately
    
    def __generate_listener__(self):
        """
        generates listeners for each of the dependencies found in the script
        not already in the element's scope.
        """
        if hasattr(self,'active') == False:
            #print 'Script is not "active"'#CP
            return
        if not self.active: return
        for dep in self.dependencies:
            dep.registerListener({"method":self.registerData, "dependent":dep})
        self.dataReturned={dep:False for dep in self.dependencies}
        self.data={}
        
    def registerData(self,params):
        """
        callack when data is ready  -  deregisters event listeners as well
        """
        if not self.active: return
        if type(params['root_changed_elm']) in [DataLink]:
            try:
                data = params['root_changed_elm'].retrieveData()
                self.data.update({params['dependent']: data})
                self.dataReturned.update({self.dataReturned[params['dependent']]:True})
            except: pass
        if all(self.dataReturned.values()): self.execute()     # this triggers script execution once all dependents have arrived   

    def execute(self):
        """
        executes the script
        """
        if not hasattr(self,'data'):
            self.data = {}
        self.data.update({'self':self})
        # if this requires a timeout facility, use timed script - note this
        # requires 0.5-1.0s of startup time!
        '''Old method of executing scripts - now moved to the script server. CP 2014-10-20
        if hasattr(self,'TimeOut'):
            self.data=sheltered_script.timed_execute_scripts([self.ScriptBody.PCDATA],[self.data])[0]
        else:  # otherwise use standard execution
            self.data=sheltered_script.execute_scripts([self.ScriptBody.PCDATA],[self.data])[0]
        '''
        
        on_main = False
        try:
            flag = self.getDescendentsByType('ExecuteOnMainServer')[0]
            if flag.PCDATA == 'False':
                on_main = False
            else:
                on_main = True
        except IndexError:
            on_main = False
        
        if on_main:
            self._execute()
            #import XTSMserver.ServerCommand move to top
            #exec_command = XTSMserver.ServerCommand(self.server, self._execute())
            #self.server.command_queue.add(exec_command)
            #self.package_outputs()
        else:
            commands = {'script_body':self.ScriptBody.PCDATA,
                    'context': self.data,
                    'callback_function':self.package_outputs,
                    'ExecuteOnMainServer': on_main}
            self.server.execute_script(commands)
            #self.server.execute_script(self.ScriptBody.PCDATA, self.data, self._execute(),self.package_outputs())
            pass
            #Note CP: This should provide a callback function to the script server
            # like, self._script_complete(), that then takes the data from the
            #script server and finishes handling it.
            #self.package_outputs()
    
    def _execute(self):
        #pdb.set_trace()
        script = self.ScriptBody.PCDATA
        context = self.data
        old_stdout = sys.stdout
        if DEBUG: print "class Script, function _execute, script:", script
        try:
            capturer = StringIO.StringIO()
            sys.stdout = capturer
            t0=time.time()
            exec script in globals(),context
            if DEBUG: print "class Script, function _execute, context:", capturer.getvalue()
            t1=time.time()
            context.update({"_starttime":t0,"_exectime":(t1-t0),"_script_console":capturer.getvalue()})
        except Exception as e: 
            context.update({'_SCRIPT_ERROR':e})
            print '_SCRIPT_ERROR'
#          del context['__builtin__']  # removes the backeffect of exec on context to add builtins
        sys.stdout = old_stdout
        self.data = [context]
        self.package_outputs(self.data)
        ###
    
    def package_outputs(self, data=None):
        """
        #TODO?
        attaches script outputs to the node after execution
        """
        if data != None:
            self.data = data
        #pdb.set_trace()
        # first attach the console output and errors
        if not hasattr(self,'ScriptConsole'):
            self.insert(ScriptConsole())
            #pdb.set_trace()
        try:
            self.ScriptConsole[0].stream(self.data[0]['_script_console'])
        except KeyError:
            pass
        try:
            self.ScriptConsole[0].stream(self.data[0]['_SCRIPT_ERROR'],texttype='err_out')
        except (KeyError,TypeError):
            #TypeError if it was looking for unicode to stream and got an exceptions.NameError
            pass
        # harvest outputs declared as child ScriptOutput elements 
        if not hasattr(self, 'ScriptOutput'):
            self.insert(ScriptOutput())
            self.ScriptOutput.insert(gnosis.xml.objectify._XO_Name('_script_console'))
            return
        for output in self.ScriptOutput:
            if hasattr(output,'Name'):
                name = output.Name.PCDATA.strip()
            else:
                pdb.set_trace()
                #The rest of else shouldn't be necessary
                #pdb.set_trace()
                try:
                    #for child in enumerate(output.getChildNodes()):
                    name = str(output.getChildNodes()[0].get_tag()).strip()
                except:
                    output.addAttribute("parser_error","could not find name of elements in script")
                    #What exceptions does this throw?
                    pdb.set_trace()
            try:
                #pdb.set_trace()
                output.set_value(self.data[0][str(name)])
                pass
            except AttributeError:
                pdb.set_trace()
                output.addAttribute("parser_error","could not set_value to XTSM")
        
    def _build_ast(self):
        """
        builds the abstract syntax tree of the script
        """
        if self.ScriptBody.PCDATA == "":
            return
        if self.ScriptBody.PCDATA == None:
            return
        arg = saxutils.unescape(self.ScriptBody.PCDATA)
        self.syn_tree=ast.parse(arg)

    def dispatch(self,server):
        """
        Searches for "Remote" tag and sends that to that server it figures out
        it needs to go to.
        If Remote does not contain a valid address (e.g. ip address,
        host name, etc...), then the script object looks into its xml context
        (e.g. am i a child of an instrument, etc... and finds what the
        host the instrument is on, etc...)
        """
        
        #Right now this will prevent any scripts from sending if PullData is False
        #We should change this so that it still sends the scripts but no data is returned from the other server
        if not hasattr(self.__parent__,'PullData'):
            return
        if self.__parent__.PullData.PCDATA == 'False':
            return
            
        xtsm_owner = self.getOwnerXTSM()
        
        if hasattr(self,'Remote'):
            self.script_destination = self.Remote.PCDATA  #Have this handle multiple kinds. name, ip, instrument etc.
        else:
            # No Remote tag given, so look for the ServerAddress in the
            # metadata of the Instrument.
            # determine context of script node.
            # These are details of how to identify the destination
            try:
                def destination_from_instrument(script):
                    #This gets the instrument object's metadata
                    instrument_head = xtsm_owner.getItemByFieldValue("Instrument",
                                                                     "Name",
                                                                     script.__parent__.OnInstrument[0].PCDATA)
                    return instrument_head.ServerAddress[0].PCDATA
                    
                anticipated_contexts = {("__parent__","InstrumentCommand"): destination_from_instrument }  # {"relation":"tag_type"}
                for cont,action in anticipated_contexts.items():
                    #self.__parent__.get_tag() == InstrumentCommand
                    if getattr(self,cont[0]).get_tag() == cont[1]:
                        self.script_destination = action(self)
            except:
                print "Error: No Remote Tag. sending to self"
                self.script_destination = self.server.ip
                    
        sn = xtsm_owner.getItemByFieldValue("Parameter","Name","shotnumber").Value.PCDATA
        #self.insert(sn)
        
        if hasattr(self,'Time'):
            self.Time[0].parse()
            
        on_main = 'False'
        if hasattr(self, 'ExecuteOnMainServer'):
            if self.ExecuteOnMainServer.PCDATA != 'False':
                on_main = 'True'
        
        pckg = simplejson.dumps({"IDLSocket_ResponseFunction":"execute_script",
                                 "script_body":self.ScriptBody.PCDATA,
                                 'context':{},
                                 'callback_function':'None',
                                 'ExecuteOnMainServer':on_main,
                                 "terminator":"die"})
        if not server.send(pckg,self.script_destination,isBinary=False):
            print self.script_destination, "Did not receive this message:"
            print pckg
            pass
        else:
            if DEBUG: print 'Script Dispatched'

    class ScriptVisitor(ast.NodeVisitor):
        """
        helper-class to allow walking the syntax tree to find assignments
        and references to undeclared variables
        """
        def __init__(self):
            self.references={}    
            self.assignments={}    
            
        def visit_Name(self, node):
            if node.id in self.assignments: return
            self.references.update({node.id:node.lineno})
        def visit_Assign(self, node):
            for targ in node.targets:
                if targ.id in self.assignments:
                    self.assignments[targ.id].append(targ.lineno)
                else: 
                    self.assignments.update({targ.id:[targ.lineno]})
                self.visit(node.value)

class InstrumentCommand(gnosis.xml.objectify._XO_,XTSM_core):
    """
    A class for instructing instrumnets that are attached to servers and taking in data.
    """
    def __init__(self):
        XTSM_core.__init__(self)
        print "class InstrumentCommand, func __init__"
        
    def __generate_listener__(self):#This is called by installListeners - which is called in Server, compile active xtsm
        """
        Returns listener creation data - this will be automatically called
        recursively down the tree by installListeners in XSTM_core class.
        """
        print "in class InstrumentCommand, function __generate_listener__"
        #pdb.set_trace()
        
        
        
        if not hasattr(self,'PullData'):
            return
        if self.PullData.PCDATA == 'False':
            return
        
        
        if (not self.scoped):
            self.buildScope()
        print "scope:", self.scope.keys()
        data={}
        #pdb.set_trace()
        data.update({"generator": self})
        xtsm_owner = self.getOwnerXTSM()
        #cm=self.getOwnerXTSM().head[0].ChannelMap[0]
        #[tg,tgi]=self.OnChannel[0].getTimingGroupIndex()
        # chanobj=cm.getChannel(self.OnChannel.PCDATA) # might need this later
        #tgobj=cm.getItemByFieldValue("TimingGroupData","GroupNumber",str(int(tg)))
        #This gets the instrument object's metadata
        #pdb.set_trace()
        #instrument_head = xtsm_owner.getItemByFieldValue("Instrument",
        #                                                 "OnInstrument",
        #                                                 self.OnInstrument[0].PCDATA)
                                                         
       
        #print gen
        
        instrument_head = xtsm_owner.getItemByFieldValue("Instrument",
                                                         "Name",
                                                         self.OnInstrument[0].PCDATA)
                                                         
        #gen =  instrument_head.ServerIPAddress[0].PCDATA                                                  
        self.__listener_criteria__ = {"shotnumber":int(self.scope["shotnumber"])}
                                   #"sender":tgobj.Name.PCDATA}
        self.__listener_criteria__.update({'server_IP_address':instrument_head.ServerIPAddress[0].PCDATA,
                                           #'data_generator':gen,
                                           'instrument_name':"CCD"})
        data.update({"listen_for":self.__listener_criteria__ })
        data.update({"method": "link"})
        data.update({"onlink":self.onlink})
        self.data_link = None
        return data
        
    def onlink(self,listener):
        """
        Callback method provided to datalistener; called after data is linked-in
        """
        # who is self here? - the owner of the callback provided 
        # - e.g. the Sample element in XTSM onlink, not the listener it is later attached to
        #print "Class InstrumentCommand, function onlink"
        #print "data links in listeners:"
        #print listener.datalinks
        for link in listener.datalinks:
            for elm in link:
                reference_string = link[elm]
                self.insert(DataLink(reference_string))#Change t oDataLInk, argument for initialization is <URL for a file>.msgp[idstring][element]
                #print "Inserted DataLink into:", self, "with arg:", reference_string
                
class ScriptOutput(gnosis.xml.objectify._XO_,XTSM_core):
    """
    A class for exporting script results to datanodes
    """
    def set_value(self,value):
        if DEBUG: print "In class ScriptOutput, function set_value"
        """
        values are held on ScriptOutput nodes - this takes a python
        data construct, and attaches it to the XTSM tree using a DataLink;
        the data is streamed to disk using the owning XTSM's _analysis_stream
        """
        self.val=value
        if not hasattr(self,'scoped'): self.buildScope()
        self.uuid=uuid.uuid1()
        '''
        self.messagepack=msgpack.packb(value)
        idheader = msgpack.packb('id')+msgpack.packb(str(self.uuid))
        timeheader = msgpack.packb('timestamp')+msgpack.packb(str(self.timestamp))
        dataheader = '\xdb' + struct.pack('>L',len(self.messagepack))
        self.raw_link=self.getOwnerXTSM()._analysis_stream.write('\x83' + idheader + timeheader + dataheader, preventFrag=True)+"["+self.uuid+"]"
        self.getOwnerXTSM()._analysis_stream.write(self.messagepack)
        '''
        try:
            self.messagepack = msgpack.packb(value, use_bin_type=True)
        except:
            pdb.set_trace()
            self.addAttribute("parser_error","can't serialize this object to msgpack")
            #what exceptions does this throw?
        to_disk = {'id': str(self.uuid),
                  'time_packed': str(time.time()),
                  'len_of_packed_data': str(len(self.messagepack)),
                  'shotnumber': self.scope['shotnumber'],
                  'packed_data': self.messagepack }
        prefix = 'SO_SN'+str(self.scope['shotnumber'])+'_'
        header = {i:to_disk[i] for i in to_disk if i!='packed_data'}
        comments = str(header)
        extension = '.msgp'
        filestream = self.getOwnerXTSM()._analysis_stream
        path = filestream.write_file(msgpack.packb(to_disk, use_bin_type=True),
                                     comments=comments,
                                     prefix=prefix,
                                     extension=extension)
        
        try:
            self.raw_links.append(path)
        except AttributeError:
            self.raw_links = path
        self.insert(gnosis.xml.objectify._XO_Value(str(value)))
        self.insert(DataNode({"link":self.raw_links}))

class ScriptConsole(gnosis.xml.objectify._XO_,XTSM_core):
    """
    A class to hold contents of a script's console output
    """
    def stream(self,text,texttype='std_out'):
        self.set_value((u'<![CDATA['+self.PCDATA+u'<'+texttype+u'>'+text+u'</'+texttype+u'>]]>'))
        self.onChange()
    
class Figure(gnosis.xml.objectify._XO_,XTSM_core,live_content.Live_Content):
    """
    A class for generating SVG-format figures for viewing data within the XTSM tree
    
    this class can be pretty trivial - just an XTSM container for SVG figure data.
    generation of SVG figures themselves can be the responsibility of the user,
    and the recommendation is to do this using matplotlib functions, specifically:
        
    f, axes = matplotlib.pyplot.subplots(len(self.xvals), sharex=True, sharey=False)
    ... generate figure ...
    stream=StringIO.StringIO()
    f.canvas.print_figure(stream,format="svg")
    
    The figure XTSM object can then be defined with a single string argument to the constructor, 
    which is itself the svg figure (captured in the stream above).
    
    For common plots this method is a bit cumbersome, so some standard plot types
    are defined under the GLAB_Figure Module.  The Figure XTSM element can refer
    to them by name with the FigureType subnode.  
    """
    def __init__(self):    
        XTSM_core.__init__(self)
        live_content.Live_Content.__init__(self)
        self.data={}
        
    elements_to_fire_onChange=["data"]    
    
    class NoImageInScriptError(Exception):
        pass

    def find_image_in_script(self,script=None):
        """
        searches for figure data in the output of a script that has already run
        """
        # look in script's dictionary for strings of the svg type
        try: 
            strings=[st for st in script.data.values if isinstance(st,basestring)]
            self.svg_data=[s for s in strings if s[0:8]=="<ns0:svg"][0]
            return self.svg_data
        except: pass
        # look in script's dictionary for figure objects
        figs=[f for f in script.data.values() if isinstance(f,glab_figure.glab_figure_core)]
        for fig in figs:
            if hasattr(fig,"svgdata"): 
                self.svg_data=fig.svgdata
                return self.svg_data
        for fig in figs:
            try: 
                fig.make()
                self.svg_data=fig.toSVG()
                return self.svg_data
            except: pass
                        
    def make_image(self, svg_data=None):
        """
        makes an SVG image - if svg_data is provided, will insert it as the
        figure data.  Otherwise, this will generate the figure data from
        information provided in XTSM and whatever data it references
        """
        if svg_data!=None:
            self.svg_data=svg_data
            return
        if self.type=="Script":
            for sc in self.Script:
                sc.execute()
                try: self.svg_data=self.find_image_in_script(sc)
                except self.NoImageInScriptError: pass
            return
        # generates the figure as an object from glab_figure module and its known type
        if not hasattr(self,'figure_object'): self.figure_object=getattr(glab_figure,self.type)()
        try: self.svg_data=self.figure_object.toSVG()
        except: raise self.CannotMakeFigureWarning
        
    class CannotMakeFigureWarning(Exception):
        pass
        
    def _generate_live_content(self):
        try: return self.svg_data
        except AttributeError:
            try:
                self.make_image()
                return self.svg_data
            except self.CannotMakeFigureWarning:
                return "<img src='../images/seqicon_building.svg' />"
        
    def guess_format(self):
        """
        performs an automated search for nearby data in XTSM tree to try to 
        determine Type - If a script or type node is explicitly defined, it
        takes precendence, otherwise if components are partially or fully defined
        the type is inferred from those.  If none of these exist, the figure type is
        determined from the parent then peer elements' _figure_autotype method (if one exists)
        """
        figure_types=glab_figure.plot_types
        figure_types.insert(0,'Script')
        # check for explicit definition
        if hasattr(self,"FigureType"): 
            self.type=FigureType[0].PCDATA
            if self.type not in figure_types.keys():
                raise self.UnrecognizedFigureTypeError
            return
        # if there is a script child, assume it defines figure
        if hasattr(self,"Script"): 
            self.type="Script"            
            self.insert(FigureType(value=self.type))            
            return
        # guess from uniquely defining elements
        components=glab_figure.unique_plot_components
        for typ in components:
            has=[hasattr(self,comtyp) for comtyp in components[typ]]
            if any(has): break
        if any(has):
            self.type=typ
            self.insert(FigureType(value=self.type))            
            return
        # guess type from parent or peers' _figure_autotype method(s)
        typefromNodes=[item for sublist in [[self.__parent__],[self.__parent__.getChildNodes()]] for item in sublist]
        for node in typefromNodes:
            try: 
                self.type=node._figure_autotype(self)
                self.insert(FigureType(value=self.type))            
                self.typeinferredfrom=node
                return
            except AttributeError: pass
        # give up and return
        self.type=None
        return

    class UnrecognizedFigureTypeError(Exception):
        pass
    class cannotFindDataWarning(Exception):
        pass

    def find_dependencies(self):
        """
        looks for data the figure is dependent upon, if any cannot be located
        and is listed by the figure type as required, raises MissingDataError
        
        data returned as an element with a retrieveData method will be deposited
        under self.dependencies for later generation of a listener on the element;
        data returned as anything else will be appended immediately to self.data
        """
        if not self.type: self.guess_format()
        if self.type=='Script': return
        self.dependencies={}
        for ditem in glab_figure.plot_types[self.type].ditems:
            try: 
                found=self.find_data_component(ditem) 
                if hasattr(found,"retrieveData"):
                    self.dependencies.append({ditem:found})
                else: self.data.append({ditem:found})
            except self.cannotFindDataWarning: 
                if glab_figure.plot_types[self.type][ditem]['required']: raise self.MissingDataError
                else: pass

    def find_data_component(self,name):
        """
        attempts to find data element for figure by its name - searches for
        elements with preference high to low:
            
        child XTSM elements with tagname corresponding to data element, their DataLink or DataNodes, then their textual value
        child, then peer DataNodes or DataLinks with a <Name /> element with correct value
        calls to parent node's _figuredata_autogen method if it exists
        elements in XTSM variable scope with appropriate name
        child then peer Scripts with appropriately named variable as ScriptOutput or in a scope's assignment list

        this script may return an XTSM object, or data itself, depending on the type of object found. 
        """
        # look for named XTSM elements
        for namev in softstring.variants(name):
            try: 
                nt=getattr(self,namev)[0]
                try: return nt.DataLink
                except AttributeError: pass
                try: return nt.DataNode
                except AttributeError: return nt.PCDATA
            except AttributeError: pass
        # look for datanodes
        DataNodeList=[item for sublist in [[self.DataNode],[self.__parent__.DataNode]] for item in sublist]
        try: 
            for dn in DataNodeList:
                try: 
                    if dn.Name[0].PCDATA in softstring.variants(name): return dn
                except AttributeError: pass
        except AttributeError: pass
        # check if parent has an autogen method
        try: return self.__parent__._figuredata_autogen(name,self)
        except AttributeError: pass
        # find in variable scope
        if not self.scoped: self.buildScope()
        if name in self.scope: return self.scope[name]
        # find in nearby script
        ScriptList=[item for sublist in [[self.Script],[self.__parent__.Script]] for item in sublist]
        try: 
            for sc in ScriptList:
                for so in sc.ScriptOutput:
                    try: 
                        if so.Name[0].PCDATA in softstring.variants(name): return so
                    except AttributeError: pass
        except AttributeError: pass
        try: 
            for sc in ScriptList:
                if name in sc.assignments: return sc
        except AttributeError: pass
        # give up and return
        raise self.cannotFindDataWarning
        return
    
    def __generate_listener__(self):
        """
        generates listeners for each of the dependencies found 
        not already in the element's scope.
        """
        if not self.active: return
        for dep in self.dependencies:
            self.dependencies[dep].registerListener({"method":self.registerData, "dependent":self.dependencies[dep], "dependent_name":dep})
        self.dataReturned={dep:False for dep in self.dependencies}
        if self.type=="Script": 
            for script in self.Script:
                script.registerListener({"method":self.find_image_in_script})

    def registerData(self,params):
        """
        callback when data is changed in a dependent
        """
        if not self.active: return
        if type(params['root_changed_elm']) in [DataLink]:
            try:
                data = params['root_changed_elm'].retrieveData()
                self.data.update({params['dependent_name']: data})
                self.dataReturned.update({self.dataReturned[params['dependent']]:True})
            except: pass
        if all(self.dataReturned.values()): self.make_image()     # this triggers figure generation once all dependents have arrived   

        
class FigureType(gnosis.xml.objectify._XO_,XTSM_core):
    pass

class DataNode(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM element to hold raw data or links to it, representations of it,
    other datanodes, etc...
    """
    def __init__(self,params={}):
        """
        creates a DataNode from some parameters, which can include:
            
        link:  a string from which to generate a DataLink object (see its constructor for details)
        """
        XTSM_core.__init__(self)
        if params.has_key("link"): 
            if type(params["link"])!=type([]): params.update({"link":[params["link"]]})            
            for link in params["link"]:            
                self.insert(DataLink(link))

class DataLink(gnosis.xml.objectify._XO_,XTSM_core):
    """
    An XTSM element created when an element has associated data too cumbersome
    to attach directly to the tree.  
    """
    def __init__(self,reference_string=None):
        """
        creates a DataLink XTSM element from a reference string - expected formats
        for reference string are:
            
        <URL for a file>.msgp?idstring=xxx
        URL for dataheap elements not devised yet... follow hdf5 convention!        
        ... no more so far ...
        xxx will be the way to navigate within the file to get to the linked
        piece of data.
        make some sort of hierarchical format that allows (with slashes would
        be simple to remember) navigation within the file.
        eg. stream to disk is shot centric. Sort by shot would make sense.
        """
        XTSM_core.__init__(self)
        if reference_string.count('.msgp') >= 1:
            self.set_value(reference_string)
            return
        else: self.set_value(reference_string)
        
    def attach_data(self):
        self.PCDATA = saxutils.escape(str(self.get_data()))
    
    def retrieveData(self):
        if self.PCDATA.find('.heap')>=0: return self.get_from_heap()
        if self.PCDATA.find('.hdf5')>=0: return self.get_from_hdf5()
        if self.PCDATA.find('.h5')>=0: return self.get_from_hdf5()
        if self.PCDATA.find('.msgp')>=0: return self.get_from_msgp()
        
    def get_from_msgp(self):
        dataelm = self.PCDATA.split('.msgp[')[1].split(']')[0]
        f = io.open(self.PCDATA.split('.msgp[')[0],'rb')
        alldata = msgpack.unpackb[f.readall()]
        f.close()
        return alldata[dataelm]

    def get_from_heap(self):
        if not self.scoped:
            self.buildScope()
        heapname = self.PCDATA.split('.heap')[0]
        try: 
            return self.getOwnerXTSM().dataContext['_heaps'][heapname].getdata(self.scope['shotnumber'])
        except:
            False

    def get_from_hdf5(self):
        loc=self.PCDATA.split['.h5']
        h5file=tables.open_file(loc[0]+'.h5',mode="r", driver="H5FD_SEC2", NODE_CACHE_SLOTS=0)
        ret=h5file.getNode(loc[1])
        h5file.close()
        return ret

class Heap(gnosis.xml.objectify._XO_,XTSM_core):
    """
    A class for exporting data from a datanode into a data heap
    
    The heap element should wait for the associated data (or link to) to appear,
    then deliver that data into a specified dataheap.  To accomplish this,
    the onchange event of its parent is modified to scan parent, siblings and children
    for new data
    """
    def __del__(self):
        try: self.disable_listener(self.listener_out)
        except: pass
    
    def __post_run_init__(self):
        self.listener_out=self.__parent__.registerListener({'method':self.send})
    
    def diasble_listener(self):
        self.__parent__.deregisterListener(self.listener_out)
    
    def send(self,params):
        """
        sends data to the heap when it arrives, and disables the associated listener
        """
        if type(params['root_changed_elm']) not in [DataLink]:
            return False
        if not self.getHeap(): return False 
        try: 
            data=params['root_changed_elm'].retrieveData()
        except: self.addAttribute("parser_error","unable to retrieve data for this heap")
        self.buildScope()  # forcing rebuild of scope to assure post-parsed scope objects are included
        try: repnum=int(self.scope["repnumber"])
        except: repnum=1
        try: sn=int(self.scope["shotnumber"])
        except:
            self.addAttribute("parser_error","unable to heap this without a valid shotnumber")
            return False
        self._heap.push(data,sn,repnum)
        self.disable_listener()
        self.insert(DataLink(self._heap.permanent_id()))

    def getHeap(self):
        """
        Attempts to find, attach and return the associated heap; if it or its
        handlers do not exist, it will create them.
        """
        if self._heap: return self._heap
        try: heapname=self.HeapTo[0].parse()  # should do this for all heapto's...
        except: 
            self.addAttribute("parser_error","could not determine a heap name - check for well-formed HeapTo child")
            return False
        try: 
            dch=self._heap=self.getOwnerXTSM().dataContext['_heaps']
        except AttributeError: 
            self.addAttribute("parser_error","XTSM object has no associated data context")
            return False
        except KeyError:
            self.addAttribute("parser_warning","Associated data context is missing a _heaps element - created it on this shot")
            dch.update({'_heaps',{}})
        try: self._heap=dch[heapname]
        except KeyError: 
            self._heap = dch.update({heapname:hdf5_liveheap.glab_liveheap()})
            self.addAttribute("parser_warning","Heap did not exist - created it on this shot")
        return self._heap
            
class Sample(gnosis.xml.objectify._XO_,XTSM_core):
    scopePeers=[['Channel','ChannelName','OnChannel']]
    def parse_proffer(self,startTime):
        """
        returns parsed values for [[timinggroup,channel,starttime,endttime,sampleType,Tresolution,id]]
        times will be returned relative to the provided (numeric) start-time
        """
        st=self.StartTime[0].parse()+startTime
        et=self.EndTime[0].parse()+startTime
        self.endtime=et
        self.starttime=st
        tres=self.TResolution[0].parse()
        [tg,c]=self.OnChannel[0].getTimingGroupIndex()
        self.tg=tg
        self.c=c
        try: self.sampT={"EVEN":-2,"ANTIALIAS":-3}[self.SampleType[0].parse().upper().strip(' \t\n\r')]
        except: 
            self.sampT=-2
            try: self.SampleType.addAttribute("parser_error","unrecognized SampleType - use EVEN or ANTIALIAS (reverted to EVEN)")
            except AttributeError: pass
        sampT=self.sampT
        if (not hasattr(self,'guid')):
            self.generate_guid(1)
        if hasattr(self,'_fasttag'): return [tg,c,st,et,sampT,tres,self._fasttag]
        else: return [tg,c,st,et,sampT,tres,-1]
        
    def expected_samples(self, dense_time_array):
        """
        Returns number of samples interval will generate given a dense time array
        """
        return ((dense_time_array>=self.starttime)&(dense_time_array<=self.endtime)).sum()
        
    def parse_harvest(self, dense_time_array):
        """
        Returns all edges according to times in this interval
        first index (timinggroup number) replaced with time index
        """
        # find the corresponding update times from the timing group's sample times
        startind=dense_time_array.searchsorted(self.starttime)
        endind=dense_time_array.searchsorted(self.endtime)        
        # The update times for this interval are extracted using the indices. 
        T=dense_time_array[startind:(endind+1)]        
        TI=T-self.starttime
        V=self.Value[0].parse({'T':T,'TI':TI})
        numelm=T.size
        
        if hasattr(self,'_fasttag'):
            new_array = numpy.vstack((numpy.arange(startind,endind+1),numpy.repeat(self.c,numelm),T,V,numpy.repeat(self._fasttag,numelm))) 
        new_array = numpy.vstack((numpy.arange(startind,endind+1),numpy.repeat(self.c,numelm),T,V,numpy.repeat(-1,numelm)))
        self.startind=startind
        self.endind=endind
        return new_array
        
    def __generate_listener__(self):
        """
        Returns listener creation data - this will be automatically called
        recursively down the tree by installListeners in XSTM_core class.
        """
        if (not self.scoped): self.buildScope()
        data={}
        data.update({"generator": self})
        cm=self.getOwnerXTSM().head[0].ChannelMap[0]
        # chanobj=cm.getChannel(self.OnChannel.PCDATA) # might need this later
        [tg,tgi]=self.OnChannel[0].getTimingGroupIndex()
        tgobj=cm.getItemByFieldValue("TimingGroupData","GroupNumber",str(int(tg)))
        data.update({"listen_for":{"shotnumber":int(self.scope["shotnumber"]),
                                   "sender":tgobj.Name.PCDATA} })
        data.update({"method": "link"})
        data.update({"onlink":self.onlink})
        return data
        
    def onlink(self,listener):
        """
        Callback method provided to datalistener; called after data is linked-in
        """
        # who is self here? - the owner of the callback provided 
        # - e.g. the Sample element in XTSM onlink, not the listener it is later attached to
        for link in listener.datalinks:
            for elm in link:
                self.insert(DataNode({"link":link[elm]}))

class OnChannel(gnosis.xml.objectify._XO_,XTSM_core):
    def getTimingGroupIndex(self):
        """
        This should return the timingGroup number and and index of the channel.
        """
        [tg,c]=self.getOwnerXTSM().head[0].ChannelMap[0].getChannelIndices(self.PCDATA)
        return [tg,c]

class Parameter(gnosis.xml.objectify._XO_,XTSM_core):
    def __init__(self, name=None, value=None):
        XTSM_core.__init__(self)
        if name!=None:
            self.insert(gnosis.xml.objectify._XO_Name(name))
        if value!=None:
            self.insert(gnosis.xml.objectify._XO_Value(str(value)))
        return None


def main_test():
    """
    Trouble-shooting and testing procedure - not for long-term use
    """
    # parse the XML file
    # c:/wamp/www/sequences/8-6-2012/alternate.xtsm
    # /12-1-2012/FPGA_based.xtsm
    # xml_obj = gnosis.xml.objectify.XML_Objectify(u'c:/wamp/vortex/sequences/12-1-2012/FPGA_based_complex.xtsm')
    xml_obj = gnosis.xml.objectify.XML_Objectify(u'c:/wamp/www/MetaViewer/sequences/3-24-2014/22h_48m_37s.xtsm')
    py_obj = xml_obj.make_instance()
    py_obj.insert(Parameter(u'shotnumber',u'23'))
    try: py_obj.body.Sequence[0].parse()
    except:
        type, value, tb = sys.exc_info()
        traceback.print_exc()
        last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
        frame = last_frame().tb_frame
        ns = dict(frame.f_globals)
        ns.update(frame.f_locals)
        code.interact(local=ns)
    return py_obj

def trace_on_err():
    """
    Used to trace into error location automatically - not used long-term
    """
    type, value, tb = sys.exc_info()
    traceback.print_exc()
    last_frame = lambda tb=tb: last_frame(tb.tb_next) if tb.tb_next else tb
    frame = last_frame().tb_frame
    ns = dict(frame.f_globals)
    ns.update(frame.f_locals)
    code.interact(local=ns)


def trace_calls(frame, event, arg):
    if event != 'call':
        return 
    co = frame.f_code
    func_name = co.co_name
    if func_name == 'write':
        # Ignore write() calls from print statements
        return
    func_line_no = frame.f_lineno
    func_filename = co.co_filename
    caller = frame.f_back
    caller_line_no = caller.f_lineno
    caller_filename = caller.f_code.co_filename
    print 'Call to %s on line %s of %s from line %s of %s' % \
        (func_name, func_line_no, func_filename,
         caller_line_no, caller_filename)
    return

class InvalidSource(Exception):
    """
    An exception class raised in the XTSM_Object initialization routine
    """
    def __init__(self,source):
        self.msg='type '+str(type(source))+' cannot create an XTSM object'

class XTSM_Object(object):
    def __init__(self,source):
        """
        Builds an XTSM object from an XTSM string, a file-like stream or a filepath to
        a textfile containing xtsm - THIS IS A TOPLEVEL ROUTINE FOR THE PARSER 
        """
        if DEBUG: print "in class Command_Library, func preparse"
        if not isinstance(source, basestring):
            try:
                source=source.getvalue()
            except AttributeError: 
                raise InvalidSource(source)
        if source.find('<XTSM')==-1:
            try:
                source=urllib.urlopen(source).read()
            except IOError: 
                try: 
                    source=urllib.urlopen('file:'+source).read()
                except IOError:
                    InvalidSource(source)
        try:
            self.XTSM = gnosis.xml.objectify.make_instance(source)
        except AttributeError as e:
            print "Error making instance of XTSM"
            print e
            return
        
    def parse(self, shotnumber = 0):
        """
        parses the appropriate sequence, given a shotnumber (defaults to zero)
        - THIS IS A TOPLEVEL ROUTINE FOR THE PARSER
        """
        if DEBUG: print "in class XTSM_Object, func parse"
        self.XTSM.insert(Parameter(u'shotnumber',str(shotnumber)))
        parserOutput=self.XTSM.body[0].parseActiveSequence()
        return parserOutput

    def installListeners(self,dataListenerManager):
        """
        scans down the XTSM tree, creating dataListeners for all elements
        which should generate them.
        """
        print "class XTSM_object, function install Listeners"
        self.XTSM.head.installListeners(dataListenerManager)#Runs the "install Listeners function in XTSM_core class
        self.XTSM.getActiveSequence().installListeners(dataListenerManager)

    def isActive(self):
        """
        Returns the state of the XTSM object - if it still has active listeners
        will return True, otherwise False - NEEDS TO BE COMPLETED
        """
        print "This function needs to be completed - isActive"
        return False
        
    def deactivate(self,params={}):
        """
        Forces deactivation of listeners to allow cleanup - NEEDS TO BE COMPLETED
        """
        print "This function needs to be completed - deactivate"
        if params.has_key("message"): self.XTSM.addattribute("server_note",params["message"])


class Command_Library:
    """
    Houses a list of commands for pre/post parsing instructions.
    
    Note: Any functions which require additional values beyond "self" and "xtsm_obj" 
        should receive them all as a single variable, aka a 1D array of extra variables.
    """
    def __init__(self):
        pass
    
    def combine_with_delaytrain_old(self, XTSM_obj, params):
        """
        POST PARSE COMMAND ONLY
        
        Combines one or more timing groups with the delay train. Must have the
        same number of updates as the delay train. Final group will take the 
        place of the delay train and delete all others.
        Required params: Timing Groups Names.
            The Timing Group Names should all be strings. Timing string values will be appended in the order that
            the timing groups are input. Must include a delay train.
        Optional params: Length per Value, Length of Filler, Position of Filler
            Length per Value is an integer representing the number of bytes each end-value should be. Default is the length of the original values combined with no filler.
                Note: If this field is shorter than the combined length of the original values, this field will be ingored.
                (Ex: Sync has values == 1 byte, Delaytrain has "values" == 4 bytes. Hence, Length per value has a default value of 5 and must be >= 5.)
            Position of Filler should only be present if Length per Value > end-value length. This specifies the index at which filler will be placed.
                If unspecified, all filler will be placed at the end of the end-value.
                (Ex: Sync, Filler, Delaytrain has Position of filler == 1, since Sync takes the 0th position.)
            Length of Filler should be an integer number of bytes for the first filler. This variable should only be present if directly preceeded by a Position of Filler variable.
                If unspecified, will take on the largest possible filler length.
            Note: This Position of Filler/Length of Filler cycle can repeated. Each pair is executed sequentially.
        """
        # File params as either a timing group or a filler number.
        timing_group_names = []
        filler_info = []
        for param in params:
            if param != None:  # Ignore blank params.
                try:  # If the param can be expressed as an integer, then it's not a timing group name.
                    filler_info.append(int(param))
                except ValueError:
                    timing_group_names.append(str(param))
        # Gets relevant information (such as bytes_per_value, or bpv) from each group. The delay group is handled differently from the other groups.
        control_num = []
        timingstring_values = []
        num_updates = []
        value_size = 0
        for tg_name in timing_group_names:
            for k in range(len(XTSM_obj.ControlData)):
                ControlData = XTSM_obj.ControlData[k]
                if str(ControlData.ControlArray.tGroupNode.Name._seq[0]) == tg_name:
                    control_num.append(k)
                    # Now get the values for each timing group.
                    tg_string = ControlData.ControlArray.timingstring.tolist()
                    tg_body = tg_string[19:]
                    tg_bpr = tg_string[10]
                    tg_values = []
                    if hasattr(ControlData.ControlArray.tGroupNode, "DelayTrain"):
                        dControlData = ControlData
                        value_size += tg_bpr
                        # Note: For the delay train, the repeats are the "values".
                        for i in range(0, len(tg_body), (tg_bpr)):
                            tg_values.append(tg_body[i:(i+tg_bpr)])
                        num_updates.append(len(tg_values))
                    else:
                        tg_bpv = tg_string[9]
                        value_size += tg_bpv
                        for i in range(0, len(tg_body), (tg_bpv + tg_bpr)):
                            tg_values.append(tg_body[i:(i+tg_bpv)])
                    timingstring_values.append(tg_values)
        # Now that the data is extracted, delete the old timing groups.
        control_num.sort()
        control_num.reverse()  # List is sorted and reversed so as to not mess up the indeces of higher entries by deleting a lower entry.
        for i in control_num:
            del XTSM_obj.ControlData[i]
        # Find the max value size, if specified.
        if filler_info:
            max_size = filler_info.pop(0)
            
        else:
            max_size = value_size
        # If the max value size is larger than the current value size, look for filler pos/len pairs. Then place filler in the designated (or default) position.
        while value_size < max_size:
            
            try:
                filler_pos = filler_info.pop(0)
                try:
                    filler_len = filler_info.pop(0)
                except:
                    filler_len = max_size - value_size
            except:
                filler_pos = len(timingstring_values)
                filler_len = max_size - value_size
            # Insert a new column with only one element at the filler position. This element has the filler length as its value.
            timingstring_values.insert(filler_pos, [filler_len])
            value_size += filler_len
        
        # Joins next timingstring array in timingstring_values to the previous one. If the next array is a filler, create a zero array with dimensions specified by the number of updates and the filler length.
                
        for group_values in timingstring_values:
            if len(group_values) == 1:
                try:
                    newstring_body = numpy.concatenate((newstring_body, numpy.zeros((num_updates[0], group_values[0]), dtype = "uint8")), axis = 1)
                except NameError:
                    try:
                        newstring_body = numpy.zeros((num_updates[0], group_values[0]), dtype = "uint8")
                    except ValueError: print 'valueError Found!'
                    
            else:
                try:
                    newstring_body = numpy.concatenate((newstring_body, numpy.array(group_values, dtype = "uint8")), axis = 1)
                except NameError:
                    newstring_body = numpy.array(group_values, dtype = "uint8")

        # Flatten the new array so that it's a 1D array of values.
        newstring_body = newstring_body.flatten()
        # Reconstruct a new header, given the string length, number of channels (1), bytes_per_value (0), bytes_per_repeat (value_size), num_updates, and body length.
        body_length = newstring_body.shape[0]
        string_length = body_length + 19
        newstring = numpy.concatenate((numpy.array([string_length], dtype = "<u8").view("<u1"), numpy.array([1,0,value_size], dtype = "<u1"), numpy.array([num_updates[0], body_length], dtype = "<u4").view("<u1"), newstring_body))
        # Replace the delay train's timingstring with the new timingstring. Then send the new delay train data back to the XTSM object.
        return newstring

    class POSTPARSEERROR(Exception):
        pass

    def combine_with_delaytrain(self, XTSM_obj, params, TESTMODE=False):
        """        
        this algorithm is used to combine the raw timingstring data generated for multiple timing groups into
        a single stream of data - for example, for some devices (particularly FPGA-based) higher level
        functions require more complicated data inputs, despite the fact that their operation can be explained
        and controlled by a combination of simple elements - consider a "delay train clocker", which repeatedly counts a
        certain number of its own clock cycles before issuing one or more clock signals to slaved devices : two
        pieces of information are required for each cycle - how many cycles to wait, and which devices to clock.
        This can be represented as a combination of two timing groups - one which has a single channel which is
        self-clocking (the "delaytrain"), and a second timing group which represents the clocking channels for the
        slave devices.  Suppose the delaytrain clock cycle count is represented by a 32-bit integer, and there are
        eight slave devices, requiring 8 bits to flag which channels should be triggered.  These two groups can
        be entered in XTSM as if they are independent entities, and the timingstrings calculated as all others by
        standard parsing algorithms.  In a final step their timingstrings must be delivered to the hardware, which
        is most simply accomplished by combining the two fictional groups into a single group for the single piece
        of hardware.  This algorithm takes each 32-bit representation of a delay time and combines it with an 8-bit
        representation of clock-channel pulses, which requires a 40-bit per cycle representation streamed into the
        hardware.  Since hardware transfer is typically arranged in 32- or 64-bit lanes, it is best to combine these
        to 64-bit with fillers.  <-- these comments by NDG; original comments by JR below  -->
        
        Combines one or more timing groups with the delay train. Must have the
        same number of updates as the delay train. Final group will take the 
        place of the delay train and delete all others.
        Required params: Timing Groups Names.
            The Timing Group Names should all be strings. Timing string values will be appended in the order that
            the timing groups are input. Must include a delay train.
        Optional params: Length per Value, Length of Filler, Position of Filler
            Length per Value is an integer representing the number of bytes each end-value should be. Default is the length of the original values combined with no filler.
                Note: If this field is shorter than the combined length of the original values, this field will be ingored.
                (Ex: Sync has values == 1 byte, Delaytrain has "values" == 4 bytes. Hence, Length per value has a default value of 5 and must be >= 5.)
            Position of Filler should only be present if Length per Value > end-value length. This specifies the index at which filler will be placed.
                If unspecified, all filler will be placed at the end of the end-value.
                (Ex: Sync, Filler, Delaytrain has Position of filler == 1, since Sync takes the 0th position.)
            Length of Filler should be an integer number of bytes for the first filler. This variable should only be present if directly preceeded by a Position of Filler variable.
                If unspecified, will take on the largest possible filler length.
            Note: This Position of Filler/Length of Filler cycle can repeated. Each pair is executed sequentially.
        """
        BENCHMARK = False

        if BENCHMARK: t0=time.time()

        # File params as either a timing group or a filler number.       
        # find the groups referred to       
        timing_group_names = []
        filler_info = []
        for param in params:
            if param != None:  # Ignore blank params.
                try:  # If the param can be expressed as an integer, then it's not a timing group name.
                    filler_info.append(int(param))
                except ValueError:
                    timing_group_names.append(str(param))
              
        # Gets information (such as bytes_per_value, or bpv) from each group. The delay group is handled differently from the other groups.
        ControlDataNodes = [[cd for cd in XTSM_obj.ControlData if cd.ControlArray.tGroupNode.Name.PCDATA==tgn][0] for tgn in timing_group_names]#[XTSM_obj.getItemByFieldValue("ControlArray","Name",tgname).__parent__ for tgname in timing_group_names]
        timingstrings = [cdn.ControlArray.timingstring for cdn in ControlDataNodes]
        bytes_per_repeats = [tg[10] for tg in timingstrings]
        bytes_per_values = [tg[9] for tg in timingstrings]
        num_values_in_strings = [(timingstring.shape[0]-19)/(bytes_per_value+bytes_per_repeat) for timingstring,bytes_per_value,bytes_per_repeat in zip(timingstrings,bytes_per_values,bytes_per_repeats)]#[tg[11:15].view(dtype=numpy.uint32) for tg in timingstrings]
        #pdb.set_trace()        
        if not all([nv==num_values_in_strings[0] for nv in num_values_in_strings]):
            raise self.POSTPARSEERROR  # if the timingstrings are of uneven length they cannot be combined

        # decide if there are filler values to insert (/or leave as garbage data if speed is required)
        real_bytes_per_output = sum(bytes_per_values)
        try: bytes_per_output=filler_info[0] # try to find if a number of bytes per output is specified explicitly
        except: bytes_per_output=real_bytes_per_output # if none, set to number of bytes in timing strings of specified groups
        if bytes_per_output > real_bytes_per_output:
            for intron in range((len(filler_info)-1)/2):
                timingstrings.insert(filler_info[intron+1],0)  # insert a byte or None into the list of timingstrings indicating the "intron" or filler byte to insert
                bytes_per_values.insert(filler_info[intron+1],filler_info[intron+2])  # insert integers into the list of bytes_per_value indicating how many "intron" bytes to insert
                bytes_per_repeats.insert(filler_info[intron+1],0)  # insert 0 into the list of bytes_per_repeats

        # allocate space for output array - use a 2D table of bytes - should determine later which table
        # orientation gives the fastest conversion to a 1D string
        output = numpy.empty((num_values_in_strings[0],bytes_per_output),dtype=numpy.uint8)
        
        # populate the output
        byteptr=0  # pointer to active column to write into
        #pdb.set_trace()
        for timingstring,bytes_per_value,bytes_per_repeat in zip(timingstrings,bytes_per_values,bytes_per_repeats):
            #pdb.set_trace()
            for thisbyteinstring in range(max(bytes_per_value,bytes_per_repeat)):
                if isinstance(timingstring, (int, long, float, complex)):  # handles filler or inferon data
                    output[:,byteptr+thisbyteinstring]=timingstring
                elif timingstring==None: 
                    pass  # allow junk data from allocation to persist
                else:  # handles real data
                    output[:,byteptr+thisbyteinstring]=timingstring[(19+thisbyteinstring)::(bytes_per_value+bytes_per_repeat)]
            byteptr+=(thisbyteinstring+1)

        # define an output string into which to dump data (can this copy step be avoided?)
        output_string = numpy.empty(output.size+19,dtype=numpy.uint8)

        # Flatten the new array so that it's a 1D array of bytes - using ravel() avoids the copy one would make with flatten
        output_string[19:] = output.ravel()
        
        # Reconstruct a new header, given the string length, number of channels (1), bytes_per_value (0), bytes_per_repeat (value_size), num_updates, and body length.
        output_string[0:8] = (numpy.array([output.size+19], dtype = "<u8").view("<u1"))
        output_string[8] = 1
        output_string[9] = 0 # don't agree with this value, but keeping for backward compatibility
        output_string[10] = bytes_per_output # don't agree with this value, but keeping it - should be switched with previous
        output_string[11:15] = (numpy.array([num_values_in_strings[0]], dtype = "<u4").view("<u1"))
        output_string[15:19] = (numpy.array([output.size], dtype = "<u4").view("<u1"))

        # find the delay train control node:
        dControlData=[cdn for cdn in ControlDataNodes if hasattr(cdn.ControlArray.tGroupNode, "DelayTrain")][0]
        # remove the control data nodes for the source data - prevents packaging of their timingstrings into parser output
        for cdn in ControlDataNodes:
            XTSM_obj.ControlData.remove(cdn)
        # Replace the delay train's control data node, with new timingstring substituted. 
        dControlData.ControlArray.timingstring = output_string
        XTSM_obj.ControlData.append(dControlData)

        if BENCHMARK:
            t1=time.time()        
            print "new combine time: ", t1-t0
            t0=time.time()
            old_version_string = self.combine_with_delaytrain_old(XTSM_obj, params)
            t1=time.time()        
            print "old combine time: ", t1-t0
            print "equality check: ", numpy.array_equal(old_version_string,output_string)        


def preparse(xtsm_obj):
    """
    Executes functions before parsing the XTSM code.
    """
    if DEBUG: print "in class Command_Library, func preparse"
    xtsm_obj.Command_Library = Command_Library()
    for command in xtsm_obj.XTSM.head.PreParseInstructions.ParserCommand:
        try:
            # Check if the command exists in the Command Library. If so, execute it.
            command_name = getattr(xtsm_obj.Command_Library, str(command.Name.PCDATA))
            command_vars = []
            try:
                # Check for values to go with the command.
                non_blank_var = False
                for var in command.Value:
                    command_vars.append(var.PCDATA)
                    if var.PCDATA != None:
                        non_blank_var = True
                if non_blank_var:
                    command_name(xtsm_obj, command_vars)
                else:
                    command_name(xtsm_obj)
            except Exception as e:
                command_name(xtsm_obj)
        except AttributeError:
            # If the command field is not blank, print missing command error.
            if command.Name.PCDATA != None:
                print 'Missing command function: ' + command.Name.PCDATA

def postparse(timingstring):
    """
    Executes functions after parsing the XTSM code.Combine timing strings from timing groups with the delay train. 
    You must list names of groups to combine (each in a seperate "value" field), including the delay train group.  These groups must have the same number of updates.
    You can optionally include integer values for a byte-length-per-value, along with filler position and filler length, the latter two of which can be repeated indefinitely.
    For more info, see the parsers Command_Library.
    """
    if DEBUG: print "in class Command_Library, func postparse"
    
    timingstring.Command_Library = Command_Library()
    timingstring.XTSM = timingstring.__parent__.__parent__.__parent__
    for command in timingstring.XTSM.head.PostParseInstructions.ParserCommand:
        # Check if the command exists in the Command Library. If so, execute it.
        try: command_name = getattr(timingstring.Command_Library, str(command.Name.PCDATA))
        except AttributeError:
            # If the command field is not blank, print missing command error.
            if command.Name.PCDATA != None:
                print 'Missing command function: ' + command.Name.PCDATA
            continue # skip the command 
        command_vars = []
        try:
            # Check for values to go with the command.
            non_blank_var = False
            for var in command.Value:
                command_vars.append(var.PCDATA)
                if var.PCDATA != None:
                    non_blank_var = True
            if non_blank_var:
                command_name(timingstring, command_vars)
            else:
                command_name(timingstring)
        except TypeError:
            command_name(timingstring)        
        
# module initialization
# override the objectify default class
gnosis.xml.objectify._XO_ = XTSM_Element
# identify all XTSM classes defined above, override the objectify _XO_ subclass for each
allclasses=inspect.getmembers(sys.modules[__name__],inspect.isclass)
XTSM_Classes=[tclass[1] for tclass in allclasses if (issubclass(getattr(sys.modules[__name__],tclass[0]),getattr(sys.modules[__name__],'XTSM_core')))]
for XTSM_Class in XTSM_Classes:
    setattr(gnosis.xml.objectify, "_XO_"+XTSM_Class.__name__, XTSM_Class)
del allclasses
# this ends module initialization 
