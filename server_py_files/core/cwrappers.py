# -*- coding: utf-8 -*-
"""
Created on Sat May 10 00:29:46 2014

@author: Nate
"""

import ctypes
#from numpy.ctypeslib import ndpointer
import numpy
from bitarray import bitarray
import time, pdb
import file_locations, uuid
    
from numpy.ctypeslib import ndpointer

class repas():
    def __init__(self):
        print file_locations.file_locations['repasint_dll'][uuid.getnode()]
        self.lib = ctypes.cdll.LoadLibrary(file_locations.file_locations['repasint_dll'][uuid.getnode()])  #"c:\\Users\\Nate\\documents\\visual studio 2010\\Projects\\testctype\\x64\\Release\\testctype.dll"
        suffixes=["","dev","pulse","pulsedev"]
        # bit-flipping versions
        repasops={"uint8": ctypes.c_ubyte, "uint32":  ctypes.c_uint32}
        for suffix in suffixes:
            for ra in repasops:
                try: 
                    setattr(self,"fun_repas"+ra+suffix,getattr(self.lib,"repas"+ra+suffix))
                    getattr(self,"fun_repas"+ra+suffix).argtypes = [ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), ctypes.c_uint32,
                                                        ndpointer(ctypes.c_uint32, flags="C_CONTIGUOUS"), repasops[ra],
                                                        ndpointer(repasops[ra], flags="C_CONTIGUOUS"), ctypes.c_uint32]
                    getattr(self,"fun_repas"+ra+suffix).restype = None
                except: continue
#    def __del__(self):
#        del self.lib
    def repasint(self,flipstring,firstelm,PULSER=False,DEV=False):
        #pdb.set_trace()        
        ptrs = ((flipstring==0).nonzero())[0].astype(numpy.uint32)
        outbits=ptrs.size
        outdata = numpy.empty(numpy.unique(flipstring).shape[0]+2, dtype=getattr(numpy,"uint"+str(outbits))) #JZ add +2 on the array size.
        func = "fun_repasuint" + str(outbits) + ({True: "pulse", False: ""})[PULSER] + ({True: "dev", False: ""})[DEV]
        getattr(self,func)(flipstring, flipstring.size, ptrs,firstelm, outdata,outdata.size)  # JZ and NDG remove the +1 from the last parameter.
        #if not PULSER: outdata[-1]=0  # this was inserted to reproduce a bug in original code NDG 081414
        return outdata[1:-1]  # Change outdata[1:] to outdata[1:-1]  JZ 8/18/2014, the first element is the seed, and the last element is an extra one to reserve a memary space for last iteration of pointer.

    def OldRepresentAsInteger(self,channeltimes,seed, PULSER=False):
                
        ptrs = ((channeltimes==0).nonzero())[0].astype(numpy.uint32)
        Nchan = ptrs.size
        Nbitout = ptrs.size  # number of bits in integer to use
        try:
            dtype = {0:numpy.uint8,8:numpy.uint8,16:numpy.uint16,32:numpy.uint32,64:numpy.uint64}[Nbitout] # data type for output
        except KeyError:
            pass
        # find the final resting places of the pointers
        fptrs = [ptr for ptr in ptrs[1:]]
        # add in end pointer
        fptrs.append(channeltimes.shape[0])
        fptrs = numpy.array(fptrs)
        # create a bit-array to represent all channel outputs
        bits = bitarray(bin(seed)[2:].zfill(Nchan))#bitarray([1]*Nchan)
        bits.reverse()
        # create arrays of output times and values for a single channel
        numtimes = len(numpy.unique(channeltimes))
        outvals = numpy.empty(numtimes,dtype=dtype)
        outtimes = numpy.empty(numtimes,dtype=numpy.uint64)
        outptr = 0  # a pointer to the first currently unwritten output element
    
        if PULSER:
            optrs=ptrs
            while not (ptrs == fptrs).all():
                active = ptrs<fptrs # identify active pointers
                tim = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                #LRJ 10-30-2013 hitstrue disables unused channels
                lineindex=0
                hitstrue=[]
                for ct in channeltimes[ptrs]:
                        if (ptrs[lineindex]-optrs[lineindex])==2 and ct==tim:#self.channels.values()[lineindex].intedges.shape[1] == 2 and ct==time:
                            hitstrue.append(False)
                        else:
                            hitstrue.append(ct==tim)
                        lineindex+=1  
                hits = [ct == tim for ct in channeltimes[ptrs]] # find active pointers
                bits = bitarray(hitstrue) # assign bits based on whether a matching time was found
                # populate output arrays
                outvals[outptr] = numpy.fromstring((bits.tobytes()[::-1]),dtype=dtype)
                outtimes[outptr] = tim
                # advances pointers if active and hits are both true for that pointer.
                ptrs += numpy.logical_and(active, hits)
                outptr += 1
        else:            
            while not (ptrs == fptrs).all():
                active = ptrs<fptrs # identify active pointers
                tim = min(channeltimes[ptrs[active.nonzero()]]) # current time smallest value for "active" pointers
                flips = [ct == tim for ct in channeltimes[ptrs]] # find active pointers
                bits = bits^bitarray(flips) # flip bits where updates dictate using bitwise XOR
                # populate output arrays
                outvals[outptr] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)
                outtimes[outptr] = tim
                # advances pointers if active and flips and both true for that pointer.
                ptrs += numpy.logical_and(active, flips)
                outptr += 1
            # Now change final values to be zeros.
            bits = bitarray([0]*Nchan)
            outvals[-1] = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = dtype)            
        return outvals

