var unified = true;

function make_unified(index) {
  var pending_added = [];
  function flush_adds(before) {
    for (var i = 0; i < pending_added.length; i++) {
      $(pending_added[i]).insertBefore(before);
    }
    pending_added.length = 0;
  }
  $(this).children().filter(".pseudorow").each(
    function (i, line) {
      line = $(line);
      if (line.hasClass("context-row")) {
        flush_adds(line);
        line.find('.code')[0].remove();
      }
      else if (line.hasClass("both-row")) {
        var added_line = $('<div class="pseudorow insert-row"><div class="lineNumber first">&nbsp;</div><div class="clear">&nbsp;</div></div>');
        var clear = $(added_line).find('.clear');
        $(line).find('.lineNumber.second').insertBefore(clear);
        $(line).find('.code.insert').insertBefore(clear);
        pending_added[pending_added.length] = added_line;
        $('<div class="lineNumber second">&nbsp;</div>').insertBefore($(line).find('.code.delete'));
        line.addClass('delete-row').removeClass('both-row');
      }
      else if (line.hasClass("insert-row")) {
        flush_adds(line);
        line.find('.blank').remove();
      }
      else if (line.hasClass("delete-row")) {
        $(line).find('.blank').remove();
        $(line).find('.lineNumber.second').insertBefore($(line).find('.code.delete'));
      }
    });
  flush_adds(null);
  $(this).addClass('unified').removeClass('sbs');
}

function make_sbs(index) {
  var added = [];
  var removed = [];
  function clear_bufs(before) {
    if (!added.length && !removed.length) return;
    var common = Math.min(added.length, removed.length);
    for (var i = 0; i < common; i++) {
      var a = added[i];
      var r = removed[i];
      a.remove();
      r.find('.lineNumber.second').remove();
      $(a).find('.lineNumber.second').insertBefore($(r).find('.clear'));
      $(a).find('.code.insert').insertBefore($(r).find('.clear'));
      r.addClass('both-row').removeClass('removed-row');
    }
    if (added.length > removed.length) {
      for (var j = common; j < added.length; j++) {
        a = $(added[j]);
        a.find('.lineNumber.second').before('<div class="code blank">&nbsp;</div>');
      }
    }
    else if (added.length < removed.length) {
      for (var j = common; j < removed.length; j++) {
        r = $(removed[j]);
        r.find('.code.delete').insertBefore(r.find('.lineNumber.second'));
        r.find('.clear').before('<div class="code blank">&nbsp;</div>')
      }
    }
    added.length = 0;
    removed.length = 0;
  }
  $(this).children().filter(".pseudorow").each(
    function (i, line) {
      line = $(line);
      if (line.hasClass("context-row")) {
        clear_bufs(line);
        $(line).find(".second").before($(line).find('.code').clone());
      }
      else if (line.hasClass("insert-row")) {
        added[added.length] = line;
      }
      else if (line.hasClass("delete-row")) {
        removed[removed.length] = line;
      }
    });
  clear_bufs(null);
  $(this).addClass('sbs').removeClass('unified');

}

function toggle_unified_sbs(event) {
  event.preventDefault();
  var pts = $(".pseudotable");
  if (unified) {
    pts && pts.each(make_sbs);
    unified = false;
    $("#toggle_unified_sbs").html("Show unified diffs");
  }
  else {
    pts && pts.each(make_unified);
    unified = true;
    $("#toggle_unified_sbs").html("Show diffs side-by-side");
  }
}

$(function() {
$('#toggle_unified_sbs').on("click", toggle_unified_sbs);
});

function toggle_expand_all_revisionview(action)
{
  var diffs = $('.diff');
  if (diffs == null) return;
  diffs.each(
    function(i, item)
    {
      var collapsable = item.collapsable;
      if(action == 'close')
      {
        $('#expand_all').css({'display': 'block'});
        $('#collapse_all').css({'display': 'none'});
        collapsable.close();
      }
      else if(action == 'open')
      {
        $('#expand_all').css({'display': 'none'});
        $('#collapse_all').css({'display': 'block'});
        collapsable.open();
      }
    });
}

$(function() {
$('#expand_all a').on(
  'click',
  function (event) {
    event.preventDefault();
    toggle_expand_all_revisionview('open');
  },
);
});

$(function() {
$('#collapse_all a').on(
  'click',
  function (event) {
    event.preventDefault();
    toggle_expand_all_revisionview('close');
  },
);
});

function node_process(node) {
  if (!unified) {
    node.children().filter('.pseudotable').each(make_sbs);
  }
}

function zoom_to_diff (path) {
  var collapsable = $('#' + path_to_id[path]).collapsable;
  if (!collapsable.is_open) {
    collapsable.open(
      function () {
        window.location.hash = '#' + path;
      });
  }
}

var original_diff_download_link = null;

function compute_diff_links() {
  var numlines = $('#contextLines').val();
  $('.diff').each(
    function(i, item)
    {
      item.collapsable.source = global_path + '+filediff/' + link_data[item.id] + '?context=' + numlines;
    });
  if(original_diff_download_link == null) original_diff_download_link = $('#download_link').attr('href');
  $('#download_link').attr('href', original_diff_download_link + '?context=' + numlines);
}

function get_num_lines() {
  var numlines = $('#contextLines').val();
  return numlines;
}

$(function () {
    $(".show_if_js").removeClass("show_if_js");
    if (!specific_path) {
      $("a#list-files").on(
        'click',
        function (e) {
          e.preventDefault();
          var path = decodeURIComponent(e.target.href.split('#')[1]);
          window.location.hash = '#' + path;
          zoom_to_diff(path);
        });
    }
    var diffs = $('.diff');
    if (diffs == null) return;
    var numlines = $('#contextLines').val();
    diffs.each(
      function(i, item)
      {
        var source_url = global_path + '+filediff/' + link_data[item.id] + '?context=' + numlines;
        $(item).find('.the-link').on(
          'click',
          function(e) {
            e.preventDefault();
            item.collapsable.source = global_path + '+filediff/' + link_data[item.id] + '?context=' + $('#contextLines').val();
            collapsable.toggle();
          });
        var collapsable = new Collapsable(
          {
            expand_icon: $(item).find('.expand_diff'),
            open_node: $(item).find('.diffinfo'),
            close_node: null,
            source: source_url,
            is_open: specific_path != null,
            loading: $(item).find('.loading'),
            node_process: node_process
          });
       item.collapsable=collapsable;
       });
    compute_diff_links();
    if (window.location.hash && !specific_path) {
      zoom_to_diff(window.location.hash.substring(1));
    }
  });
