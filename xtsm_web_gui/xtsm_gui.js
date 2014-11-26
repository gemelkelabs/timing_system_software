/*jslint browser: true*/
/*jslint plusplus: true*/
/*global $, jQuery, DOMParser, XMLSerializer, XSLTProcessor, XPathResult, CodeMirror, alert */

/*
Recent additions:
- Ping server for Data Contexts in order to send the active experiment to the correct DC.
- Search field and jump capabilities for search results.
- Help box.

Potential things to add, in no particular order:
- Keybindings for certain fields (eg. hitting enter on the python console and having it execute)
- Ability to change server connection, both computer and port.
- Display multiple XTSM trees.
- Display channel plots.
- Add a jump function for edges/intervals, channels, and timing groups.
- Add functionality to many buttons in HTML tree (eg. lock, x move field up/down, x cloning)
*/

function live_content_event(elm) {
    // registers a live content event with the server, passes arguments of call to server
    var cid;
    var slicedArgs = Array.prototype.slice.call(arguments, 1);
    // find first parent element in DOM specifying a content_id
    cid = $(elm).parents('[content_id]')[0].getAttribute("content_id");
    // pass the event content_id, and other arguments of call to server as a live_content_event
	var pxi_dc;
	pxi_dc = document.getElementById('pxi_dc').value;
    mes = JSON.stringify({ "IDLSocket_ResponseFunction": "live_content_event", "content_id": cid, "args": slicedArgs });
    $('#server_push_output_textarea')[0].sendText(mes);
}

function textarea_console(textarea_generator,arg) {
    textarea_generator.className="server_push_textarea";
    textarea_generator.innerHTML = "websocket not connected";
    //ws_function = websocketize(textarea_generator,arg);
    websocketize(textarea_generator,arg);
    ws_function = textarea_generator;
}

function websocketize(target,arg) {
	
//function createWebSocket () {
//  var connection = new WebSocket();
//  connection.onclose = function () {setTimeout(function () {createWebSocket(); }, 10*1000);}
//};

    function openSocket() {
        if (target.reconnectAttempts > 1000) {
            target.parentNode.parentNode.style.backgroundColor = "#E0E0E0";
            clearInterval(target.reconnectInterval);
            return;
        };
        //console.log("reconnecting... attempted " + target.reconnectAttempts + " reconnects");
        target.commandLibrary.server_console("reconnecting... attempted " + target.reconnectAttempts + " reconnects");
        target.socket = new WebSocket("ws://127.0.0.1:8084");
        target.socket.binaryType = "arraybuffer";
        target.socket.owner = target;
        target.socket.onopen = onopencall;
        target.socket.onclose = onclosecall;
        target.reconnectAttempts += 1;
    };
    target.openSocket = openSocket;
    function onopencall() {
        //var ta = document.getElementById("server_push_output_textarea")
        //console.log("Websocket open");
        //target.innerHTML = target.innerHTML + "\n" + "Websocket Connected.";
        target.commandLibrary.server_console("Websocket Connected.");
        target.isopen = true;
        if (target.reconnectInterval !== '') { clearInterval(target.reconnectInterval); };
        //clearInterval(target.reconnectInterval);
        target.reconnectInterval = '';
        target.parentNode.parentNode.style.backgroundColor = "#FFFFFF";
        target.reconnectAttempts +=1 ;
    };
    target.onopencall = onopencall;

    function onclosecall(e) {
        if (target.isopen) {
            //console.log("Websocket closed.");
            target.commandLibrary.server_console("Websocket closed.");
            target.isopen = false;
            target.reconnectAttempts = 0;
            target.parentNode.parentNode.style.backgroundColor = "#FFCCCC";
			//setTimeout(function () {websocketize(target,arg); }, 1000);
            target.reconnectInterval = setInterval(target.openSocket, 2000); //CP 2014-10-21
        };
    };
    target.onclosecall = onclosecall;

    function ReopenSocket() {
        target.reconnectAttempts = 0;
		if (typeof reconimg_ws !== 'undefined') {
			target.socket.close();
		}
		websocketize(target,arg);//CP 2014-10-30
        //target.openSocket();CP 2014-10-30
    };
    target.ReopenSocket = ReopenSocket;

    function sendText(mes) {
        if (target.isopen) {
            target.socket.send(mes);
            target.commandLibrary.server_console("Text message sent.");
        } else {
            target.commandLibrary.server_console("Attempted to send message, but connection not opened.");
        };
    };
    target.sendText = sendText;

    target.commandLibrary = new CommandLibrary(arg);
    target.commandLibrary.owner = target;
    target.reconnectAttempts = 0;
    target.openSocket();
    target.socket.onopen = onopencall;
    target.socket.onclose = onclosecall;
	if (typeof reconimg_ws === 'undefined') {
		reconimg_ws = target.parentNode.parentNode.insertBefore(document.createElement('img'), target.parentNode);
		reconimg_ws.src = "images/seqicon_refresh.png";
		reconimg_ws.height = 15;
		reconimg_ws.onclick = target.ReopenSocket;
	}

    target.log = function (message) {
        /*
        writes server messages to the textarea console log. 
        */
        target.innerHTML = target.innerHTML.split("\n").slice(-6,-1).join() + "\n" + message;
        }
        target.socket.onmessage = function (e) {
			console.log("in function: target.socket.onmessage");
            /*
            Here we define the response to any incoming websocket data.  We assume if the
            data is text format that it consists of a json-formatted set of key-value pairs.
            For each pair, the key defines an action, and the data contains any necessary 
            parameters for the GUI's reaction.  The action should be the name of a command
            in this target's command library, which takes a single parameter as its argument, which
            will be passed the value of the key-value pair.
			This will by default execute the received function for any data_context
			that was not specified. However, if a data_context was specified in the wbsocket
			message, then it will only execute that command if the pxi_dc matches that
			data_context. Note, the variable name, 'pxi_dc' is a bit of a misnomer because
			it isn't necessarily the "PXI's" data_context- CP 2014-10-20
            */
            if (typeof e.data == "string") {
                // if data is a string, it is assumed to be JSON form
                var obj = jQuery.parseJSON(e.data);
                // following should call requested functions :
				var dc_present = false;
                for (var action in obj) {
					//console.log('command: ' + action);
                    if(action == "data_context"){
						var dc_present = true;
						if (obj[action] != document.getElementById('pxi_dc').value){
							return;
						}
					}
                }
                for (var action in obj) {
                    if(action == "data_context"){
						continue;
					}
                    var thearg = obj[action];
					try{
                    eval("this.owner.commandLibrary." + action + '(thearg)');
					}
					catch(err){
						this.owner.commandLibrary.server_console("Error:"+action);
						console.log("Error:"+action);
						console.log(err);
					}
                }
            } else { // the data is of binary form - this is not currently used
                var arr = new Uint8Array(e.data);
                var hex = '';
                for (var i = 0; i < arr.length; i++) {
                    hex += ('00' + arr[i].toString(16)).substr(-2);
                }
                console.log("Binary message received on websocket: " + hex);
            }
    }
};

function CommandLibrary(arg) {
    // this library defines responses to incoming websocket messages - each websocket message should consist
    // of a JSON string, with keys corresponding to function names in this library, and the value its payload

    function server_console(mes) {
        var prior = this.owner.innerHTML.split("\n");
        if (prior.length >= 6) {prior = prior.slice(1, prior.length); };
        this.owner.innerHTML = prior.join("\n") + "\n" + mes;
    };
    this.server_console = server_console;

    function shotnumber(sn) {
		console.log('shotnumber');
        arg.running_shot = sn;
        //arg.shotnumber_browse = arg.running_shot + Number($("#toolbar").contents().find("#shotnumber_browse_input").val());
        arg.shotnumber_browse = Number($("#toolbar").contents().find("#shotnumber_browse_input").val());//CP 2014-11-19
        mes = "Exp. Control - Shot " + (sn) + " Running";
        document.title = mes;
        this.server_console(mes);
		var pxi_dc;
		pxi_dc = document.getElementById('pxi_dc').value;
        $("#toolbar").contents().find("#toolpanel_statusbar").html("Shot " + (sn) + " Running");
        if (!arg.shotnumber_lock) {
			console.log('sending request_xtsm');
            this.owner.sendText('{"IDLSocket_ResponseFunction":"request_xtsm","data_context":"' + pxi_dc + '","shotnumber":"' + arg.shotnumber_browse + arg.running_shot + '"}');
        }
    };
    this.shotnumber = shotnumber;

    function parsed_active_xtsm(time) {
        this.server_console("experiment parsed.");
    };
    this.parsed_active_xtsm = parsed_active_xtsm;

    function xtsm_change(shotnumber) {
        //console.log("In function xtsm_change. shotnumber_browser:" +  arg.shotnumber_browse + "shotnumber: " + shotnumber);
        this.server_console("xtsm for shotnumber " + shotnumber + " changed.");
        if (!(arg.shotnumber_lock) && (arg.shotnumber_browse === shotnumber)) {
            console.log("getting in response to xtsm change");
			var pxi_dc;
			pxi_dc = document.getElementById('pxi_dc').value;
			console.log('sending request_xtsm');
            this.owner.sendText('{"IDLSocket_ResponseFunction":"request_xtsm","data_context":"' + pxi_dc + '","shotnumber":"' + arg.shotnumber_browse + arg.running_shot + '"}');
        }
    };
    this.xtsm_change = xtsm_change;

    function xtsm_return(payload) {
		console.log('inside xtsm_return');
        var pay = jQuery.parseJSON(payload);
		console.log('arg.shotnumber_browse ' + arg.shotnumber_browse);
		console.log("pay['shotnumber'] "+pay['shotnumber']);
		console.log("arg.running_shot "+arg.running_shot);
        //if ((arg.shotnumber_browse === pay['shotnumber']) && (!arg.shotnumber_lock)) { TODO: still update the xtsm when looking at past shots
        if ((arg.shotnumber_browse === 0) && (!arg.shotnumber_lock)) {
			console.log('updating XTSM. '+ 'shotnumber: ' +  pay['shotnumber']);
            arg.xml_string = pay['xtsm'];
            arg.update_editor();
            arg.refresh_tree();
            if (arg.cm_expand === true) { $("#toolbar").contents().find("#content_lock").click(); };
            }
    };
    this.xtsm_return = xtsm_return;

    function receive_live_content(payload) {
        var content_id;
        payload = jQuery.parseJSON(payload);
        for (content_id in payload) { 
			arg.update_livedata(content_id, payload[content_id]); 
		};

    };
    this.receive_live_content = receive_live_content;

    function live_content_changed(payload) {
        //payload = jQuery.parseJSON(payload);
		return; //CP 2014-11-1
		var pxi_dc;
		pxi_dc = document.getElementById('pxi_dc').value;
        if ($("[content_id='" + payload['content_id'] + "']").length > 0) {
            this.owner.sendText('{"IDLSocket_ResponseFunction":"request_content","content_id":"' + payload['content_id'] + '","' + data_context + '":"' + pxi_dc + '"}');
        };
    };
    this.live_content_changed = live_content_changed;

	/*Added ws by Craig 2014-10-28*/
	function parse_preview_ws(arg) {
		/*
		asks server to test-parse active XTSM via Ajax request, return xtsm 
		*/
		var pxi_dc;
		pxi_dc = document.getElementById('pxi_dc').value;
		if (pxi_dc === '') {
			alert('You must enter a PXI Data Context in order to post an active experiment!');
			return;
		}
		// Send request for test-parse.
		message = JSON.stringify({'IDLSocket_ResponseFunction':'testparse_active_xtsm','data_context': pxi_dc,'terminator':'die'});
		this.owner.sendText(message);
	};
    this.parse_preview_ws = parse_preview_ws;

	
	function post_active_xtsm_ws(arg) {
		/*
		Sends active XTSM code to server, along with the name of the data context of the
		 PXI system which will run that code. 
		Note: This requires two Ajax requests, as the 'set_global_variable...' command only sets one variable per request.
		
		Also compresses the html parser div if the option is checked.
		*/

		var _active_xtsm, pxi_dc;
		_active_xtsm = arg.xml_string;
		pxi_dc = document.getElementById('pxi_dc').value;
		if (pxi_dc === '') {
			alert('You must enter a PXI Data Context in order to post an active experiment!');
			return;
		}
		// Send active XTSM object.
		message = JSON.stringify({'IDLSocket_ResponseFunction':'post_active_xtsm','data_context': pxi_dc,'_active_xtsm': _active_xtsm,'terminator':'die'});
		this.owner.sendText(message);

		if (document.getElementById("compress_on_post_button").checked) {
			toggle_menu("parser_menu", "parser_operations");
		}
	};
    this.post_active_xtsm_ws = post_active_xtsm_ws;
	

	function retrieve_active_xtsm_ws(arg) {
		/*
		Retrieves active XTSM code from server.
		Then replaces the active XTSM in the code editor with the data retrieved.
		*/

		var pxi_dc;
		pxi_dc = document.getElementById('pxi_dc').value;
		if (pxi_dc === '') {
			alert('You must enter a PXI Data Context in order to retrieve an active experiment!');
			return;
		}
		message = JSON.stringify({'IDLSocket_ResponseFunction':'get_global_variable_from_socket','data_context': pxi_dc,'variablename': '_active_xtsm','terminator':'die'});
		this.owner.sendText(message);
		if (document.getElementById("compress_on_post_button").checked) {
			toggle_menu("parser_menu", "parser_operations");
		}
	};
	this.retrieve_active_xtsm_ws = retrieve_active_xtsm_ws;

};

