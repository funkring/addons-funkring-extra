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
from openerp.addons.at_base import util
from openerp.addons.at_base import format
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

class res_partner(osv.Model):
    
    def _groupable_amount(self, cr, uid, ids, field_names, arg, context=None):
        res = dict.fromkeys(ids)
        if ids:            
            for oid in ids:
                res[oid] = {
                    "ga_amount": 0.0,
                    "ga_count": 0
                } 
                
                
            cr.execute("SELECT f.partner_id, SUM(f.amount_total), COUNT(f.id) FROM pos_order o "
                       "INNER JOIN fpos_order f ON f.id = o.fpos_order_id "
                       "WHERE f.partner_id IN %s AND f.ga AND o.fpos_group_id IS NULL "
                       "GROUP BY 1 ", (tuple(ids),))
            
            for partner_id, amount, count in cr.fetchall():
                values = res[partner_id]
                values["ga_amount"] = amount
                values["ga_count"] = count
                
        return res
    
    def fpos_ga_order(self,cr, uid, partner_id, context=None):
        order_obj = self.pool["pos.order"]
        
        cr.execute("SELECT o.id FROM pos_order o "
                   "INNER JOIN fpos_order f ON f.id = o.fpos_order_id "
                   "WHERE f.partner_id = %s AND f.ga AND o.fpos_group_id IS NULL "
                   "ORDER BY o.date_order DESC ", (partner_id, ))
        
        order_ids = [r[0] for r in cr.fetchall()]
        res = []
        
        for order in order_obj.browse(cr, uid, order_ids, context=context):
            if not order:
                continue
            
            journals = []            
            for st in order.statement_ids:
                journal = st.statement_id.journal_id
                if journal.type != "cash":
                    journals.append(journal.name)
            
            journals.sort()
            
            res.append({
                "id": order.id,
                "date_order": order.date_order,
                "name": order.name,
                "pos_reference" : order.pos_reference,
                "amount_total": order.amount_total,
                "journal": ", ".join(journals) 
            })
            
        return res
    
    def fpos_ga_order_create(self, cr, uid, partner_id, order_ids, defaults=None, context=None):
        jdoc_obj = self.pool["jdoc.jdoc"]
        order_obj = self.pool["pos.order"]
        fpos_line_obj = self.pool["fpos.order.line"]
        fpos_order_obj = self.pool["fpos.order"]
        
        data_obj = self.pool["ir.model.data"]
        product_balance_id = data_obj.xmlid_to_res_id(cr, uid, "fpos.product_fpos_balance", raise_if_not_found=True)
        
        f = format.LangFormat(cr, uid, context=context)
        
        lines = []
        filtered_order_ids = []
        partner_id = None
        first = True
        
        order_ids = order_obj.search(cr, uid, [("id","in",order_ids)], context=context)
        for order in order_obj.browse(cr, SUPERUSER_ID, order_ids, context=context):            
            fpos_order = order.fpos_order_id
            if not fpos_order:
                continue

            if fpos_order.partner_id:
                partner_id = fpos_order.partner_id.id
                
            if partner_id != partner_id:
                continue
                                
            filtered_order_ids.append(order.id)  
            lines.append({
                "name": " ".join([f.formatLang(fpos_order.date, date_time=True), order.name]),
                "notice": order.pos_reference,
                "qty": 1,
                "price": fpos_order.amount_total,
                "subtotal_incl": fpos_order.amount_total,
                "subtotal": fpos_order.amount_total,                
                "tag": "s",
                "flags" : first and "1b" or "1bl" # main section
            })
            
            first = False
            
            line_values = None
            for fpos_line in fpos_order.line_ids:
                if fpos_line.tag and not fpos_line.tag in ("i","o"):
                    continue
                line_values = fpos_line_obj.copy_data(cr, uid, fpos_line.id, context=context)
                
                # replace product with none
                line_values["product_id"] = product_balance_id
                
                # sub section and payment
                flags = line_values.get("flags") or ""
                if flags.find("2") < 0:
                    flags += "2"
                if flags.find("x") < 0:
                    flags += "x"
                
                # correct negative
                idx_minus = flags.find("-")
                if idx_minus < 0 and fpos_line.subtotal_incl < 0:
                    flags += "-"                    
                elif idx_minus >= 0 and fpos_line.subtotal_incl > 0:
                    flags = flags.replace("-","")

                # set flags                    
                line_values["flags"] = flags
                                         
                # add            
                lines.append(line_values)
                
        # set values for order
        order_values = defaults and dict(defaults) or {}
        order_values["line_ids"] = [(0,0,l) for l in lines]
        order_values["fpos_user_id"] = uid
        if not "user_id" in order_values:
            order_values["user_id"] = uid
        if not "date" in order_values:
            order_values["date"] = util.currentDateTime()
        if not "ref" in order_values:
            order_values["ref"] = _("Group Invoice")
        if partner_id and not "partner_id" in order_values:
            order_values["partner_id"] = partner_id
            
        # create order
        fpos_ga_order_id = fpos_order_obj.create(cr, uid, order_values, context=context)
        # update order group
        order_obj.write(cr, uid, filtered_order_ids, {"fpos_group_id": fpos_ga_order_id}, context=context)

        res = jdoc_obj.jdoc_by_id(cr, uid, "fpos.order", fpos_ga_order_id, options={"empty_values":False}, context=context)
        return res
    
    _inherit = "res.partner"
    _columns = {
        "available_in_pos" : fields.boolean("Available in POS"),
        "ga_amount" : fields.function(_groupable_amount, type="float", store=False, string="Groupable POS Amount", multi="ga"),
        "ga_count" : fields.function(_groupable_amount, type="integer", store=False, string="Groupable Order Count", multi="ga"),
        "sale_discount": fields.float("Sale Discount %")
    }