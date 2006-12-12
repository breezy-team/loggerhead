<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${tg.url('/atom')}" title="RSS feed for ${branch_name}" />
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch_name}</span> : changes </h1>
    
<span py:if="len(merge_points) > 0">
    <table class="info-entry">
        <tr> <th> merged in: </th>
        <td> 
            <span py:for="merge in merge_points" class="revision">
	        ${revision_link(merge.revid, merge.revno)} <br />
	        </span>
	    </td>
	    </tr>
    </table>
</span>

<div class="log-entries">
    <div py:for="entry in changes" class="revision">
        <div class="revision-header">
            <table>
                <tr>
                    <td class="revision-number"> 
                        <a title="Show revision" href="${tg.url([ '/revision', entry.revid ])}" class="revno"> ${entry.revno} </a>
                    </td>
					<td>
					    <a title="Show revision" href="${tg.url([ '/revision', entry.revid ])}" class="revno"> ${entry.short_comment} </a>
					</td>
				</tr>
			</table>
        </div>
        
        <div class="revision-log">
        <table>
	        <tr>
	            <th class="author">committer:</th>
	            <td class="author"> ${util.hide_email(entry.author)} </td>
	        </tr>
	        <tr>
	            <th class="date">date:</th>
	            <td class="date"> ${entry.date.strftime('%d %b %Y %H:%M')} &nbsp; (${entry.age}) </td>
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
    
    <!--table>
        <col class="header" />
        <col class="data" />
        <col class="mark-diff" />
        
        <div py:for="entry in changes">
            
            <tr>
                <th class="firstline header age"> ${entry.age} </th>
                <th class="firstline data"> ${entry.short_comment} </th>
                <th class="firstline"> #dodiff# </th>
            </tr>
            
            <tr>
                <th class="revision header top"> revision: </th>
                <td class="revision data top"> ${revision_link(entry.revid, entry.revno)} </td>
                <td class="revision mark-diff top"><span class="buttons">
                    <a href="${tg.url([ '/changes', entry.revid ])}"> Mark for diff </a>
                </span></td>
            </tr>
            
            <span py:if="len(entry.parents) > 1">
                <span py:for="parent in entry.parents">
                    <tr>
                        <th class="revision header"> parent: </th>
                        <td class="revision data"> ${revision_link(parent.revid, parent.revno)} </td>
                    </tr>
                </span>
            </span>
            
            <tr>
                <th class="author header"> committer: </th>
                <td class="author data"> ${util.hide_email(entry.author)} </td>
            </tr>
            <tr>
                <th class="date header"> date: </th>
                <td class="date data"> ${entry.date.strftime('%d %b %Y %H:%M')} </td>
                <td class="date mark-diff"> &nbsp; </td>
            </tr>
        </span-->
</div>

</body>
</html>
