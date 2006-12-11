<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<?python import sitetemplate ?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#" py:extends="sitetemplate">

<head py:match="item.tag=='{http://www.w3.org/1999/xhtml}head'" py:attrs="item.items()">
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
    <title py:replace="''">Your title goes here</title>
    <meta py:replace="item[:]"/>
    <style type="text/css" media="screen">
@import "/static/css/style.css";
    </style>

<!-- define common navbar -->
<span py:def="navbar()">
    <!-- requires: ${revid}, ${buttons} -->
    <div class="navbar">
        <div class="bar">
            <table>
                <tr><td>
                    <span class="buttons">
                        <span py:for="label, url in buttons">
                            <a href="${url}"> ${label} </a>
                        </span>
                    </span>
                </td><td align="right">
                    <span class="navbuttons">
                        <span py:for="label, l_revid in history.scan_range(revid)">
                            <a py:if="l_revid" href="${tg.url([ scan_url, l_revid ])}"> ${label} </a>
                            <span py:if="not l_revid"> ${label} </span>
                        </span>
                    </span>
                </td></tr>
            </table>
        </div>
        <div class="navposition">
            <table>
                <tr>
                    <td> </td>
                    <td class="navposition" align="right">
                        changes: ${history.get_sequence(revid) + 1} / ${history.count}
                    </td>
                </tr>
            </table>
        </div>
    </div>
</span>

</head>

<body py:match="item.tag=='{http://www.w3.org/1999/xhtml}body'" py:attrs="item.items()">

    <div py:replace="[item.text]+item[:]"/>

	<!-- End of main_content -->
</body>

</html>
