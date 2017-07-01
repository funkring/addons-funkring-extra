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

from openerp import models, fields, api, _

# class account_invoice(models.Model):
#     _inherit = "account.invoice"
#     
#     def invoice_validate(self):
#         res =  super(account_invoice, self).invoice_validate()
#         
#         # check for reconcilation with point of sale order
#         order_obj = self.env["pos.order"]
#         for invoice_id in self.ids:            
#             order = order_obj.search([("state","=","invoiced"),("invoice_id","=",invoice_id),("invoice_id.state","=","open")])
#             #order.statement_ids.confirm_statement()
#             order.reconcile_invoice()     
#         
#         return res
    

class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"
    
    @api.multi
    def _line_format(self):
        res = super(account_invoice_line, self)._line_format()        

        # format status as section
        data_obj = self.env["ir.model.data"]
        status_id = data_obj.xmlid_to_res_id("fpos.product_fpos_status",raise_if_not_found=False)
        if status_id:
            for line in self:
                line_format = res.get(line.id,"")
                if line.product_id and line.product_id.id == status_id and not "s" in line_format:
                    line_format += "s"
                    res[line.id] = line_format
        
        return res 