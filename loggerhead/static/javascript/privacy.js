YUI.add('loggerhead.privacy', function(Y) {

var namespace = Y.namespace('loggerhead.privacy');

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
    var target_id = "maincontent";
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
    var main = Y.one(id_selector);
    notification_node = Y.Node.create('<div></div>')
        .addClass('global-notification');
    if (hidden) {
        notification_node.addClass('hidden');
    }
    var notification_span = Y.Node.create('<span></span>')
        .addClass('sprite')
        .addClass('notification-private');
    notification_node.set('text', notification_text);

    main.appendChild(notification_node);
    notification_node.appendChild(notification_span);
}
namespace.setup_privacy_notification = setup_privacy_notification;

/**
 * For unit tests - we need to reset the notification setup.
 */
namespace._reset_privacy_notification = function () {
    notification_node = null;
};

function display_privacy_notification() {
    /* Set a temporary class on the body for the feature flag,
     this is because we have no way to use feature flags in
     css directly. This should be removed if the feature
     is accepted. */
    var body = Y.one('body');
    body.addClass('feature-flag-bugs-private-notification-enabled');
    /* Set the visible flag so that the content moves down. */
    body.addClass('global-notification-visible');

    setup_privacy_notification();
    var global_notification = Y.one('.global-notification');
    if (global_notification.hasClass('hidden')) {
        global_notification.addClass('transparent');
        global_notification.removeClass('hidden');

        var fade_in = new Y.Anim({
            node: global_notification,
            to: {opacity: 1},
            duration: 0.3
        });
        var body_space = new Y.Anim({
            node: 'body',
            to: {'paddingTop': '40px'},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });
        var login_space = new Y.Anim({
            node: '.login-logout',
            to: {'top': '45px'},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });

        fade_in.run();
        body_space.run();
        login_space.run();
    }
}
namespace.display_privacy_notification = display_privacy_notification;

/*
 * Hide privacy notifications
 *
 * This should be called after the page has loaded e.g. on 'domready'.
 */
function hide_privacy_notification() {
    setup_privacy_notification();
    if (!Y.one('.global-notification').hasClass('hidden')) {
        var fade_out = new Y.Anim({
            node: '.global-notification',
            to: {opacity: 0},
            duration: 0.3
        });
        var body_space = new Y.Anim({
            node: 'body',
            to: {'paddingTop': 0},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });
        var login_space = new Y.Anim({
            node: '.login-logout',
            to: {'top': '6px'},
            duration: 0.2,
            easing: Y.Easing.easeOut
        });
        fade_out.on('end', function() {
            fade_out.get('node').addClass('hidden');
        });
        body_space.on('end', function() {
            Y.one('body').removeClass('global-notification-visible');
        });

        fade_out.run();
        body_space.run();
        login_space.run();

        var privacy_portlet =  Y.one('.portlet.private');
        if (privacy_portlet !== null) {
            var portlet_colour = new Y.Anim({
                node: privacy_portlet,
                to: {
                    color: '#fff',
                    backgroundColor:'#8d1f1f'
                },
                duration: 0.4
            });
            portlet_colour.run();
        }
    }
}
namespace.hide_privacy_notification = hide_privacy_notification;


}, "0.1", {"requires": ["base", "node", "anim"]});
