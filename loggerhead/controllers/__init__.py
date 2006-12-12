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

from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.inventory_ui import InventoryUI


log = logging.getLogger("loggerhead.controllers")

class Root (controllers.RootController):
    changes = ChangeLogUI()
    atom = AtomUI()
    revision = RevisionUI()
    inventory = InventoryUI()
    
    @turbogears.expose()
    def index(self):
        raise HTTPRedirect(turbogears.url('/changes'))
