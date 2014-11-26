#!/usr/bin/python
#
# Software License Agreement (BSD License)
#
# Copyright (c) 2008, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#


##\author Derek King
##\brief Interface to Prologix GPIB-Ethernet controller

"""
Interactive interface to GPIB device using Prologix GPIB-Ethernet controller.

Usage: %(progname)s [-h] [-a adresss] [-u usb serial dev] [-g gpib_addr]

Options:
  -a address : Use address to connect to Prologix GPIB-Ethernet controller.  
               Address can be IPv4 address or hostname.
  -u dev     : Use given usb serial device to communicate to Prologix GPIB-USB controller.  
               Device is usually /dev/ttyUSBX
  -g gpib    : Use GPIP address to access specific device on GPIB bus.
               GPIB address is usually number 1-30.
  -h : show this help

Example:
  %(progname)s -a 10.0.1.197 -g 22

Interative Usage:
  Type SCPI command at prompt '>'.  Pressing enter will send command to device.
  To read SCPI output from previous command, don't type anything and just press enter.

  Note : SCPI = Standard Commands for Programmable Instruments

Interactive Example : (Reading device identification string)
  > *idn? <enter>
  > << ENTER >>
  Agilent Technologies,34410A,MY47007427,2.35-2.35-0.09-46-09

Interactive Example : (Voltage measurement from DMM)
  > meas:volt:dc?
  > << ENTER >>
  -2.12071654E-04
"""

import traceback
import socket
import sys
import re
import pdb
import time
import datetime
import matplotlib
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import math
import numpy

import getopt
import pdb

DEBUG = True
    
def usage(progname):
  print __doc__ % vars()


# Interface to GPIB bus
class PrologixGpibEthernet:
    def __init__(self, ip_address):
        self._gpib_address = None
        try :
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            port = 1234
            sock.connect((ip_address, port))
        except socket.error :
            raise RuntimeError("Error making connection to Prologix GPIB controller with address '%s'" %  ip_address)

        self._sock = sock

        self.settimeout(0.1)
        self._write('++auto 0\n')
        self._write('++eot_enable 1\n')
        self._write('++eot_char 0\n')
        self._write('++ver\n')
        ver = self._read("\n")
        m = re.match('Prologix GPIB-ETHERNET Controller version ([0-9.]+)', ver)
        if not m:
            raise RuntimeError("Error ++ver response is incorrect : '%s'" % ver.strip('\r\n'))

        msg = self.flush()
        if msg:
            print "Warning, flushed : ", msg

    def _read(self, eot="\x00"):
        sock = self._sock
        msg = ""
        try:
            while True:
                msg += sock.recv(1024)
                end = msg.find(eot)
                if end == len(msg)-1:
                    return msg[0:end-1]
                elif end != -1:
                    print "warning, dropping %d byte tail of message. Tail='%s'"%(len(msg)-end, msg[end:])
                    return msg[0:end-1]
        except socket.timeout:
            if len(msg) > 0:
                raise RuntimeError("Got timeout after receiving partial result : %s" % msg)
            else:
                return None

    def _write(self, line):
        self._sock.sendall(line)

    def _select(self, gpib_address):
        #print 'select %d' % self._gpib_address
        self._write('++addr %d\n' % self._gpib_address)

    def settimeout(self, timeout):
        """ Set read timeout in seconds """ 
        self._sock.settimeout(timeout)
        self._timeout = timeout

    def flush(self):
        """ Clear any read buffers out """
        self._sock.settimeout(0.1)
        line = self._read()
        result = ""
        while line != None:
            result += line
            line = self._read()
        self._sock.settimeout(self._timeout)
        return result

    # Core functions : every gpib adapter should implement: read() write() select()
    def select(self, gpib_address):
        if self._gpib_address != gpib_address:
            self._gpib_address = gpib_address
            self._select(self._gpib_address)

    def read(self):
        if self._gpib_address == None:
            raise RuntimeError("GPIB address must select()ed before read() is called\n")
        self._write("++read eoi\n")
        return self._read()

    def write(self, line):
        if self._gpib_address == None:
            raise RuntimeError("GPIB address must select()ed before read() is called\n")
        # escape +, \n, \r, and \27 (ESC) chars
        line = line.replace('\x1B', '\x1B\x1B')
        line = line.replace('\n', '\x1B\n')
        line = line.replace('\r', '\x1B\r')
        line = line.replace('+',  '\x1B+')
        self._write(line + "\n")
        

