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
from openerp.exceptions import Warning

class stock_picking(osv.Model):
    _inherit = "stock.picking"
    
    def picking_app_pack(self, cr, uid, picking_id, weight=0.0, context=None):
        if weight:
            self.write(cr, uid, picking_id, {"carrier_weight":weight}, context=context)
        
        self.action_done_from_ui(cr, uid, picking_id, context=context)
        return self.picking_app_get(cr, uid, picking_id, context=context)
    
    def picking_app_pack_notify(self, cr, uid, picking_id, context=None):
        self.pool["bus.bus"].sendone(cr, uid, "%s,%s" % (cr.dbname,'delivery_picking'), {"picking_id":picking_id, "action":"packed"})
        return True
    
    def picking_app_update(self, cr, uid, values, context=None):
        op_obj = self.pool["stock.pack.operation"]
        
        op_id = values and values.get("id") or None
        if not op_id:
            raise Warning(_("Empty Data"))
        
        op = op_obj.browse(cr, uid, op_id, context=context)
        if not op:
            raise Warning(_("No picking operation with id %s") % op_id)
        
        if op.processed != "true":
            package_count = values.get("package_count", 0)
            if package_count > 0:
                if package_count > 10:
                    package_count = 10
                qty_done = 1            
            else:
                qty_done = values.get("qty_done", 0)
                
            if qty_done > op.product_qty:
                qty_done = op.product_qty
            elif qty_done < 0:
                qty_done = 0
                
            op_obj.write(cr, uid, op_id, {
                "qty_done" : qty_done,
                "package_count" : package_count
            }, context=context)
        
        # load again
        op = op_obj.browse(cr, uid, op_id, context=context)
        return  {
            "id" : op.id,
            "name" : op.product_id.name,
            "uom" : op.product_uom_id.name,
            "qty" : op.product_qty,
            "qty_done" : op.qty_done or 0,
            "package_count" : op.package_count or 0
        }
    
    def picking_app_get(self, cr, uid, picking_id, context=None):
        if not picking_id:
            return {}
        
        picking = self.browse(cr, uid, picking_id, context=context)
        if not picking.state in ("partially_available","assigned"):
            if picking.group_id:
                picking_id = self.search_id(cr, uid, [("group_id","=",picking.group_id.id),("state","in",["partially_available","assigned"]),("picking_type_id.code","=",picking.picking_type_id.code)])
                if picking_id:
                    picking = self.browse(cr, uid, picking_id, context=context)
                else:
                    return {}
            else:
                return {}
        
        if not picking.pack_operation_ids:
            self.do_prepare_partial(cr, uid, [picking_id], context=context)
            picking = self.browse(cr, uid, picking_id, context=context)
        
        ops = []
        
        for op in picking.pack_operation_ids:
            ops.append({
                "id" : op.id,
                "name" : op.product_id.name,
                "uom" : op.product_uom_id.name,
                "qty" : op.product_qty,
                "qty_done" : op.qty_done or 0,
                "package_count" : op.package_count or 0
            })
        
        return {
            "id" : picking.id,
            "name" : picking.name,
            "ops" : ops
        }
    
    def picking_app_scan(self, cr, uid, code, context=None):
        if not code:
            return {}
        
        picking_id = self.pool["stock.picking"].search_id(cr, uid, [("name","ilike","%%%s" % code)], context=context)
        return self.picking_app_get(cr, uid, picking_id, context=context)
