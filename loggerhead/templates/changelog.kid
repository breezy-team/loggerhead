<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${tg.url('/atom')}" title="RSS feed for ${branch_name}" />
    
    <span py:def="revlink(revid, text)">
        <a title="Show revision" href="${tg.url([ '/revision', revid ])}" class="revlink"> ${text} </a>
    </span>

    <span py:def="loglink(revid, text)">
        <a title="Show revision" href="${tg.url([ '/changes', revid ])}" class="revlink"> ${text} </a>
    </span>
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch_name}</span> : changes </h1>
    
<!-- i don't understand this -->
<!--!span py:if="len(merge_points) > 0">
    <table class="info-entry">
        <tr> <th> merged in: </th>
        <td> 
            <span py:for="merge in merge_points" class="revision">
	        ${revision_link(merge.revid, merge.revno)} <br />
	        </span>
	    </td>
	    </tr>
    </table>
</span-->

<div class="log-entries">
    <div py:for="entry in changes" class="revision">
        <div class="revision-header">
            <table>
                <tr>
                    <td class="revision-number"> ${revlink(entry.revid, entry.revno)} </td>
					<td> ${revlink(entry.revid, entry.short_comment)} </td>
					<td class="inventory-link"> <a href="${tg.url([ '/inventory', entry.revid ])}">(files)</a> </td>
				</tr>
			</table>
        </div>
        
        <div class="revision-log">
        <table>
	        <tr>
	            <th class="author">committed by:</th>
	            <td class="author"> ${util.hide_email(entry.author)} </td>
	        </tr>
	        <tr>
	            <th class="date">date:</th>
	            <td class="date"> ${entry.date.strftime('%d %b %Y %H:%M')} &nbsp; (${entry.age}) </td>
	        </tr>
	        <tr py:if="len(entry.children) > 1">
	            <th class="children"> merged in: </th>
	            <td class="children">
	                <span py:for="child in entry.children">  <span py:if="child.revid != entry.left_child"> ${loglink(child.revid, '(' + child.revno + ')')} &nbsp; </span></span>
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
        </table>
	    </div>
    </div>
</div>

</body>
</html>
