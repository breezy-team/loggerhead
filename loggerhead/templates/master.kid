<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <meta py:replace="item[:]"/>
    <style type="text/css" media="screen">
@import "${tg.url('/static/css/style.css')}";
    </style>

<!-- !define common navbar -->
<span py:def="navbar()">
    <!-- !requires: ${navigation: start_revid, revid, revid_list, pagesize, buttons, scan_url}, ${branch}, ${history} -->
    <div class="navbar" py:if="navigation is not None">
        <div class="bar">
            <!-- form must go OUTSIDE the table, or safari will add extra padding :( -->
            <form action="${branch.url('/changes', start_revid=getattr(navigation, 'start_revid', None), file_id=getattr(navigation, 'file_id', None))}">
            <table>
                <tr><td>
                    <span class="buttons">
                        <!-- ! navbar buttons never change, from now on.  i decree it! -->
                        <a href="${branch.url('/changes')}"> changes </a>
                        <a href="${branch.url('/files')}"> files </a>
                        <span class="search"> search: <input type="text" name="q" /> </span>
                    </span>
                </td><td align="right" py:if="hasattr(navigation, 'revid_list')">
                    <span py:if="hasattr(navigation, 'feed')" class="rbuttons feed">
                        <a href="${branch.url('/atom')}"><img src="${tg.url('/static/images/feed-icon-16x16.gif')}" /></a>
                    </span>
                    <span class="navbuttons">
                    	<span py:if="navigation.prev_page_revid"> <a href="${navigation.prev_page_url}" title="Previous page"> &#171; </a>	</span>
                    	<span py:if="not navigation.prev_page_revid"> &#171; </span>
                        	revision ${history.get_revno(revid)} (<span py:if="navigation.pagesize > 1">page </span>${navigation.page_position} / ${navigation.page_count})
                    	<span py:if="navigation.next_page_revid"> <a href="${navigation.next_page_url}" title="Next page"> &#187; </a>	</span>
                    	<span py:if="not navigation.next_page_revid"> &#187; </span>
                    </span>
                </td></tr>
            </table>
            </form>
        </div>
    </div>
</span>

<span py:def="revlink(revid, start_revid, file_id, text)">
    <a title="Show revision ${history.get_revno(revid)}" href="${branch.url([ '/revision', revid ], start_revid=start_revid, file_id=file_id)}" class="revlink"> ${text} </a>
</span>
<span py:def="revlink_q(revid, start_revid, file_id, query, text)">
    <a title="Show revision ${history.get_revno(revid)}" href="${branch.url([ '/revision', revid ], start_revid=start_revid, file_id=file_id, q=query)}" class="revlink"> ${text} </a>
</span>

<span py:def="use_expand_buttons()">
	<!-- this is totally matty's fault.  i don't like javacsript. ;) -->
	<script type="text/javascript"> // <!--

	function getElementsByClass(name) {
	    var filter = function(node) {
	        // cannot filter here.  treeWalker will skip the entire subtree if you reject. :(
	        return NodeFilter.FILTER_ACCEPT;
	    };
	    var treeWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, { acceptNode: filter }, false);
	    
	    var ret = new Array();
	    while (treeWalker.nextNode()) {
	        var classes = treeWalker.currentNode.className.split(' ');
	        for (var i = 0; i < classes.length; i++) {
	            // is the string either identical, or startsWith?
	            if (classes[i].indexOf(name) == 0) { ret.push(treeWalker.currentNode); }
	        }
	    }
	    return ret;
	}

	function displayDetails(name, display) {
	    var dthide = 'inline', dtshow = 'none';
	    if (display == 'none') { dthide = 'none'; dtshow = 'inline'; }
	    document.getElementById('hide-' + name).style.display = dthide;
	    document.getElementById('show-' + name).style.display = dtshow;
	    var elem = document.getElementById('details-' + name);
	    if (elem) { elem.style.display = display; }
	    var nodes = getElementsByClass('details-' + name);
	    for (var i = 0; i < nodes.length; i++) {
	        nodes[i].style.display = display;
	    }
	}
	
	function contains(arr, item) { for (var i = 0; i < arr.length; i++) { if (arr[i] == item) { return true; } } return false; }
	
	function displayAll(display) {
	    var dthide = 'inline', dtshow = 'none';
	    if (display == 'none') { dthide = 'none'; dtshow = 'inline'; }
	    
	    var nodes = getElementsByClass('details-');
	    var names = new Array();
	    for (var i = 0; i < nodes.length; i++) {
	        nodes[i].style.display = display;
	        var classes = nodes[i].className.split(' ');
	        for (var j = 0; j < classes.length; j++) {
	            if (classes[j].indexOf('details-') == 0) {
	                var name = classes[j].substring(8);
	                if (! contains(names, name)) { names.push(name); }
	            }
	        }
	    }
	    for (var i = 0; i < names.length; i++) {
            document.getElementById('hide-' + names[i]).style.display = dthide;
            document.getElementById('show-' + names[i]).style.display = dtshow;
        }
	    document.getElementById('hide-all').style.display = dthide;
	    document.getElementById('show-all').style.display = dtshow;
	}
	// -->
	</script>
</span>

<span py:def="expand_all_button(normal='block')">
    <a class="hide-all" id="hide-all" href="javascript:displayAll('none')"> (collapse all) </a>
    <a class="hide-all" id="show-all" href="javascript:displayAll('${normal}')"> (expand all) </a>
</span>

<span py:def="expand_button(name, normal='block')">
    <a href="javascript:displayDetails('${name}', 'none')" id="hide-${name}" class="hide-button" title="collapse">
        <img src="${tg.url('/static/images/nav-small-down.gif')}" width="10" height="10" alt="collapse" />
    </a>
    <a href="javascript:displayDetails('${name}', '${normal}')" id="show-${name}" class="show-button" title="expand">
    	<img src="${tg.url('/static/images/nav-small-right.gif')}" witdh="10" height="10" alt="expand" />
    </a>
</span>

</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">

    <div py:replace="[item.text]+item[:]"/>

	<!-- End of main_content -->
	
	<div class="footer">
	    <span class="banner"><a href="http://www.bazaar-vcs.org/"><img src="${tg.url('/static/images/bazaar-banner.png')}" /></a></span>
	    <span class="banner"><a href="http://www.lag.net/loggerhead/"><img src="${tg.url('/static/images/loggerhead-banner.png')}" /></a></span>
	</div>
</body>

</html>
