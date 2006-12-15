<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <meta py:replace="item[:]"/>
    <style type="text/css" media="screen">
@import "/static/css/style.css";
    </style>

<!-- !define common navbar -->
<span py:def="navbar()">
    <!-- !requires: ${navigation: start_revid, revid, revlist, pagesize, buttons, scan_url}, ${history} -->
    <div class="navbar">
        <div class="bar">
            <table>
                <tr><td>
                    <span class="buttons">
                        <!-- ! navbar buttons never change, from now on.  i decree it! -->
                        <a href="${tg.url('/changes')}"> changes </a>
                        <a href="${tg.url('/files')}"> files </a>
                    </span>
                </td><td align="right" py:if="hasattr(navigation, 'revlist')">
                    <span py:if="hasattr(navigation, 'feed')" class="rbuttons feed">
                        <a href="${tg.url('/atom')}"><img src="/static/images/feed-icon-16x16.gif" /></a>
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
        </div>
    </div>
</span>

<span py:def="revlink(revid, text)">
    <a title="Show revision" href="${tg.url([ '/revision', revid ])}" class="revlink"> ${text} </a>
</span>
<span py:def="revlink_path(revid, start_revid, text, path)">
    <a title="Show revision" href="${tg.url([ '/revision', revid ], start_revid=start_revid, path=path)}" class="revlink"> ${text} </a>
</span>

</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">

    <div py:replace="[item.text]+item[:]"/>

	<!-- End of main_content -->
</body>

</html>
