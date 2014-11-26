// JavaScript Document
function toggleDiv(divid){
//Toggle the given division element open and closed
//Mark the expanded attribute of the corresponding element
    if(document.getElementById(divid).style.display == 'none'){
		newexpvalue='1';
      document.getElementById(divid).style.display = 'block';
    }else{
		newexpvalue='0';
      document.getElementById(divid).style.display = 'none';
    }
}

function toggleDiv_byElem(div){
//Toggle the given division element open and closed
//Mark the expanded attribute of the corresponding element
    if(div.style.display == 'none'){
		newexpvalue='1';
      div.style.display = 'block';
    }else{
		newexpvalue='0';
      div.style.display = 'none';
    }
}

function toggleDiv_byElem_flipIcon(div,img,icon1,icon2){
	toggleDiv_byElem(div);
	if (img.getAttribute('src')==icon1) img.setAttribute('src',icon2); else img.setAttribute('src',icon1);
	}

  function toggleDiv_update_editor(divid){
//Toggle the given division element open and closed
//Mark the expanded attribute of the corresponding element

    if(document.getElementById(divid).style.display == 'none'){
		newexpvalue='1';
      document.getElementById(divid).style.display = 'block';
    }else{
		newexpvalue='0';
      document.getElementById(divid).style.display = 'none';
    }
	//The rest of this code updates xml to reflect expanded state
		xmlDoc=get_xml_from_editor();
	//This parses the divid string input to find the appropriate field in the DOM object to change
		update_nodelist=divid.replace('divtree__','').split('__');
	//This loop builds the reference to the appropriate DOM object
		elem_to_modify=xmlDoc;
		for (j=0;j<update_nodelist.length;j++)
			{
			elem_to_modify=elem_to_modify.getElementsByTagName(update_nodelist[j].split('_')[0])[parseInt(update_nodelist[j].split('_')[1])-1];
			}
//This changes the value of the right node attribute in the DOM object...
		elem_to_modify.setAttribute("expanded",newexpvalue);	
//...and recreates the XML as text
		newxmlstring=XMLtoString(xmlDoc);
//This replaces the code in the editor window
		editor.setValue(newxmlstring);
		refreshtree();		
  }