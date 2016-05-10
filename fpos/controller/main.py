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

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import content_disposition
import simplejson

class Config(http.Controller):
    
    @http.route("/fpos/export", type="http", auth="user")
    def build(self, wizard_type, wizard_id):
        wizard_id = simplejson.loads(wizard_id)
        wizard_obj = request.registry["fpos.wizard.export.%s" % wizard_type]
        fname, ctype, datas = wizard_obj.export(request.cr, request.uid, [wizard_id], context=request.context)
        return request.make_response(datas,
            headers=[
                 ("Content-Disposition", content_disposition(fname)),
                 ("Content-Type", ctype),
                 ("Content-Length", len(datas))]) 