function replaceHtml(el, html) {
	var oldEl = typeof el === "string" ? document.getElementById(el) : el;
	/*@cc_on // Pure innerHTML is slightly faster in IE
		oldEl.innerHTML = html;
		return oldEl;
	@*/
	var newEl = oldEl.cloneNode(false);
	newEl.innerHTML = html;
	oldEl.parentNode.replaceChild(newEl, oldEl);
	/* Since we just removed the old element from the DOM, return a reference
	to the new element, which can be used to restore variable references. */
	return newEl;
};

function does_nothing() {
	"use strict";
	/*
	Filler function for an HTML element that is present yet not functional. Also used for debugging.
	*/

	alert('This field is currently nonfunctional. Please try again later.');
}

function randomString(string_length) {
	"use strict";
	/*
	Creates a random string, of length = string_length, consisting of alphanumeric characters.
	*/

	var chars, randomstring, i, rnum;
	chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz";
	randomstring = '';
	for (i = 0; i < string_length; i++) {
		rnum = Math.floor(Math.random() * chars.length);
		randomstring += chars.substring(rnum, (rnum + 1));
	}
	return randomstring;
}

function get_elem_to_modify_from_idname(xmlDoc, elem) {
	"use strict";
	/*
	Retrieves an element by Id.
	*/
	var update_nodelist, elem_to_modify, j;

	//This parses the elem string input to find the appropriate field in the DOM object to change
	update_nodelist = elem.split('__');
	//This loop builds the reference to the appropriate DOM object
	elem_to_modify = xmlDoc;
	for (j = 0; j < update_nodelist.length; j++) {
		elem_to_modify = elem_to_modify.getElementsByTagName(update_nodelist[j].split('_')[0])[parseInt(update_nodelist[j].split('_')[1], 10) - 1];
	}
	return elem_to_modify;
}

function generate_name_for_element(elem) {
	"use strict";
	/*
	If element does not have a name, give it one.
	*/
	var name, it, siblingcount, sibit;

	name = '';
	it = elem;
	while (it.parentNode !== null) {
		siblingcount = 1;
		sibit = it;
		while (sibit.previousSibling !== null) {
			if (sibit.previousSibling.nodeName === it.nodeName) {
				siblingcount = siblingcount + 1;
			}
			sibit = sibit.previousSibling;
		}
		name = it.nodeName + '_' + siblingcount + '__' + name;
		it = it.parentNode;
	}
	return name.substring(0, name.length - 2);
}

function highlight_expand(elem, arg) {
	"use strict";
	/*
	Finds the desired tree element, highlights it, and sets it as the focus.
	The element's old class is stored for later restoration.
	*/
	var nextelem, divid, gen_ids, i, prev_class;

	nextelem = elem;
	while (nextelem.nodeName !== 'XTSM') {
		nextelem.setAttribute('expanded', "1");
		nextelem = nextelem.parentNode;
	}
	divid = 'divtree__' + generate_name_for_element(elem);
	gen_ids = document.querySelectorAll('div[gen_id]');
	for (i = 0; i < gen_ids.length; i++) {
		if (gen_ids[i].getAttribute('gen_id') === divid) {
			prev_class = gen_ids[i].getAttribute('class');
			gen_ids[i].setAttribute('old_class', prev_class);
			gen_ids[i].setAttribute('class', "highlighted");
			prev_class = gen_ids[i].previousSibling.getAttribute('class');
			gen_ids[i].previousSibling.setAttribute('old_class', prev_class);
			gen_ids[i].previousSibling.setAttribute('class', "highlighted");
			gen_ids[i].previousSibling.scrollIntoView();
		}
	}
}

function searchjump(name, arg) {
	"use strict";
	/*
	Parses the existing XML code into a DOM object.
	Used to find an element in XML code and jump to it in the tree.
	*/
	var parser2, xmlDoc2, elem;

	parser2 = new DOMParser();
	xmlDoc2 = parser2.parseFromString(arg.xml_string, "text/xml");
	elem = get_elem_to_modify_from_idname(xmlDoc2, name);
	highlight_expand(elem);
}

function toggle_menu(img_name, div_name) {
	"use strict";
	/*
	Toggles a right-arrow to a down-arrow upon clicking.
	A down-arrow expands a section, while a right-arrow hides it.
	*/

	var state;
	//Plus sign in front of document.blah is used to quickly convert to integer.
	state = (+document.getElementById(div_name).getAttribute("data-switch"));
	if (state === 0) {
		document.getElementById(img_name).src = "/images/DownTriangleIcon.png";
		document.getElementById(div_name).style.display = "block";
		document.getElementById(div_name).setAttribute("data-switch", 1);
	} else if (state === 1) {
		document.getElementById(img_name).src = "images/RightFillTriangleIcon.png";
		document.getElementById(div_name).style.display = "none";
		document.getElementById(div_name).setAttribute("data-switch", 0);
	} else {alert('Still not working'); }
}

function toggle_button(div_name, disable) {
	"use strict";
	/*
	Toggles a button from disabled to enabled, or vice versa. Disable = true for enabled-to-enabled, and false for disabled-to-enabled.
	Also changes the image, assuming the image follows a naming scheme as follows:
		Located in wamp/www/images folder.
		Enabled version is named 'semicon_divname.png'
		Disabled version is named 'semicon_divname_inactive.png'
	*/

	var img_name;
	if (disable === true) {
		document.getElementById(div_name).setAttribute("disabled", "disabled");
		img_name = "/images/seqicon_" + div_name + "_inactive.png";
		document.getElementById(div_name).setAttribute("src", img_name);
	} else if (disable === false) {
		document.getElementById(div_name).removeAttribute("disabled");
		img_name = "/images/seqicon_" + div_name + ".png";
		document.getElementById(div_name).setAttribute("src", img_name);
	} else {
		alert('disable should only be true or false');
	}
}

function populate_file_info() {
	"use strict";
	/*
	Provides a description of a file selected in the file menu, including (if available): filename, description, last saved, and last saved by.
	*/

	var location;
	if (document.getElementById("file_type").value === 'XTSM File') {
		location = "sequences/";
	} else if (document.getElementById("file_type").value === 'XSL Transform') {
		location = "transforms/";
	}
	document.getElementById('file_info_div').innerHTML = 'File:&nbsp;<b>' + document.getElementById('folder_select').value + '/' + document.getElementById('file_select').value + '</b><div id="file_desc">Description:</div><br />Last Saved: <br />Last Saved By: ';
	//document.getElementById('load_file').value = ("c:/wamp/www/MetaViewer/" + location + document.getElementById('folder_select').value + "/" + document.getElementById('file_select').value).replace('//', '/');
	document.getElementById('load_file').value = ("" + location + document.getElementById('folder_select').value + "/" + document.getElementById('file_select').value).replace('//', '/');

}

function populate_files(folder_select) {
	"use strict";
	/*
	Gets files and folders from c:/wamp/www/MetaViewer/sequences/some_folder or ../MetaViewer/transforms/some_folder via lookup_sequences.php.
	Displays results. Upon selection, sends value to load_file textbox and opens populate_file_info() function.
	*/

	if (document.getElementById("file_type").value === 'XTSM File') {
		$("#file_op").load("lookup_sequences.php?folder=" + folder_select.value, function (data) {
			if (document.getElementById("file_select") !== null) {
				document.getElementById("file_select").parentNode.removeChild(document.getElementById("file_select"));
			}
			var files, fileselect, k, newfileinput;
			files = data.split(',');
			fileselect = document.getElementById("file_operations").insertBefore(document.createElement('select'), document.getElementById("file_operations").firstChild.nextSibling);
			fileselect.setAttribute('id', 'file_select');
			fileselect.options[fileselect.options.length] = new Option('Select File:  ', 'none');
			for (k = 0; k < files.length; k++) {
				fileselect.options[fileselect.options.length] = new Option(files[k], files[k]);
			}
			fileselect.setAttribute('multiple', 'multiple');
			fileselect.setAttribute('size', '8');
			document.getElementById('file_select').onchange = function () {
				if (fileselect.value !== "none") {
					populate_file_info();
				}
			};
		});
	} else if (document.getElementById("file_type").value === 'XSL Transform') {
		$("#file_op").load("lookup_transforms.php?folder=" + folder_select.value, function (data) {
			if (document.getElementById("file_select") !== null) {
				document.getElementById("file_select").parentNode.removeChild(document.getElementById("file_select"));
			}
			var files, fileselect, k, newfileinput;
			files = data.split(',');
			fileselect = document.getElementById("file_operations").insertBefore(document.createElement('select'), document.getElementById("file_operations").firstChild.nextSibling);
			fileselect.setAttribute('id', 'file_select');
			fileselect.options[fileselect.options.length] = new Option('Select File:  ', 'none');
			for (k = 0; k < files.length; k++) {
				fileselect.options[fileselect.options.length] = new Option(files[k], files[k]);
			}
			fileselect.setAttribute('multiple', 'multiple');
			fileselect.setAttribute('size', '8');
			document.getElementById('file_select').onchange = function () {
				if (fileselect.value !== "none") {
					populate_file_info();
				}
			};
		});
	}
	if (document.getElementById("folder_select").selectedIndex === 1) {
		document.getElementById("file_op_target_input").selectedIndex = 1;
	}
	if (document.getElementById("folder_select").selectedIndex !== 1) {
		document.getElementById("file_op_target_input").selectedIndex = 0;
	}
}

function populate_folders() {
	"use strict";
	/*
	Gets folders from location c:/wamp/www/MetaViewer/sequences or ..MetaViewer/transforms via loopkup_sequences.php.
	Then displays files in reverse-chronological order. Upon selecting a file, goes to populate_folders(folder_select) function.
	*/

	if (document.getElementById("file_type").value === 'XTSM File') {
		$("#file_op").load("lookup_sequences.php?folder=none", function (data) {
			if (document.getElementById("folder_select") !== null) {
				document.getElementById("folder_select").parentNode.removeChild(document.getElementById("folder_select"));
			}
			var folders, folderselect, k;
			folders = data.split(',');
			folderselect = document.getElementById("file_operations").insertBefore(document.createElement('select'), document.getElementById("file_operations").firstChild);
			folderselect.setAttribute('id', 'folder_select');
			folderselect.options[folderselect.options.length] = new Option('Select Folder:  ', 'none');
			for (k = 0; k < folders.length; k++) {
				if (folders[k] !== 'EXCLUDE_ME') {  // Files in this list are purposefully excluded.
					folderselect.options[folderselect.options.length] = new Option(folders[k], '/' + folders[k]);
				}
			}
			folderselect.setAttribute('multiple', 'multiple');
			folderselect.setAttribute('size', '8');
			document.getElementById('folder_select').onchange = function () {
				if (folderselect.value !== "none") {
					populate_files(this);
				}
			};
		});
	} else if (document.getElementById("file_type").value === 'XSL Transform') {
		$("#file_op").load("lookup_transforms.php?folder=none", function (data) {
			if (document.getElementById("folder_select") !== null) {
				document.getElementById("folder_select").parentNode.removeChild(document.getElementById("folder_select"));
			}
			var folders, folderselect, k;
			folders = data.split(',');
			folderselect = document.getElementById("file_operations").insertBefore(document.createElement('select'), document.getElementById("file_operations").firstChild);
			folderselect.setAttribute('id', 'folder_select');
			folderselect.options[folderselect.options.length] = new Option('Select Folder:  ', 'none');
			for (k = 0; k < folders.length; k++) {
				if (folders[k] !== 'EXCLUDE_ME') {  // Files in this list are purposefully excluded.
					folderselect.options[folderselect.options.length] = new Option(folders[k], '/' + folders[k]);
				}
			}
			folderselect.setAttribute('multiple', 'multiple');
			folderselect.setAttribute('size', '8');
			document.getElementById('folder_select').onchange = function () {
				if (folderselect.value !== "none") {
					populate_files(this);
				}
			};
		});
	}
}

function default_save_name() {
	"use strict";
	/*
	Creates default save name of "c:/wamp/www/MetaViewer/sequences/MM-DD-YYYY/HHh_MMm_SSs" 
	for XTSM sequences and similar for transforms."
	*/

	var file_location, file_type, x, year, month, day, hour, minute, second, datetime, save_name;

	if (document.getElementById("file_type").value === 'XTSM File') {
		file_location = "sequences/";
		file_type = ".xtsm";
	} else if (document.getElementById("file_type").value === 'XSL Transform') {
		file_location = "transforms/";
		file_type = ".xsl";
	}
	x = new Date();
	year = x.getFullYear();
	month = x.getMonth() + 1;
	day = x.getDate() + 1;
	hour = x.getHours();
	minute = x.getMinutes();
	second = x.getSeconds();
	datetime = month + "-" + day + "-" + year + "/" + hour + "h_" + minute + "m_" + second + "s";
	//save_name = "c:/wamp/www/MetaViewer/" + file_location + datetime + file_type;
	save_name = "../psu_data/" + file_location + datetime + file_type;

	return save_name;
}

