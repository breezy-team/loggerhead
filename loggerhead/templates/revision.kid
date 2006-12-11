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
            <th class="author">committer:</th>
            <td class="author"> ${util.hide_email(author)} </td>
        </tr>
        <tr>
            <th class="date">date:</th>
            <td class="date"> ${date.strftime('%d %b %Y %H:%M')} </td>
        </tr>
        <tr>
            <th class="description">description:</th>
            <td class="description"> <span py:for="line in comment">${line} <br /></span> </td>
        </tr>
        <tr class="divider"> <th></th> <td></td> </tr>
        <tr py:if="files_added">
            <th class="files"> files added: </th>
            <td class="files"> <span py:for="filename in files_added">${filename} <br /></span> </td>
        </tr>
        <tr py:if="files_removed">
            <th class="files"> files removed: </th>
            <td class="files"> <span py:for="filename in files_removed">${filename} <br /></span> </td>
        </tr>
        <tr py:if="files_renamed">
            <th class="files"> files renamed: </th>
            <td class="files"> <span py:for="old_filename, new_filename in files_renamed">${old_filename} => ${new_filename}<br /></span> </td>
        </tr>
        <tr py:if="files_modified">
            <th class="files"> files modified: </th>
            <td class="files"> <span py:for="filename in files_modified">${filename} <br /></span> </td>
        </tr>
    </table>
</div>

<div class="diff" py:if="diff">
    <div py:for="css_class, line in diff" class="${css_class}"> ${line} </div>
</div>
<span py:if="not diff">
    <a href="${tg.url([ '/revision', revid ], show_diff=1)}"> (show diff) </a>
</span>

</body>
</html>
