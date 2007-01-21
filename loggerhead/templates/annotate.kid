<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch.friendly_name} : contents of ${path} at revision ${change.revno} </title>
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch.friendly_name}</span> : <span class="annotate-path">${path}</span> (revision ${change.revno})
	<div class="links">
	    <div> <b>&#8594;</b> <a href="${branch.url([ '/files', revid ], **util.get_context(clear=1))}"> browse files </a> </div>
	    <div> <b>&#8594;</b> <a href="${branch.url('/revision', **util.get_context(clear=1, start_revid=revid))}"> view revision </a> </div>
	    <div> <b>&#8594;</b> <a href="${branch.url('/changes', **util.get_context(clear=1, start_revid=revid, file_id=file_id))}"> view changes to this file </a> </div>
	    <div> <b>&#8594;</b> <a href="${branch.url([ '/download', revid, file_id, filename ])}"> view/download file </a> </div>
	</div>
</h1>

<div class="annotate">
    <table>
        <tr>
            <th class="lineno"> Line# </th>
            <th class="revision"> Revision </th>
            <th class="text"> Contents </th>
        </tr>

        <tr py:for="line in contents" class="parity${line.parity}">
            <td class="lineno ${line.status}"> ${line.lineno} </td>
            <td class="revno ${line.status}">
                <a py:if="line.status=='changed'" href="${branch.url('/revision', **util.get_context(clear=1, start_revid=line.change.revid, file_id=file_id))}"
                    title="${line.change.revno} by ${util.hide_email(line.change.author)}, on ${line.change.date.strftime('%d %b %Y %H:%M')} (${util.ago(line.change.date)})">${util.trunc(line.change.revno)}</a>
            </td>
            <td class="text ${line.status}"> ${XML(line.text)} </td>
        </tr>
    </table>
</div>

</body>
</html>
