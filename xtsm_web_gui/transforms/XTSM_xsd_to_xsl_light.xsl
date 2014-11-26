<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xtsm_viewer="http://braid.phys.psu.edu/xtsm_viewer" exclude-result-prefixes="xs xsl xtsm_viewer">
	<xsl:output method="xml" indent="yes" encoding="utf-8" omit-xml-declaration="no" />

    <!-- Remove annotations -->
    <xsl:template match="xs:annotation" />

    <!-- Find non-terminal nodes -->
    <xsl:template match="*[count(./*/xs:element)>0]" >
      <xsl:element name="xsl:template"><xsl:attribute name="match"><xsl:value-of select="./@name"/></xsl:attribute>
        <li>
          <div>
            <!--topline expand arrow, disable checkbox, lock icon, element-name are in preamble template-->
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">topline_preamble</xsl:attribute>
            </xsl:element>
            <!--this outputs a 'tab'-->
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">repeat</xsl:attribute>
              <xsl:element name="xsl:with-param">
                <xsl:attribute name="name">count</xsl:attribute>
                <xsl:attribute name="select">20- string-length(name(.))</xsl:attribute>
              </xsl:element>
              <xsl:element name="xsl:with-param" >
                <xsl:attribute name="name">output</xsl:attribute>
                <xsl:text>.</xsl:text>
              </xsl:element>
            </xsl:element>
            <!--generate a list of topline elements, create a for-each with these or'd, call a input-maker routine-->
            <xsl:if test="count(./xs:sequence/xs:element/xs:annotation/xs:appinfo/xtsm_viewer:topline | ./xs:all/xs:element/xs:annotation/xs:appinfo/xtsm_viewer:topline)>0">
              <xsl:element name="xsl:for-each">
                  <xsl:attribute name="select">
                    <xsl:for-each select="./xs:sequence/xs:element/xs:annotation/xs:appinfo/xtsm_viewer:topline | ./xs:all/xs:element/xs:annotation/xs:appinfo/xtsm_viewer:topline">
                      <xsl:value-of select="../../../@name"/>
                      <xsl:if test="position() != last()">
                        <xsl:text> | </xsl:text>
                      </xsl:if>
                    </xsl:for-each>
                  </xsl:attribute>
                  <xsl:element name="xsl:call-template">
                    <xsl:attribute name="name">
                      <xsl:text>gen_input_field</xsl:text>
                    </xsl:attribute>
                  </xsl:element>
              </xsl:element>
            </xsl:if>            
            <!--Right-side, topline buttons -->
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">toolpanel</xsl:attribute>
            </xsl:element>
          </div>
          <!-- CHILD DIVISION OUTPUT -->
          <div>
            <xsl:element name="xsl:choose">
              <xsl:element name="xsl:when">
                <xsl:attribute name="test">
                  <xsl:text>@expanded='1'</xsl:text>
                </xsl:attribute>
                <!--BROKE BELOW OUT TO child_div template-->
                <xsl:element name="xsl:call-template">
                  <xsl:attribute name="name">child_div</xsl:attribute>
                </xsl:element>
                <!--BROKE ABOVE OUT TO child_div template-->
              </xsl:element>
              <xsl:element name="xsl:otherwise">
              </xsl:element>
            </xsl:element>
          </div>
        </li>
      </xsl:element>
    </xsl:template>

    <!-- Find terminal nodes, create a specific template to match node name -->
	<xsl:template match="xs:complexType[count(.//xs:element)=0]" >
		<xsl:element name="xsl:template">
      <xsl:attribute name="match"><xsl:value-of select="@name"/></xsl:attribute>
		  <li><div>          
        <xsl:element name="xsl:attribute"><xsl:attribute name="name"><xsl:text>gen_id</xsl:text></xsl:attribute><xsl:element name="xsl:call-template"><xsl:attribute name="name"><xsl:text>treeid</xsl:text></xsl:attribute></xsl:element></xsl:element>
			  <input type="checkbox">
				  <xsl:element name="xsl:attribute">
					  <xsl:attribute name="name">xtsm_viewer_event</xsl:attribute>
					  <xsl:text>onclick:toggleProp_update_editor('disable');</xsl:text>
				  </xsl:element>
          <xsl:element name="xsl:if">
            <xsl:attribute name="test">not(@disable) or @disable!='1'</xsl:attribute>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>checked</xsl:text>
              </xsl:attribute>
              <xsl:text>checked</xsl:text>
            </xsl:element>
          </xsl:element>
        </input>
        <xsl:element name="xsl:call-template">
          <xsl:attribute name="name"><xsl:text>gen_input_field</xsl:text></xsl:attribute>
        </xsl:element>
        <xsl:element name="xsl:call-template">
          <xsl:attribute name="name">
            <xsl:text>toolpanel</xsl:text>
          </xsl:attribute>
        </xsl:element>
		  </div></li>
    </xsl:element>
  </xsl:template>
    
    <xsl:template match="/">
      <xsl:element name="xsl:stylesheet">
        <!--THIS IS DOCUMENT HEADER INFO-->
        <xsl:attribute name="version">
          <xsl:text>1.0</xsl:text>
        </xsl:attribute>
        <xsl:attribute name="exclude-result-prefixes">
          <xsl:text>xs xsl xtsm_viewer</xsl:text>
        </xsl:attribute>
        <xsl:element name="xsl:output">
          <xsl:attribute name="omit-xml-declaration">
            <xsl:text>yes</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="indent">
            <xsl:text>yes</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="encoding">
            <xsl:text>UTF-8</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="method">
            <xsl:text>xml</xsl:text>
          </xsl:attribute>
        </xsl:element>

        <!--THIS GENERATES THE ICONS ON THE FAR_RIGHT OF EACH ELEMENT-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="name">
            <xsl:text>toolpanel</xsl:text>
          </xsl:attribute>
          <img src="images/seqicon_uparrow.png" height="15px" align="right" alt="⇑" xtsm_viewer_event="onclick:modifyElement_update_editor('move','+1');"/>
          <img src="images/seqicon_downarrow.png" height="15px" align="right" alt="⇓" xtsm_viewer_event="onclick:modifyElement_update_editor('move','-1');"/>
          <img src="images/seqicon_clone.png" height="15px" align="right" alt="c" xtsm_viewer_event="onclick:modifyElement_update_editor('clone');"/>
          <img src="images/seqicon_x.png" height="15px" align="right" alt="X" xtsm_viewer_event="onclick:modifyElement_update_editor('delete');"/>
          <img src="images/seqicon_code.png" height="15px" align="right" alt="&lt;..&gt;" xtsm_viewer_event="onclick:toggleProp_update_editor('editMode');"/>
          <img src="images/seqicon_plus.png" height="15px" align="right" alt="+" xtsm_viewer_event="onclick:spawn_child_menu();"/>
        </xsl:element>

        <!--THIS PUTS OUT A CERTAIN CHARACTER N TIMES (FOR USE IN TABS)-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="name">
            <xsl:text>repeat</xsl:text>
          </xsl:attribute>
          <xsl:element name="xsl:param">
            <xsl:attribute name="name">
              <xsl:text>output</xsl:text>
            </xsl:attribute>
          </xsl:element>
          <xsl:element name="xsl:param">
            <xsl:attribute name="name">
              <xsl:text>count</xsl:text>
            </xsl:attribute>
          </xsl:element>
          <xsl:element name="xsl:value-of">
            <xsl:attribute name="select">$output</xsl:attribute>
          </xsl:element>
          <xsl:element name="xsl:if">
            <xsl:attribute name="test">$count &gt; 1</xsl:attribute>
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">
                <xsl:text>repeat</xsl:text>
              </xsl:attribute>
              <xsl:element name="xsl:with-param">
                <xsl:attribute name="name">
                  <xsl:text>output</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="select">
                  <xsl:text>$output</xsl:text>
                </xsl:attribute>
              </xsl:element>
              <xsl:element name="xsl:with-param">
                <xsl:attribute name="name">
                  <xsl:text>count</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="select">
                  <xsl:text>$count - 1</xsl:text>
                </xsl:attribute>
              </xsl:element>
            </xsl:element>
          </xsl:element>
        </xsl:element>

        <!--THIS GENERATES BREADCRUMB NAMES LINKING HTML ELEMENTS TO THEIR GENERATING XML-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="name">
            <xsl:text>treeid</xsl:text>
          </xsl:attribute>
          <xsl:text>divtree</xsl:text>
          <xsl:element name="xsl:for-each">
            <xsl:attribute name="select">
              <xsl:text>ancestor-or-self::*</xsl:text>
            </xsl:attribute>
            <xsl:text>__</xsl:text>
            <xsl:element name="xsl:value-of">
              <xsl:attribute name="select">
                <xsl:text>name()</xsl:text>
              </xsl:attribute>
            </xsl:element>
            <xsl:text>_</xsl:text>
            <xsl:element name="xsl:value-of">
              <xsl:attribute name="select">
                <xsl:text>count(preceding-sibling::*[name(.) = name(current())])+1</xsl:text>
              </xsl:attribute>
            </xsl:element>
          </xsl:element>
        </xsl:element>

        <!--THIS IS THE TEMPLATE THAT GENERATES THE DOCUMENT ROOT OF THE HTML OUTPUT-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="match">
            <xsl:text>/XTSM</xsl:text>
          </xsl:attribute>
          <xsl:element name="ul">
            <xsl:element name="xsl:apply-templates" />
          </xsl:element>
        </xsl:element>

        <!--THIS IS THE TOPLINE PREAMBLE TEMPLATE-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="name">
            <xsl:text>topline_preamble</xsl:text>
          </xsl:attribute>
          <xsl:element name="xsl:attribute">
            <xsl:attribute name="name">
              <xsl:text>gen_id</xsl:text>
            </xsl:attribute>
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">
                <xsl:text>treeid</xsl:text>
              </xsl:attribute>
            </xsl:element>
            <xsl:element name="xsl:text">
              <xsl:text>__</xsl:text>
            </xsl:element>
          </xsl:element>
          <xsl:element name="xsl:attribute">
            <xsl:attribute name="name">
              <xsl:text>class</xsl:text>
            </xsl:attribute>
            <xsl:text>xtsm_</xsl:text>
            <xsl:element name="xsl:value-of">
              <xsl:attribute name="select">
                <xsl:text>name()</xsl:text>
              </xsl:attribute>
            </xsl:element>
            <xsl:text>_head</xsl:text>
          </xsl:element>
          <img height="15px">
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>src</xsl:text>
              </xsl:attribute>
              <xsl:element name="xsl:choose">
                <xsl:element name="xsl:when">
                  <xsl:attribute name="test">
                    <xsl:text>@expanded='1'</xsl:text>
                  </xsl:attribute>
                  <xsl:text>images/DownTriangleIcon.png</xsl:text>
                </xsl:element>
                <xsl:element name="xsl:otherwise">
                  <xsl:text>images/RightFillTriangleIcon.png</xsl:text>
                </xsl:element>
              </xsl:element>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>xtsm_viewer_event</xsl:text>
              </xsl:attribute>
              <xsl:text>onclick:toggleProp_update_editor('expanded');</xsl:text>
            </xsl:element>
          </img>
          <input type="checkbox">
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>xtsm_viewer_event</xsl:text>
              </xsl:attribute>
              <xsl:text>onclick:toggleProp_update_editor('disable');</xsl:text>
            </xsl:element>
            <xsl:element name="xsl:if">
              <xsl:attribute name="test">not(@disable) or @disable!='1'</xsl:attribute>
              <xsl:element name="xsl:attribute">
                <xsl:attribute name="name">
                  <xsl:text>checked</xsl:text>
                </xsl:attribute>
                <xsl:text>checked</xsl:text>
              </xsl:element>
            </xsl:element>
          </input>
          <img height="15px">
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>xtsm_viewer_event</xsl:text>
              </xsl:attribute>
              <xsl:text>onclick:toggleProp_update_editor('lock');</xsl:text>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>src</xsl:text>
              </xsl:attribute>
              <xsl:element name="xsl:choose">
                <xsl:element name="xsl:when">
                  <xsl:attribute name="test">
                    <xsl:text>@lock='1'</xsl:text>
                  </xsl:attribute>
                  <xsl:text>images/seqicon_lock.png</xsl:text>
                </xsl:element>
                <xsl:element name="xsl:otherwise">
                  <xsl:text>images/seqicon_unlock.png</xsl:text>
                </xsl:element>
              </xsl:element>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>alt</xsl:text>
              </xsl:attribute>
              <xsl:text>☠</xsl:text>
            </xsl:element>
          </img>
          <xsl:element name="xsl:value-of">
            <xsl:attribute name="select">
              <xsl:text>name()</xsl:text>
            </xsl:attribute>
          </xsl:element>
          <xsl:text>:</xsl:text>
        </xsl:element>

        <!--THIS CREATES INPUT FIELDS FOR TERMINAL AND TOPLINE ELEMENTS-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="name">
            <xsl:text>gen_input_field</xsl:text>
          </xsl:attribute>
          <xsl:element name="xsl:value-of">
            <xsl:attribute name="select">name()</xsl:attribute>
          </xsl:element>
          <xsl:text>:</xsl:text>
          <xsl:element name="xsl:call-template">
            <xsl:attribute name="name">repeat</xsl:attribute>
            <xsl:element name="xsl:with-param">
              <xsl:attribute name="name">count</xsl:attribute>
              <xsl:attribute name="select">20- string-length(name(.))</xsl:attribute>
            </xsl:element>
            <xsl:element name="xsl:with-param" >
              <xsl:attribute name="name">output</xsl:attribute>
              <xsl:text>.</xsl:text>
            </xsl:element>
          </xsl:element>
          <input>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>value</xsl:text>
              </xsl:attribute>
              <xsl:element name="xsl:value-of">
                <xsl:attribute name="select">
                  <xsl:text>child::node()</xsl:text>
                </xsl:attribute>
              </xsl:element>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>title</xsl:text>
              </xsl:attribute>
              <xsl:element name="xsl:value-of">
                <xsl:attribute name="select">
                  <xsl:text>concat("parsed-to:      ",@current_value)</xsl:text>
                </xsl:attribute>
              </xsl:element>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>name</xsl:text>
              </xsl:attribute>
              <xsl:element name="xsl:value-of">
                <xsl:attribute name="select">
                  <xsl:text>name()</xsl:text>
                </xsl:attribute>
              </xsl:element>
              <xsl:text>_</xsl:text>
              <xsl:element name="xsl:value-of">
                <xsl:attribute name="select">
                  <xsl:text>count(preceding-sibling::*[name(.) = name(current())])+1</xsl:text>
                </xsl:attribute>
              </xsl:element>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>xtsm_viewer_event</xsl:text></xsl:attribute><xsl:text>onblur:updateElement_update_editor('');</xsl:text><xsl:for-each select="/*//xtsm_viewer:autocomplete/../../.."><xsl:element name="xsl:if"><xsl:attribute name="test">name()='<xsl:value-of select="@name"/>'</xsl:attribute><xsl:text>onkeydown:autocomplete('</xsl:text><xsl:value-of select=".//xtsm_viewer:autocomplete/@value"/><xsl:text>');</xsl:text></xsl:element></xsl:for-each>
            </xsl:element>
            <xsl:element name="xsl:attribute">
              <xsl:attribute name="name">
                <xsl:text>size</xsl:text>
              </xsl:attribute>
              <xsl:text>25</xsl:text>
            </xsl:element>
        </input>
        <xsl:element name="xsl:if">
          <xsl:attribute name="test">
            <xsl:text>@editmode='html' or @editmode='tohtml'</xsl:text>
          </xsl:attribute>
          <img src="images/seqicon_translate.png" height="20px" />
        </xsl:element>
      </xsl:element>

        <!--template for child division contents-->
        <xsl:element name="xsl:template">
          <xsl:attribute name="name"><xsl:text>child_div</xsl:text></xsl:attribute>
        <xsl:element name="xsl:attribute">
          <xsl:attribute name="name"><xsl:text>gen_id</xsl:text></xsl:attribute>
          <xsl:text>divtree</xsl:text>
          <xsl:element name="xsl:for-each">
            <xsl:attribute name="select"><xsl:text>ancestor-or-self::*</xsl:text></xsl:attribute>
            <xsl:text>__</xsl:text>
            <xsl:element name="xsl:value-of">
              <xsl:attribute name="select"><xsl:text>name()</xsl:text></xsl:attribute>
            </xsl:element>
            <xsl:text>_</xsl:text>
            <xsl:element name="xsl:value-of">
              <xsl:attribute name="select"><xsl:text>count(preceding-sibling::*[name(.) = name(current())])+1</xsl:text></xsl:attribute>
            </xsl:element>
          </xsl:element>
        </xsl:element>
        <xsl:element name="xsl:attribute"><xsl:attribute name="name"><xsl:text>class</xsl:text></xsl:attribute><xsl:text>xtsm_</xsl:text><xsl:element name="xsl:value-of"><xsl:attribute name="select"><xsl:text>name()</xsl:text></xsl:attribute></xsl:element><xsl:text>_body</xsl:text></xsl:element>
        <xsl:element name="xsl:attribute">
          <xsl:attribute name="name"><xsl:text>style</xsl:text></xsl:attribute>
          <xsl:text>display:</xsl:text>
          <xsl:element name="xsl:choose">
            <xsl:element name="xsl:when">
              <xsl:attribute name="test"><xsl:text>@expanded='1'</xsl:text></xsl:attribute>
              <xsl:text>block</xsl:text>
            </xsl:element>
            <xsl:element name="xsl:otherwise">
              <xsl:text>none</xsl:text>
            </xsl:element>
          </xsl:element>
          <xsl:text>;</xsl:text>
        </xsl:element>
          <xsl:element name="xsl:if">
            <xsl:attribute name="test">
              <xsl:text>name()='Figure'</xsl:text>
            </xsl:attribute>
            <div>
              <xsl:element name="xsl:attribute">
                <xsl:attribute name="name">content_id</xsl:attribute>
                <xsl:element name="xsl:value-of">
                  <xsl:attribute name="select">@content_id</xsl:attribute>
                </xsl:element>
              </xsl:element>
              <img  src="images/seqicon_null.jpg" height="15px">
                <xsl:element name="xsl:attribute">
                  <xsl:attribute name="name">xtsm_viewer_event</xsl:attribute>
                  <xsl:text>onload:load_livedata('</xsl:text>
                  <xsl:element name="xsl:value-of">
                    <xsl:attribute name="select">@content_id</xsl:attribute>
                  </xsl:element>
                  <xsl:text>');</xsl:text>
                </xsl:element>
              </img>
            </div>
          </xsl:element>
        <ul>
          <xsl:element name="xsl:choose">
            <xsl:element name="xsl:when">
              <xsl:attribute name="test"><xsl:text>@editmode='codemirror'</xsl:text></xsl:attribute>
              <li>
                <textarea cols="80" rows="10">
                  <xsl:element name="xsl:copy-of">
                    <xsl:attribute name="select"><xsl:text>.</xsl:text></xsl:attribute>
                  </xsl:element>
                </textarea>
              </li>
            </xsl:element>
            <xsl:element name="xsl:otherwise">
              <xsl:element name="xsl:apply-templates">
                <xsl:attribute name="select"><xsl:text>child::node()</xsl:text></xsl:attribute>
              </xsl:element>
            </xsl:element>
          </xsl:element>
        </ul>
      </xsl:element>
        
        <!-- Create default template for terminal nodes -->
        <xsl:element name="xsl:template">
          <xsl:attribute name="match">
            <xsl:text>*[not(*)]</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="priority">
            <xsl:text>-2</xsl:text>
          </xsl:attribute>
          <li>
           <div>
             <xsl:element name="xsl:attribute">
               <xsl:attribute name="name">
                 <xsl:text>gen_id</xsl:text>
               </xsl:attribute>
               <xsl:element name="xsl:call-template">
                 <xsl:attribute name="name">
                   <xsl:text>treeid</xsl:text>
                 </xsl:attribute>
               </xsl:element>
             </xsl:element>
             <input type="checkbox">
              <xsl:element name="xsl:attribute">
                <xsl:attribute name="name">xtsm_viewer_event</xsl:attribute>
                <xsl:text>onclick:toggleProp_update_editor('disable');</xsl:text>
              </xsl:element>
              <xsl:element name="xsl:if">
                <xsl:attribute name="test">not(@disable) or @disable!='1'</xsl:attribute>
                <xsl:element name="xsl:attribute">
                  <xsl:attribute name="name">
                    <xsl:text>checked</xsl:text>
                  </xsl:attribute>
                  <xsl:text>checked</xsl:text>
                </xsl:element>
              </xsl:element>
            </input>
            <a title="Non-standard XTSM tag." style="background-color:yellow;">
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">
                <xsl:text>gen_input_field</xsl:text>
              </xsl:attribute>
            </xsl:element>
            </a>
            <xsl:element name="xsl:call-template">
              <xsl:attribute name="name">
                <xsl:text>toolpanel</xsl:text>
              </xsl:attribute>
            </xsl:element>
           </div>
          </li>
        </xsl:element>

        <!-- Create default template for non-terminal nodes -->
        <xsl:element name="xsl:template">
          <xsl:attribute name="match">
            <xsl:text>*[*]</xsl:text>
          </xsl:attribute>
          <xsl:attribute name="priority">
            <xsl:text>-2</xsl:text>
          </xsl:attribute>
          <li>
            <div>
              <!--topline expand arrow, disable checkbox, lock icon, element-name are in preamble template-->
              <xsl:element name="xsl:call-template">
                <xsl:attribute name="name">topline_preamble</xsl:attribute>
              </xsl:element>
              <a title="Nonstandard XTSM element as container" style="background-color:yellow;">
                <xsl:element name="xsl:text">(?)</xsl:element>
              </a>
              <!--this outputs a 'tab'-->
              <xsl:element name="xsl:call-template">
                <xsl:attribute name="name">repeat</xsl:attribute>
                <xsl:element name="xsl:with-param">
                  <xsl:attribute name="name">count</xsl:attribute>
                  <xsl:attribute name="select">20- string-length(name(.))</xsl:attribute>
                </xsl:element>
                <xsl:element name="xsl:with-param" >
                  <xsl:attribute name="name">output</xsl:attribute>
                  <xsl:text>.</xsl:text>
                </xsl:element>
              </xsl:element>
              <xsl:element name="xsl:call-template">
                <xsl:attribute name="name">toolpanel</xsl:attribute>
              </xsl:element>
            </div>
            <!-- CHILD DIVISION OUTPUT -->
            <div>
              <xsl:element name="xsl:call-template">
                <xsl:attribute name="name">child_div</xsl:attribute>
              </xsl:element>
            </div>
          </li>

        </xsl:element>


        <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>
    
</xsl:stylesheet>