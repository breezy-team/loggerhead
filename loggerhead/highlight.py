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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from pygments import highlight as _highlight_func
from pygments.lexers import guess_lexer, guess_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from loggerhead import util

DEFAULT_PYGMENT_STYLE = 'colorful'


def highlight(path, text, style=DEFAULT_PYGMENT_STYLE):
    """
    Returns a list of highlighted (i.e. HTML formatted) strings and it
    replaces initial spaces with nonbreaking spaces to maintain
    indentation.
    """

    formatter = PygmentsHtmlFormatter(style=style)

    encoding = 'utf-8'
    try:
        text = text.decode(encoding)
    except UnicodeDecodeError:
        text = text.decode(encoding)
        encoding = 'iso-8859-15'

    try:
        lexer = guess_lexer_for_filename(path, text, encoding=encoding)
    except (ClassNotFound, ValueError):
        try:
            lexer = guess_lexer(text, encoding=encoding)
        except (ClassNotFound, ValueError):
            lexer = TextLexer(encoding=encoding)

    hl_lines = _highlight_func(text, lexer, formatter).split('\n')
    hl_lines = [util.fix_whitespace(line) for line in hl_lines]

    return hl_lines


class PygmentsHtmlFormatter(HtmlFormatter):
    def wrap(self, source, outfile):
	return self._wrap_code(source)

    def _wrap_code(self, source):
	yield 0, ''
	for i, t in source:
	    yield i, t

	yield 0, ''
