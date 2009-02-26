#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
# Copyright (C) 2006  Goffredo Baroncelli <kreijack@inwind.it>
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

import os
import time

import bzrlib.errors
import bzrlib.textfile

from pygments import highlight
from pygments.lexers import guess_lexer, guess_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from paste.httpexceptions import HTTPBadRequest, HTTPServerError

from loggerhead.controllers import TemplatedBranchView
from loggerhead import util


class AnnotateUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.annotate'

    def annotate_file(self, file_id, revid):
        z = time.time()
        lineno = 1
        parity = 0

        file_revid = self._history.get_inventory(revid)[file_id].revision
	file_name  = os.path.basename(self._history.get_path(revid, file_id))
        tree = self._history._branch.repository.revision_tree(file_revid)

        try:
	    file_lines = tree.get_file_lines(file_id)

            bzrlib.textfile.check_text_lines(file_lines)

	    pa = PygmentAnnotater(file_name, '\n'.join(file_lines[:128]))
        except bzrlib.errors.BinaryFile:
                # bail out; this isn't displayable text
                yield util.Container(parity=0, lineno=1, status='same',
                                     text='(This is a binary file.)',
                                     change=util.Container())
        else:
            change_cache = {}

            last_line_revid = None
            for line_revid, text in tree.annotate_iter(file_id):
                if line_revid == last_line_revid:
                    # remember which lines have a new revno and which don't
                    status = 'same'
                else:
                    status = 'changed'
                    parity ^= 1
                    last_line_revid = line_revid
                    if line_revid in change_cache:
                        change = change_cache[line_revid]
                    else:
                        change = self._history.get_changes([line_revid])[0]
                        change_cache[line_revid] = change

                yield util.Container(
                    parity=parity, lineno=lineno, status=status,
                    change=change, text=pa.annotate(text))
                lineno += 1

        self.log.debug('annotate: %r secs' % (time.time() - z))

    def get_values(self, path, kwargs, headers):
        history = self._history
        branch = history._branch
        revid = self.get_revid()
        revid = history.fix_revid(revid)
        file_id = kwargs.get('file_id', None)
        if (file_id is None) and (path is None):
            raise HTTPBadRequest('No file_id or filename '
                                 'provided to annotate')

        if file_id is None:
            file_id = history.get_file_id(revid, path)

        # no navbar for revisions
        navigation = util.Container()

        if path is None:
            path = history.get_path(revid, file_id)
        filename = os.path.basename(path)

        change = history.get_changes([ revid ])[0]
        # If we're looking at the tip, use head: in the URL instead
        if revid == branch.last_revision():
            revno_url = 'head:'
        else:
            revno_url = history.get_revno(revid)

        # Directory Breadcrumbs
        directory_breadcrumbs = (
            util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'files'))

        # Create breadcrumb trail for the path within the branch
        try:
            inv = history.get_inventory(revid)
        except:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')
        branch_breadcrumbs = util.branch_breadcrumbs(path, inv, 'files')

        return {
            'revno_url': revno_url,
            'file_id': file_id,
            'path': path,
            'filename': filename,
            'navigation': navigation,
            'change': change,
            'contents': list(self.annotate_file(file_id, revid)),
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
        }


class PygmentAnnotater:
    def __init__(self, path, text):
	self.formatter = CustomHtmlFormatter(style='colorful')

	try:
	    self.lexer = guess_lexer_for_filename(path, text, stripall=False)
	except (ClassNotFound, ValueError):
	    try: 
		self.lexer = guess_lexer(text, stripall=False)
	    except (ClassNotFound, ValueError):
		self.lexer = TextLexer(stripall=False)

    def annotate(self, text):
	hl_text  = highlight(text.expandtabs(), self.lexer, self.formatter)
	hl_split = hl_text.find('<')

	hl_text  = hl_text[:hl_split].replace(' ', util.NONBREAKING_SPACE) + \
		   hl_text[hl_split:]

	return hl_text


class CustomHtmlFormatter(HtmlFormatter):
    def wrap(self, source, outfile):
	return self._wrap_code(source)

    def _wrap_code(self, source):
	yield 0, ''
	for i, t in source:
	    yield i, t
	    
	yield 0, ''
