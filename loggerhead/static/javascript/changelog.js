function toggle_expand_all(action)
{
  var revlogs = Y.all('.revision_log');
  if (revlogs == null) return;
  revlogs.each(
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
    revlogs.each(
      function(item, i)
      {
        var revid = revids[item.get('id').replace('log-', '')];
        var collapsable = new Collapsable(
          {
            expand_icon: item.query('.expand_icon'),
            open_node: item.query('.long_description'),
            close_node: item.query('.short_description'),
            source: global_path + '+revlog/' + revid,
            source_target: item.query('.source_target'),
            loading: item.query('.loading'),
            is_open: false
          });

        item.query('.expand_revisioninfo a').on(
          'click',
          function(e) {
            e.preventDefault();
            collapsable.toggle();
          });
        item.collapsable = collapsable;
      });

  });
