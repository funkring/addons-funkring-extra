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
from openerp.exceptions import Warning

class fpos_order(models.Model):
    _name = "fpos.order"
    _description = "Fpos Order"
    
    name = fields.Char("Name")
    fpos_user_id = fields.Many2one("res.users", "Device", required=True, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    user_id = fields.Many2one("res.users", "User", required=True, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    partner_id = fields.Many2one("res.partner","Partner", readonly=True, states={'draft': [('readonly', False)]}, index=True)
    date = fields.Datetime("Date", required=True, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    seq = fields.Integer("Internal Sequence", readonly=True, index=True)
    ref = fields.Char("Reference", readonly=True, states={'draft': [('readonly', False)]})
    tax_ids = fields.One2many("fpos.order.tax", "order_id", "Taxes", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    payment_ids = fields.One2many("fpos.order.payment","order_id", "Payments", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    state = fields.Selection([("draft","Draft"),
                              ("paid","Paid"),
                              ("done","Done")], "Status", default="draft", readonly=True, index=True)
    
    note = fields.Text("Note")
    send_invoice = fields.Boolean("Send Invoice", index=True)
    amount_tax = fields.Float("Tax Amount")
    amount_total = fields.Float("Total")
    
    company_id = fields.Many2one("res.company", string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env["res.company"]._company_default_get("fpos.order"))
    
    currency_id = fields.Many2one("res.currency", "Currency", related="company_id.currency_id", store=True, readonly=True)
    
    line_ids = fields.One2many("fpos.order.line", "order_id", "Lines", readonly=True, states={'draft': [('readonly', False)]}, composition=False)
    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state not in ("draft"):
                raise Warning(_("You cannot delete an order which are not in draft state"))
        return super(fpos_order, self).unlink()
    
    @api.model
    def create(self, vals):
        return super(fpos_order, self).create(vals)
        

class fpos_order_line(models.Model):
    _name = "fpos.order.line"
    _description = "Fpos Order Line"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product", index=True)
    uom_id = fields.Many2one("product.uom", "Unit", required=True)
    tax_ids = fields.Many2many("account.tax", "fpos_line_tax_rel", "line_id", "tax_id", "Taxes")
    brutto_price = fields.Float("Brutto Price")
    qty = fields.Float("Quantity")
    subtotal_incl = fields.Float("Subtotal")
    discount = fields.Float("Discount %")
    notice = fields.Text("Notice")
    sequence = fields.Integer("Sequence")
 

class fpos_tax(models.Model):
    _name = "fpos.order.tax" 
    _description = "Fpos Order Tax"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    name = fields.Char("Name")
    amount_tax = fields.Float("Tax")
    
    
class fpos_payment(models.Model):
    _name = "fpos.order.payment"
    _description = "Fpos Payment"
    _rec_name = "journal_id"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    journal_id = fields.Many2one("account.journal", "Journal", required=True)
    amount = fields.Float("Amount")
    payment = fields.Float("Payment")
    
    
    