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
<span py:def="navbar()" py:strip="True">
    <!-- !requires: ${navigation: start_revid, revid, revid_list, pagesize, buttons, scan_url}, ${branch}, ${history} -->
    <div class="navbar" py:if="navigation is not None"><div class="bar">
        <!-- form must go OUTSIDE the table, or safari will add extra padding :( -->
        <form action="${branch.url('/changes', start_revid=getattr(navigation, 'start_revid', None),
              file_id=getattr(navigation, 'file_id', None))}"><table><tr>
            <td><span class="buttons">
                <!-- ! navbar buttons never change, from now on.  i decree it! -->
                <a href="${branch.url('/changes', **util.get_context(clear=1))}"> changes </a>
                <a href="${branch.url('/files', **util.get_context(clear=1))}"> files </a>
                <span class="search"> search: <input type="text" name="q" /> </span>
            </span></td>
            <td align="right" py:if="hasattr(navigation, 'revid_list')">
                <span py:if="hasattr(navigation, 'feed')" class="rbuttons feed">
                    <a href="${branch.url('/atom')}">
                    <img src="${tg.url('/static/images/feed-icon-16x16.gif')}" /></a>
                </span>
                <span class="navbuttons">
                	<span py:if="navigation.prev_page_revid">
                	<a href="${navigation.prev_page_url}" title="Previous page"> &#171; </a>
                    </span>
                	<span py:if="not navigation.prev_page_revid"> &#171; </span>
                    revision ${history.get_revno(revid)}
                    (<span py:if="navigation.pagesize > 1">page </span>
                    ${navigation.page_position} / ${navigation.page_count})
                	<span py:if="navigation.next_page_revid">
                    <a href="${navigation.next_page_url}" title="Next page"> &#187; </a>
                    </span>
                	<span py:if="not navigation.next_page_revid"> &#187; </span>
                </span>
            </td>
        </tr></table></form>
    </div></div>
</span>

<span py:def="revision_link(revid, text, **overrides)" py:strip="True">
    <a title="Show revision ${history.get_revno(revid)}"
       href="${branch.url([ '/revision', revid ], **util.get_context(**overrides))}"> ${text} </a>
</span>


<!-- ! expand button functions: -->

	<span py:strip="True" py:def="use_collapse_buttons()">
		<!-- this is totally matty's fault.  i don't like javacsript. ;) -->
		<script type="text/javascript" src="${tg.url('/static/javascript/collapse.js')}"></script>
	</span>
	
	<span py:strip="True" py:def="collapse_all_button(group, normal='block')">
	    <a class="hide-all collapse-${group}-hideall"
	       href="javascript:collapseAllDisplay('${group}','none')">
	        <img src="${tg.url('/static/images/nav-small-down.gif')}"
	             width="10" height="10" alt="collapse"
	             class="collapse-triangle" />collapse all</a>
	    <a class="hide-all collapse-${group}-showall"
	       href="javascript:collapseAllDisplay('${group}','${normal}')">
	        <img src="${tg.url('/static/images/nav-small-right.gif')}"
	             width="10" height="10" alt="expand"
	             class="collapse-triangle" />expand all</a>
	</span>
	
	<span py:strip="True" py:def="collapse_button(group, name, normal='block')">
	    <a href="javascript:collapseDisplay('${group}','${name}','none')"
	       class="hide-button collapse-${group}-${name}-hide" title="collapse">
	        <img src="${tg.url('/static/images/nav-small-down.gif')}"
	             width="10" height="10" alt="collapse"
	             class="collapse-triangle" />
	    </a>
	    <a href="javascript:collapseDisplay('${group}','${name}','${normal}')"
	       class="show-button collapse-${group}-${name}-show" title="expand">
	    	<img src="${tg.url('/static/images/nav-small-right.gif')}"
	    	     witdh="10" height="10" alt="expand"
	    	     class="collapse-triangle" />
	    </a>
	</span>

</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'"
      py:attrs="item.items()">

    <div py:replace="[item.text]+item[:]"/>

	<!-- End of main_content -->
	
	<div class="footer">
	    <span class="banner"><a href="http://www.bazaar-vcs.org/">
	    <img src="${tg.url('/static/images/bazaar-banner.png')}" /></a></span>
	    <span class="banner"><a href="http://www.lag.net/loggerhead/">
	    <img src="${tg.url('/static/images/loggerhead-banner.png')}" /></a></span>
	</div>
</body>

</html>
