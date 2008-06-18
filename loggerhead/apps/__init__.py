#


static = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static')

static_app = urlparser.make_static(None, static)