repas=repas()

def test_repas():

    def generate_testdata(scale, nbits):
        a=numpy.array([0,100*scale]*(nbits-5), dtype=numpy.uint32)
        a=numpy.append(a,numpy.arange(0,scale, dtype=numpy.uint32)*10)
        a=numpy.append(a,numpy.array([100*scale], dtype=numpy.uint32))    
        a=numpy.append(a,numpy.arange(0,scale, dtype=numpy.uint32)*15)
        a=numpy.append(a,numpy.array([100*scale], dtype=numpy.uint32))    
        a=numpy.append(a,numpy.array([0,100*scale]*(2), dtype=numpy.uint32))
        a=numpy.append(a,numpy.array([0,150*scale]*(1), dtype=numpy.uint32))
        return a

    VERBOSE=False
    BENCHMARK=False
    DEVELOP=True
    PULSER=True

    NBITS=8
    a=generate_testdata(10000000,NBITS)
    bits=bitarray(NBITS)
    seed = numpy.fromstring((bits[::-1].tobytes()[::-1]), dtype = getattr(numpy,"uint"+str(NBITS)))
    t0=time.time()
    outdata=repas.repasint(a,seed[0],PULSER=PULSER)
    print time.time()-t0
    if VERBOSE:
        strout=""
        for line in range(0,NBITS):
            for elm in outdata:
                strout += str((int(elm) >> line) % 2)
            strout += "\n"
        print strout
    
    if DEVELOP:
        t0=time.time()
        outdata3=repas.repasint(a,seed[0],DEV=True, PULSER=PULSER)
        print time.time()-t0
        if VERBOSE:
            strout=""
            for line in range(0,NBITS):
                for elm in outdata3:
                    strout += str((int(elm) >> line) % 2)
                strout += "\n"
            print strout
        print "equality check: ", (outdata3==outdata).all()
    
    
    if BENCHMARK:
        t0=time.time()
        outdata2=repas.OldRepresentAsInteger(a,seed[0], PULSER=PULSER)
        print time.time()-t0
        if VERBOSE:
            strout=""
            for line in range(0,NBITS):
                for elm in outdata2:
                    strout += str((int(elm) >> line) % 2)
                strout += "\n"
            print strout
        print "equality check: ", (outdata2==outdata).all()
        
