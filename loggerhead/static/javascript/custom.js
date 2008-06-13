window.addEvent('domready', function()
{
    $$('.revision_log').each(function(item, i)
    {
        var thisSlider = new Fx.Slide( item.getElement( '.revisioninfo' ), { duration: 200 } );
        thisSlider.hide();
        item.getElement( '.expand_revisioninfo' ).addEvent( 'click', function(){ thisSlider.toggle(); } );
    });

});

