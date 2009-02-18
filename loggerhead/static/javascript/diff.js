var Y = YUI().use("*");
var unified = true;
function doit(event) {
  if (unified) {
    Y.all(".pseudotable").each(
      function (chunk) {
        chunk.replaceClass('unified', 'sbs');
        var added = [];
        var removed = [];
        function clear_bufs(before) {
          if (!added.length && !removed.length) return;
          Y.log('hai');
          var common = Math.min(added.length, removed.length);
          for (var i = 0; i < common; i++) {
            var a = added[i];
            var r = removed[i];
            a.ancestor().removeChild(a);
            r.removeChild(r.query('.lineNumber.second'));
            r.insertBefore(a.query('.lineNumber.second'), r.query('.clear'));
            r.insertBefore(a.query('.code.insert'), r.query('.clear'));
            r.replaceClass('removed', 'both');
          }
          Y.log('hai');
          if (added.length > removed.length) {
            for (var j = common; j < added.length; j++) {
              a = added[j];
              a.insertBefore(a.create('<div class="blank">&nbsp;</div>'), a.query('.lineNumber.second'));
            }
          }
          else if (added.length < removed.length) {
            for (var j = common; j < removed.length; j++) {
              r = removed[j];
              r.insertBefore(r.query('.code.delete'), r.query('.lineNumber.second'));
              r.insertBefore(r.create('<div class="blank">&nbsp;</div>'), r.query('.clear'));
            }
          }
          added.length = 0;
          removed.length = 0;
        }
        chunk.get('children').filter(".pseudorow").each(
          function (line) {
            if (line.hasClass("context")) {
              clear_bufs(line);
              line.insertBefore(line.query('.code').cloneNode(true), line.query(".second"));
            }
            else if (line.hasClass("insert")) {
              added[added.length] = line;
            }
            else if (line.hasClass("delete")) {
              removed[removed.length] = line;
            }
          });
        clear_bufs(null);
      });
    unified = false;
  }
  else { // unified -> sbs
    Y.all(".pseudotable").each(
      function (chunk) {
        var pending_added = [];
        function flush_adds(before) {
          for (var i = 0; i < pending_added.length; i++) {
            before.ancestor().insertBefore(pending_added[i], before);
          }
          pending_added.length = 0;
        }
        chunk.get('children').filter(".pseudorow").each(
          function (line) {
            if (line.hasClass("context")) {
              flush_adds(line);
              line.removeChild(line.query('.code'));
            }
            else if (line.hasClass("both")) {
              var added_line = line.create('<div class="pseudorow insert"><div class="lineNumber first">&nbsp;</div><div class="clear">&nbsp;</div></div>');
              var clear = added_line.query('.clear');
              added_line.insertBefore(line.query('.lineNumber.second'), clear);
              added_line.insertBefore(line.query('.code.insert'), clear);
              pending_added[pending_added.length] = added_line;
              line.insertBefore(line.create('<div class="lineNumber second">&nbsp;</div>'), line.query('.code.delete'));
              line.replaceClass("both", "delete");
            }
            else if (line.hasClass("insert")) {
              flush_adds(line);
              line.removeChild(line.query('.blank'));
            }
            else if (line.hasClass("delete")) {
              line.removeChild(line.query('.blank'));
              line.insertBefore(line.query('.lineNumber.second'), line.query('.code.delete'));
            }
          });
        flush_adds(null);
        chunk.replaceClass('sbs', 'unified');
      });
    unified = true;
  }
}
