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

class leakage_report(models.Model):
    _name = "leakage.report"
    _description = "Leakage Report"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    @api.model
    def _default_test_ids(self):
        res = []
        for test in self.env["leakage.test"].search([]):
            res.append((0,0,{
                "test_id" : test.id
            }))
        return res
    
    name = fields.Char("Name", default="/", required=True)
    shop_id = fields.Many2one("sale.shop", "Shop", required=True)
    date = fields.Date("Date", required=True)
    partner_id = fields.Many2one("res.partner", "Partner", required=True)
    address_id = fields.Many2one("res.partner", "Address")
    ref = fields.Char("Reference")
    
    order_id = fields.Many2one("sale.order","Order")
    user_id = fields.Many2one("res.partner", "Repairman")
    measure_from = fields.Datetime("Measure From")
    measure_to = fields.Datetime("Measure To")
    partner_ids = fields.Many2many("res.partner", "leakage_report_partner_rel", "report_id", "partner_id", "Present Partners")
    description = fields.Text("Description", help="Damage on arrival / damp areas")
    
    leakage_state = fields.Selection([("active","Active when measured"),
                                      ("inactive","Inactive when measured"),
                                      ("no_statement","No Statement possible")],
                                     "Leakage State")
    
    
    open_state = fields.Selection([("not_open","No Open"),
                                    ("opened","Openend by us"),
                                    ("opened_other","Opened by other")],
                                  "Open State")
    
    open_partner_id = fields.Many2one("res.partner","Opener")
    
    measure_noresult = fields.Boolean("No Result", help="Result could not be clarified")
    measure_result = fields.Text("Measure Result")
    
    work_description = fields.Text("Work Description")
    work_further = fields.Boolean("Further Work needed")
    
    floormat_state = fields.Selection([("no_damage","No Damage"),
                                       ("damage_mat","Damaged, but enough material for repair"),
                                       ("not_clear", "Not clear"),
                                       ("no_material","No Material"),
                                       ("material","Material available")],
                                      "Material Status")
    
    floormat_product_id = fields.Many2one("product.product", "Floor Product")
    floormat_name = fields.Char("Floor Material")
    floormat_amount = fields.Float("Floor Material amount")
        
    affected_cailing = fields.Float("Affected Cailing")
    affected_wall = fields.Float("Affected Wall")
    affected_floor = fields.Float("Affected Floor")
    affected_order = fields.Boolean("See order for details")
    affected_other = fields.Text("Affected Areas")
    
    damage_id = fields.Many2one("leakage.damage","Damage")
    damage_amount = fields.Float("Damage Amount")
       
    insurance_needed = fields.Boolean("Insurance needed")
    insurance_informed = fields.Boolean("Insurance informed")
    insurance_id = fields.Many2one("res.partner","Insurance")
    
    action_drying = fields.Boolean("Drying needed")
    action_drying_order = fields.Boolean("Order for Drying")
    action_renovation = fields.Boolean("Renovation needed")
    action_other = fields.Text("Other Actions")
    
    method_ids = fields.One2many("leakage.method", "report_id", "Methods")
    method_other = fields.Char("Other Method")
            
    test_ids = fields.One2many("leakage.report.test", "report_id", "Test", default=_default_test_ids)
    test_other = fields.Char("Other Test")
    
    material_ids = fields.Many2many("leakage.material", "leakage_report_material_rel", "report_id", "material_id", "Material")
    material_other = fields.Char("Other Material")
    
    @api.multi
    def onchange_order(self, order_id, shop_id=None, partner_id=None, user_id=None, address_id=None, ref=None):
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
    
    @api.model
    def create(self, vals):
        name = vals.get("name")
        if not name or name == "/":
            vals["name"] = self.env["ir.sequence"].get("leakage.report") or name
        return super(leakage_report, self).create(vals)    
    
        
class leakage_test(models.Model):
    _name = "leakage.test"
    _description = "Leakage Test"
    
    name = fields.Char("Name")
    type = fields.Selection([("pressure","Pressure Test"),
                            ("seal","Seal Test")],
                           "Type", required=True)
    

class leakage_report_test(models.Model):
    _name = "leakage.report.test"
    _description = "Leakage Test"
    _rec_name = "test_id"
    
    report_id = fields.Many2one("leakage.report","Report", required=True)
    test_id = fields.Many2one("leakage.test","Test", required=True)
    status = fields.Selection([("ok","OK"),
                               ("failed","Failed")],
                              "Status")
    

class leakage_method(models.Model):
    _name = "leakage.method"
    _description = "Leakage Method"
    
    report_id = fields.Many2one("leakage.report","Report", required=True)
    product_id = fields.Many2one("product.product", "Product")    
    name = fields.Char("Name", required=True)    
    uom_id = fields.Many2one("product.uom", "Unit", required=True)
    amount = fields.Float("Amount")
    
    @api.multi
    def product_id_change(self, product_id, name, uom_id):
        product_obj = self.env["product.product"]
        
        value = {}
        domain = {}
        
        if product_id:
            product = product_obj.browse(product_id)
            value["name"] = product.name
            uom = product.uos_id or product.uom_id
            value["uom_id"] = uom.id
            value["domain"] = [("category_id","=",uom.category_id.id)]
                
        return { "value": value, "domain": domain }
    
    
class leakage_material(models.Model):
    _name = "leakage.material"
    _description = "Material"
    
    name = fields.Char("Name", required=True)
    
    
class leakage_damage(models.Model):
    _name = "leakage.damage"
    _description = "Damage"
    
    name = fields.Char("Name", required=True)