def test_merge_sorted():

    VERBOSE=False
    PERF_TEST=True
    BM_SS=True

    if PERF_TEST:
        a0=numpy.arange(3000000,dtype=numpy.float64)#numpy.array([2.0,3.0,4.0,9.0],dtype=numpy.float64)
        b1=numpy.array([17.5,100],dtype=numpy.float64)##numpy.array([3.0,7.0,8.0],dtype=numpy.float64)
        b0=numpy.array([22.5],dtype=numpy.float64)##numpy.array([3.0,7.0,8.0],dtype=numpy.float64)
        b2=numpy.array([10,17,24],dtype=numpy.float64)##numpy.array([3.0,7.0,8.0],dtype=numpy.float64)
        a1=2.5*numpy.arange(10000013,dtype=numpy.float64)
        arrs=[a0,b0,a1,b1,b2]
    else:
        a=numpy.array([2.0,3.0,4.0,9.0],dtype=numpy.float64)
        a1=numpy.array([2.5,3.0,4.5,9.0],dtype=numpy.float64)
        b=numpy.array([3.0,7.0,8.0],dtype=numpy.float64)
        arrs=[a,a1,b]
        
    t0=time.time()
    lens = (ctypes.c_ulong*(len(arrs)+1))()
    totsiz=0
    for arr in range(len(arrs)):
        lens[arr]=arrs[arr].size
        totsiz+=lens[arr]
    outarr=numpy.empty(totsiz,dtype=numpy.float64)
    arrs.append(outarr)
    if VERBOSE:
        for arr in arrs: print arr

    ctypes_arrays = [numpy.ctypeslib.as_ctypes(array) for array in arrs]
    pointer_ar = (ctypes.POINTER(ctypes.c_longdouble) * len(arrs))(*ctypes_arrays)
    ctypes_lens=ctypes.POINTER(ctypes.c_uint32)(lens)
    ctypes_arrnum = ctypes.c_uint16(len(arrs));
    ctypes.CDLL(file_locations.file_locations['repasint_dll'][uuid.getnode()]).merge_sorted_arrays3(pointer_ar,ctypes_arrnum,ctypes_lens)
    cc=outarr[0:ctypes_lens[len(arrs)-1]-1]
    t1=time.time()

    if VERBOSE:
        for arr in arrs: print arr
        print "length:" ,lens[len(arrs)-1]

    t2=time.time()
    ss = numpy.unique(numpy.concatenate(arrs[0:-1]))
    t3=time.time()


    print "Agrees with numpy.unique(numpy.concatenate(x)): ", numpy.array_equal(ss,cc)
    print "merge_sorted time:", t1-t0
    print "numpy sort time:", t3-t2
    print "merge_sorted/numpy: ", (t1-t0)/(t3-t2) 

    if BM_SS:
        t4=time.time()
        dd=numpy.insert(a0,a0.searchsorted(b0),b0)
        t5=time.time()
        print "inserted ", b0.size, " elms with searchsorted in ", t5-t4
    pdb.set_trace()

class DataWrongShapeError(Exception):
    pass

def merge_sorted_orig(arrs):
    """
    merges a list of pre-sorted 64-bit floating point (numpy) arrays, discarding duplicate items
    returns the merged array.  equivalent to numpy.unique(numpy.concatenate(arrs)) for pre-sorted
    arrays without self-duplicates, but ~x6 faster
        
    this routine calls a precompiled dll library function
    """
    if type(arrs)!=type([]): arrs=[arrs]
    num_arr=len(arrs)
    lens = (ctypes.c_ulong*(len(arrs)+1))()
    totsiz=0
    for arr in range(len(arrs)):
        if len(arrs[arr].shape)!=1: arrs[arr]=arrs[arr].flatten()
        #arrs[arr]=numpy.asarray(arrs[arr],dtype=numpy.float64).astype(numpy.float64)
        lens[arr]=arrs[arr].size
        totsiz+=lens[arr]
    outarr=numpy.empty(totsiz+1,dtype=numpy.float64)
    arrs.append(outarr)
    ctypes_arrays = [numpy.ctypeslib.as_ctypes(array) for array in arrs]
    pointer_ar = (ctypes.POINTER(ctypes.c_longdouble) * len(arrs))(*ctypes_arrays)
    ctypes_lens=ctypes.POINTER(ctypes.c_uint32)(lens)
    ctypes_arrnum = ctypes.c_uint16(len(arrs));
    ctypes.CDLL(file_locations.file_locations['repasint_dll'][uuid.getnode()]).merge_sorted_drop_dup(pointer_ar,ctypes_arrnum,ctypes_lens)
    cc=(outarr[1:ctypes_lens[num_arr]])
    del arrs[-1]
    #pdb.set_trace()
    return cc
 
