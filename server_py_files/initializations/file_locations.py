# -*- coding: utf-8 -*-
"""
File locations for various parts of XTSM server and parser functions - 
each entry has a typename as key, with a dictionary as value, in which the keys
are machine id numbers (as returned by uuid.getnode() on the machine in question)
and the value is a filepath root ending in '/' or a file location.


Created on Sat Apr 05 21:32:42 2014

@author: Nate
"""
file_locations={"raw_buffer_folders" : {69129942709L:"c:/wamp/www/raw_buffers/DBFS",264840316731455L: "c:/wamp/vortex/raw_buffers/DBFS",11603160389L:"c:/psu_data/raw_buffers/DBFS",161342404561L:"C:\\wamp\\www\\psu_data\\raw_buffers\\databomb_filestream"},
"xtsm_feed" : {69129942709L:"c:/wamp/www/xtsm_feed/",264840316731455L: "c:/wamp/vortex/xtsm_feed/",11603160389L:"c:/psu_data/xtsm_feed",161342404561L:"C:\\wamp\\www\\psu_data\\xtsm_feed"},
'analysis_stream':{69129942709L:"c:/wamp/www/analysis_feed/",264840316731455L: "c:/wamp/vortex/analysis_feed/",11603160389L:"c:/psu_data/analysis_feed",161342404561L:"C:\\wamp\\www\\psu_data\\analysis_feed"},
'last_xtsm':{69129942709L:"c:/wamp/www/WebSocketServer/",264840316731455L:"c:/wamp/vortex/MetaViewer/",11603160389L:"c:/www/XTSM/",161342404561L:"C:\\wamp\\www\\WebSocketServer"},
'repasint_dll':{69129942709L: "c:/wamp/www/WebSocketServer/testctype.dll",264840316731455L: "c:/wamp/vortex/WebSocketServer/testctype.dll",11603160389L:"c:/www/XTSM/testctype32.dll",161342404561L:"C:\\wamp\\www\\WebSocketServer\\testctype.dll"}}





#Below are the id's before the change in IP address for vortex and PXI
"""
file_locations={"raw_buffer_folders" : {264840316731455L: "c:/wamp/vortex/raw_buffers/DBFS",11603160389L:"c:/psu_data/raw_buffers/DBFS",161342404561L:"c:/psu_data/raw_buffers/DBFS"},
"xtsm_feed" : {264840316731455L: "c:/wamp/vortex/xtsm_feed/",11603160389L:"c:/psu_data/xtsm_feed",161342404561L:"c:/psu_data/xtsm_feed"},
'analysis_stream':{264840316731455L: "c:/wamp/vortex/analysis_feed/",11603160389L:"c:/psu_data/analysis_feed",161342404561L:"c:/psu_data/analysis_feed"},
'last_xtsm':{264840316731455L:"c:/wamp/vortex/MetaViewer/",11603160389L:"c:/www/XTSM/",161342404561L:"c:/wamp/www/XTSM/"},
'repasint_dll':{264840316731455L: "c:/wamp/vortex/WebSocketServer/testctype.dll",11603160389L:"c:/www/XTSM/testctype32.dll",161342404561L:"C:\wamp\www\WebSocketServer/testctype.dll"}}
"""


"""
file_locations={"raw_buffer_folders" : {264840316731455L: "c:/wamp/vortex/raw_buffers/DBFS",11603160389L:"c:/psu_data/raw_buffers/DBFS",161342404561L:"c:/psu_data/raw_buffers/DBFS"},
"xtsm_feed" : {264840316731455L: "c:/wamp/vortex/xtsm_feed/",11603160389L:"c:/psu_data/xtsm_feed",161342404561L:"c:/psu_data/xtsm_feed"},
'analysis_stream':{264840316731455L: "c:/wamp/vortex/analysis_feed/",11603160389L:"c:/psu_data/analysis_feed",161342404561L:"c:/psu_data/analysis_feed"},
'last_xtsm':{264840316731455L:"c:/wamp/vortex/MetaViewer/",11603160389L:"c:/www/XTSM/",161342404561L:"c:/www/XTSM/"},
'repasint_dll':{264840316731455L: "c:/wamp/vortex/WebSocketServer/testctype.dll",11603160389L:"Does Not Exist",161342404561L:"C:\wamp\www\WebSocketServer/testctype.dll"}}

"""


"""
file_locations={"raw_buffer_folders" : {69129942709L:"c:/wamp/www/raw_buffers/DBFS", 264840316731455L: "c:/wamp/vortex/raw_buffers/DBFS",11603160389L:"c:/psu_data/raw_buffers/DBFS"},
"xtsm_feed" : {69129942709L:"c:/wamp/www/xtsm_feed/", 264840316731455L: "c:/wamp/vortex/xtsm_feed/",11603160389L:"c:/psu_data/xtsm_feed"},
'analysis_stream':{69129942709L:"c:/wamp/www/analysis_feed/",264840316731455L: "c:/wamp/vortex/analysis_feed/",11603160389L:"c:/psu_data/analysis_feed"},
'last_xtsm':{69129942709L:"c:/wamp/www/WebSocketServer/", 264840316731455L:"c:/wamp/vortex/MetaViewer/",11603160389L:"c:/www/XTSM/"},
'repasint_dll':{69129942709L: "c:/wamp/www/WebSocketServer/testctype.dll", 264840316731455L: "c:/wamp/vortex/WebSocketServer/testctype.dll",11603160389L:"Does Not Exist"}}
"""

"""
11603160389 = Rb_analysis/fqhe master?
161342404561 = pfaffian
264840316731455L: nate's laptop
69129942709L: Vortex
"""