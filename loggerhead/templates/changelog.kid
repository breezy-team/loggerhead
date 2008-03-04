<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch.friendly_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${branch.url('/atom')}" title="RSS feed for ${branch.friendly_name}" />
    
    <span py:def="loglink(revid, text)">
        <a title="Show history" href="${branch.url('/changes', **util.get_context(start_revid=revid))}" class="revlink"> ${text} </a>
    </span>

    <span py:def="file_link(filename, file_id, revid)">
        <a href="${branch.url([ '/annotate', revid ], **util.get_context(file_id=file_id))}" title="Annotate ${filename}">${filename}</a>
    </span>
    
    <span py:def="file_diff_link(revid, filename)">
        <a href="javascript:diff_url('${branch.context_url([ '/revision', revid ]) + '#' + filename}')"
           title="View diff for ${filename}">${filename}</a>
    </span>
    
    ${use_collapse_buttons()}

    <script type="text/javascript"> <!--
    function diff_url(url) {
        if (document.cookie.indexOf('diff=unified') >= 0) {
            this.location.href = url + "-u";
        } else {
            this.location.href = url + "-s";
        }
    }
    // --> </script>
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

<span py:if="not changes">
    No revisions!
</span>

<span py:if="not search_failed" class="changelog"> ${collapse_all_button('cl')} </span>

<table class="log-entries">
    <tr class="log-header">
        <th class="revision-number">Rev</th>
        <th></th>
        <th class="summary">Summary</th>
        <span py:strip="True" py:if="all_same_author">
            <th></th>
        </span>
        <span py:strip="True" py:if="not all_same_author">
            <th class="author">Committer</th>
        </span>
        <th class="date" colspan="2">Date</th>
    </tr>
    <div py:for="entry in changes" class="revision">
        <a name="entry-${entry.revno}" />
        <tr class="revision-header parity${entry.parity}">
            <td class="revision-number"> ${revision_link(entry.revid, util.trunc(entry.revno))} </td>
            <td class="expand-button"> ${collapse_button('cl', entry.revno)} </td>
            <td class="summary"> ${revision_link(entry.revid, entry.short_comment)} </td>
            <span py:strip="True" py:if="all_same_author">
                <td></td>
            </span>
            <span py:strip="True" py:if="not all_same_author">
                <td class="author"> ${util.trunc(util.hide_email(entry.author), 20)} </td>
            </span>
            <td class="date"> ${util.lp_format_date(entry.date)} </td>
            <td class="inventory-link"> 
                <a href="${branch.url([ '/files', entry.revid ])}"
                    title="Files at revision ${entry.revno}"> files</a>
            </td>
        </tr>
        
        <tr class="revision-details-block parity${entry.parity}">
            <td colspan="2"></td>
            <td colspan="4"><table class="revision-details hidden-details collapse-cl-${entry.revno}-content">
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
                        <span py:for="parent in entry.parents[1:]">
                            ${loglink(parent.revid, parent.revno + util.if_present(' (%s)', parent.branch_nick))} <br />
                        </span>
                    </td>
                </tr>
                <span py:strip="True" py:if="all_same_author">
                    <tr>
                        <th class="author">committed by:</th>
                        <td class="author"> ${util.hide_email(entry.author)} </td>
                    </tr>
                </span>
                <tr>
                    <th class="description">description:</th>
                    <td class="description"><span py:for="line in entry.comment_clean">${XML(line)} <br /></span> </td>
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
                        <span class="filename">${file_diff_link(entry.revid, item.filename)}</span>
                        <br />
                    </span> </td>
                </tr>
                </table>
            </td>
        </tr>
    </div>
</table>

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