function load_new_file(arg) {
	"use strict";
	/*
	Load a file of the user's choice.
	Note: Given the versatility of the arg.load_file() function, this is not limited to xml strings in the future.
	*/

	var filename;
	//filename = document.getElementById("load_file").value.split('c:/wamp/www').pop();
	filename = document.getElementById("load_file").value.split('c:/wamp/www/timing_system_software/xtsm_gui').pop();
	if (document.getElementById("file_type").value === 'XTSM File') {
		arg.load_file(filename, 'xml_string');
	} else if (document.getElementById("file_type").value === 'XSL Transform') {
		arg.load_file(filename, 'xsl_string');
	}
}

function save_file(arg) {
	"use strict";
	/*
	Saves the active XTSM under a save name of the user's choice, by way of the "save_file.php" file.
	*/

	var save_name, test_name, active_xtsm;
	//Get save value name.
	save_name = document.getElementById('save_file').value;
	//Get the active XTSM.
	active_xtsm = arg.xml_string;
	//Make sure the pathname does not contain any colons, besides c:/... This pathname is invalid.
	test_name = save_name.substring(2);
	if (test_name.indexOf(':') !== -1) {
		alert('File name cannot contain ":", besides "c:/..."');
	} else {
		$.post("save_file.php", {filename: save_name, filedata: active_xtsm}, function () { });
	}
}

function refresh(arg) {
	"use strict";
	/*
	Specifically does the following:
	Refreshes code tree, resets load file and save file text boxes, 
	refreshes file select drop-down menu, eliminates speed test results, 
	resets python console, resets search field and search results,
	sets font type and size back to defaults.
	
	Specifically does not do the following: 
	Reset data context list, reset data context of PXI system,  eliminate history,
	reset undo levels, stop displaying help options, load/save any files, 
	send/receive any request to/from any server.
	*/

	var i, select_length, search_list;
	arg.refresh_tree();
	document.getElementById('load_file').value = "";
	document.getElementById('save_file').value = default_save_name();
	populate_folders();
	document.getElementById('python_speed_result').innerHTML = '';
	document.getElementById('python_input_textarea').value = '';
	document.getElementById('python_response_textarea').value = '';
	change_font(true, false, 'monospace');
	change_font(false, true, '14');

	select_length = document.getElementById('python_variable_list').length;
	for (i = 1; i < select_length; i++) {
		document.getElementById('python_variable_list').remove(1);
	}

	search_list = document.getElementById('search_results_div');
	while (search_list.firstChild) {
		search_list.removeChild(search_list.firstChild);
	}
	document.getElementById('search_input').value = '';

}

function parse_preview(arg) {
    "use strict";
    /*
    asks server to test-parse active XTSM via Ajax request, return xtsm 
    */

    var transferdata, boundary, _active_xtsm, pxi_dc;
    boundary = "--aardvark";
    pxi_dc = document.getElementById('pxi_dc').value;
    if (pxi_dc === '') {
        alert('You must enter a PXI Data Context in order to post an active experiment!');
        return;
    }
    // Send request for test-parse.
    transferdata = [];
    transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'testparse_active_xtsm' + '\n\r--' + boundary + '--\n\r';
    transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
    transferdata = transferdata.join("");
    //alert(transferdata);
    $.ajax({
        url: 'http://127.0.0.1:8083',
        type: 'POST',
        contentType: 'multipart/form-data; boundary=' + boundary,
        processData: false,
        data: transferdata,
        dataType: "text",
        success: function (result) {
            alert(result);
            arg.xml_string = result;
            arg.refresh_tree();
            arg.update_editor();
        }
    });

}


function post_active_xtsm(arg) {
	"use strict";
	/*
	Sends active XTSM code to server via Ajax request, along with the name of the data context of the
	 PXI system which will run that code. 
	Note: This requires two Ajax requests, as the 'set_global_variable...' command only sets one variable per request.
	
	Also compresses the html parser div if the option is checked.
	*/

	var transferdata, boundary, _active_xtsm, pxi_dc;
	boundary = "--aardvark";
    _active_xtsm = arg.xml_string;
	pxi_dc = document.getElementById('pxi_dc').value;
	if (pxi_dc === '') {
		alert('You must enter a PXI Data Context in order to post an active experiment!');
		return;
	}
	// Send active XTSM object.
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'set_global_variable_from_socket' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="data_context"\n\r\n\r' + pxi_dc + '\n\r--' + boundary + '--\n\r';
	transferdata[2] = '--' + boundary + '\n\rContent-Disposition: form-data; name="_active_xtsm"\n\r\n\r' + _active_xtsm + '\n\r--' + boundary + '--\n\r';
	transferdata[3] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	//alert(transferdata);
	$.ajax({
	    url: 'http://127.0.0.1:8083',
	    type: 'POST',
	    contentType: 'multipart/form-data; boundary=' + boundary,
	    processData: false,
	    data: transferdata,
	    success: function (result) {
	        //alert(result);
	        document.getElementById('Server_Messages_div').innerHTML=result;
	    }
	});
	// Send information about which PXI system to connect to.
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'set_global_variable_from_socket' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="pxi_data_context"\n\r\n\r' + pxi_dc + '\n\r--' + boundary + '--\n\r';
	transferdata[2] = '--' + boundary + '\n\rContent-Disposition: form-data; name="data_context"\n\r\n\r' + pxi_dc + '\n\r--' + boundary + '--\n\r';
	transferdata[3] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	//alert(transferdata);
	$.ajax({
		url: 'http://127.0.0.1:8083',
		type: 'POST',
		contentType: 'multipart/form-data; boundary=' + boundary,
		processData: false,
		data: transferdata,
		success: function (result) {
			//alert(result);
		}
	});

	if (document.getElementById("compress_on_post_button").checked) {
		toggle_menu("parser_menu", "parser_operations");
	}
}

function retrieve_active_xtsm(arg) {
	"use strict";
	/*
	Retrieves active XTSM code from server via Ajax request.
	Then replaces the active XTSM in the code editor with the data retrieved.
	Also compresses the html parser div if the option is checked.
	*/

	var boundary, transferdata, pxi_dc;
	boundary = '--aardvark';
	pxi_dc = document.getElementById('pxi_dc').value;
	if (pxi_dc === '') {
		alert('You must enter a PXI Data Context in order to retrieve an active experiment!');
		return;
	}
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'get_global_variable_from_socket' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="variablename"\n\r\n\r' + '_active_xtsm' + '\n\r--' + boundary + '--\n\r';
	transferdata[2] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	//alert(transferdata);
	$.ajax({
		url: 'http://127.0.0.1:8083',
		type: 'POST',
		contentType: 'multipart/form-data; boundary=' + boundary,
		processData: false,
		data: transferdata,
		dataType: 'text',
		success: function (result) {
			//alert(result);
			// Eliminates junk string at beginning of message, which was required so that the message would be a string.
			arg.editor.xml_string=result;
		}
	});
	if (document.getElementById("compress_on_post_button").checked) {
		toggle_menu("parser_menu", "parser_operations");
	}
}

function launch_python() {
	"use strict";
	/*
	Launches python twisted server via Ajax (post) request. Server appears under system processes, not user processes.
	Cannot interact directly with server launched in this manner (eg. though Spyder), though all interactions with this GUI function.
	*/

	var url_out, port_out;
	url_out = '127.0.0.1';
	port_out = 8083;
	//The following ajax and post requests are identical in meaning, though the post request is less complex/faster.
	/*$.ajax({
		url: url_out + ':8081/MetaViewer/launch_python.php',
		type: 'POST',
		data: {port: port_out},
		success: function (data) {//alert(data); }
	});*/
	$.post('launch_python.php', {port: port_out}, function (data) {
		//alert(data);
	});
}

function disable_python_socket() {
	"use strict";
	/*
	Sends an Ajax request to the server which closes the server.
	*/

	var transferdata, boundary;
	boundary = "--aardvark";
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'stop_listening' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	//alert(transferdata);
	$.ajax({
		url: 'http://127.0.0.1:8083',
		type: 'POST',
		contentType: 'multipart/form-data; boundary=' + boundary,
		processData: false,
		data: transferdata,
		success: function (result) {alert(result); }
	});
}

function test_pythontransferspeed(data_length, results) {
	"use strict";
	/*
	Tests how long it takes to send data to python twisted server, in chucks of 10 bytes, 100 bytes, etc, through 10 million bytes.
	This is accomplished by sending random bytes of data (in set quantities) to the server via Ajax request.
	Results are then displayed in a table by the speed test button.
	*/

	var boundary, transferdata, ajaxtime;
	boundary = '--aardvark';
	if (!data_length) {
		//Assigns an initial length of 10 bytes to our test data.
		data_length = 10;
	}
	if (data_length > 10000000) {
		//After final run, displays results in table.
		document.getElementById("python_speed_result").innerHTML = results + "</table>";
		return 1;
	}
	if (!results) {
		//Creates results table before the first test run.
		results = '<br /><table border="1"><tr><td><b>GUI<>Python SpeedTest</b></td><td colspan="4">Time (ms)</td></tr><tr><td align="right">Size (Bytes)</td><td>Python read</td><td>Python write</td><td>Python init</td><td>Ajax Roundtrip</td></tr>';
	}
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'set_global_variable_from_socket' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSPEEDTEST"\n\r\n\r' + randomString(data_length) + '\n\r--' + boundary + '--\n\r';
	transferdata[2] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	ajaxtime = new Date().getTime();
	$.ajax({
		url: 'http://127.0.0.1:8083',
		type: 'POST',
		contentType: 'multipart/form-data; boundary=' + boundary,
		processData: false,
		data: transferdata,
		success: function (result) {
			result = result.substring(16);
			result = result.substring(data_length + 39);
			var now = new Date().getTime();
			setTimeout(function () {
				//Appends new results to previous (if any), increases size of test data by a factor of 10, and repeats the test run.
				results += '<tr><td align="right">' + data_length.toExponential(2) + '&nbsp;</td><td>' + ((result.split(',')).slice(0, 3)).join('</td><td>') + '</td><td>' + (now - ajaxtime) + '</td></tr>';
				data_length *= 10;
				test_pythontransferspeed(data_length, results);
			});
		}
	});
}

function execute_python() {
	"use strict";
	/*
	Ajax request to execute arbitrary python code taken from the 'python_input_textarea' element.
	Takes results from server and does the following:
		Displays code sent.
		Displays python results.
		Displays server variables available to user.
	*/

	var boundary, transferdata;
	boundary = '--aardvark';
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'execute_from_socket' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="command"\n\r\n\r' + document.getElementById("python_input_textarea").value + '\n\r--' + boundary + '--\n\r';
	transferdata[2] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	//alert(transferdata);
	$.ajax({
		url: 'http://127.0.0.1:8083',
		type: 'POST',
		contentType: 'multipart/form-data; boundary=' + boundary,
		processData: false,
		data: transferdata,
		success: function (result) {
			var consoleresult, varresult, i, j, newopt, select_length;
			//Removes variables from results and prints to appropriate textbox.
			consoleresult = [];
			consoleresult[0] = (result.substring(19).split('>Code>'))[0];
			consoleresult[1] = (result.substring(19).split('>Code>'))[2];
			consoleresult = consoleresult.join("");
			document.getElementById("python_response_textarea").value = consoleresult;
			//Separates variables from group.
			varresult = ((result.substring(19).split('>Code>'))[1]).split('>Var>');
			//Wipes previous variables, if any, from variable list textarea.
			select_length = document.getElementById('python_variable_list').length;
			for (i = 1; i < select_length; i++) {
				document.getElementById('python_variable_list').remove(1);
			}
			//Writes new variables to variable list textarea.
			for (j = 0; j < varresult.length; j++) {
				newopt = document.createElement('option');
				newopt.text = varresult[j];
				document.getElementById("python_variable_list").add(newopt, null);
			}
		}
	});
}

function get_data_contexts() {
	"use strict";
	/*
	Gets data context names from the server and displays in a list.
	Currently only used to determine the PXI system to send an XTSM sequence to.
	*/

	var transferdata, boundary, data_contexts, select_length, i, j, newopt;
	boundary = "--aardvark";
	transferdata = [];
	transferdata[0] = '--' + boundary + '\n\rContent-Disposition: form-data; name="IDLSocket_ResponseFunction"\n\r\n\r' + 'get_data_contexts' + '\n\r--' + boundary + '--\n\r';
	transferdata[1] = '--' + boundary + '\n\rContent-Disposition: form-data; name="terminator"\n\r\n\r' + 'die' + '\n\r--' + boundary + '--\n\r';
	transferdata = transferdata.join("");
	$.ajax({
		url: 'http://127.0.0.1:8083',
		type: 'POST',
		contentType: 'multipart/form-data; boundary=' + boundary,
		processData: false,
		data: transferdata,
		success: function (results) {
			data_contexts = results.split(',');
			//Wipes previous variables, if any, from variable list textarea.
			select_length = document.getElementById('data_contexts_list').length;
			for (i = 1; i < select_length; i++) {
				document.getElementById('data_contexts_list').remove(1);
			}
			//Writes new variables to variable list textarea.
			for (j = 0; j < (data_contexts.length - 1); j++) {
				newopt = document.createElement('option');
				newopt.text = data_contexts[j];
				document.getElementById("data_contexts_list").add(newopt, null);
			}
		}
	});
}

