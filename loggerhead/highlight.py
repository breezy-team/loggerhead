#
# Copyright (C) 2009  Peter Bui <pnutzh4x0r@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

from html import escape

import breezy.osutils
from pygments import highlight as _highlight_func
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, guess_lexer, guess_lexer_for_filename
from pygments.util import ClassNotFound

DEFAULT_PYGMENT_STYLE = 'colorful'

# Trying to highlight very large files using pygments was killing
# loggerhead on launchpad.net, because pygments isn't very fast.
# So we only highlight files if they're 512K or smaller.
MAX_HIGHLIGHT_SIZE = 512000;

def highlight(path, text, encoding, style=DEFAULT_PYGMENT_STYLE):
    """
    Returns a list of highlighted (i.e. HTML formatted) strings.
    """

    if len(text) > MAX_HIGHLIGHT_SIZE:
        return list(map(escape, text.splitlines()))

    formatter = HtmlFormatter(style=style, nowrap=True, classprefix='pyg-')

    try:
        lexer = guess_lexer_for_filename(path, text[:1024], encoding=encoding)
    except (ClassNotFound, ValueError):
        try:
            lexer = guess_lexer(text[:1024], encoding=encoding)
        except (ClassNotFound, ValueError):
            lexer = TextLexer(encoding=encoding)

    hl_lines = _highlight_func(text, lexer, formatter)
    hl_lines = "".join(hl_lines).splitlines(True)

    return hl_lines
