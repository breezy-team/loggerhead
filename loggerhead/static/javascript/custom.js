window.addEvent('domready', function()
{
    $$('.revision_log').each(function(item, i)
    {
        // FIXME: Make less redundant
        var thisSlider = new Fx.Slide( item.getElement( '.revisioninfo' ), { duration: 200 } );
        var shortDescription = item.getElement( '.short_description' );
        var longDescription = item.getElement( '.long_description' );
        thisSlider.hide();
        item.getElement( '.expand_revisioninfo' ).addEvent( 'click', function()
            {
                thisSlider.toggle();
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
            } );
    });

});

function toggle_expand_all(action)
{
    $$('.revision_log').each(function(item, i)
    {
        // FIXME: Make less redundant
        var thisSlider = new Fx.Slide( item.getElement( '.revisioninfo' ), { duration: 200 } );
        var shortDescription = item.getElement( '.short_description' );
        var longDescription = item.getElement( '.long_description' );
        if(action == 'close')
        {
            thisSlider.slideOut();
            $('expand_all').style.display = 'block';
            $('collapse_all').style.display = 'none';

        }
        else if(action == 'open')
        {
            thisSlider.slideIn();
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