function build_analysis_plots(num_analysis_plots) {
	"use strict";

	var startind, jj, toprow, toprowspan, midrow, leftarrtd, leftarr, viewerdivtd, viewerdiv, indin, rightarrtd, rightarr, botrow, statspan, jumpbutt, srcimg, viewer_name, ev, coords;

	startind = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[0].getElementsByTagName("td").length - 1;
	for (jj = startind; jj < (startind + num_analysis_plots); jj++) {
		toprow = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[0].appendChild(document.createElement('td'));
		toprow.setAttribute("colspan", "3");
		toprowspan = toprow.appendChild(document.createElement('span'));
		toprowspan.setAttribute("id", "python_analysis_plottitle_" + jj);

		midrow = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[1];//.appendChild(document.createElement('td'));
		leftarrtd = midrow.appendChild(document.createElement('td'));
		leftarr = leftarrtd.appendChild(document.createElement('img'));
		leftarr.setAttribute("src", "images/LeftFillTriangleIcon.png");
		leftarr.setAttribute("height", "15px");
		leftarr.setAttribute("onclick", "javascript:increment_value(-1,'python_analysis_plotindex_" + jj + "');update_analysis_plots();");
		viewerdivtd = midrow.appendChild(document.createElement('td'));
		viewerdiv = viewerdivtd.appendChild(document.createElement('div'));
		viewerdiv.setAttribute("id", "python_analysis_plotviewer_" + jj);
		viewerdiv.setAttribute("class", "viewer");
		indin = viewerdivtd.appendChild(document.createElement('input'));
		indin.setAttribute("type", "text");
		indin.setAttribute("hidden", "hidden");
		indin.setAttribute("id", "python_analysis_plotindex_" + jj);
		indin.value = jj;
		rightarrtd = midrow.appendChild(document.createElement('td'));
		rightarr = rightarrtd.appendChild(document.createElement('img'));
		rightarr.setAttribute("src", "images/RightFillTriangleIcon.png");
		rightarr.setAttribute("height", "15px");
		rightarr.setAttribute("onclick", "javascript:increment_value(1,'python_analysis_plotindex_" + jj + "');update_analysis_plots();");

		botrow = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[2].appendChild(document.createElement('td'));
		botrow.setAttribute("colspan", "3");
		//divfordiv = botrow.appendChild(document.createElement('div'));
		//buttdiv = divfordiv.appendChild(document.createElement('div'));
		//buttdiv.setAttribute("id","python_analysis_plotbuttons_" + jj);
		statspan = botrow.appendChild(document.createElement('span'));
		statspan.setAttribute("id", "python_analysis_plotviewerstatus_" + jj);
		statspan.setAttribute("align", "right");
		jumpbutt = botrow.appendChild(document.createElement('img'));
		jumpbutt.setAttribute("src", "images/seqicon_tonewtab.png");
		jumpbutt.setAttribute("height", "15px");
		jumpbutt.setAttribute("align", "right");
		jumpbutt.setAttribute("onclick", "window.open($('#python_analysis_plotviewer_" + jj + "').iviewer('info', 'src',''));");

		srcimg = 'images/seqicon_null.jpg';

		$("#python_analysis_plotviewer_" + jj).iviewer({
			src: srcimg,
			onMouseMove: function (ev, coords) {
				document.getElementById('python_analysis_plots_coords').innerHTML = '(' + coords.x.toFixed(1) + ', ' + coords.y.toFixed(1) + ')';
			}
		});
	}
}

function destroy_analysis_plots(num_to_destroy) {
	"use strict";

	var toprow, midrow, botrow, j, element;

	toprow = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[0].getElementsByTagName("td");
	midrow = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[1].getElementsByTagName("td");
	botrow = document.getElementById('analysis_plot_table').getElementsByTagName("tr")[2].getElementsByTagName("td");
	if (toprow.length > 1) {
		for (j = 0; j < num_to_destroy; j++) {
			element = toprow[toprow.length - 1];
			element.parentNode.removeChild(element);
			element = midrow[midrow.length - 1];
			element.parentNode.removeChild(element);
			element = midrow[midrow.length - 1];
			element.parentNode.removeChild(element);
			element = midrow[midrow.length - 1];
			element.parentNode.removeChild(element);
			element = botrow[botrow.length - 1];
			element.parentNode.removeChild(element);
		}
	}
}

function undo(arg) {
	"use strict";
	/*
	Functions as an undo button for the text editor, for when Ctrl-Z won't work. (Ie. When editing the hdiode tree.)
	*/

	var index_number;
	arg.history_level++;
	//Next, find the index of the xml string that we want to access of the history array.
	index_number = arg.history.length - arg.history_level - 1;
	arg.xml_string = arg.history[index_number];
	//Here we remove the entry we're using from the history array.
	arg.history.splice(index_number, 1);
	//Tells the history function to keep the history level it's at.
	arg.keep_hlevel = true;
	arg.update_editor();
	arg.keep_hlevel = false;
	//Remove the newest entry to the history array, which was created by reverting the editor to its previous state.
	arg.history.pop();
	//Add back in the entry we just reverted the tree to, thus preserving the sequence order of the history array.
	arg.history.splice(index_number, 0, arg.xml_string);
	//If the history_level is now 1 (hence, it was zero), enable the redo button.
	if (arg.history_level === 1) {
		toggle_button("redo", false);
	}
	//Similarly, if the history level is now at the max value of the history array, disable the undo button.
	if ((arg.history.length - 1) === arg.history_level) {
		toggle_button("undo", true);
	}
}

function redo(arg) {
	"use strict";
	/*
	Functions as a redo button for the text editor, for when Ctrl-Y won't work. (Ie. When editing the hdiode tree.)
	*/

	var index_number;
	arg.history_level--;
	//Next, find the index of the xml string that we want to access of the history array.
	index_number = arg.history.length - arg.history_level - 1;
	arg.xml_string = arg.history[index_number];
	//Here we remove the entry we're using from the history array.
	arg.history.splice(index_number, 1);
	//Tells the history function to keep the history level it's at.
	arg.keep_hlevel = true;
	arg.update_editor();
	arg.keep_hlevel = false;
	//Remove the newest entry to the history array, which was created by reverting the editor to its previous state.
	arg.history.pop();
	//Add back in the entry we just reverted the tree to, thus preserving the sequence order of the history array.
	arg.history.splice(index_number, 0, arg.xml_string);
	//If the history_level is now 1 (hence, it was zero), enable the redo button.
	if (arg.history_level === 0) {
		toggle_button("redo", true);
	}
	//Similarly, if the history level is now at the max value of the history array, disable the undo button.
	if ((arg.history.length - 2) === arg.history_level) {
		toggle_button("undo", false);
	}
}

function change_color_scheme() {
	"use strict";
	/*
	Changes XTSM colors from dark to light or vice versa, along with input, select, and textarea's background and text colors.
	This is accomplished by loading a separate stylesheet for the XTSM changes, and manually modifying all input, select, and textarea fields.
	*/
	var button, stylesheet, i, input_fields, select_fields, textarea_fields;

	button = document.getElementById("light_dark_button");
	if (button.value === 'Dark Room Color') {
		// First change the stylesheet for the xtsm elements to a dark room version.
		stylesheet = document.getElementById('stylesheet');
		stylesheet.href = "xtsm_dark.css";
		// Change the page's background color.
		document.body.style.background = '#4f515a';
		// Change the page's text color.
		document.body.style.color = '#ffffff';
		// Change the background and text colors of every input field.
		input_fields = document.getElementsByTagName('input');
		for (i = 0; i < input_fields.length; i++) {
			input_fields[i].style.background = '#212126';  // Background color
			input_fields[i].style.color = '#ffffff';  // Text color
		}
		// Change the background and text colors of every select field.
		select_fields = document.getElementsByTagName('select');
		for (i = 0; i < select_fields.length; i++) {
			select_fields[i].style.background = '#212126';  // Background color
			select_fields[i].style.color = '#ffffff';  // Text color
		}
		// Change the background and text colors of every textarea field.
		textarea_fields = document.getElementsByTagName('textarea');
		for (i = 0; i < textarea_fields.length; i++) {
			textarea_fields[i].style.background = '#212126';  // Background color
			textarea_fields[i].style.color = '#ffffff';  // Text color
		}
		// Change the button's value.
		button.value = 'Light Room Color';
	} else if (button.value === 'Light Room Color') {
		// First change the stylesheet for the xtsm elements to a light room version.
		stylesheet = document.getElementById('stylesheet');
		stylesheet.href = "xtsm.css";
		// Change the page's background color.
		document.body.style.background = '#ffffff';
		// Change the page's text color.
		document.body.style.color = '#000000';
		// Change the background and text colors of every input field.
		input_fields = document.getElementsByTagName('input');
		for (i = 0; i < input_fields.length; i++) {
			input_fields[i].style.background = '#ffffff';  // Background color
			input_fields[i].style.color = '#000000';  // Text color
		}
		// Change the background and text colors of every select field.
		select_fields = document.getElementsByTagName('select');
		for (i = 0; i < select_fields.length; i++) {
			select_fields[i].style.background = '#ffffff';  // Background color
			select_fields[i].style.color = '#000000';  // Text color
		}
		// Change the background and text colors of every textarea field.
		textarea_fields = document.getElementsByTagName('textarea');
		for (i = 0; i < textarea_fields.length; i++) {
			textarea_fields[i].style.background = '#ffffff';  // Background color
			textarea_fields[i].style.color = '#000000';  // Text color
		}
		// Change the button's value.
		button.value = 'Dark Room Color';
	}
}

function toggle_help() {
	"use strict";
	/*
	Sets help options to tree elements when applicable. This includes a title and a link to a page on the wiki.
	
	First time checking/unchecking the help checkbox will create new text elements to replace the original text.
	Subsequent checking/unchecking will simply change the text values in those new text elements (one will be blank while the other contains the actual text value to display).
	*/
	var top, help_nodes, help_text_nodes, nonstandard, nonstandard_nodes, divs, i, j, children, text_node, text_value, text_fields, help_text, k, linkitem, replacement_text, textitem;

	// Get basic node groups. Second and third groups only exist after one cycle of help being toggled on and off.
	top = document.getElementsByClassName('hdiode_xml_tree_treediv')[0];
	help_nodes = top.getElementsByClassName('help_node');
	help_text_nodes = top.getElementsByClassName('help_text');
	nonstandard_nodes = top.getElementsByClassName('nonstandard');

	if (document.getElementById("show_help").checked === true) {
		// Standard XTSM elements.
		if (help_nodes.length === 0) {  // Occurs first time checkbox is checked.
			// We want to find all text nodes in all divs of the hdiode tree, split them up into keywords, and create new nodes of those keywords with helpful titles and links.
			divs = top.getElementsByTagName('div');
			for (i = 0; i < divs.length; i++) {
				for (j = 0; j < divs[i].childNodes.length; j++) {
					children = divs[i].childNodes[j];
					// If child node is a text node, then analyze it.
					if (children.nodeName === '#text') {
						text_node = children.nodeName;
						text_value = children.nodeValue;
						// Split at colons.
						text_fields = text_value.split(':');
						for (k = 0; k < text_fields.length; k++) {
							// Specifies the key word to search for in the help_fields.
							help_text = text_fields[k].replace(/\./g, '');
							if (jQuery.inArray(help_text, help_fields.available_fields) !== -1) {
								// Create a new text node and insert it after the current text. This will contain the help information, including the keyword, helpful title, and link.
								linkitem = divs[i].appendChild(document.createElement('a'));
								$(linkitem).insertAfter(children);
								linkitem.appendChild(document.createTextNode(help_text));
								linkitem.setAttribute('href', help_fields.links[jQuery.inArray(help_text, help_fields.available_fields)]);
								linkitem.setAttribute('target', "_blank_");  // Opens link on a new page.
								linkitem.setAttribute('title', help_fields.quick_descript[jQuery.inArray(help_text, help_fields.available_fields)]);
								linkitem.setAttribute('class', 'help_node');  // To help classify these new nodes.
								// Create a text node after this node, in order to restore the displayed text to its original state.
								replacement_text = text_value.split(help_text);
								textitem = divs[i].appendChild(document.createElement('a'));
								// Change new text node to contain only the text after the keyword.
								textitem.appendChild(document.createTextNode(replacement_text[1]));
								$(textitem).insertAfter(linkitem);
								// Change the original text node to contain only the text before the keyword.
								children.nodeValue = replacement_text[0];
							}
						}
					}
				}
			}
		} else {  // Occurs each subsequent time checkbox is checked, in order to avoid remaking everything.
			// Standard XTSM elements.
			for (i = 0; i < help_nodes.length; i++) {
				// Get the text_value from the text node, make the text node blank, and give that text_value to the help node.
				text_value = help_text_nodes[i].textContent;
				help_text_nodes[i].textContent = '';
				help_nodes[i].textContent = text_value;
			}
		}
		// Nonstandard XTSM elements. Nonstandard XTSM elements with help fields should probably be added as standard...
		for (i = 0; i < nonstandard_nodes.length; i++) {
			// Split into keyword and non-keyword portions. (Unlike standard elements, these will only have one keyword.)
			help_text = nonstandard_nodes[i].textContent.split(':');
			if (jQuery.inArray(help_text[0], help_fields.available_fields) !== -1) {
				linkitem = nonstandard_nodes[i];
				// Add helpful title and link to node.
				linkitem.setAttribute('title', help_fields.quick_descript[jQuery.inArray(help_text[0], help_fields.available_fields)]);
				linkitem.setAttribute('href', help_fields.links[jQuery.inArray(help_text[0], help_fields.available_fields)]);
				linkitem.setAttribute('target', "_blank_");  // Opens link on a new page.
			}
		}
	} else {  // If not checked, remove nodes.
		// Standard elements.
		if (help_text_nodes.length === 0) {  // Occurs first time checkbox is checked.
			for (i = 0; i < help_nodes.length; i++) {
				// Create a new text_node for each help node with the same text_value but none of the help features (eg. link to wiki page).
				help_text = help_nodes[i].textContent;
				textitem = help_nodes[i].appendChild(document.createElement('a'));
				textitem.appendChild(document.createTextNode(help_text));
				textitem.setAttribute('class', 'help_text');
				$(textitem).insertAfter(help_nodes[i]);
				// Make the text_value of the help node blank now that the corresponding text_node has that value.
				help_nodes[i].textContent = '';
			}
		} else {  // Occurs each subsequent time checkbox is unchecked, in order to avoid remaking everything.
			for (i = 0; i < help_nodes.length; i++) {
				// Get the text_value from the help node, make the help node blank, and give that value to the text_node.
				text_value = help_nodes[i].textContent;
				help_nodes[i].textContent = '';
				help_text_nodes[i].textContent = text_value;
			}
		}
		// Nonstandard elements.
		for (i = 0; i < nonstandard_nodes.length; i++) {
			// Get the text_value from the text node, make the text node blank, and give that text_value to the help node.
			nonstandard_nodes[i].setAttribute('title', 'Non-standard XTSM tag');
			nonstandard_nodes[i].removeAttribute('href');
		}
	}
}

