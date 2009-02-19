YUI().use(
  "node", function (Y) {

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

  });


YUI().use(
  "node",
  function (Y) {
    Y.on(
      "domready", function () {
        Y.all(".show_if_js").removeClass("show_if_js");
      });
  });
