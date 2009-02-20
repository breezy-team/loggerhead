function toggle_expand_all(action)
{
  Y.all('.revision_log').each(
    function(item, i)
    {
      var collapsable = item.collapsable;
      if(action == 'close')
      {
        Y.get('#expand_all').setStyle('display','block');
        Y.get('#collapse_all').setStyle('display','none');
        collapsable.close();
      }
      else if(action == 'open')
      {
        Y.get('#expand_all').setStyle('display','none');
        Y.get('#collapse_all').setStyle('display','block');
        collapsable.open();
      }
    });
}

Y.on(
  'click',
  function (event) {
    event.preventDefault();
    toggle_expand_all('open');
  },
  '#expand_all a'
);

Y.on(
  'click',
  function (event) {
    event.preventDefault();
    toggle_expand_all('close');
  },
  '#collapse_all a'
);

Y.on(
  "domready", function () {
    Y.all(".show_if_js").removeClass("show_if_js");
  });

Y.on(
  'domready',
  function()
  {
    var revlogs = Y.all('.revision_log');
    if (revlogs == null) return;
    Y.all('.revision_log').each(
      function(item, i)
      {
        var item_slide = item.query('.revisioninfo');
        var open_content  = new Array();
        var close_content = new Array();
        open_content.push(item.query('.long_description'));
        close_content.push(item.query('.short_description'));
        var expand_icon = item.query('.expand_icon');
        var collapsable = new Collapsable(item_slide, expand_icon, open_content, close_content, false);

        item.query('.expand_revisioninfo').on('click',function(){collapsable.toggle();});
        item.collapsable = collapsable;
      });

  });
