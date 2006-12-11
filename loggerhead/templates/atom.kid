<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:py="http://purl.org/kid/ns#">
    <title> bazaar changes for ${branch_name} </title>
    <updated>${updated}</updated>
    <id>${tg.url([ external_url, 'atom' ])}</id>
    <link rel="self" href="${tg.url([ external_url, 'atom' ])}" />

	<entry py:for="entry in changes">
	    <title> ${entry.short_comment} </title>
	    <updated> ${entry.date.isoformat() + 'Z'} </updated>
	    <id>${tg.url([ external_url, 'atom', entry.revid ])}</id>
	    <author> <name> ${util.hide_email(entry.author)} </name> </author>
	    <content type="text">
            ${entry.comment}
	    </content>
	    <link rel="alternate" href="${tg.url([ external_url, 'revision', entry.revid ])}" />
	</entry>
</feed>
