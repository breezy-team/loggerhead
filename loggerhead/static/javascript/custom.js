Y = YUI().use("node");

var global_timeout_id = null;
var global_search_request = null;

window.addEvent(
  'domready', function()
  {
    var search_box = $('q');
    if ($defined(search_box))
    {
      search_box.removeEvents();
      search_box.addEvents(
        {
          keyup: function()
          {
            if($('q').value == '')
            {
              $('search_terms').setStyle('display','none');
            }
            else
            {
              if (null != global_timeout_id)
              {
                clearTimeout(global_timeout_id);
              }
              global_timeout_id = setTimeout('$("q").fireEvent("search",$("q").value)',200);
            }
          },

          search: function(query)
          {
            url = global_path + 'search?query=' + query;

            if ($defined(global_search_request))
            {
              global_search_request.cancel();
            }
            global_search_request = new Request({'url':url,'method':'get','onComplete':function(response)
                                                 {
                                                   cool_search(response,query);
                                                 }});

            global_search_request.send('');
            var posicion = search_box.getPosition();
            var size     = search_box.getSize();

            $('search_terms').setStyle('position','absolute');
            $('search_terms').setStyle('left',posicion.x);
            $('search_terms').setStyle('top',posicion.y + size.y);
            $('search_terms').setStyle('display','block');
            $('search_terms').set('html','Loading...');

            new Request({'url':url,'method':'get','onComplete':cool_search}).send('');


          }
        });
    }
  });

function cool_search(response, query)
{
  var q = Y.get('#q');
  var region = q.get('region');
  var current_query = q.get('value');
  if (current_query == query)
  {
    Y.get('#search_terms').set('innerHTML', response);
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

function Colapsable(item, expand_icon, open_content, close_content, is_open)
{
  this.is_open = is_open;
  this.item = item;
  this.open_content  = open_content;
  this.close_content = close_content;
  this.expand_icon   = expand_icon;

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

Colapsable.prototype.open = function()
{
  this.item.setStyle('display', 'block');
  //var expander = this.item.get('slide');
  //expander.slideIn();
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

Colapsable.prototype.close = function()
{
  this.item.setStyle('display', 'none');
  //var expander = this.item.get('slide');
  //expander.slideOut();
  for (var i=0;i<this.open_content.length;++i)
  {
    this.open_content[i].setStyle('display','none');
  }

  for (var i=0;i<this.close_content.length;++i)
  {
    this.close_content[i].setStyle('display','block');
  }
  this.expand_icon.set('src',this.expand_icon.get('title'));
  this.is_open = false;
};

Colapsable.prototype.isOpen = function()
{
  return this.is_open;
};

Colapsable.prototype.toggle = function()
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