''' '''
def init_GPIB(self):
    '''
    if ip address is not found, run the program "GPIB Configuator" and look
    at ip. Or run "NetFinder" from Prologix
    '''
    self.GPIB_adapter = GPIB_control.PrologixGpibEthernet('10.1.1.113')
    
    read_timeout = 1.0
    if DEBUG: print "Setting adapter read timeout to %f seconds" % read_timeout
    self.GPIB_adapter.settimeout(read_timeout)
    
    gpib_address = int(7)#Scope over Rb exp
    if DEBUG: print "Using device GPIB address of %d" % gpib_address
    self.GPIB_device = GPIB_control.GpibDevice(self.GPIB_adapter, gpib_address)
    if DEBUG: print "Finished initialization of GPIB controller"
    
    

def get_scope_field(self,q1="Data:Source CH1",
                    q2="Data:Encdg: ASCII",
                    q3="Data:Width 2",
                    q4="Data:Start 1",
                    q5="Data:Stop 500",
                    q6="wfmpre?" ,
                    q7="curve?"):


    e1 = time.time()
    if not hasattr(self,'GPIB_device'):
        if DEBUG: print "GPIB device not ready"
        return
    response = self.GPIB_device.converse([q1,q2,q3,q4,q5,q6,q7])
    e2 = time.time()
    if DEBUG: print "Scope communication took", e2-e1, "sec"
    
    ystr = response["curve?"]
    if DEBUG: print "Data:", ystr
''' '''

# Interface to specific GPIB device on GPIB bus
class GpibDevice:
    def __init__(self, gpib_adapter, gpib_addr):
        self._gpib_addr = gpib_addr
        self._gpib_adapter = gpib_adapter

    def read(self):
        self._gpib_adapter.select(self._gpib_addr)
        return self._gpib_adapter.read()

    def write(self, line):
        self._gpib_adapter.select(self._gpib_addr)
        self._gpib_adapter.write(line)    

    
    def converse(self,commands):
        responses={}
        if isinstance(commands, basestring): commands=[commands]
        i = 0
        for command in commands:   
            
            self.write(command)
            responses.update({command:self.read()})
            i = i + 1
        return responses
    
    
    
    
    
#    def converse(self,commands, timeouts):
#        responses={}
#        if isinstance(commands, basestring): commands=[commands]
#        i = 0
#        for command in commands:   
#            self._gpib_adapter.settimeout(timeouts[i])
#            self.write(command)
#            responses.update({command:self.read()})
#            i = i + 1
#        return responses

def main(argv):
    progname = argv[0]
    print argv
    import getopt
    optlist,argv = getopt.gnu_getopt(argv, "a:s:g:h");

    gpib_address = 22
    read_timeout = 1.0
    adapter = None
#    for opt,arg in optlist:
#        if (opt == "-h"):
#            usage(progname)
#            return 0
#        elif (opt == "-a") :
#          print "Connecting to Prologix GPIB Ethernet adapter using network address %s" % arg
#          adapter = PrologixGpibEthernet(arg)
    adapter = PrologixGpibEthernet('10.1.1.113')#if ip address is not found, run the program "GPIB Configuator" and look at ip. Or run "NetFinder" from Prologix
#
#        elif (opt == "-u") :
#          print "USB adapter is not supported yet..."
#          return 1
#        elif (opt == "-g") :
#            gpib_address = int(arg)
    gpib_address = int(7)
