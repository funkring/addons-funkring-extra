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


class sale_order(osv.Model):
    
    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, order_lines, context=None):
        res = super(sale_order, self).onchange_pricelist_id(cr, uid, ids, pricelist_id, order_lines, context=context)
        default_partner_id = context.get("default_partner_id")
        if default_partner_id:
            partner_obj = self.pool["res.partner"]
            line_obj = self.pool["sale.order.line"]
            if default_partner_id:
                partner = partner_obj.browse(cr, uid, default_partner_id, context=context)
                if partner:
                    products = set()
                    vals = []
                    order_ids = self.search(cr, uid, [("partner_id","=",partner.id),("state","!=","cancel")], limit=10, order="date_order desc", context=context)
                    for order in self.browse(cr, uid, order_ids, context=context):
                        for line in order.order_line:
                            if line.product_id and line.product_id.active and not line.product_id.id in products:
                                products.add(line.product_id.id)
                                # add copy data
                                copy_vals = line_obj.copy_data(cr, uid, line.id, context=context)
                                copy_vals["product_uom_qty"] = 0.0
                                copy_vals["product_uos_qty"] = 0.0
                                del copy_vals["order_id"]
                                vals.append((0,0,copy_vals))                                
                    if vals:
                        if not "value" in res:
                            res["value"] = {}
                        res["value"]["order_line"] = vals
        return res

    def action_print_delivery(self, cr, uid, ids, context=None):
        res = self.pool["report"].get_action(cr, uid, ids, "fast_sale.report_sale_delivery", context=context)
        return res
   
    def action_group(self, cr, uid, ids, context=None):
        line_ids = []
        for order in self.browse(cr, uid, ids, context=context):
            if not order.state in ("draft","sent"):
                continue
            for line in order.order_line:
                if not line.product_uom_qty:
                    line_ids.append(line.id) 
            
        if line_ids:
            self.pool["sale.order.line"].unlink(cr, uid, line_ids, context=context)
            
        return True
    
    def confirm_force_all(self, cr, uid, ids, context=None):
        self.action_group(cr, uid, ids, context=context)
        return super(sale_order, self).confirm_force_all(cr, uid, ids, context=context)
    
    def action_group_invoice(self, cr, uid, ids, context=None):
        if ids:
            order = self.browse(cr, uid, ids[0], context=context)
            order_ids = self.search(cr, uid, [("partner_id","=",order.partner_id.id),("state","in",["draft","sent"])], context=context)
            if order_ids:
                self.confirm_force_all(cr, uid, order_ids, context=context)            
        return True
        

    _inherit = "sale.order"
