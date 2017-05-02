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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class res_partner(osv.Model):
   
    def _pending_order_count(self, cr, uid, ids, field_names, arg, context=None):
        res = dict.fromkeys(ids, 0)
        
        cr.execute("SELECT p.id, COUNT(o.id) FROM res_partner p "
                   " LEFT JOIN sale_order o ON o.partner_id = p.id AND o.state IN ('draft','sent','waiting_date') "
                   " WHERE p.id IN %s GROUP BY 1",(tuple(ids),))
        
        for oid, count in cr.fetchall():
            res[oid] = count
            
        return res
    
    def action_create_order(self, cr, uid, ids, context=None):
        for partner in self.browse(cr, uid, ids, context=context):
            view_mode = "form,tree"
            if partner.pending_order_count > 0:
                view_mode = "tree,form"
            return {
                "name": _("Orders"),
                "view_type": "form",
                "view_mode": view_mode,
                "res_model": "sale.order",
                "type": "ir.actions.act_window",
                "domain" : [("partner_id","=",partner.id),("state","in",["draft","sent","waiting_date"])],
                "context": {
                    "default_partner_id" : partner.id
                 }
              }
                
    
    _inherit = "res.partner"
    _columns = {
        "pending_order_count" : fields.function(_pending_order_count, string="Orders", type="integer", store=False)
    }
    
    