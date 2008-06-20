window.addEvent('domready', function() 
{
    var search_box = $('q');
    search_box.addEvents(
    {
        keyup: function()
        {
            search_box.fireEvent('search', search_box.value, 200);
        },

        search: function(query)
        {
            url = '/bazaar/bzr.garbage/search?query=' + query;
	
	        var posicion = search_box.getPosition();
	        var size     = search_box.getSize();

	        $('search_terms').setStyle('position','absolute');
	        $('search_terms').setStyle('left',posicion.x);
	        $('search_terms').setStyle('top',posicion.y + size.y);
	        $('search_terms').setStyle('display','block');
	        $('search_terms').set('html','Loading...');

            new Request({'url':url,'method':'get','onComplete':cool_search}).send('');


        }
    });
});

function cool_search(response)
{
	var posicion = $('q').getPosition();
	var size     = $('q').getSize();
	$('search_terms').set('html',response);
	$('search_terms').setStyle('display','block');
	$('search_terms').setStyle('position','absolute');
	$('search_terms').setStyle('left',posicion.x);
	$('search_terms').setStyle('top',posicion.y + size.y);
}