def merge_sorted(arrs,track_indices=False,cast_up=True):
    """
    merges a list of pre-sorted 64-bit floating point (numpy) arrays, discarding duplicate items.
    returns the merged array and REPLACES input arrays' values with record of the corresponding index of the output 
    (merged) array. Aside from index-tracking, this is equivalent to numpy.unique(numpy.concatenate(arrs)) 
    for pre-sorted arrays without self-duplicates, but ~x6 faster
    
    example:  
        a=numpy.arange(1000,dtype=numpy.float64)*.01
        b=numpy.arange(1000,dtype=numpy.float64)*.01+.002
        ao=a.copy()
        bo=b.copy()
        arr=[a,b]
        c=merge_sorted_track_indices(arr)
        c[0:10]
        << array([ 0.   ,  0.002,  0.01 ,  0.012,  0.02 ,  0.022,  0.03 ,  0.032,
        0.04 ,  0.042])
        a[0:10]
        << array([  0.,   2.,   4.,   6.,   8.,  10.,  12.,  14.,  16.,  18.])
        b[0:10]
        << array([  1.,   3.,   5.,   7.,   9.,  11.,  13.,  15.,  17.,  19.])
        ao[7]
        << 0.070000000000000007
        c[a[7]]
        << 0.070000000000000007
        numpy.array_equal(c[a.astype(numpy.uint32)],ao)
        << True
        
    this routine calls a precompiled dll library function
    """
    # analyze input arrays to flatten if necessary and find total size
    if type(arrs)!=type([]): arrs=[arrs]
    num_arr=len(arrs)
    lens = (ctypes.c_ulong*(len(arrs)+1))()
    totsiz=0
    for arr in range(len(arrs)):
        if len(arrs[arr].shape)!=1: arrs[arr]=arrs[arr].flatten()
        lens[arr]=arrs[arr].size
        totsiz+=lens[arr]

    # scan input arrays to find appropriate data type for output
    input_types=[arr.dtype for arr in arrs]
    cast_to_bytes=sorted([it.itemsize for it in input_types])[{True:-1,False:0}[cast_up]]
    cast_to_type=input_types[[it.itemsize for it in input_types].index(cast_to_bytes)]
    cast_to_ctype=numpy_type_to_C(cast_to_type)
    
    # if necessary, cast inputs to common type
    for arr,i in [(arr,i) for arr,i in zip(arrs,range(num_arr)) if arr.dtype!=cast_to_type]:
        arrs[i]=arr.astype(cast_to_type)
    
    # define output and input arrays for passage to dll
    outarr=numpy.empty(totsiz+1,dtype=cast_to_type)
    arrs.append(outarr)
    ctypes_arrays = [numpy.ctypeslib.as_ctypes(array) for array in arrs]
    pointer_ar = (ctypes.POINTER(cast_to_ctype) * len(arrs))(*ctypes_arrays)
 
    # create variables to pass lengths and array counts
    ctypes_lens=ctypes.POINTER(ctypes.c_uint32)(lens)
    ctypes_arrnum = ctypes.c_uint16(len(arrs));

    # call the appropriate dll function
    dll_name=file_locations.file_locations['repasint_dll'][uuid.getnode()]
    func_root = "merge_sorted_"
    func_tail = {True:"track_indices_", False:""}[track_indices] + str(cast_to_type)
    getattr(ctypes.CDLL(dll_name),func_root+func_tail)(pointer_ar,ctypes_arrnum,ctypes_lens)

    # trim the output and eliminate the backeffect of appending output array argument, return
    cc=(outarr[1:ctypes_lens[num_arr]])
    del arrs[-1]
    return cc

def numpy_type_to_C(dtype):
    
    return {numpy.dtype('float64'):ctypes.c_double, numpy.dtype('float32'):ctypes.c_float}[dtype]