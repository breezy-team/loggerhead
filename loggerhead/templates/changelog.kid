<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${tg.url('/atom')}" title="RSS feed for ${branch_name}" />
    
    <span py:def="loglink(revid, text)">
        <a title="Show history" href="${tg.url('/changes', start_revid=revid)}" class="revlink"> ${text} </a>
    </span>

    <span py:def="file_link(filename, file_id, revid)">
        <a href="${tg.url([ '/annotate', revid ], file_id=file_id)}" title="Annotate ${filename}">${filename}</a>
    </span>

    <!-- this is totally matty's fault.  i don't like javacsript. ;) -->
    <script type="text/javascript"> // <!--
    function displayDetails(name, hide, show) {
        if (show == '') { show = 'inline'; }
        var bhide = hide, ihide = hide;
        if (hide == '') { bhide = 'block'; ihide = 'inline'; }
        document.getElementById('details-' + name).style.display = bhide;
        document.getElementById('hide-' + name).style.display = ihide;
        document.getElementById('show-' + name).style.display = show;
    }
    function displayAll(hide, show) {
        if (show == '') { show = 'inline'; }
        var bhide = hide, ihide = hide;
        if (hide == '') { bhide = 'block'; ihide = 'inline'; }
        var nodes = document.getElementsByTagName('div');
        for (var i = 0; i < nodes.length; i++) {
            var id = nodes[i].id;
            if ((id.length > 8) && (id.substring(0, 8) == 'details-')) {
                nodes[i].style.display = bhide;
                var revno = id.substring(8);
                document.getElementById('hide-' + revno).style.display = ihide;
                document.getElementById('show-' + revno).style.display = show;
            }
        }
        document.getElementById('hide-all').style.display = ihide;
        document.getElementById('show-all').style.display = show;
    }
    // -->
	</script>
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch_name}</span> : changes
<span py:if="file_id"> to <span class="filename">${history.get_path(revid, file_id)}</span></span>
<span py:if="(last_revid != start_revid) and not search_failed"> from ${history.get_revno(start_revid)} </span>
<span py:if="query"> (search results)</span>
</h1>

<span py:if="search_failed">
    Sorry, no results found for your search.
</span>

<span py:if="not search_failed">
<a class="hide-all" id="hide-all" href="javascript:displayAll('none', '')"> (hide all) </a>
<a class="hide-all" id="show-all" href="javascript:displayAll('', 'none')"> (show all) </a>
</span>

<div class="log-entries">
    <div py:for="entry in changes" class="revision">
        <a name="entry-${entry.revno}" />
        <div class="revision-header">
            <table>
                <tr>
                    <td class="revision-number"> ${revlink(entry.revid, start_revid, file_id, util.trunc(entry.revno))} </td>
                    <td class="expand-button">
                        <a href="javascript:displayDetails('${entry.revno}', 'none', '')" id="hide-${entry.revno}" class="show-button">
                            <img src="${tg.url('/static/images/nav-small-down.gif')}" width="10" height="10" />
                        </a>
                        <a href="javascript:displayDetails('${entry.revno}', '', 'none')" id="show-${entry.revno}" class="hide-button">
                        	<img src="${tg.url('/static/images/nav-small-right.gif')}" witdh="10" height="10" />
                        </a>
                    </td>
					<td class="summary"> ${revlink(entry.revid, start_revid, file_id, entry.short_comment)} </td>
					<td class="inventory-link"> <a href="${tg.url([ '/files', entry.revid ])}">&#8594; files</a> </td>
				</tr>
			</table>
        </div>
        
        <div class="revision-details-block">
            <div class="revision-details">
			    <table>
			        <tr>
			            <th class="author">committed by:</th>
			            <td class="author"> ${util.hide_email(entry.author)} </td>
			        </tr>
			        <tr>
			            <th class="date">date:</th>
			            <td class="date"> ${entry.date.strftime('%d %b %Y %H:%M')} &nbsp; (${util.ago(entry.date)}) </td>
			        </tr>
			    </table>
			</div>
	        <div class="revision-details hidden-details" id="details-${entry.revno}">
		        <table>
			        <tr py:if="len(entry.merge_points) > 0">
			            <th class="children"> merged in: </th>
			            <td class="children">
			                <span py:for="child in entry.merge_points">
			                    ${loglink(child.revid, '(' + child.revno + util.if_present(' %s', child.branch_nick) + ')')} <br />
			                </span>
			            </td>
			        </tr>
			        <tr py:if="len(entry.parents) > 1">
			        	<th class="parents"> merged from: </th>
			        	<td class="parents">
			        	    <span py:for="parent in entry.parents"><span py:if="parent.revid != entry.parents[0].revid">
			        	        ${loglink(parent.revid, '(' + parent.revno + util.if_present(' %s', parent.branch_nick) + ')')} <br />
			        	    </span></span>
			        	</td>
			        </tr>

			        <tr py:if="entry.changes.added">
			            <th class="files"> files added: </th>
			            <td class="files"> <span py:for="filename, file_id in entry.changes.added" class="filename">${file_link(filename, file_id, entry.revid)} <br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.removed">
			            <th class="files"> files removed: </th>
			            <td class="files"> <span py:for="filename, file_id in entry.changes.removed" class="filename">${file_link(filename, file_id, entry.revid)} <br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.renamed">
			            <th class="files"> files renamed: </th>
			            <td class="files"> <span py:for="old_filename, new_filename, file_id in entry.changes.renamed" class="filename">
			                ${file_link(old_filename, file_id, entry.revid)} => ${file_link(new_filename, file_id, entry.revid)}<br />
			            </span> </td>
			        </tr>
			        <tr py:if="entry.changes.modified">
			            <th class="files"> files modified: </th>
			            <td class="files"> <span py:for="item in entry.changes.modified">
			                <span class="filename">${file_link(item.filename, item.file_id, entry.revid)}</span> &nbsp;
			                <a href="${tg.url([ '/revision', entry.revid ], start_revid=start_revid, file_id=file_id) + '#' + item.filename}" class="jump">&#8594; diff</a>
			                <br />
			            </span> </td>
			        </tr>
			        <tr>
			            <th class="description">description:</th>
		                <td class="description"><span py:for="line in entry.comment_clean">${XML(line)} <br /></span> </td>
		            </tr>
		        </table>
	    	</div>
        </div>
    </div>
</div>

<div py:if="navigation.prev_page_revid or navigation.next_page_revid" class="bar">
    <table>
        <tr>
        	<td class="buttons">
            	<a py:if="navigation.prev_page_revid" href="${navigation.prev_page_url}"> &lt;&lt; page </a>
	 		</td>
 			<td class="rbuttons" align="right">
            	<a py:if="navigation.next_page_revid" href="${navigation.next_page_url}"> page &gt;&gt; </a>
 			</td>
 		</tr>
 	</table>
</div>

</body>
</html>
