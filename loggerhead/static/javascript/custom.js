var global_timeout_id = null;
var global_search_request = null;

window.addEvent('domready', function() 
{
    var search_box = $('q');
    if ($defined(search_box))
    {
        search_box.removeEvents();
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
                global_search_request = new Request({'url':url,'method':'get','onComplete':function(response)
                  {
                     cool_search(response,query);
                 }});

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
    }
});

function cool_search(response, query)
{
	var posicion = $('q').getPosition();
	var size     = $('q').getSize();
    var current_query = $('q').get('value');
    if (current_query == query)
    {
	    $('search_terms').set('html',response);
	    $('search_terms').setStyle('display','block');
	    $('search_terms').setStyle('position','absolute');
	    $('search_terms').setStyle('left',posicion.x);
	    $('search_terms').setStyle('top',posicion.y + size.y);
    }
}

function hide_search()
{
    hide_div = setTimeout("$('search_terms').setStyle('display','none')", 300);
}
var Colapsable = new Class({
    initialize: function(item,expand_icon,open_content,close_content,is_open)
    {
        this.is_open = false;
        if ($defined(is_open))
        {
            this.is_open = is_open;
        }
        this.item = item;
        item.set('colapsable',this);
        this.open_content  = open_content;
        this.close_content = close_content;
        this.expand_icon   = expand_icon;

        var expander = new Fx.Slide(this.item, { duration: 200 } );
        if (!this.is_open)
        {
            expander.hide();
            if ($defined(this.expand_icon))
            {
                this.expand_icon.set('src',this.expand_icon.title);
            }
        }
        else
        {
            if ($defined(this.expand_icon))
            {
                this.expand_icon.set('src',this.expand_icon.alt);
            }
        }
    },

    open: function()
    {
        this.item.setStyle('display', 'block');
        var expander = this.item.get('slide');
        expander.slideIn();
        if ($defined(this.open_content))
        {
            for (var i=0;i<this.open_content.length;++i)
            {
                this.open_content[i].setStyle('display','block');
            }
		}
		
        if ($defined(this.close_content))
        {
            for (var i=0;i<this.close_content.length;++i)
            {
                this.close_content[i].setStyle('display','none');
            }
        }

        if ($defined(this.expand_icon))
        {
            this.expand_icon.set('src',this.expand_icon.alt);
        }
        this.is_open = true;
    },

    close: function()
    {
        var expander = this.item.get('slide');
        expander.slideOut();
        if ($defined(this.open_content))
        {
            for (var i=0;i<this.open_content.length;++i)
            {
                this.open_content[i].setStyle('display','none');
            }
        }

        if ($defined(this.close_content))
        {
            for (var i=0;i<this.close_content.length;++i)
            {
                this.close_content[i].setStyle('display','block');
            }
        }
        if ($defined(this.expand_icon))
        {
            this.expand_icon.set('src',this.expand_icon.title);
        }
        this.is_open = false;
    },

    isOpen : function()
    {
        return this.is_open;
    },

    toggle: function()
    {
        if (this.isOpen())
        {
            this.close();
        }
        else
        {
            this.open();
        }
    }
    });


window.addEvent('domready', function()
{
    $$('.revision_log').each(function(item, i)
    {
        var item_slide = item.getElement('.revisioninfo');
        var open_content  = new Array();
        var close_content = new Array();
        open_content.push(item.getElement('.long_description'));
        close_content.push(item.getElement('.short_description'));
        var expand_icon = item.getElement('.expand_icon');
        var colapsable = new Colapsable(item_slide,expand_icon,open_content,close_content);
        
        item.getElement('.expand_revisioninfo').addEvent('click',function(){colapsable.toggle();});
        item.colapsable = colapsable;
    });

    $$('.diffBox').each(function(item, i)
    {
        var item_slide = item.getNext('.diffinfo');
        var expand_icon = item.getElement( '.expand_diff' );
        var colapsable = new Colapsable(item_slide,expand_icon,null,null,true);
        item.getElement( '.expand_diff' ).addEvent( 'click', function(){colapsable.toggle();});
        item.colapsable=colapsable;
    });
});

function toggle_expand_all(action)
{
    $$('.revision_log').each(function(item, i)
    {
    	var colapsable = item.colapsable;
        if(action == 'close')
        {
            $('expand_all').setStyle('display','block');
            $('collapse_all').setStyle('display','none');
            colapsable.close();
        }
        else if(action == 'open')
        {
            $('expand_all').setStyle('display','none');
            $('collapse_all').setStyle('display','block');
            colapsable.open();
        }
    });
}

function toggle_expand_all_revisionview(action)
{
    $$('.diffBox').each(function(item, i)
    {
    	var colapsable = item.colapsable;
        if(action == 'close')
        {
            $('expand_all').setStyle('display','block');
            $('collapse_all').setStyle('display','none');
            colapsable.close();
        }
        else if(action == 'open')
        {
            $('expand_all').setStyle('display','none');
            $('collapse_all').setStyle('display','block');
            colapsable.open();
        }
    });
}

