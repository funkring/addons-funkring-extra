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

from openerp.osv import osv
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.web.controllers.main import content_disposition
import simplejson
import logging

_logger = logging.getLogger(__name__)

class fpos_export(http.Controller):
    
    @http.route(["/fpos/dep/<int:profile_id>"], type="http", auth="user", methods=["GET"])
    def dep_download(self, profile_id, **kwargs):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        
        if isinstance(profile_id, basestring):
            profile_id = int(profile_id)
          
        profile_obj = pool["pos.config"]
        profile = profile_obj.browse(cr, uid, profile_id, context=context)
        
        res = profile_obj._dep_export(cr, uid, profile, context=context)
        res = simplejson.dumps(res, indent=2)
        
        return request.make_response(
                res,
                [("Content-Type", "application/json"),
                 ("Content-Disposition", content_disposition("dep.json"))])
        