<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch.friendly_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${branch.url('/atom')}" title="RSS feed for ${branch.friendly_name}" />
    
    <span py:def="loglink(revid, text)">
        <a title="Show history" href="${branch.url('/changes', start_revid=revid)}" class="revlink"> ${text} </a>
    </span>

    <span py:def="file_link(filename, file_id, revid)">
        <a href="${branch.url([ '/annotate', revid ], file_id=file_id)}" title="Annotate ${filename}">${filename}</a>
    </span>
    
    ${use_collapse_buttons()}
</head>

<body onload="javascript:sortCollapseElements();">

${navbar()}

<h1> <span class="branch-name">${branch.friendly_name}</span> : changes
<span py:if="file_id"> to <span class="filename">${history.get_path(revid, file_id)}</span></span>
<span py:if="viewing_from"> from ${history.get_revno(start_revid)} </span>
<span py:if="query"> matching "${query}"</span>
</h1>

<span py:if="search_failed">
    Sorry, no results found for your search.
</span>

<span py:if="not search_failed" class="changelog"> ${collapse_all_button('cl')} </span>

<div class="log-entries">
    <div py:for="entry in changes" class="revision">
        <a name="entry-${entry.revno}" />
        <div class="revision-header">
            <table>
                <tr>
                    <td class="revision-number"> ${revlink_q(entry.revid, start_revid, file_id, query, util.trunc(entry.revno))} </td>
                    <td class="expand-button"> ${collapse_button('cl', entry.revno)} </td>
					<td class="summary"> ${revlink_q(entry.revid, start_revid, file_id, query, entry.short_comment)} </td>
					<td class="inventory-link"> <a href="${branch.url([ '/files', entry.revid ])}">&#8594; files</a> </td>
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
	        <div class="revision-details hidden-details collapse-cl-${entry.revno}-content">
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
			            <td class="files"> <span py:for="filename, fid in entry.changes.added" class="filename">${file_link(filename, fid, entry.revid)} <br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.removed">
			            <th class="files"> files removed: </th>
			            <td class="files"> <span py:for="filename, fid in entry.changes.removed" class="filename">${file_link(filename, fid, entry.revid)} <br /></span> </td>
			        </tr>
			        <tr py:if="entry.changes.renamed">
			            <th class="files"> files renamed: </th>
			            <td class="files"> <span py:for="old_filename, new_filename, fid in entry.changes.renamed" class="filename">
			                ${file_link(old_filename, fid, entry.revid)} => ${file_link(new_filename, fid, entry.revid)}<br />
			            </span> </td>
			        </tr>
			        <tr py:if="entry.changes.modified">
			            <th class="files"> files modified: </th>
			            <td class="files"> <span py:for="item in entry.changes.modified">
			                <span class="filename">${file_link(item.filename, item.file_id, entry.revid)}</span> &nbsp;
			                <a href="${branch.url([ '/revision', entry.revid ], start_revid=start_revid, file_id=file_id, query=query) + '#' + item.filename}" class="jump">&#8594; diff</a>
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
