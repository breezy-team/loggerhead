var global_timeout_id = null;
var global_search_request = null;

window.addEvent('domready', function() 
{
    var search_box = $('q');
    search_box.addEvents(
    {
        keyup: function()
        {
            if($('q').value == '')
            {
                $('search_terms').setStyle('display','none');
            }
            else
            {
	            if (null != global_timeout_id)
	            {
	                clearTimeout(global_timeout_id);
	            }
                    global_timeout_id = setTimeout('$("q").fireEvent("search",$("q").value)',200);
            }
        },

        search: function(query)
        {
            url = global_path + 'search?query=' + query;
	
            if ($defined(global_search_request))
            {
                global_search_request.cancel();
            }
            global_search_request = new Request({'url':url,'method':'get','onComplete':cool_search});
            global_search_request.send('');
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

function hide_search()
{
    $('search_terms').setStyle('display','none');
}
