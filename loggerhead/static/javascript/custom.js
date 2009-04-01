Y = YUI().use("node", "io-base", "anim");

var global_timeout_id = null;
var global_search_request = null;

Y.on(
  'domready',
  function()
  {
    var search_box = Y.get('#q');
    if (!Y.Lang.isNull(search_box))
    {
      function get_suggestions() {
        var query = search_box.get('value');
        var url = global_path + 'search?query=' + query;

        if (!Y.Lang.isNull(global_search_request))
        {
          global_search_request.abort();
        }
        global_search_request = Y.io(
          url,
          {
            on: {complete: cool_search},
            arguments: [query]
          }
        );

        var region = search_box.get('region');
        var current_query = search_box.get('value');

        Y.get('#search_terms').setStyle('display', 'block');
        Y.get('#search_terms').setStyle('position', 'absolute');
        Y.get('#search_terms').setStyle('left', region.left);
        Y.get('#search_terms').setStyle('top', region.bottom);
        Y.get('#search_terms').set('innerHTML','Loading...');
      }
      search_box.on(
        "keyup",
        function(event)
        {
          if(search_box.get('value') == '')
          {
            Y.get('#search_terms').setStyle('display', 'none');
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
  });

function cool_search(tid, response, query)
{
  var q = Y.get('#q');
  var region = q.get('region');
  var current_query = q.get('value');
  if (current_query == query)
  {
    Y.get('#search_terms').set('innerHTML', response.responseText);
    Y.get('#search_terms').setStyle('display', 'block');
    Y.get('#search_terms').setStyle('position', 'absolute');
    Y.get('#search_terms').setStyle('left', region.left);
    Y.get('#search_terms').setStyle('top', region.bottom);
  }
}

function hide_search()
{
  setTimeout("Y.get('#search_terms').setStyle('display','none')", 300);
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
  node.setStyle('position', 'absolute');
  node.setStyle('top', -1000000000);
  node.setStyle('display', 'block');
  var height = node.get('region').height;
  node.setStyle('display', 'none');
  node.setStyle('position', 'static');
  node.setStyle('top', 'auto');
  return height;
}

Collapsable.prototype._animate = function (callback)
{
  if (this.anim) this.anim.stop();

  this.anim = new Y.Anim(
    {
      node: this.container,
      from: {
        marginBottom: this.container.getStyle('marginBottom')
      },
      to: {
        marginBottom: 0
      },
      duration: 0.2
    });

  this.anim.run();
  this.anim.on('end', this.animComplete, this, callback);
}

Collapsable.prototype._load_finished = function(tid, res, args)
{
  var l = res.responseText.split('\n');
  l.splice(0, 1);
  var newNode = Y.Node.create(l.join(''));
  if (this.node_process)
    this.node_process(newNode);
  this.source = null;
  newNode.setStyle('display', 'none');
  this.loading.ancestor().insertBefore(newNode, this.loading);
  var delta = this.loading.get('region').height - get_height(newNode);
  newNode.setStyle('display', 'block');
  this.container.setStyle('marginBottom', parseFloat(this.container.getStyle('marginBottom')) + delta);
  this.loading.ancestor().removeChild(this.loading);
  this._animate(args[0]);
};

Collapsable.prototype._ensure_container = function(callback)
{
  if (this.container == null) {
    this.container = Y.Node.create('<div></div>');
    if (this.closed_node) {
      this.closed_node.ancestor().replaceChild(
        this.container, this.closed_node);
      this.container.appendChild(this.closed_node);
      if (this.open_node) {
        this.container.appendChild(this.open_node);
      }
    }
    else {
      this.open_node.ancestor().replaceChild(
        this.container, this.open_node);
      this.container.appendChild(this.open_node);
    }
    var outer = Y.Node.create('<div style="overflow:hidden;"></div>');
    this.container.ancestor().replaceChild(outer, this.container);
    outer.appendChild(this.container);
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
  this.expand_icon.set('src', expanded_icon_path);

  this._ensure_container();

  var open_height = get_height(this.open_node);

  var close_height;
  if (this.close_node) {
    close_height = this.close_node.get('region').height;
  }
  else {
    close_height = 0;
  }

  this.container.setStyle('marginBottom', close_height - open_height);
  if (this.close_node) {
    this.close_node.setStyle('display', 'none');
  }
  this.open_node.setStyle('display', 'block');

  this._animate(callback);

  if (this.source) {
    Y.io(
      this.source,
      {
        on: {complete: this._load_finished},
        arguments: [callback],
        context: this
      });
    return;
  }

};

Collapsable.prototype.animComplete = function(evt, callback)
{
  this.anim = null;
  if (this._loading) return;
  if (callback) callback();
  this.is_open = true;
};

Collapsable.prototype.close = function()
{
  this._ensure_container();

  var open_height = this.open_node.get('region').height;

  var close_height;
  if (this.close_node) {
    close_height = get_height(this.close_node);
  }
  else {
    close_height = 0;
  }

  var anim = new Y.Anim(
    {
      node: this.container,
      from: {
        marginBottom: 0
      },
      to: {
        marginBottom: close_height - open_height
      },
      duration: 0.2
    });
  anim.on("end", this.closeComplete, this);
  anim.run();
};

Collapsable.prototype.closeComplete = function () {
  this.open_node.setStyle('display', 'none');
  if (this.close_node) {
    this.close_node.setStyle('display', 'block');
  }
  this.container.setStyle('marginBottom', 0);
  this.expand_icon.set('src', collapsed_icon_path);
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

