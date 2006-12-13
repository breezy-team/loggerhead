<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${tg.url('/atom')}" title="RSS feed for ${branch_name}" />
    
    <span py:def="loglink(revid, text)">
        <a title="Show history" href="${tg.url([ '/changes', revid ])}" class="revlink"> ${text} </a>
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
<span py:if="path"> to <span class="filename">${path}</span></span>
</h1>

<a class="hide-all" id="hide-all" href="javascript:displayAll('none', '')"> (hide all) </a>
<a class="hide-all" id="show-all" href="javascript:displayAll('', 'none')"> (show all) </a>

<div class="log-entries">
    <div py:for="entry in changes" class="revision">
        <a name="entry-${entry.revno}" />
        <div class="revision-header">
            <table>
                <tr>
                    <td class="revision-number"> ${revlink_path(entry.revid, entry.revno, path)} </td>
                    <td class="expand-button">
                        <a href="javascript:displayDetails('${entry.revno}', 'none', '')" id="hide-${entry.revno}" class="show-button">
                            <img src="${tg.url('/static/images/nav-small-down.gif')}" width="10" height="10" border="0" />
                        </a>
                        <a href="javascript:displayDetails('${entry.revno}', '', 'none')" id="show-${entry.revno}" class="hide-button">
                        	<img src="${tg.url('/static/images/nav-small-right.gif')}" witdh="10" height="10" border="0" />
                        </a>
                    </td>
					<td class="summary"> ${revlink_path(entry.revid, entry.short_comment, path)} </td>
					<td class="inventory-link"> <a href="${tg.url([ '/inventory', entry.revid ])}">(files)</a> </td>
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
			            <td class="date"> ${entry.date.strftime('%d %b %Y %H:%M')} &nbsp; (${entry.age}) </td>
			        </tr>
			    </table>
			</div>
	        <div class="revision-details hidden-details" id="details-${entry.revno}">
		        <table>
			        <tr py:if="len(entry.merge_points) > 0">
			            <th class="children"> merged in: </th>
			            <td class="children">
			                <span py:for="child in entry.merge_points"> ${loglink(child.revid, '(' + child.revno + ')')} &nbsp; </span>
			            </td>
			        </tr>
			        <tr py:if="len(entry.parents) > 1">
			        	<th class="parents"> merged from: </th>
			        	<td class="parents">
			        	    <span py:for="parent in entry.parents"><span py:if="parent.revid != entry.parents[0].revid"> ${loglink(parent.revid, '(' + parent.revno + ')')} &nbsp; </span></span>
			        	</td>
			        </tr>
			        <!--tr class="divider"> <th></th> <td></td> </tr-->
			        <tr py:if="entry.changes.added">
			            <th class="files"> files added: </th>
			            <td class="files"> <span py:for="filename in entry.changes.added">${filename} <br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.removed">
			            <th class="files"> files removed: </th>
			            <td class="files"> <span py:for="filename in entry.changes.removed">${filename} <br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.renamed">
			            <th class="files"> files renamed: </th>
			            <td class="files"> <span py:for="old_filename, new_filename in entry.changes.renamed">${old_filename} => ${new_filename}<br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.modified">
			            <th class="files"> files modified: </th>
			            <td class="files"> <span py:for="item in entry.changes.modified">${item.filename} <br /></span> </td>
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

</body>
</html>
