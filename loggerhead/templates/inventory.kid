<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch.friendly_name} : files for revision ${change.revno} </title>
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch.friendly_name}</span> : files for revision ${change.revno}
	<div class="links">
	    <div> <b>&#8594;</b> <a href="${branch.context_url('/revision', clear=1, start_revid=revid)}">
	        view revision </a> </div>
	    <div> <b>&#8594;</b> <a href="${branch.context_url('/changes', clear=1, start_revid=revid)}">
	        view branch changes </a> </div>
	</div>
</h1>

<!-- !FIXME: this is just copied verbatim from revision.kid -->
<div class="revision-info">
    <table>
        <tr>
            <th class="author">committed by:</th>
            <td class="author"> ${util.hide_email(change.author)} </td>
        </tr>
        <tr>
            <th class="date">date:</th>
            <td class="date"> ${util.date_time(change.date)} </td>
        </tr>

        <tr py:if="len(change.merge_points) > 0">
            <th class="children"> merged in: </th>
            <td class="children">
                <span py:for="child in change.merge_points">
                    ${revision_link(child.revid, '(' + child.revno + util.if_present(' %s', child.branch_nick) + ')', clear=1, start_revid=child.revid)} <br />
                </span>
            </td>
        </tr>
        <tr py:if="len(change.parents) > 1">
        	<th class="parents"> merged from: </th>
        	<td class="parents">
        	    <span py:for="parent in change.parents"><span py:if="parent.revid != change.parents[0].revid">
        	        ${revision_link(parent.revid, '(' + parent.revno + util.if_present(' %s', parent.branch_nick) + ')', clear=1, start_revid=parent.revid)} <br />
        	    </span></span>
        	</td>
        </tr>

        <tr>
            <th class="description">description:</th>
            <td class="description"><span py:for="line in change.comment_clean">${XML(line)} <br /></span></td>
        </tr>
    </table>
</div>

<div class="inventory-path">
    <b>folder:</b> <span class="folder"> ${path} </span>
</div>

<table class="inventory" width="100%">
    <tr class="header">
        <th class="permissions"> Permissions </th>
        <th> <a href="${branch.context_url([ '/files', revid ], sort='filename')}">Filename</a> </th>
        <th> Latest Rev </th>
        <th> <a href="${branch.context_url([ '/files', revid ], sort='date')}">Last Changed</a> </th>
        <th> <a href="${branch.context_url([ '/files', revid ], sort='size')}">Size</a> </th>
        <th>  </th>
        <th>  </th>
    </tr>
    
    <tr class="parity1" py:if="updir">
        <td class="permissions">drwxr-xr-x</td>
        <td class="filename directory"><a href="${branch.context_url([ '/files', revid ], file_id=updir_file_id)}"> (up) </a></td>
        <td> </td> <td> </td> <td> </td> <td> </td>
    </tr>

    <tr py:for="file in filelist" class="parity${file.parity}">
        <td class="permissions"> ${util.fake_permissions(file.kind, file.executable)} </td>
        <td class="filename ${file.kind}">
            <a py:if="file.kind=='directory'" href="${branch.context_url([ '/files', revid ],
                file_id=file.file_id)}">${file.filename}/</a>
            <span py:if="file.kind=='symlink'">${file.filename}@</span>
            <a py:if="file.kind=='file'" href="${branch.context_url([ '/annotate', revid ],
                file_id=file.file_id)}" title="Annotate ${file.filename}">${file.filename}</a>
        </td>
        <td class="revision"> ${revision_link(file.revid, util.trunc(file.change.revno, 15), **util.get_context(start_revid=file.revid, file_id=file.file_id))} </td>
        <td class="date"> ${util.date_time(file.change.date)} </td>
        <td class="size"> <span py:if="file.kind=='file'"> ${util.human_size(file.size)} </span></td>
        <td class="changes-link"> 
            <a href="${branch.context_url('/changes', start_revid=file.revid, file_id=file.file_id)}"
               title="Changes affecting ${file.filename} up to revision ${file.change.revno}"> changes </a>
        </td>
        <td class="download-link">
            <a href="${branch.url([ '/download', file.revid, file.file_id, file.filename ])}"
               title="Download ${file.filename} at revision ${file.change.revno}">  download </a></td>
    </tr>
</table>

</body>
</html>
