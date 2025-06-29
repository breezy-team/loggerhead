"""WSGI applications for serving Bazaar branches."""

import os

from paste import fileapp, urlparser

from ..util import convert_file_errors

static = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Static things can be cached for half a day, we could probably make this
# longer, except for just before rollout times.
static_app = urlparser.make_static(None, static, cache_max_age=12 * 60 * 60)

favicon_app = convert_file_errors(
    fileapp.FileApp(os.path.join(static, "images", "favicon.ico"))
)

robots_app = convert_file_errors(fileapp.FileApp(os.path.join(static, "robots.txt")))


def health_app(environ, start_response):
    start_response("200 OK", [])
    yield b"ok"
