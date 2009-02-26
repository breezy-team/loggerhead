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

function Collapsable(item, expand_icon, open_content, close_content, is_open)
{
  this.is_open = is_open;
  this.item = item;
  this.open_content  = open_content;
  this.close_content = close_content;
  this.expand_icon   = expand_icon;

  if (this.is_open) {
    this.height = item.get('region').height;
  }
  else {
    this.height = null;
  }

  //var expander = new Fx.Slide(this.item, { duration: 200 } );
  if (!this.is_open)
  {
    this.expand_icon.set('src',this.expand_icon.get('title'));
  }
  else
  {
    this.expand_icon.set('src',this.expand_icon.get('alt'));
  }
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

Collapsable.prototype.open = function()
{
  if (this.height == null) {
    this.height = get_height(this.item);
  }

  var anim = new Y.Anim(
    {
      node: this.item,
      from: {
        height: 0
      },
      to: {
        height: this.height
      },
      duration: 0.2
    });
  anim.on('end', this.openComplete, this);
  this.item.setStyle('height', 0);
  this.item.setStyle('display', 'block');
  anim.run();
};

Collapsable.prototype.openComplete = function()
{
  for (var i=0;i<this.open_content.length;++i)
  {
    this.open_content[i].setStyle('display','block');
  }

  for (var i=0;i<this.close_content.length;++i)
  {
    this.close_content[i].setStyle('display','none');
  }

  this.expand_icon.set('src',this.expand_icon.get('alt'));
  this.is_open = true;
};

Collapsable.prototype.close = function()
{
  var item = this.item;
  var anim = new Y.Anim(
    {
      node: this.item,
      from: {
        height: this.height
      },
      to: {
        height: 0
      },
      duration: 0.2
    });
  anim.on("end", this.closeComplete, this);
  anim.run();
};

Collapsable.prototype.closeComplete = function () {
  this.item.setStyle('display', 'none');
  var i;
  for (i=0;i<this.open_content.length;++i)
  {
    this.open_content[i].setStyle('display','none');
  }

  for (i=0;i<this.close_content.length;++i)
  {
    this.close_content[i].setStyle('display','block');
  }
  this.expand_icon.set('src',this.expand_icon.get('title'));
  this.is_open = false;
};

Collapsable.prototype.isOpen = function()
{
  return this.is_open;
};

Collapsable.prototype.toggle = function()
{
  if (this.isOpen())
  {
    this.close();
  }
  else
  {
    this.open();
  }
};

