<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
    py:extends="'master.kid'">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
    <title> loggerhead branches </title>
</head>

<body>

<h1>
    <span py:if="title">${title}</span>
    <span py:if="not title"> bazaar branches in loggerhead </span>
</h1>

<div class="browse-group" py:for="group in groups">
    <div class="browse-group-name">
        ${group.friendly_name}
    </div>
    
    <div class="browse-view">
        <table>
        <tr class="heading">
            <th> Name </th>
            <th> Description </th>
            <th> Last change </th>
        </tr>
        <span py:for="view in group.views">
            <tr>
            <td class="name"> <a href="${tg.url([ '/' + group.name, view.name ])}">${view.friendly_name}</a> </td>
            <td class="description"> ${view.description} </td>
            <td class="last-update"> <!--${view.last_updated().strftime('%d %b %Y')} &nbsp;--> ${util.ago(view.last_updated())} </td>
            </tr>
            <tr py:if="view.url">
                <td class="name"> </td>
                <td class="description url" colspan="2"> <a href="${view.url}">${view.branch_url}</a> </td>
            </tr>
        </span>
        </table>
    </div>

</div>

</body>
</html>