#        else :
#            print "Internal error : opt = ", opt
#            return 2

#    if adapter == None:
#      usage(progname)
#      print "Please use -a or -u options to select GPIB adapter"
#      return 1

    print "Setting adapter read timeout to %f seconds" % read_timeout
    adapter.settimeout(read_timeout)
    print "Using device GPIB address of %d" % gpib_address
    dev = GpibDevice(adapter, gpib_address)
##file = open("scopetest.txt","a")

    print "File is open and am now writing to it. Ctrl-c to stop data taking."
	##i = datetime.datetime.now()
	##file.write("Current date & time = %s\n" % i)
    startTime = time.time()
    
    def func(x, intercept, w1,a1,d1,w2,a2,d2):
        return intercept + a1*numpy.exp(-((x-d1)**2)/(2.*w1**2))+a2*numpy.exp(-((x-d2)**2)/(2.*w2**2))

 
        
	#while True:
	#query1 = "MEAS:VOLT:DC? 10,0.0001"
    #query1 = "Measurement:meas2:value?"
    #data = dev.converse([query1])  
    q1="Data:Source CH3"
    q2="Data:Encdg: ASCII"
    q3="Data:Width 2"
    q4="Data:Start 1"
    q5="Data:Stop 500"
    q6="wfmpre?" 
    q7="curve?"
    e1=time.time()
    response=dev.converse([q1,q2,q3,q4,q5,q6,q7])
    ystr=response["curve?"]
    '''
    response=dev.converse([q7])
    ystr=response["curve?"]
    '''
    
    e2=time.time()
    print "Scope communication took", e2-e1,"s"
    #pdb.set_trace()
    ydata=[int(s) for s in ystr.split(',')]

    xdata=numpy.multiply(range(len(ydata)),(10.0*10.0)/500.0) #xdata converted for 10ms/div scale
    
    ydata=numpy.multiply(ydata,(5.0*5.0)/2**15) #ydata converted for 5mV/div scale
    
    
    fig,ax=plt.subplots()
    ax.plot(xdata,ydata)    
    '''
    popt,popv = curve_fit(func, xdata, ydata, (-12.,12.,15.,25.,6.,5.,50.))
    popt,popv = curve_fit(func, xdata, ydata, (1,1,1,1,1,1.,1))  
    fit = func(xdata, *popt)
    #plt.plot(xdata, fit, 'b-')
    print "FWHM 1=",popt[1]*2*numpy.sqrt(2*numpy.log(2)), "ms", "and FWHM 2=",popt[4]*2*numpy.sqrt(2*numpy.log(2)),"ms"
    print "Temp 1 approximately:",(popt[1]*2*numpy.sqrt(2*numpy.log(2))/10.0)**2*16.3, "uK and Temp 2 approximately",(popt[4]*2*numpy.sqrt(2*numpy.log(2))/10.0)**2*16.3, "uK"
   '''   
   # plt.plot(range(len(ydata)),func(range(len(ydata)), 1,1) )
    ydatasave=str(ydata).translate(None,'[]\n')
    savefile=open("Lattice0Order",'w')
    savefile.write(ydatasave)
    savefile.close()
    print "ASCII data saved"
    plt.savefig("Lattice0Order")
    print "Figure saved"
    
    #print str(query1 + ": " + str(data.pop(query1)) + "\n" )
	##file.write("Time [s]: " + str(time.time()-startTime) + " "+ query1 + ": " + str(data.pop(query1)) + "\n" )
	#time.sleep(1)'''

#    import readline
#    line = raw_input("> ")
#    while True:
#        if line:
#            dev.write(line)
#        else:
#          result = dev.read()
#          if result != None:
#            print result
#          else:
#            print '<<< NO RESPONSE >>>'
#        line = raw_input("> ")


if __name__ == '__main__':
    main(sys.argv)
