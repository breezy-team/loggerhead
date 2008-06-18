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
            url = '/bazaar/bzr_garbage/search?query=' + query;
            new Ajax(url, {
                            method: 'get',
                            update: $('search_terms')
                           }).request(); 
        }
    });
});

