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
    <!-- !requires: ${navigation: start_revid, revid, revid_list, pagesize, buttons, scan_url}, ${history} -->
    <div class="navbar">
        <div class="bar">
            <!-- form must go OUTSIDE the table, or safari will add extra padding :( -->
            <form action="${tg.url('/changes', start_revid=getattr(navigation, 'start_revid', None), file_id=getattr(navigation, 'file_id', None))}">
            <table>
                <tr><td>
                    <span class="buttons">
                        <!-- ! navbar buttons never change, from now on.  i decree it! -->
                        <a href="${tg.url('/changes')}"> changes </a>
                        <a href="${tg.url('/files')}"> files </a>
                        <span class="search"> search: <input type="text" name="q" /> </span>
                    </span>
                </td><td align="right" py:if="hasattr(navigation, 'revid_list')">
                    <span py:if="hasattr(navigation, 'feed')" class="rbuttons feed">
                        <a href="${tg.url('/atom')}"><img src="${tg.url('/static/images/feed-icon-16x16.gif')}" /></a>
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
    <a title="Show revision ${history.get_revno(revid)}" href="${tg.url([ '/revision', revid ], start_revid=start_revid, file_id=file_id)}" class="revlink"> ${text} </a>
</span>
<span py:def="revlink_q(revid, start_revid, file_id, query, text)">
    <a title="Show revision ${history.get_revno(revid)}" href="${tg.url([ '/revision', revid ], start_revid=start_revid, file_id=file_id, q=query)}" class="revlink"> ${text} </a>
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
