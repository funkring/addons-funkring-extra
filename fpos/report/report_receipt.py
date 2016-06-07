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

from openerp.osv import osv
from openerp.report import report_sxw


class order(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context=context)

        self.localcontext.update({
            "get_order" : self.get_order,
            "header" : self.header
        })

    def header(self, o):
        return o.session_id.config_id.receipt_header or ""

    def get_order(self, o):
        order_lines = []
        order_payment = []
        order_taxes = []
        order = { "lines" : order_lines,
                  "payment" : order_payment, 
                  "taxes" : order_taxes,
                  "cur" : o.session_id.currency_id.symbol}
        
        account_tax_obj = self.pool.get('account.tax')
        taxes_dict = {}
        
        # lines
        for line in o.lines:             
            taxes = [tax for tax in line.product_id.taxes_id if tax.company_id.id == line.order_id.company_id.id]

            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) 
            taxes_calc = account_tax_obj.compute_all(self.cr, self.uid, taxes, price, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
            
            # calc taxes
            netto = False
            if taxes:
                tax = taxes[0] 
                netto = not tax.price_include
                tax_value = taxes_dict.get(tax.id)
                amount_tax = taxes_calc["total_included"]-taxes_calc["total"]
                if tax_value is None:
                    tax_value = {
                        "name" : tax.name,
                        "amount_tax" : amount_tax,
                        "amount_netto" : taxes_calc["total"]
                    }
                    order_taxes.append(tax_value)
                    taxes_dict[tax.id] = tax_value
                else:
                    tax_value["amount_tax"] = tax_value["amount_tax"]+amount_tax
                    tax_value["amount_netto"] = tax_value["amount_netto"]+taxes_calc["total"]
                
            # order line
            l = {
                "l" : line,
                "flags" : "",
                "tag" : "",
                "netto" : netto,
                "a_dec" : 3,
                "unit" : line.product_id.uom_id.name
            }
            
            fpos_line = line.fpos_line_id
            if fpos_line:
                l["flags"] = fpos_line.flags or ""
                l["tag"] = fpos_line.tag or ""
                if fpos_line.a_dec > 0:
                    l["a_dec"] = fpos_line.a_dec
                elif fpos_line.a_dec < 0:
                    l["a_dec"] = 0
                
            order_lines.append(l)
            
        # get payment
        for stat in o.statement_ids:
            order_payment.append({
                "name" : stat.statement_id.journal_id.name,
                "amount" : stat.amount
            })
        
        return [order]
        

class report_order_receipt(osv.AbstractModel):
    _name = 'report.fpos.report_receipt'
    _inherit = 'report.abstract_report'
    _template = 'fpos.report_receipt'
    _wrapped_report_class = order

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
