var global_timeout_id = null;
var global_search_request = null;

$(function()
  {
    var search_box = $('#q');
    if (search_box != undefined)
    {
      function get_suggestions() {
        var query = search_box.value;
        var url = global_path + 'search?query=' + query;

        if (global_search_request != undefined)
        {
          global_search_request.abort();
        }
        global_search_request = $.get(url, {'query': query}).done(cool_search);

        var current_query = search_box.value;

        $('#search_terms').css({
            'display': 'block',
            'position': 'absolute',
            'left': search_box.left,
            'top': search_box.bottom,
            'innerHTML': 'Loading...',
      });
      search_box.on(
        "keyup",
        function(event)
        {
          if(search_box.value == '')
          {
            $('#search_terms').css({'display': 'none'});
          }
          else
          {
            if (null != global_timeout_id)
            {
              clearTimeout(global_timeout_id);
            }
            global_timeout_id = setTimeout(get_suggestions, 200);
          }
        });
      }
    }
});

function cool_search(tid, response, query)
{
  var q = $('#q');
  var current_query = q.value;
  if (current_query == query)
  {
    $('#search_terms').html(response.responseText);
    $('#search_terms').css({
       'display': 'block',
       'position': 'absolute',
       'left': q.left,
       'top': q.bottom,
    });
  }
}

function hide_search()
{
  setTimeout("$('#search_terms').css({'display': 'none'})", 300);
}

function Collapsable(config)
{
  this.is_open = config.is_open;
  this.open_node = config.open_node;
  this.close_node = config.close_node;
  this.expand_icon = config.expand_icon;
  this.source = config.source;
  this.loading = config.loading;
  this.node_process = config.node_process;
  this.container = null;
  this.anim = null;
  this._loading = false;
}

function get_height(node) {
  $(node).css({
     'position': 'absolute',
     'top': -1000000000,
     'display': 'block',
  });
  var height = $(node).height;
  $(node).css({
     'display': 'none',
     'position': 'static',
     'top': 'auto',
  });
  return height;
}

Collapsable.prototype._animate = function (callback)
{
  if (this.anim) this.anim.stop();

  this.anim = $(this.container).animate(
     {marginBottom: 0 }, 0.2, "swing" , function(event) {
       this.anim = null;
       if (this._loading) return;
       if (callback) callback();
       this.is_open = true;
     }.bind(this));
}

Collapsable.prototype._load_finished = function(data, callback)
{
  var l = data.split('\n');
  l.splice(0, 1);
  var newNode = $(l.join(''));
  if (this.node_process)
    this.node_process(newNode);
  this.source = null;
  newNode.css({'display': 'none'});
  newNode.insertBefore(this.loading);
  var delta = this.loading.height - get_height(newNode);
  newNode.css({'display': 'block'});
  this.container.css({'marginBottom': parseFloat(this.container.css('marginBottom')) + delta});
  this.loading.remove();
  this._animate(callback);
};

Collapsable.prototype._ensure_container = function(callback)
{
  if (this.container == null) {
    this.container = $('<div></div>');
    if (this.closed_node) {
      this.closed_node.ancestor().replaceChild(
        this.container, this.closed_node);
      this.container.appendChild(this.closed_node);
      if (this.open_node) {
        this.container.appendChild(this.open_node);
      }
    }
    else {
      $(this.open_node).replaceWith(this.container);
      $(this.container).append(this.open_node);
    }
    var outer = $('<div style="overflow:hidden;"></div>');
    this.container.replaceWith(outer);
    $(outer).append(this.container);
  }
}

