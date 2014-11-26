# -*- coding: utf-8 -*-
"""
Created on Sat Apr 05 21:30:07 2014

@author: Nate
"""

from xml.sax import saxutils

class xstatus_ready():
    """
    Inheritance class to add a status output in xml-format to any object
    """
    def xstatus(self):
        """
        returns status of the listener as xml, and follows-on to child objects
        """
        status="<"+self.__class__.__name__+">"
        status+=self.iterate_dict(vars(self))
        status+="</"+self.__class__.__name__+">"
        return status
        
    def iterate_dict(self,dictelm):
        """
        steps through a dictionary
        """
        status=''
        for var in dictelm.keys():
            status+="<"+var+">"
            if type(dictelm[var])==type({}): status+=self.iterate_dict(dictelm[var])            
            elif hasattr(dictelm[var],'xstatus'): 
                status+=dictelm[var].xstatus()
            else: status+=saxutils.escape(str(dictelm[var]))
            status+="</"+var+">"                
        return status