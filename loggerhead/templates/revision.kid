<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : revision ${util.clean_revid(revid)} </title>
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch_name}</span> : revision ${revno} </h1>

<div class="info-entries">
    <table>
        <tr>
            <th class="revision">revision:</th>
            <td class="revision"> ${revision_link(revid, revno)} </td>
        </tr>
        <tr py:if="parents">
            <th class="revision">parents:</th>
            <td class="revision">
                <span py:for="p in parents">
                    ${revision_link(p.revid, p.revno)} <br />
                </span>
            </td>
        </tr>
        <tr py:if="children">
            <th class="revision">children:</th>
            <td class="revision">
                <span py:for="c in children">
                    ${revision_link(c.revid, c.revno)} <br />
                </span>
            </td>
        </tr>
        <tr>
            <th class="author">committed by:</th>
            <td class="author"> ${util.hide_email(author)} </td>
        </tr>
        <tr>
            <th class="date">date:</th>
            <td class="date"> ${date.strftime('%d %b %Y %H:%M')} </td>
        </tr>
        <tr>
            <th class="description">description:</th>
            <td class="description"> <span py:for="line in comment_clean">${XML(line)} <br /></span> </td>
        </tr>
        <tr class="divider"> <th></th> <td></td> </tr>
        <tr py:if="changes.added">
            <th class="files"> files added: </th>
            <td class="files"> <span py:for="filename in changes.added">${filename} <br /></span> </td>
        </tr>
        <tr py:if="changes.removed">
            <th class="files"> files removed: </th>
            <td class="files"> <span py:for="filename in changes.removed">${filename} <br /></span> </td>
        </tr>
        <tr py:if="changes.renamed">
            <th class="files"> files renamed: </th>
            <td class="files"> <span py:for="old_filename, new_filename in changes.renamed">${old_filename} => ${new_filename}<br /></span> </td>
        </tr>
        <tr py:if="changes.modified">
            <th class="files"> files modified: </th>
            <td class="files"> <span py:for="item in changes.modified">${item.filename} <br /></span> </td>
        </tr>
    </table>
</div>

<div class="diff" py:if="changes.modified">
    <table py:for="item in changes.modified" class="diff-block">
        <tr><th class="filename"> ${item.filename} </th></tr>
        <tr><td>
            <table py:for="chunk in item.chunks" class="diff-chunk">
                <tr> <th class="lineno">old</th> <th class="lineno">new</th> <th></th> </tr>
                <tr py:for="line in chunk.diff">
                    <td class="lineno">${line.old_lineno}</td>
                    <td class="lineno">${line.new_lineno}</td>
                    <td class="${line.type} text">${XML(line.line)}</td>
                </tr>
            </table>
        </td></tr>
    </table>
</div>

</body>
</html>
