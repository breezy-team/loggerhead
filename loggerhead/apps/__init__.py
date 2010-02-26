"""WSGI applications for serving Bazaar branches."""

import os

from paste import urlparser, fileapp

from loggerhead.util import convert_file_errors

static = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static')

static_app = urlparser.make_static(None, static)

favicon_app = convert_file_errors(fileapp.FileApp(
    os.path.join(static, 'images', 'favicon.ico')))

robots_app = convert_file_errors(fileapp.FileApp(
    os.path.join(static, 'robots.txt')))
