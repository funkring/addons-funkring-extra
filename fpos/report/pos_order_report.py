# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.addons.at_base import extreport

class Parser(extreport.basic_parser):
    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            "prepare": self._prepare,            
        })
       
    def _prepare(self, orders):
        res = []
        
        tax_obj = self.pool["account.tax"]
        cur_obj = self.pool["res.currency"]
        
        for order in orders:
            fpos_order = None
                       
            if order._model._name == "pos.order":
                fpos_order = order.fpos_order_id
            if order._model._name == "fpos.order":
                fpos_order = order
            
            if not fpos_order:
                continue
            
            lines = []
            pos = 1
            
            partner = fpos_order.partner_id
            cur = fpos_order.currency_id
            
            for line in fpos_order.line_ids:
                values = { 
                    "line" : line,
                    "pos" : pos             
                }
                
                price = line.price
                if line.netto:
                    values["price_netto"] = price
                else:
                    taxes = tax_obj.compute_all(self.cr, self.uid, line.tax_ids, price, 1, line.product_id.id, partner and partner.id or False)
                    values["price_netto"] = cur_obj.round(self.cr, self.uid, cur, taxes['total'])
                              
                lines.append(values)
                pos += 1
            
            values =  {
                "order" : fpos_order,
                "lines" : lines,
                "currency" : fpos_order.currency_id.symbol,
                "partner_id" : fpos_order.partner_id,
                "mail_salutation" : "",
                "mail_address" : "",
                "partner_ref" : ""
            }
            
            partner = fpos_order.partner_id
            if partner:
                values["mail_salutation"] = partner.mail_salutation
                values["mail_address"] = partner.mail_address
                values["partner_ref"] = partner.ref
            
            res.append(values)
            
        return res
               