/* What happens when you click open.
 *
 * 1. The arrow flips to the expanded position.
 *
 * 2. If necessary, the div which will be running the animation is
 * created and the open/closed content stuffed into it (and has height
 * set to the height of the closed content).
 *
 * 3. The open content is shown and the closed content is closed.
 *
 * 4. The animation to expose all of the open content is started.
 *
 * 5. If we have to do ajax to load content, start the request.
 *
 * 6. When the request completes, parse the content into a node, run
 * the node_process callback over it and replace the spinner (assumed
 * to be appropriately contained in the open node) with the new node.
 *
 * 7. If the animation showing the open content has not completed,
 * stop it.
 *
 * 8. Start a new animation to show the rest of the new content.
 */

Collapsable.prototype.open = function(callback)
{
  this.expand_icon[0].src = expanded_icon_path;

  this._ensure_container();

  var open_height = get_height(this.open_node);

  var close_height;
  if (this.close_node) {
    close_height = this.close_node.height;
  }
  else {
    close_height = 0;
  }

  $(this.container).css({'marginBottom': close_height - open_height});
  if (this.close_node) {
    $(this.close_node).css({'display': 'none'});
  }
  $(this.open_node).css({'display': 'block'});

  this._animate(callback);

  var collapsable = this;

  if (this.source) {
      $.get(this.source, function(data) {
            collapsable._load_finished(data, callback);
      });
    return;
  }

};

Collapsable.prototype.close = function()
{
  this._ensure_container();

  var open_height = this.open_node.height;

  var close_height;
  if (this.close_node) {
    close_height = get_height(this.close_node);
  }
  else {
    close_height = 0;
  }

  var anim = $(this.container).animate(
      { marginBottom: [0, close_height - open_height]},
      0.2, "swing", this.closeComplete.bind(this));
};

Collapsable.prototype.closeComplete = function () {
  $(this.open_node).css({'display': 'none'});
  if (this.close_node) {
    $(this.close_node).css({'display': 'block'});
  }
  $(this.container).css({'marginBottom': 0});
  this.expand_icon[0].src = collapsed_icon_path;
  this.is_open = false;
};

Collapsable.prototype.toggle = function()
{
  if (this.is_open)
  {
    this.close();
  }
  else
  {
    this.open();
  }
};

var notification_node = null;
/*
 * Display privacy notifications
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
function setup_privacy_notification(config) {
    if (notification_node !== null) {
        return;
    }
    var notification_text = 'The information on this page is private';
    var hidden = true;
    var target_id = "loggerheadCont";
    if (config !== undefined) {
        if (config.notification_text !== undefined) {
            notification_text = config.notification_text;
        }
        if (config.hidden !== undefined) {
            hidden = config.hidden;
        }
        if (config.target_id !== undefined) {
            target_id = config.target_id;
        }
    }
    var id_selector = "#" + target_id;
    var main = $(id_selector);
    notification_node = $('<div></div>')
        .addClass('global-notification');
    if (hidden) {
        notification_node.addClass('hidden');
    }
    var notification_span = $('<span></span>')
        .addClass('sprite')
        .addClass('notification-private');
    notification_node.set('innerHTML', notification_text);
    main.appendChild(notification_node);
    notification_node.appendChild(notification_span);
};

function display_privacy_notification() {
    /* Set a temporary class on the body for the feature flag,
     this is because we have no way to use feature flags in
     css directly. This should be removed if the feature
     is accepted. */
    var body = $(document.body);
    body.addClass('feature-flag-bugs-private-notification-enabled');
    // Set the visible flag so that the content moves down.
    body.addClass('global-notification-visible');

    setup_privacy_notification();
    var global_notification = $('.global-notification');
    if (global_notification.hasClass('hidden')) {
        global_notification.addClass('transparent');
        global_notification.removeClass('hidden');

        $(global_notification).animate({
            opacity: 1,
        }, 0.3);
        $(document.body).animate(
            {'paddingTop': '40px'}, 0.2, "easeOutBounce");
        $('.black-link').animate(
            {'top': '45px'}, 0.2, "easeOutBounce");
    }
};

$(function() {
    var body = $(document.body);
    if (body.hasClass('private')) {
        setup_privacy_notification();
        display_privacy_notification();
    }
});
