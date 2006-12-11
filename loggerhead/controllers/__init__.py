#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
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

import logging

import turbogears
from turbogears import controllers
from cherrypy import HTTPRedirect, NotFound

"""
from okulo.controllers.page_ui import PageUI
from okulo.controllers.login_ui import LoginUI, LogoutUI
from okulo.controllers.history_ui import HistoryUI
from okulo.controllers.edit_ui import EditUI
from okulo.controllers.contents_ui import ContentsUI
from okulo.controllers.source_ui import SourceUI
from okulo.controllers.search_ui import SearchUI
from okulo.controllers.add_ui import AddUI
from okulo.controllers.signup_ui import SignupUI
from okulo.controllers.atom_ui import AtomUI
from okulo.controllers.userhome_ui import UserHomeUI
from okulo.controllers.delete_ui import DeleteUI
"""
from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.atom_ui import AtomUI


log = logging.getLogger("loggerhead.controllers")

class Root (controllers.RootController):
    changes = ChangeLogUI()
    atom = AtomUI()
    
    @turbogears.expose(template="loggerhead.templates.welcome")
    def index(self):
        import time
        log.debug("Happy TurboGears Controller Responding For Duty")
        return dict(now=time.ctime())

"""
            if args['cmd'][0] == 'changelog':

                otherrevid = get("otherrevid")
                pathrevid = get("pathrevid")
                path = get("path")

                self.write(self.changelog(revno, None, path, pathrevid, otherrevid))

    def changelog(self, revid, search=None, path=None,
        pathrevid=None, otherrevid=None ):
            import cmd_changelog
            return cmd_changelog.changelog(self, revid, search, path,
                pathrevid, otherrevid )



    revid, history, pathrevid, otherrevid =
     hgweb.compute_history(revid, path,        pathrevid, otherrevid )
                                                    
                                                    
class Root (controllers.Root):
    page = PageUI()
    login = LoginUI()
    logout = LogoutUI()
    history = HistoryUI()
    edit = EditUI()
    contents = ContentsUI()
    source = SourceUI()
    search = SearchUI()
    add = AddUI()
    signup = SignupUI()
    atom = AtomUI()
    delete = DeleteUI()
    
    @turbogears.expose()
    def index(self, *args):
        raise HTTPRedirect(turbogears.url('/page/start'))
    
    @turbogears.expose()
    def default(self, *args):
        if args[0].startswith('~'):
            home = UserHomeUI(args[0][1:])
            if len(args) == 1:
                return home.index()
            return home.default(*args[1:])
        raise NotFound()
"""