function change_font(type, size, value) {
	"use strict";
	/*
	Changes either the font type or font size of all text elements in the hdiode tree.
	If font type, also checks if the specified value is a valid font type.
	*/

	var tree, font_type, tree_divs, i, font_size;
	// Find all text nodes in the hdiode tree.
	tree = document.getElementsByClassName('hdiode_xml_tree_treediv')[0];
	if (type === true) {
		// For font type, you must change the font family attribute of each div.
		font_type = value;
		tree_divs = tree.getElementsByTagName('div');
		for (i = 0; i < tree_divs.length; i++) {
			tree_divs[i].style.fontFamily = font_type;
		}
	} else if (size === true) {
		// For font size, you can simply change the parent element's font size attribute.
		font_size = value;
		if (!isNaN(font_size)) {  // Only change font size if size is a number.
			tree.style.fontSize = font_size + 'px';  // Here px stands for pixels. Example font size: 14px.
		}
	}
}

function search_dom(termfield, arg) {
	/*
	Takes as input a text box object (termfield) and an hdiode tree element (arg).
	Turns XTSM (from hdiode tree) into a DOM object and searches for the value of the termfield.
	Displays the results underneath the termfield. Results include:
		A button to delete results.
		A button to jump to the relevant element.
	*/

	//This parses the existing XML code into a DOM object
	var parser2, xmlDoc2, search_result, results_list_super_div, results_list_div, delicon, ital, results_list, result, list_item, name, jump_icon, match_text, underscored;

	//Create new DOM object and use it to parse XTSM from arg.
	parser2 = new DOMParser();
	xmlDoc2 = parser2.parseFromString(arg.xml_string, "text/xml");
	//Search the XTSM for the value of termfield.
	search_result = xmlDoc2.evaluate("//*[text()[contains(.,'" + termfield.value + "')]]", xmlDoc2, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
	//Find the search results div element and add a new result node to it.
	results_list_super_div = document.getElementById('search_results_div');
	results_list_div = results_list_super_div.appendChild(document.createElement('div'));
	delicon = results_list_div.appendChild(document.createElement("img"));
	//Create delete button for the new result node.
	delicon.setAttribute('src', '/images/seqicon_item_delete.png');
	delicon.setAttribute('height', '12px');
	delicon.setAttribute('title', 'Delete results');
	delicon.setAttribute('onclick', 'javascript:this.parentNode.parentNode.removeChild(this.parentNode);');
	//List the term that was searched for.
	results_list_div.appendChild(document.createTextNode("  Results for '"));
	ital = results_list_div.appendChild(document.createElement("i"));
	ital.appendChild(document.createTextNode(termfield.value));
	results_list_div.appendChild(document.createTextNode("':"));
	//Create a new node to list the search results.
	results_list = results_list_div.appendChild(document.createElement('ul'));
	results_list.setAttribute("style", "list-style-type:none");
	//For each search result...
	result = search_result.iterateNext();
	if (result === null) {
		//Create a new node.
		list_item = results_list.appendChild(document.createElement('li'));
		//List lack of result.
		list_item.appendChild(document.createTextNode('No results for ' + termfield.value + ' were found.'));
	} else {
		while (result) {
			//Create a new node.
			list_item = results_list.appendChild(document.createElement('li'));
			//Create a jump button.
			jump_icon = list_item.appendChild(document.createElement('img'));
			jump_icon.setAttribute('src', '/images/seqicon_go.png');
			jump_icon.setAttribute('height', '18px');
			jump_icon.setAttribute('title', 'Jump to this element');
			name = generate_name_for_element(result.parentNode);
			jump_icon.name = name;
			jump_icon.onclick = function () {searchjump(this.name, arg); };
			//Add in a search result.
			match_text = result.childNodes[0].nodeValue.split(termfield.value);
			list_item.appendChild(document.createTextNode(result.parentNode.nodeName + " : " + result.nodeName + " = '" + match_text[0]));
			//Underline the searched term in the listed result.
			underscored = list_item.appendChild(document.createElement('u'));
			underscored.appendChild(document.createTextNode(termfield.value));
			list_item.appendChild(document.createTextNode(match_text[1] + "'"));
			//Continue loop.
			result = search_result.iterateNext();
		}
	}
}

function Hdiode_code_tree(html_div, sources) {

// This object implements a linked-pair of text/code-editor (using codeMirror) 
// and HTML xml tree-editor. The HTML representation of the tree is built using
// an XSL transform which can be dynamically loaded/reloaded.  
// Optionally, an XSD schema can also be loaded (not yet used for anything).
// Both editor and tree are inserted into the HTML DOM at the provided html_div.


    function create_container(html_div) {
    // creates child divisions to house title (topline), codemirror, and tree. 
    // Creates textarea to later be converted into codemirror editor.
        this.html_div_title = html_div.appendChild(document.createElement('div'));
        this.html_div_title.setAttribute("class", "hdiode_xml_tree_titlediv");
        this.html_div_title.appendChild(document.
            createElement('span')).appendChild(document.createTextNode('XML Editor'));
        this.html_div_fe = html_div.appendChild(document.createElement('div'));
		new Hdiode_file_ops(this.html_div_fe);
        this.html_div_undo = html_div.appendChild(document.createElement('div'));
		new Hdiode_undo(this.html_div_undo);
        this.html_div_cm = html_div.appendChild(document.createElement('div'));
        this.html_div_cm.setAttribute("class", "hdiode_xml_tree_cmdiv");

        html_div.setAttribute("width", "100%");
        html_div2 = html_div.appendChild(document.createElement('div'));
        this.html_table = html_div2.appendChild(document.createElement('table'));
        this.html_table.setAttribute("width", "100%");
        this.html_row = this.html_table.appendChild(document.createElement('row'));
        this.html_row.setAttribute("width", "100%");
        this.html_div_post_button_td = this.html_row.appendChild(document.createElement('td'));
        this.html_div_post_button_td.setAttribute("width", "2%");
        this.html_div_post_button_td.setAttribute("class", "hdiode_xml_tree_titlediv");
        this.html_div_post_button_td.onclick = this.post_active_xtsma;
        this.html_div_post_button_td.owner = this;
        this.html_div_post_button_td.setAttribute("title", "post to server");
        this.html_div_tree_td = this.html_row.appendChild(document.createElement('td'));
        this.html_div_tree_td.setAttribute("width", "96%");
        this.html_div_retrieve_button_td = this.html_row.appendChild(document.createElement('td'));
        this.html_div_retrieve_button_td.setAttribute("width", "2%");
        this.html_div_retrieve_button_td.setAttribute("class", "hdiode_xml_tree_titlediv");
        this.html_div_retrieve_button_td.onclick = this.retrieve_active_xtsma;
        this.html_div_retrieve_button_td.setAttribute("title", "retrieve from server");
        this.html_div_retrieve_button_td.owner = this;
        this.html_div_tree = this.html_div_tree_td.appendChild(document.createElement('div'));
        this.html_div_tree.setAttribute("id", "hdiode_xml_tree_treediv");
        this.html_div_tree.setAttribute("class", "hdiode_xml_tree_treediv");
		this.cm_expand_icon=this.html_div_cm.appendChild(document.createElement('img'));
		this.cm_expand_icon.src="/images/DownTriangleIcon.png";
		this.cm_expand_icon.setAttribute("height", "16px");
		this.cm_expand_icon.onclick=this.toggle_cm;
		this.cm_expand_icon.owner=this;
		this.html_div_cm.appendChild(document.createTextNode('Code Mirror'));
        this.textarea = this.html_div_cm.appendChild(document.createElement('textarea'));
        this.textarea.value = this.xml_string;
        //Tool Panel
        this.toolpanel = document.createElement("IFRAME");
        this.toolpanel.setAttribute("style", "position: fixed; right: 10px; top: 10px; z-index:999;background-color:#ffcccc;");
        this.toolpanel.setAttribute("id", "toolbar");
        document.body.appendChild(this.toolpanel);
        this.toolpaneldoc = document.getElementById("toolbar").contentDocument;
        this.tooltable = this.toolpaneldoc.body.appendChild(this.toolpaneldoc.createElement("table"));
        var row0 = this.tooltable.appendChild(this.toolpaneldoc.createElement("tr"));
        row0.appendChild(this.toolpaneldoc.createElement("td")).appendChild(this.toolpaneldoc.createTextNode("Shot Number Navigation"));
        this.toolpanel_statusbar = row0.appendChild(this.toolpaneldoc.createElement("td")).appendChild(this.toolpaneldoc.createElement("div"));
        this.toolpanel_statusbar.setAttribute("id", "toolpanel_statusbar");
        var row1 = this.tooltable.appendChild(this.toolpaneldoc.createElement("tr"));
        this.shotnumber_larrow = row1.appendChild(this.toolpaneldoc.createElement("td")).appendChild(this.toolpaneldoc.createElement("img"));
        this.shotnumber_input = row1.appendChild(this.toolpaneldoc.createElement("td")).appendChild(this.toolpaneldoc.createElement("input"));
        this.shotnumber_rarrow = row1.appendChild(this.toolpaneldoc.createElement("td")).appendChild(this.toolpaneldoc.createElement("img"));
        this.shotnumber_larrow.src = "/images/LeftFillTriangleIcon.png";
        this.shotnumber_larrow.setAttribute("id", "shotnumber_browse_larrow");
        this.shotnumber_rarrow.src = "/images/RightFillTriangleIcon.png";
        this.shotnumber_rarrow.setAttribute("id", "shotnumber_browse_rarrow");
        this.shotnumber_larrow.setAttribute("style", "height:15px;align:right;");
        this.shotnumber_larrow.align = "right";
        this.shotnumber_rarrow.setAttribute("style","height:15px;align:left;");
        this.shotnumber_rarrow.onclick = this.update_shotnumber_browse;
        this.shotnumber_larrow.onclick = this.update_shotnumber_browse;
        this.shotnumber_input.setAttribute("value", "0");
        this.shotnumber_input.setAttribute("id", "shotnumber_browse_input");
        this.shotnumber_input.onchange = this.update_shotnumber_browse;
        this.shotnumber_larrow.owner=this;
        this.shotnumber_rarrow.owner=this;
        this.shotnumber_input.owner = this;
        var row2 = this.tooltable.appendChild(this.toolpaneldoc.createElement("tr"));
        this.shotnumber_lock_img = row2.appendChild(this.toolpaneldoc.createElement("td")).appendChild(this.toolpaneldoc.createElement("img"));
        this.shotnumber_lock_img.src = "/images/seqicon_unlock.png";
        this.shotnumber_lock_img.onclick = this.shotnumber_lockdown;
        this.shotnumber_lock_img.owner = this;
        this.shotnumber_lock_img.title = "content lock";
        this.shotnumber_lock_img.id = "content_lock";
    }
    this.create_container = create_container;
    this.shotnumber_browse = 0;  // this is the shotnumber currently browsed in the code editor - controls when xtsm is requested back from server
    this.shotnumber_lock = false;  // if true, browsed xtsm will be requested when changes occur on editor side

    function update_shotnumber_browse(e) {
        // this is called anytime the left or right arrows are clicked or the shotnumber browse field is changed on the pink toolbar at bottom right of screen.
        var newval;
        if (e.target.src === "") {
            this.owner.shotnumber_browse = e.target.value + this.owner.running_shot;
            newval = Number(e.target.value);
        }
        if (e.target.src.split("Right").length > 1) {
            this.owner.shotnumber_browse += 1;
            newval = Number(this.owner.shotnumber_input.value) + 1;
        }
        if (e.target.src.split("Left").length > 1) {
            this.owner.shotnumber_browse -= 1;
            newval = Number(this.owner.shotnumber_input.value) - 1;
        }
        this.owner.shotnumber_input.setAttribute("value", newval);
        // here we will request new xtsm no matter what the status of the browser lock is; obviously the user wants new data.
		var pxi_dc;
		pxi_dc = document.getElementById('pxi_dc').value;
		var get_shotnumber = newval + parseInt(this.owner.running_shot);
		console.log("request_xtsm " + "this.owner.shotnumber_browse " + this.owner.shotnumber_browse + " this.owner.running_shot " + this.owner.running_shot + ", " + get_shotnumber + ", " + newval);
        document.getElementById("server_push_output_textarea").sendText('{"IDLSocket_ResponseFunction":"request_xtsm","data_context":"' + pxi_dc + '","shotnumber":"' + get_shotnumber + '"}');
    }
    this.update_shotnumber_browse = update_shotnumber_browse;

    function shotnumber_lockdown(state) {
        // this is called when the shotnumber lock icon is clicked.
        if (typeof state !== "boolean") { that = this.owner; state = !that.shotnumber_lock; } else {that = this;}
        that.shotnumber_lock = state;
        if (that.shotnumber_lock) {
            that.shotnumber_lock_img.src = "/images/seqicon_lock.png";
            that.toolpanel.style.backgroundColor = "#ffcccc";
            }
        else {
            that.shotnumber_lock_img.src = "/images/seqicon_unlock.png";
            that.toolpanel.style.backgroundColor = "#ccff88";
            }
    }
    this.shotnumber_lockdown = shotnumber_lockdown;


    function retrieve_active_xtsma() {
        // The global function retrieve_active_xtsm should be moved here
        retrieve_active_xtsm(this.owner);
    }
    this.retrieve_active_xtsma = retrieve_active_xtsma;

    function post_active_xtsma(e) {
        // The global function post_active_xtsm should be moved here
		ws_function.commandLibrary.post_active_xtsm_ws(this.owner);//Craig 2014-10-28
        //post_active_xtsm(this.owner);
    }
    this.post_active_xtsma = post_active_xtsma;

    function toggle_cm(e) {
		if (this.owner.cm_expand===true){
			this.owner.cm_expand=false;
			this.owner.cm_expand_icon.src="images/RightFillTriangleIcon.png";
			this.owner.html_div_cm.removeChild(this.owner.editor.getWrapperElement());
		} else {
			this.owner.cm_expand=true;
			this.owner.cm_expand_icon.src="/images/DownTriangleIcon.png";
	        this.owner.textarea = this.owner.html_div_cm.appendChild(document.createElement('textarea'));
    	    this.owner.textarea.value = this.owner.xml_string;
			this.owner.create_cm(this.owner.textarea);			
		}
    }
    this.toggle_cm = toggle_cm;

    function create_cm(textarea) {
    // this is used to create main CodeMirror editor
		that=this;
        this.editor = CodeMirror.fromTextArea(this.textarea,
            { mode: "text/html", gutter: "True", lineNumbers: "True",
                gutters: ["note-gutter", "CodeMirror-linenumbers"],
                linewrapping: "True", autoCloseTags: true, cursorBlinkRate:"500"});
        this.editor.on("change", function () {
            that.xml_string = that.editor.getValue();
            that.refresh_tree();
            return;
		});
	}
    this.create_cm = create_cm;

    var root_tree = this;
    function create_subcm(textarea, format) {
    // this is used to create CodeMirror editors for in-tree editing (not the main XTSM editor)
        var cmobj;
        var that = this;
        var forms = { python: { mode: { name: "python", version: 2, singleLineStringErrors: false },
                                lineNumbers: true, indentUnit: 4, matchBrackets: true},
                      xml: { mode: "text/html", gutter: "True", lineNumbers: "True",
                                gutters: ["note-gutter", "CodeMirror-linenumbers"],
                                linewrapping: "True", autoCloseTags: true, cursorBlinkRate: "500"}
                        };
        cm_obj = CodeMirror.fromTextArea(textarea,forms[format]);
        cm_obj.setSize(900,300);
        cm_obj.setValue(textarea.value.replace(/<!\[CDATA\[.*?\]\]>/g, ''));
        cm_obj.container_tree = root_tree;
        cm_obj.on("blur", function (e) {
                e.target = textarea;
                e.target.name = textarea.name;
                e.target.value = ""+cm_obj.getValue();
                e.data=Object();
                e.data.container=e.container_tree;  // this needs to pass ref to hdiode_codetree object
                e.gen_id = textarea.gen_id;
                e.container = textarea.container;
                updateElementEscaped_update_editor(e);
                return;
            });
    }
    this.create_subcm = create_subcm;


    function xmltoString(elem) {
        var serialized, serializer;
        try {
			if (!(typeof this.serializer === 'object')){
            	this.serializer = new XMLSerializer();
			}
            serialized = this.serializer.serializeToString(elem);
        } catch (e) { serialized = elem.xml; }
        return serialized;
    }

    function refresh_tree() {
        //builds HTML tree by applying XSL to XML.
        var xslparser, docparser, xml, xsltProcessor, ex, exs, elem_num, elem, linkitem, divitem, h_classes, i, prev_class, tocms;
        if (!this.xml_string) { return; }
        if (!this.xsl_string) { return; }
        // -> would be good to avoid reparsing the xsl everytime.
        if (!(typeof this.xslDoc === 'object')) {
			xslparser = new DOMParser();
            this.xslDoc = xslparser.parseFromString(this.xsl_string, "text/xml");
        }
        if (!(typeof this.docparser === 'object')) {
            this.docparser = new DOMParser();
        }
        //docparser = new DOMParser();
        xml = this.docparser.parseFromString(this.xml_string, "text/xml");
        if (!(typeof this.xsltProcessor === 'object')) {
            if (typeof XSLTProcessor == 'function') {
                this.xsltProcessor = new XSLTProcessor();
                this.xsltProcessor.importStylesheet(this.xslDoc);
            } else {
                this.xsltProcessor = PyXSLTProcessor; // for use in PyQT Webkit implementations
                this.xsltProcessor.importStylesheet(this.xsl_string);
                //this.xslDoc = this.xsltProcessor;    
            }
	        
		} 
		//var ownerDocument = document.implementation.createDocument("", "test", null);
        //ex = this.xsltProcessor.transformToFragment(xml, ownerDocument);
		//ex=this.xsltProcessor.transformToDocument(xml);
		if (typeof XSLTProcessor == 'function') {
		    var sResult = zXslt.transformToText(xml, this.xslDoc);
		} else {
		    var sResult = this.xsltProcessor.transformToText(this.xml_string); 
        }
        //exs = xmltoString(ex); // would have preferred this.xsltProcessor.GetXmlStringFromXmlDoc(xml) but chrome doesn't support it // 
        this.unbind_events();  // this is important to allow garbage collection and avoid memory leak
		this.html_div_tree = replaceHtml(this.html_div_tree, sResult);// exs);
		// -> need to bind update methods here - 
        // must require xsl routine to tag inputs for binding.
        this.bind_events();
		// Creates jump links if applicable (IN PROGRESS)
		// this.jump_links();
		// Creates help titles and links if applicable
		// Reenables help options if it was on before refresh.
		toggle_help();
		// Restores fields highlighted by searching to their original state.
		h_classes = document.querySelectorAll('class[highlighted]');
		for (i = 0; i < h_classes.length; i++) {
			prev_class = h_classes[i].getAttribute('old_class');
			h_classes[i].setAttribute('class', prev_class);

        }

        // swap textareas requesting codemirrorization

        tocms = $("[codemirrorize]");
        for (i = 0; i < tocms.length; i++) {
            create_subcm(tocms[i],$(tocms[i]).attr("codemirrorize")) 
            }

		delete ex, exs, xml, h_classes, prev_class, sResult;
    }
    this.refresh_tree = refresh_tree;

    function to_server(mes) {
        // passes a request to the server using websocket, if connected, (FUTURE: or by ajax if not)
        $('#server_push_output_textarea')[0].sendText(mes);
    }
    this.to_server = to_server;

    // live_data are data elements too large to directly embed into the XTSM tree, such
    // as images or data - the livedata mechanism allows them to be loaded and interacted with
    // on demand. When requested, these elements retrieve their content from the server,
    // and a local copy is retained.  The server also provides notification when these elements' content
    // is altered server-side, allowing this GUI to update their contents. 
    // when all references to a live_content item are dropped, the local storage is freed and notification is sent to 
    // the server.

    function load_livedata(event) {
        // the onload listener for live_data elements - generates a request for previously
        // unrequested live_data elements, or returns locally archived data
		return; //CP 2014-11-1
        var ed, cid;
        cid = event.data.args[0].replace(/["']{1}/gi, "");
        ed = event.data.container;
        if (!ed.live_gui_data) {ed.live_gui_data = {}; };
        if (!ed.live_gui_data[cid]) {
			var pxi_dc;
			pxi_dc = document.getElementById('pxi_dc').value;
            ed.to_server('{"IDLSocket_ResponseFunction":"request_content","content_id":"' + cid + '","data_context":"' + pxi_dc + '"}');
        } else {
            this.parentNode.innerHTML = ed.live_gui_data[cid]; };
    }
    this.load_livedata = load_livedata;

    function update_livedata(content_id,data) {
        // updates live data stack and html elements if they are displayed
		return;//CP 2014-11-1
        if (!this.live_gui_data) { this.live_gui_data = {}; };
        this.live_gui_data[content_id] = data;
        $("[content_id='" + content_id + "']").html(data);  // sets all current matching content's innerHTML
    }
    this.update_livedata = update_livedata;

    function flush_livedata() {
        // flushes the unused live data items from local storage to allow garbage collector to free memory
		return; //CP 2014-11-1
        var item;
        for (item in this.live_gui_data) {
            // scan editor tree for live_data id's - if they are not present, deallocate storage and inform server of disinterest
            if ($("[content_id=" + item + "]").size() == 0) {
                delete this.live_gui_data[item];
				var pxi_dc;
				pxi_dc = document.getElementById('pxi_dc').value;
                this.to_server('{"IDLSocket_ResponseFunction":"derequest_content","content_id":"' + item + '"}');
                };
            };
    }
    this.flush_livedata = flush_livedata;

    function toggleProp_update_editor(event) {
        // toggles an element between expanded and collapsed view by rewriting XML, 
        // and re-generating entire tree.  Retrieve XPATH to generating XML element 
        // from first parent division's gen_id property
        var change_prop, elmpath, docparser, xml, target, newval, temp, targets, i;
        change_prop = event.data.args[0].replace(/["']{1}/gi, "");
        docparser = new DOMParser();
        xml = docparser.parseFromString(event.data.container.xml_string, "text/xml");
        target = event.data.container.event_get_elm(event, xml);
        newval = ($(target).attr(change_prop) === "1") ? '0' : '1';
        if ($(target).attr(change_prop) === "1") {
            $(target).attr(change_prop, "0");
        } else {
            (temp = $(target).attr(change_prop, "1"));
        }
        if (event.ctrlKey) {
            //ctrl-toggle applies to children
            elmpath = event.data.container.event_get_elmpath(event);
            targets = xml.evaluate(elmpath + "/*", xml, null,
                XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
            for (i = 0; i < targets.snapshotLength; i += 1) {
                $(targets.snapshotItem(i)).attr(change_prop, newval);
            }
        }
        if (event.altKey) {
            //alt-toggle applies to all decendants
            elmpath = event.data.container.event_get_elmpath(event);
            targets = xml.evaluate(elmpath + "//*", xml, null,
                XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
            for (i = 0; i < targets.snapshotLength; i += 1) {
                $(targets.snapshotItem(i)).attr(change_prop, newval);
            }
        }
        event.data.container.xml_string = xmltoString(xml);
        event.data.container.update_editor();
        // (tree is automatically refreshed by onchange event of codemirror editor if present)
		event.data.container.refresh_tree();
    }
    this.toggleProp_update_editor = toggleProp_update_editor;

    function spawn_child_menu(event) {
        // menu for adding child XTSM elements - reads schema to find valid children to add, creates dropdown menu to select them from.
        var elmfin, elmname, docparser, xsdobj, types, subtypes, i, j, elm, subtypenames;
        elmfin = this.parentNode.attributes.getNamedItem("gen_id").nodeValue.split("_");
        elmname = "";
        while ((elmname === "") || (!isNaN(elmname))) { elmname = elmfin.pop(); };
        elm = elmname;
        docparser = new DOMParser();
        event.data.container.xsdobj = docparser.parseFromString(event.data.container.xsd_string, "text/xml");
        types = event.data.container.xsdobj.getElementsByTagName("complexType");
        i = 0;
        while ((i < types.length) && ((types[i]).attributes.getNamedItem("name").nodeValue) != elm) { i++; };
        if (!types[i]) { return; };
        subtypes = (types[i]).getElementsByTagName("element");
        if (subtypes.length == 0) {return;};
        subtypenames = [];
        subtypeselect = [];
        for (j = 0; j < subtypes.length; j++) {
            subtypenames.push(subtypes[j].attributes.getNamedItem("name").nodeValue);
            subtypeselect.push({ "method": event.data.container.addElement_update_editor, "root_event": event, "add_type": subtypes[j], "editor": event.data.container });
        };
        ($(this)).hover(event.data.container.dropdown(event, this, subtypenames, subtypeselect));        
    }
    this.spawn_child_menu = spawn_child_menu;

    function dropdown(event, lockto, labels, actions) {
        var menu_in,menu_in_ul,li,i;
        menu_in = document.createElement("div");
        menu_in.setAttribute("class", "custom-menu");
        menu_in_ul = menu_in.appendChild(document.createElement("ul"));
        if ((!this.dropmenus) || (this.dropmenus.length==0)) { this.dropmenus = [menu_in]; } else {this.dropmenus.push(menu_in);};
        for (i = 0; i < labels.length; i++) {
            li=menu_in_ul.appendChild(document.createElement("li"));
            li.appendChild(document.createTextNode(labels[i]));
            li.container = event.data.container;
            li.target = event.target;
            li.target_params = actions[i];
            li.onclick = this.dropdown_select;
        }
        $(menu_in).appendTo("body").css({ top: event.pageY + "px", left: event.pageX + "px" });
    }
    this.dropdown = dropdown;

    function keyboard_shorts(e) {
        if (e.keyCode == 27) { arguments.callee.parent.remove_dropmenus(e); };
        if (e.shiftKey && (e.keyCode==76)) {$("#toolbar").contents().find("#content_lock").click();};
        if (e.shiftKey && (e.keyCode == 37)) { $("#toolbar").contents().find("#shotnumber_browse_larrow").click(); };
        if (e.shiftKey && (e.keyCode == 39)) { $("#toolbar").contents().find("#shotnumber_browse_rarrow").click(); };
    }
    this.keyboard_shorts = keyboard_shorts;
    this.keyboard_shorts.parent = this;

    function remove_dropmenus(e) {
        if (!this.dropmenus) { return; };
        for (i = 0; i < this.dropmenus.length; i++) {
            this.dropmenus[i].parentNode.removeChild(this.dropmenus[i]);
        };
        this.dropmenus = [];
    }
    this.remove_dropmenus = remove_dropmenus;
    function dropdown_select(e) {
        e.target_params = this.target_params;
        this.target_params["method"](e);
        this.parentNode.parentNode.parentNode.removeChild(this.parentNode.parentNode);
    }
    this.dropdown_select = dropdown_select;

    function event_get_elmpath(event) {
    // given an event, this returns the xpath to the corresponding xml element that generated the control
        var elmpath;
        if (typeof (event) != "string") {
            elmpath = $(event.target).parents("div:first").get(0).
            getAttribute('gen_id');
        } else {elmpath = event;}
        if (elmpath.substr(elmpath.length - 2, 2) === '__') {
            if (event.target.name) {
                elmpath += event.target.name;
            } else {
                elmpath = elmpath.substr(0, elmpath.length - 2);
            }
        }
        elmpath = elmpath.split('divtree__')[1].replace(/__/g, "]/").
            replace(/_/g, "[") + "]";
        return elmpath;
    }
    this.event_get_elmpath = event_get_elmpath;

    function event_get_elm(event, xml) {
        // given an event, this returns the xml object that generated the control;
        // (it safely assumes there is only one such element)
        var elmpath, target;
        elmpath = event.data.container.event_get_elmpath(event);
        target = xml.evaluate(elmpath, xml, null, XPathResult.
            UNORDERED_NODE_ITERATOR_TYPE, null).iterateNext();
        return target;
    }
    this.event_get_elm = event_get_elm;

    function updateElement_update_editor(event) {
        // toggles an element between expanded and collapsed view by 
        // rewriting XML, and re-generating entire tree
        // retrieve XPATH to generating XML element from 
        // first parent division's gen_id property
        //var elmpath, docparser, xml, target;
		var elmpath, docparser, xml, target;
        elmpath = $(event.target).parents("div:first").get(0).
            getAttribute('gen_id');
        if (elmpath.substr(elmpath.length - 2, 2) === '__') {
            elmpath += event.target.name;
        }
        elmpath = elmpath.split('divtree__')[1].replace(/__/g, "]/").
            replace(/_/g, "[") + "]";
        docparser = new DOMParser();
        xml = docparser.parseFromString(event.data.container.xml_string, "text/xml");
        target = xml.evaluate(elmpath, xml, null, XPathResult.
            UNORDERED_NODE_ITERATOR_TYPE, null).iterateNext();
        if (target.firstChild) { target.firstChild.data = event.target.value; } else { target.appendChild(xml.createTextNode(event.target.value)); }
        event.data.container.xml_string = xmltoString(xml);
        event.data.container.update_editor();
        // (tree is automatically refreshed by onchange event of codemirror editor)
    }
    this.updateElement_update_editor = updateElement_update_editor;

    function updateElementEscaped_update_editor(event) {
        // toggles an element between expanded and collapsed view by 
        // rewriting XML, and re-generating entire tree
        // retrieve XPATH to generating XML element from 
        // first parent division's gen_id property
        //var elmpath, docparser, xml, target;
        var elmpath, docparser, xml, target, upd;
        elmpath = $(event.target).parents("div:first").get(0).
            getAttribute('gen_id');
        if (elmpath.substr(elmpath.length - 2, 2) === '__') {
            elmpath += event.target.name;
        }
        elmpath = elmpath.split('divtree__')[1].replace(/__/g, "]/").
            replace(/_/g, "[") + "]";
        docparser = new DOMParser();
        xml = docparser.parseFromString(event.data.container.xml_string, "text/xml");
        target = xml.evaluate(elmpath, xml, null, XPathResult.
            UNORDERED_NODE_ITERATOR_TYPE, null).iterateNext();
        upd = event.target.value.replace(/<!\[CDATA\[.*?\]\]>/g, '');
        if (target.firstChild) {
            target.removeChild(target.firstChild);
        }
        target.appendChild(xml.createCDATASection(upd)); 
        event.data.container.xml_string = xmltoString(xml);
        event.data.container.update_editor();
        // (tree is automatically refreshed by onchange event of codemirror editor)
    }
    this.updateElementEscaped_update_editor = updateElementEscaped_update_editor;

    function autocomplete(event) {
        var docparser, tevent, xml, res;//  res, xml;
        //first exit if the keypress is not ctrl-right- or ctrl-left-arrow
        tevent = event;
        if (!(event.ctrlKey)) { return; }
        if ((event.keyCode !== 39) && (event.keyCode !== 37)) { return; }
        // this event handler autocompletes by looking up values 
        // from xml dom when uparrow is pressed.
        // check if this input was the last pressed 
        // autocomplete, if not, reset index to zero
        if (event.data.container.autocomplete_lastfield !==
                $(event.target).attr('name')) {
            event.data.container.autocomplete_lastfield = $(event.target).attr('name');
            event.data.container.autocomplete_root = $(event.target).attr('value');
            event.data.container.autocomplete_index = 0;
        } else {
            if (event.keyCode === 39) { event.data.container.autocomplete_index += 1; }
            if (event.keyCode === 37) { event.data.container.autocomplete_index -= 1; }
        }
        docparser = new DOMParser();
        xml = docparser.parseFromString(event.data.container.xml_string, "text/xml");
        res = xml.evaluate(event.data.args[0].split("'")[1].replace('$', '"' + event.data.container.autocomplete_root + '"'), xml, null,
            XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
        // take modulus of index to reference hits, insert them into field
        if (res.snapshotLength > 1) {
            $(event.target).attr('value', $(res.snapshotItem(
                event.data.container.autocomplete_index - Math.floor(
                    event.data.container.autocomplete_index / res.snapshotLength
                ) * res.snapshotLength
            )).text());
        } else { $(event.target).attr('value', $(res.snapshotItem(0)).text()); }
    }
    this.autocomplete = autocomplete;

    function addElement_update_editor(e) {
        var docparser, xml, elm, allelm, i, subelmlist;
        docparser = new DOMParser();
        xml = docparser.parseFromString(e.target_params["editor"].xml_string, "text/xml");
        elm = e.target_params["editor"].event_get_elm(e.target_params["root_event"], xml);
//        newelm = e.target_params["add_type"];
//        allelm = e.target_params["editor"].xsdobj.getElementsByTagName('complexType');
//        i = 0;
//        while ((i < allelm.length) && ((allelm[i]).attributes.getNamedItem("name").nodeValue != newelm.attributes.getNamedItem("name").nodeValue)) { i++; };
//        subelmlist = allelm[i].getElementsByTagName('element');
//        newelm = e.target_params["editor"].xsdobj.createElement(newelm.attributes.getNamedItem("name").nodeValue);
//        for (i = 0; i < subelmlist.length; i++) {newelm.insertBefore(e.target_params["editor"].xsdobj.createElement(subelmlist[i].attributes.getNamedItem("name").nodeValue),newelm.firstChild); };
        newelm = e.target_params["editor"].build_empty_element(e.target_params["add_type"].attributes.getNamedItem("name").nodeValue);
        elm.insertBefore(newelm, elm.firstChild);
        e.target_params["editor"].xml_string = xmltoString(xml);
        e.target_params["editor"].update_editor();
    }
    this.addElement_update_editor = addElement_update_editor;

    function build_empty_element(tagname) {
        var docparser, newelm, i, subelmlist, j;
        if (!this.xsdobj) {
            docparser = new DOMParser();
            this.xsdobj = docparser.parseFromString(this.xsd_string, "text/xml");
            };
        if (!this.xsdelms) { this.xsdelms = this.xsdobj.getElementsByTagName('complexType'); };
        newelm = this.xsdobj.createElement(tagname); // creates newelm
        i = 0; // start searching for its xsd schema entry
        while ((i < this.xsdelms.length) && ((this.xsdelms[i]).attributes.getNamedItem("name").nodeValue != tagname)) { i++; };
        if (i == this.xsdelms.length) {return newelm;};
        subelmlist = this.xsdelms[i].getElementsByTagName('element');  // gets default subelements
        if (subelmlist.length == 0) {return newelm;};
        for (j = 0; j < subelmlist.length; j++) {
            if (subelmlist[j].attributes.getNamedItem("name").nodeValue != tagname) { // avoids infinite recursion on self-appending
                if (subelmlist[j].hasAttribute("minOccurs") && (subelmlist[j].attributes.getNamedItem("minOccurs").nodeValue > 0)) { // only populates necessary children
                    newelm.insertBefore(this.build_empty_element(subelmlist[j].attributes.getNamedItem("name").nodeValue), newelm.firstChild);
                };
            }
        };
        return newelm;
    }
    this.build_empty_element = build_empty_element;

    function modifyElement_update_editor(event) {
		var docparser, xml, elm;
        docparser = new DOMParser();
        xml = docparser.parseFromString(event.data.container.xml_string, "text/xml");
        elm = event.data.container.event_get_elm(event, xml);  //(Unordered_node_iterator_type)
        if (event.data.args[0] === "'delete'") {
            elm.parentElement.removeChild(elm);
        } else if (event.data.args[0] === "'move','+1'") {
            elm.parentElement.insertBefore(elm.cloneNode(true),better_sibling(elm,'previous'));
			elm.parentElement.removeChild(elm);
        } else if (event.data.args[0] === "'move','-1'") {
            elm.parentElement.insertBefore(elm.cloneNode(true),better_sibling(better_sibling(elm,'next'),'next'));
			elm.parentElement.removeChild(elm);
        } else if (event.data.args[0] === "'clone'") {
            elm.parentElement.insertBefore(elm.cloneNode(true),elm);
        } else if (event.data.args[0] === "'add'") {
            alert("into");
            elm.parentElement.insertBefore(elm.cloneNode(true), elm);
        }
        event.data.container.xml_string = xmltoString(xml);
        event.data.container.update_editor();
    }
    this.modifyElement_update_editor = modifyElement_update_editor;

	function better_sibling(elem,direction) {
		var sib;
		if (direction === 'previous') {
			sib=elem.previousSibling;
			while (sib.nodeType!=1){
				sib=sib.previousSibling;
			}
			return sib;
		}
		if (direction === 'next') {
			sib=elem.nextSibling;
			while (sib.nodeType!=1){
				sib=sib.nextSibling;
			}
			return sib;
		}
	}
	this.better_sibling = better_sibling;

    function unbind_events() {
        $('#hdiode_xml_tree_treediv *').unbind();
		return;
	}
	this.unbind_events = unbind_events;

    function bind_events() {
        // this searches the html tree looking for xtsm_viewer_event attributes 
        // their value should be of the form 
        // eventType:handlerFunctionName(arg1,arg2...)
        // it then attaches the handler (should be a method of this object) 
        // to the HTML event
        var bind_targets, next_target, eventtype, handler_name, handler_args,
            that, thisevent, allevents, j;
        bind_targets = document.evaluate('//*[@xtsm_viewer_event]', document, null,
            XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null);
        next_target = bind_targets.iterateNext();
        while (next_target) {
            // this parses the event type and handler function 
            // from the xtsm_viewer_event attribute
            // multiple events should be split by semicolons
            //var thisevent=next_target.getAttribute('xtsm_viewer_event').split(';')[0];
            allevents = next_target.getAttribute('xtsm_viewer_event').split(';');
            for (j = 0; j < allevents.length - 1; j++) {
                thisevent = allevents[j];
                eventtype = thisevent.split(':')[0];
                if (eventtype.substr(0, 2) === 'on') {
                    eventtype = eventtype.substr(2);
                }
                handler_name = thisevent.
                    split(':')[1].split('(')[0];
                handler_args = thisevent.
                    split(':')[1];
                handler_args = handler_args.substring(handler_args.indexOf("(") + 1);
                handler_args = handler_args.substring(0, handler_args.lastIndexOf(")")).match(/(?!;| |$)([^";]*"[^"]*")*([^";]*[^ ";])?/g); //split(',');
//                if (handler_name === "autocomplete") {alert(handler_args ); }
                if (typeof this[handler_name] === 'function') {
                    //this[handler_name].apply(this, handler_args);
                    //this line does the event-binding
                    that = this;
                    $(next_target).on(eventtype, null,
                        { container: this, args: handler_args }, this[handler_name]);
                }
            }
            next_target = bind_targets.iterateNext();
        }
    }
    this.bind_events = bind_events;

    function update_editor() {
        var newxmlstringlines, origxmllines, j, linemarker;
		if (this.cm_expand===false) {this.refresh_tree();  return;}
		//This helps us identify the changed line in the XML code to highlight it in the editor window
		newxmlstringlines=this.xml_string.split('\n');
		origxmllines=this.editor.getValue().split('\n');
		//this changes editor content
		this.editor.setValue(this.xml_string);
		//This loop identifies the first changed line in the XML code
		for(j=0;j<origxmllines.length; j++ ) {
			if (origxmllines[j] != newxmlstringlines[j]) {
				break;
				}
			}
		//This marks the gutter
		linemarker=this.editor.setGutterMarker(j,"note-gutter",document.createTextNode('-c->'));
		this.editor.setCursor(j,0);
		//This line pinks-out the background of line in editor
		this.editor.markText({ line: j, ch: 0 }, { line: j, ch: 1000 }, { className: "CodeMirror-matchhighlight2" });
		this.shotnumber_lockdown(true);
        return;
	}
    this.update_editor = update_editor;

    function load_file(filename, target) {
        var thatt = this;
        $.get(filename, function (source) {
            if (target === 'xml_string') {
                thatt.xml_string = source;
                thatt.update_editor();
                thatt.refresh_tree();
                return source;
            }
            if (target === 'xsl_string') {
                thatt.xsl_string = source;
                return source;
            }
            if (target === 'xsd_string') {
                thatt.xsd_string = source;
                return source;
            }
            if (filename.split(/\.xml|\.xtsm/).length > 1) {
                thatt.xml_string = source;
                thatt.update_editor();
                thatt.refresh_tree();
                return source;
            }
            if (filename.split(/\.xs|\.xsl/).length > 1) {
                thatt.xsl_string = source;
                return source;
            }
            if (filename.split(/\.xsd/).length > 1) {
                thatt.xsd_string = source;
                return source;
            }

        }, 'text');
    }
    this.load_file = load_file;

	function jump_links() {
		/*
		Search XTSM for matching elements. If found, creates a jump link between the two.
		Currently links: Channel to Timing Group, Edge/Interval to Channel.
		*/
		var tree, divs, i, children, j, parser2, xmlDoc2, value, name, search_result;

		// Create new DOM object and use it to parse XTSM from arg.
		parser2 = new DOMParser();
		xmlDoc2 = parser2.parseFromString(this.xml_string, "text/xml");
		// Find searchable fields and search document for other instances.
		tree = document.getElementsByClassName('hdiode_xml_tree_treediv')[0];
		divs = tree.getElementsByTagName('div');
		for (i = 0; i < divs.length; i++) {
			children = divs[i].children;
			for (j = 0; j < children.length; j++) {
				if (children[j].nodeName === 'INPUT' && children[j].value !== 'on') {
					// Get relevant value we want to search for.
					value = children[j].value;
					// Get field name, so that we know if we want to search and whether this the element to link to, or link from.
					alert(value);
					alert(children[j].parentNode.textContent);  // GOT THIS FAR ---> Gets correct input field value, gets parent's text which includes all text on same line, not just text for this field.
					alert(divs[i].textContent);  // Duplicate of the previous line.
				}
			}
		}
		//Search the XTSM for the value of termfield.
		//search_result = xmlDoc2.evaluate("//*[text()[contains(.,'" + termfield.value + "')]]", xmlDoc2, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE, null);
	}
	this.jump_links = jump_links;

	function add_to_history(xml_string) {
		/*Adds an element to the history array.
		If undo/redo triggers this, this.keep_hlevel will be true. This stores the most recent history into a buffer.
		If not triggered by undo/redo, the.keep_hlevel will be false. This resets the history_level index and,
			if the buffer is storing an xml string, places it before the next change. It then sets the buffer as an empty string.
		In either case, the change which triggered this function will then be added onto the end of the history array.
		Finally, the history array is shortened (via FIFO) to the max size value.
		*/
		//Checks whether or not this was triggered by undo/redo buttons.
		if (this.keep_hlevel === false) {
			//If not, check if buffer contains the empty string. If not, get buffer value, reset buffer, and reset history level.
			if (this.history_buffer !== '') {
				this.history.push(this.history_buffer);
				this.history_buffer = '';
				this.history_level = 0;
				//Disable redo, since we've now stopped messing with history, and enable undo (in case it was disabled).
				toggle_button("undo", false);
				toggle_button("redo", true);
			}
		} else if (this.keep_hlevel !== true) {
			alert(this.keep_hlevel);
		} else {
			this.history_buffer = xml_string;
		}
		//Add a new element to the end of the history array.
		this.history.push(xml_string);
		//If the history array is now longer than the specified history size, remove the first element.
		while (this.history.length > this.history_max_size) {
			this.history.shift();
		}
	}
	this.add_to_history = add_to_history;

    this.xml_string = sources.xml_string;
    this.xsl_string = sources.xsl_string;
    this.xsd_string = sources.xsd_string;

	this.cm_expand=true;

    if (html_div) { this.create_container(html_div); }

	this.history = [];
	this.history_max_size = document.getElementById('undo_levels').value;
	this.history_level = 0;
	this.keep_hlevel = false;
	this.history_buffer = '';

	var that;
    that = this;
    if (this.textarea) {this.create_cm(this.textarea);}
    this.editor.setGutterMarker(0, "note-gutter", document.createTextNode("start>"));

    return this;


}

function Hdiode_file_ops(html_div) {
// This object is a general-purpose file operation object 
	function create_container(html_div) {
		this.html_div_title = html_div.appendChild(document.createElement('div'));
		this.html_div_title.setAttribute("class", "hdiode_fileops_titlediv");
		this.expand_control=this.html_div_title.appendChild(document.createElement('img'));
		this.expand_control.setAttribute("src","images/RightFillTriangleIcon.png");
		this.expand_control.setAttribute("height","15px");
        this.html_div_title.appendChild(document.
            createElement('span')).appendChild(document.createTextNode('File Operations'));
	}
	this.create_container = create_container;

	if (html_div) { this.create_container(html_div); }
	return this;

}

function Hdiode_undo(html_div) {
// This object is a general-purpose file operation object 
	function create_container(html_div) {
		this.html_div_title = html_div.appendChild(document.createElement('div'));
		this.html_div_title.setAttribute("class", "hdiode_fileops_titlediv");
		this.expand_control=this.html_div_title.appendChild(document.createElement('img'));
		this.expand_control.setAttribute("src","images/RightFillTriangleIcon.png");
		this.expand_control.setAttribute("height","15px");
        this.html_div_title.appendChild(document.
            createElement('span')).appendChild(document.createTextNode('History / Undo'));
	}
	this.create_container = create_container;

	if (html_div) { this.create_container(html_div); }
	return this;

}

arg = 1;  // expose editor at base level

function main() {
	"use strict";
	/*
	Responsible for all functionality of the GUI:
		Creates a new Hdiode code tree.
		Houses function calls for html elements' dynamic functions.
	*/

	//Creates new hdiode tree
	//var arg;
	arg = new Hdiode_code_tree(document.getElementById('Create_Tree'), {xml_string: '<none>', xsl_string: '<none>', xsd_string: '<none>'});
	arg.load_file("transforms/default.xsl", 'xsl_string');
	arg.load_file("default.xtsm", 'xml_string');
	arg.load_file("transforms/default.xsd", 'xsd_string');
	
	/*Controls html page elements outside of the code tree*/

	//Server Push
	document.getElementById("server_push_menu").onclick = function () { toggle_menu("server_push_menu", "server_push_output_div"); };
	// websocketize(document.getElementById("server_push_output_div"));
	var ta = document.getElementById("server_push_output_div").appendChild(document.createElement("textarea"));
	ta.id = "server_push_output_textarea";
    textarea_console(ta,arg);

	//File Operations
	document.getElementById("file_menu").onclick = function () {toggle_menu("file_menu", "file_operations"); };
	document.getElementById("file_type").onchange = function () {populate_folders(); document.getElementById('save_file').value = default_save_name(); };
	document.getElementById("load").onclick = function () {load_new_file(arg); };
	document.getElementById("save_file").defaultValue = default_save_name();
	document.getElementById("save").onclick = function () {save_file(arg); };
	document.getElementById("refresh").onclick = function () {refresh(arg); };
	document.getElementById("refresh").onload = function () {populate_folders(); };
	//Parser
	document.getElementById("parser_menu").onclick = function () {toggle_menu("parser_menu", "parser_operations"); };
	document.getElementById("parse_preview_button").onclick = function () {parse_preview(arg); }; //DNWY [Does Not Work Yet]
	//document.getElementById("post_xtsm_button").onclick = function () {post_active_xtsm(arg); };
	document.getElementById("post_xtsm_button").onclick = function () {ws_function.commandLibrary.post_active_xtsm_ws(arg); };//CP 2014-10-28
	document.getElementById("retrieve_xtsm_button").onclick = function () {retrieve_active_xtsm(arg); };
	document.getElementById("pxi_dc").onfocus = function () {document.getElementById("pxi_dc").value = ''; }; //Clears text field upon focus.
	document.getElementById("disable_python_socket_button").onclick = function () {disable_python_socket(); };
	document.getElementById("launch_python_button").onclick = function () {launch_python(); };
	document.getElementById("test_pythontransferspeed_button").onclick = function () {test_pythontransferspeed(); };
	//Python Console
	document.getElementById("python_menu").onclick = function () {toggle_menu("python_menu", "python_operations"); };
	document.getElementById("python_submit_code_button").onclick = function () {execute_python(); };
	document.getElementById("data_contexts_button").onclick = function () {get_data_contexts(); };
	//Plot Console
	document.getElementById("plot_menu").onclick = function () {toggle_menu("plot_menu", "plot_operations"); };
	document.getElementById("remove_plot").onclick = function () {destroy_analysis_plots(1); };
	document.getElementById("add_plot").onclick = function () {build_analysis_plots(1); };
	//History
	document.getElementById("history_menu").onclick = function () {toggle_menu("history_menu", "history_operations"); };
	document.getElementById("undo").onclick = function () {undo(arg); };
	document.getElementById("redo").onclick = function () {redo(arg); };
	document.getElementById("undo_levels").onchange = function () {arg.history_max_size = document.getElementById("undo_levels").value; }; //Sets the history buffer size to this field's value.
	//Display and Help
	document.getElementById("display_menu").onclick = function () {toggle_menu("display_menu", "display_operations"); };
	document.getElementById("light_dark_button").onclick = function () {change_color_scheme(); };
	document.getElementById("show_help").onclick = function () {toggle_help(); };
	document.getElementById("font_type").onblur = function () {change_font(true, false, document.getElementById('font_type').value); };
	document.getElementById("font_size").onblur = function () {change_font(false, true, document.getElementById('font_size').value); };
	//Search Tools
	document.getElementById("search_menu").onclick = function () {toggle_menu("search_menu", "search_operations"); };
	document.getElementById("search_input").onfocus = function () {document.getElementById("search_input").value = ''; }; //Clears text field upon focus.
	document.getElementById("search_input").onchange = function () { search_dom(document.getElementById("search_input"), arg); };

	document.onkeyup = arg.keyboard_shorts;
}
