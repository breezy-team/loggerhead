function toggle_expand_all(action)
{
  $('.revision_log').each(
    function(i, item)
    {
      var collapsible = item.collapsible;
      if(action == 'close')
      {
        $('#expand_all').css({'display': 'block'});
        $('#collapse_all').css({'display': 'none'});
        collapsible.close();
      }
      else if(action == 'open')
      {
        $('#expand_all').css({'display': 'none'});
        $('#collapse_all').css({'display': 'block'});
        collapsible.open();
      }
    });
}

$(function() {
$('#expand_all a').on('click',
  function (event) {
    event.preventDefault();
    toggle_expand_all('open');
  },
);
});

$(function() {
$('#collapse_all a').on('click',
  function (event) {
    event.preventDefault();
    toggle_expand_all('close');
  },
);
});

$(function () {
    $(".show_if_js").removeClass("show_if_js");
});

$(function()
  {
    $('.revision_log').each(
      function(i, item)
      {
        var revid = revids[item.id.replace('log-', '')];
        var collapsible = new Collapsible(
          {
            expand_icon: $(item).find('.expand_icon'),
            open_node: $(item).find('.long_description'),
            close_node: $(item).find('.short_description'),
            source: global_path + '+revlog/' + revid,
            loading: $(item).find('.loading'),
            is_open: false
          });

        $(item).find('.expand_revisioninfo a').on(
          'click',
          function(e) {
            e.preventDefault();
            collapsible.toggle();
          });
        item.collapsible = collapsible;
      });

  });
