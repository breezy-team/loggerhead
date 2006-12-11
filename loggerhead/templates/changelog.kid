<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : changes </title>
    <link rel="alternate" type="application/atom+xml" href="${tg.url('/atom')}" title="RSS feed for ${branch_name}" />
</head>

<body>

<span py:def="revision_link(revid, revno)">
    <a title="Show revision info" href="${tg.url([ '/revision', revid ])}">
        <span class="revno"> ${revno} </span>
    </a>
    <a title="Show changelog" href="${tg.url([ '/changes', revid ])}" class="log"> (log) </a>
    <a title="Show revision info" href="${tg.url([ '/revision', revid ])}">
        <span class="revid"> ${util.clean_revid(revid)} </span>
    </a>
</span>

${navbar()}

<h1> <span class="branch-name">${branch_name}</span> : changes </h1>
    
<span py:if="len(merge_points) > 0">
    <table class="info-entry">
        <tr> <th> merged in: </th>
        <td> 
            <span py:for="merge in merge_points" class="revision">
	        ${revision_link(merge.revid, merge.revno)}
	        </span> <br />
            <span py:for="merge in merge_points" class="revision">
	        ${revision_link(merge.revid, merge.revno)}
	        </span>
	    </td>
	    </tr>
    </table>
</span>

<!-- #prevpage# -->

<div class="log-entries">
    <table width="100%">
        <col class="header" />
        <col class="data" />
        <col class="mark-diff" />
        
        <span py:for="entry in changes">
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
            
            <!-- for multiple-parents: -->
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
        </span>
    </table>
</div>

<!-- #nextpage# -->

</body>
</html>
