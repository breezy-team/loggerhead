
/* reusable implementation of expand/collapse buttons, used to show/hide
 * "more detailed" sections of the page.
 */


/* return all elements on this page which have a 'class' attribute that starts
 * with the given name, and for classes which were not exact matches, return
 * a separate list of the different unique suffixes found.
 */ 
function getElementsByClass(name) {
    var names = new Array();
    var nodes = new Array();

    var elements = document.getElementsByTagName('*');
    for (var i = 0; i < elements.length; i++) {
        var classes = elements[i].className.split(' ');
        for (var j = 0; j < classes.length; j++) {
            if (classes[j].indexOf(name) == 0) {
                var suffix = classes[j].substring(name.length).split('-')[0];
                if ((suffix.length > 0) && ! contains(names, suffix)) {
                    names.push(suffix);
                }
                nodes.push(elements[i]);
            }
        }
    }
    return [ nodes, names ];
}


/* python 'item in array' -- i can't believe javascript doesn't have this! */
function contains(arr, item) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i] == item) { return true; }
    }
    return false;
}

function collapseContent(group, name) {
    return 'collapse-' + group + '-' + name + '-content';
}

function collapseDisplay(group, name, display, nodes) {
    // display mode for the disclosure triangles:
    var dthide = 'inline', dtshow = 'none';
    if (display == 'none') { dthide = 'none'; dtshow = 'inline'; }

    if (typeof(nodes) == "undefined") {
        nodes = getElementsByClass('collapse-' + group + '-' + name + '-')[0];
    }
    var show_name = 'collapse-' + group + '-' + name + '-show';
    var hide_name = 'collapse-' + group + '-' + name + '-hide';
    var content_name = 'collapse-' + group + '-' + name + '-content';
    for (var i in nodes) {
        if (nodes[i].className.indexOf(show_name) >= 0) {
            nodes[i].style.display = dtshow;
        } else if (nodes[i].className.indexOf(hide_name) >= 0) {
            nodes[i].style.display = dthide;
        } else if (nodes[i].className.indexOf(content_name) >= 0) {
            nodes[i].style.display = display;
        }
    }
}

function collapseAllDisplay(group, display) {
    var elements = getElementsByClass('collapse-' + group + '-');
    var names = elements[1];
    var nodes = elements[0];
    for (var i in names) {
        if ((names[i] != 'show') && (names[i] != 'hide')) {
            collapseDisplay(group, names[i], display, nodes);
        }
    }
    
    var dthide = 'inline', dtshow = 'none';
    if (display == 'none') { dthide = 'none'; dtshow = 'inline'; }
    var showall_name = 'collapse-' + group + '-showall';
    var hideall_name = 'collapse-' + group + '-hideall';
    for (var i in nodes) {
        if (nodes[i].className.indexOf(showall_name) >= 0) {
            nodes[i].style.display = dtshow;
        } else if (nodes[i].className.indexOf(hideall_name) >= 0) {
            nodes[i].style.display = dthide;
        }
    }
}

