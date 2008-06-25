window.addEvent('domready', function()
{
    $$('.revision_log').each(function(item, i)
    {
        // FIXME: Make less redundant
        var expander = new Fx.Slide( item.getElement( '.revisioninfo' ), { duration: 200 } );
        var shortDescription = item.getElement( '.short_description' );
        var longDescription = item.getElement( '.long_description' );
        var expand_icon = item.getElement( '.expand_icon' );
        expander.hide();
        item.getElement( '.expand_revisioninfo' ).addEvent( 'click', function()
            {
                expander.toggle();
                if(longDescription.style.display == 'none')
                {
                    longDescription.style.display = 'block';
                    shortDescription.style.display = 'none';
                    expand_icon.src = expand_icon.alt;
                }
                else
                {
                    longDescription.style.display = 'none';
                    shortDescription.style.display = 'block';
                    expand_icon.src = expand_icon.title;
                }
            });
    });

    $$('.diff').each(function(item, i)
    {
        // FIXME: Make less redundant
        var expander = new Fx.Slide( item.getElement( '.diffinfo' ), { duration: 200 } );
        var expand_icon = item.getElement( '.expand_icon' );
        item.getElement( '.expand_diff' ).addEvent( 'click', function()
            {
                expander.toggle();
                /*if(longDescription.style.display == 'none')
                {
                    expand_icon.src = expand_icon.alt;
                }
                else
                {
                    expand_icon.src = expand_icon.title;
                }*/
            });
    });

});

function toggle_expand_all(action)
{
    $$('.revision_log').each(function(item, i)
    {
        // FIXME: Make less redundant
        var expander = new Fx.Slide( item.getElement( '.revisioninfo' ), { duration: 200 } );
        var shortDescription = item.getElement( '.short_description' );
        var longDescription = item.getElement( '.long_description' );
        if(action == 'close')
        {
            expander.slideOut();
            $('expand_all').style.display = 'block';
            $('collapse_all').style.display = 'none';

        }
        else if(action == 'open')
        {
            expander.slideIn();
            $('expand_all').style.display = 'none';
            $('collapse_all').style.display = 'block';
        }
                if(longDescription.style.display == 'none')
                {
                    longDescription.style.display = 'block';
                    shortDescription.style.display = 'none';
                }
                else
                {
                    longDescription.style.display = 'none';
                    shortDescription.style.display = 'block';
                }
    });
}
