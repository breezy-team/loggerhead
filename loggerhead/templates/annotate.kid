<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> ${branch_name} : contents of ${path} at revision ${change.revno} </title>
</head>

<body>

${navbar()}

<h1> <span class="branch-name">${branch_name}</span> : ${path} (revision ${change.revno}) </h1>

<!-- !FIXME: this is just copied verbatim from revision.kid -->
<!--div class="revision-info">
    <table>
        <tr>
            <th class="author">committed by:</th>
            <td class="author"> ${util.hide_email(change.author)} </td>
        </tr>
        <tr>
            <th class="date">date:</th>
            <td class="date"> ${change.date.strftime('%d %b %Y %H:%M')} </td>
        </tr>

        <tr py:if="len(change.merge_points) > 0">
            <th class="children"> merged in: </th>
            <td class="children">
                <span py:for="child in change.merge_points"> ${revlink(child.revid, '(' + child.revno + ')')} &nbsp; </span>
            </td>
        </tr>
        <tr py:if="len(change.parents) > 1">
        	<th class="parents"> merged from: </th>
        	<td class="parents">
        	    <span py:for="parent in change.parents"><span py:if="parent.revid != change.parents[0].revid"> ${revlink(parent.revid, '(' + parent.revno + ')')} &nbsp; </span></span>
        	</td>
        </tr>

        <tr>
            <th class="description">description:</th>
            <td class="description"><span py:for="line in change.comment_clean">${XML(line)} <br /></span></td>
        </tr>
    </table>
</div-->

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
                <a py:if="line.status=='changed'" href="${tg.url([ '/revision', line.revid ], path=path)}">${line.trunc_revno}</a>
            </td>
            <!--td class="author"> ${util.hide_email(line.author)} </td-->
            <td class="text ${line.status}"> ${XML(line.text)} </td>
        </tr>
    </table>
</div>


</body>
</html>
