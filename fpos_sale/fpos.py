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

from openerp import models, api

class fpos_order(models.Model):
    _inherit = "fpos.order"
    
    @api.model
    def post_order_notify(self, uuid):
        mapping_obj = self.env["res.mapping"]
        order_id = mapping_obj.get_id("fpos.order", uuid)
        if order_id:
            self.env["bus.bus"].sendone("%s,%s" % (self._cr.dbname,'post_order'), 
                                        {"forder_id": order_id,
                                         "uid" : self._uid } )
        return super(fpos_order, self).post_order_notify(uuid)