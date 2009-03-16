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
  this.source_target = config.source_target;
  this.open_node = config.open_node;
  this.close_node = config.close_node;
  this.expand_icon = config.expand_icon;
  this.source = config.source;
  this.loading = config.loading;
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

Collapsable.prototype._load_finished = function(tid, res)
{
  var newNode = Y.Node.create(res.responseText.split('\n').splice(1).join(''));
  this.source_target.ancestor().replaceChild(newNode, this.source_target);
  this.source_target = null;
  this.source = null;
  this.loading.setStyle('display', 'none');
  this.open();
};

Collapsable.prototype.open = function()
{
  if (this.source) {
    this.loading.setStyle('display', 'block');
    Y.io(
      this.source,
      {
        on: {complete: this._load_finished},
        context: this
      });
    return;
  }

  var open_height = get_height(this.open_node);

  var close_height;
  if (this.close_node) {
    close_height = this.close_node.get('region').height;
  }
  else {
    close_height = 0;
  }

  var container = this.open_node.ancestor('.container');

  var anim = new Y.Anim(
    {
      node: container,
      from: {
        marginBottom: close_height - open_height
      },
      to: {
        marginBottom: 0
      },
      duration: 0.2
    });

  anim.on('end', this.openComplete, this);
  container.setStyle('marginBottom', close_height - open_height);
  if (this.close_node) {
    this.close_node.setStyle('display', 'none');
  }
  this.open_node.setStyle('display', 'block');
  this.expand_icon.set('src', this.expand_icon.get('alt'));
  anim.run();
};

Collapsable.prototype.openComplete = function()
{
  this.is_open = true;
};

Collapsable.prototype.close = function()
{
  var container = this.open_node.ancestor('.container');

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
      node: container,
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
  this.open_node.ancestor('.container').setStyle('marginBottom', 0);
  this.expand_icon.set('src', this.expand_icon.get('title'));
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

