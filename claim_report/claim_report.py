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
from openerp.tools import image

class claim_report(models.Model):
    
    _name = "claim.report"
    _description = "Claim Report"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    name = fields.Char("Name", default="/", required=True)
    
    description = fields.Text("Description")
    customer_description = fields.Text("Customer Description")
    
    ref = fields.Char("Reference")
    shop_id = fields.Many2one("sale.shop", "Shop", required=True)
    
    date = fields.Datetime("Review Date")    
    user_id = fields.Many2one("res.users","User")
    
    order_id = fields.Many2one("sale.order", "Order")
    partner_id = fields.Many2one("res.partner", "Partner", required=True)
    address_id = fields.Many2one("res.partner", "Address")
    contact_id = fields.Many2one("res.partner", "Contact")
    categ_ids = fields.Many2many("crm.case.categ", "claim_report_crm_categ", "report_id", "categ_id", "Categories")
    
    insurance_id = fields.Many2one("res.partner", "Insurance")
    expert_id = fields.Many2one("res.partner", "Expert")
    
    claim_date = fields.Datetime("Claim Date")
    claim_partner_id = fields.Many2one("res.partner","Claim Partner")
    
    line_ids = fields.One2many("claim.report.line","claim_id","Documentation")
    
    @api.model
    def create(self, vals):
        name = vals.get("name")
        if not name or name == "/":
            vals["name"] = self.env["ir.sequence"].get("claim.report") or name
        return super(claim_report, self).create(vals)
    
    @api.multi
    def onchange_order(self, order_id, shop_id=None, partner_id=None, user_id=None, address_id=None, contact_id=None, ref=None):
        res = {}
        if order_id:
            value = {}
            res["value"] = value
            
            order = self.env["sale.order"].browse(order_id)
            if not shop_id:
                value["shop_id"] = order.shop_id.id
                
            if not partner_id:
                value["partner_id"] = order.partner_id.id
                
            if not user_id:
                value["user_id"] = order.user_id.id
                
            if not address_id:
                value["address_id"] = order.partner_shipping_id.id
                
            if not ref:
                value["ref"] = order.client_order_ref
            
        return res
            
            
    
    
class claim_report_line(models.Model):
    
    _name = "claim.report.line"
    _description = "Claim Report Line"
    
    name = fields.Char("Name", required=True)
    description = fields.Text("Description")
    claim_id = fields.Many2one("claim.report", "Report", required=True, ondelete="cascade")
    sequence = fields.Integer("Sequence", default=10)
    
    image = fields.Binary("Image")
    image_report = fields.Binary("Image", compute="_get_image",  readonly=True, store=True, help="resized as 256x256px image, with aspect ratio preserved")
    image_medium = fields.Binary("Image", compute="_get_image",  inverse="_set_image_m", store=True, help="resized as 128x128px image, with aspect ratio preserved")
    image_small = fields.Binary("Image", compute="_get_image",  inverse="_set_image_s", store=True,  help="resized as 64x64px image, with aspect ratio preserved")
    
    @api.one
    def _set_image_m(self):
        self.image = self.image_medium
        
    @api.one
    def _set_image_s(self):
        self.image = self.image_small
    
    @api.one
    @api.depends('image')
    def _get_image(self):
        self.image =  image.image_resize_image_big(self.image)
        self.image_report = image.image_resize_image_big(self.image,size=(256,256))
        self.image_medium = image.image_resize_image_medium(self.image)
        self.image_small = image.image_resize_image_small(self.image)
    