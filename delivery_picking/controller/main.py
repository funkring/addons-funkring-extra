# -*- coding: utf-8 -*-
#############################################################################
#
#    Copyright (c) 2007 Martin Reisenhofer <martin.reisenhofer@funkring.net>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
import logging
import werkzeug.utils

_logger = logging.getLogger(__name__)

class delivery_picking(http.Controller):
        
    @http.route(["/delivery_picking/static/src/index.html"], type="http", auth="user")
    def app_index(self, debug=False, **kwargs):
        cr, session = request.cr, request.session
        html = request.registry["ir.ui.view"].render(cr, session.uid, "delivery_picking.app_index", {})
        return html
    
    @http.route(["/delivery_picking/static/app/index.html"], type="http", auth="user")
    def app_release_index(self, debug=False, **kwargs):
        cr, session = request.cr, request.session
        html = request.registry["ir.ui.view"].render(cr, session.uid, "delivery_picking.app_release_index", {})
        return html
    
    @http.route(["/picking"], type="http", auth="user")
    def app_redirect(self, debug=False, **kwargs):
        if debug:
            return werkzeug.utils.redirect("/delivery_picking/static/src/index.html?debug")
        else:
            return werkzeug.utils.redirect("/delivery_picking/static/src/index.html")
