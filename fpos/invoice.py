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

class account_invoice(models.Model):
    _inherit = "account.invoice"
    
    email_invoice = fields.Boolean("E-Mail Invoice", compute="_email_invoice", readonly=True)
     
    @api.multi
    def invoice_validate(self):
        res = super(account_invoice, self).invoice_validate()
        for invoice in self:
            if not invoice.sent and invoice.email_invoice:
                
                template = self.env.ref('account.email_template_edi_invoice', False)
                message_obj = self.env["mail.compose.message"]
                                
                message = message_obj.with_context(
                    default_template_id=template.id,                                        
                    default_model="account.invoice",
                    default_res_id=invoice.id,
                    mark_invoice_as_sent=True,
                    default_partner_ids=[invoice.partner_id.id],
                    default_composition_mode="comment",
                    default_notify=True).create({})
                     
                message.send_mail()
                
        return res

    @api.one
    def _email_invoice(self):
        self.email_invoice = False

        if self.partner_id.email:
            order = self.env["pos.order"].sudo().search([("invoice_id","=",self.id)])
            if order:
                fpos_order = order.fpos_order_id
                if fpos_order and fpos_order.send_invoice:
                    self.email_invoice = True
                else:
                    order = order[0]
                    for payment in order.statement_ids:
                        if payment.statement_id.journal_id.fpos_invoice_email:
                            self.email_invoice = True
                            break
                   

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
                if line.product_id and line.product_id.id == status_id and not line.price_unit and not line.quantity and not "s" in line_format:
                    line_format += "s"
                    res[line.id] = line_format
        
        return res 