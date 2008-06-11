
/* reusable implementation of expand/collapse buttons, used to show/hide
 * "more detailed" sections of the page.
 */


var collapse_cache = new Object();
var collapse_all_cache = new Object();

function cacheElement(group, name, remainder, element) {
    var g = collapse_cache[group];
    if (typeof(g) == "undefined") {
        g = new Object();
        collapse_cache[group] = g;
    }
    var n = g[name];
    if (typeof(n) == "undefined") {
        n = new Array();
        g[name] = n;
    }
    n.push(new Array(remainder, element));
}

function cacheAllElement(group, name, element) {
    var g = collapse_all_cache[group];
    if (typeof(g) == "undefined") {
        g = new Array();
        collapse_all_cache[group] = g;
    }
    g.push(new Array(name, element));
}

/*
 * cache all the elements that have a collapse-<group>-<name>-* class on them.
 * javascript can be very slow so this should make the UI more responsive.
 */
function sortCollapseElements() {
    var elements = document.getElementsByTagName("*");
    for (var i = 0; i < elements.length; i++) {
        var classes = elements[i].className.split(' ');
        for (var j = 0; j < classes.length; j++) {
            if (classes[j].indexOf("collapse-") == 0) {
                var segments = classes[j].split('-');
                if (segments.length == 4) {
                    cacheElement(segments[1], segments[2], segments[3], elements[i]);
                }
                if (segments.length == 3) {
                    cacheAllElement(segments[1], segments[2], elements[i]);
                }
            }
        }
    }
}


function collapseContent(group, name) {
    return 'collapse-' + group + '-' + name + '-content';
}

function collapseDisplay(group, name, display) {
    // display mode for the disclosure triangles:
    var dthide = 'inline', dtshow = 'none';
    if (display == 'none') { dthide = 'none'; dtshow = 'inline'; }

    var elements = collapse_cache[group][name];
    for (var i in elements) {
        var kind = elements[i][0], node = elements[i][1];
        if (kind == "show") {
            node.style.display = dtshow;
        } else if (kind == "hide") {
            node.style.display = dthide;
        } else if (kind == "content") {
            node.style.display = display;
        }
    }
}

function collapseAllDisplay(group, display) {
    for (var name in collapse_cache[group]) {
        collapseDisplay(group, name, display);
    }
    
    var dthide = 'inline', dtshow = 'none';
    if (display == 'none') { dthide = 'none'; dtshow = 'inline'; }
    for (var element in collapse_all_cache[group]) {
        var x = collapse_all_cache[group][element];
        var name = x[0], node = x[1];
        if (name == "showall") {
            node.style.display = dtshow;
        } else if (name == "hideall") {
            node.style.display = dthide;
        }
    }
}


// for debugging
function debug(s) {
    var d = new Date();
    var hh = d.getHours(), mm = d.getMinutes(), ss = d.getSeconds(), ms = d.getMilliseconds();
    var ds = ((hh < 10) ? "0" + hh : hh) + ":" + ((mm < 10) ? "0" + mm : mm) + ":" + ((ss < 10) ? "0" + ss : ss) + "." + ((ms < 10) ? "00" + ms : ((ms < 100) ? "0" + ms : ms));
    console.log("[" + ds + "] " + s);
}

function diff_url(url) {
    if (document.cookie.indexOf('diff=unified') >= 0) {
        this.location.href = url + "-u";
    } else {
        this.location.href = url + "-s";
    }
}
