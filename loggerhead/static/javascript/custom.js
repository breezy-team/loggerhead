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

