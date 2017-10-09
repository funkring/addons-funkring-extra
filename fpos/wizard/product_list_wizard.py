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

class product_list_wizard(models.TransientModel):
    _name = "fpos.product.list.wizard"
    _description = "Product List Wizard"
    
    pricelist_id = fields.Many2one("product.pricelist","Pricelist")
    type = fields.Selection([("private","Privat Customers"),
                            ("b2b","Business Customers"),
                            ("all","All")], string="Type", default="private", required=True)
    
    category_less = fields.Boolean("Print Categoryless")
    
    
    @api.multi
    def action_print(self):
        product_obj = self.env["product.product"]
                
        for wizard in self:
            products = None

            domain = not wizard.category_less and [("pos_categ_id","!=",False)] or []
            if wizard.type == "private":
                domain.append(("taxes_id.price_include","=",True))
            elif wizard.type == "b2b":
                domain.append(("taxes_id.price_include","!=",True))
                
            products = product_obj.search(domain)
           
            # get context
            report_ctx = self._context and dict(self._context) or {}
            if wizard.pricelist_id:
                report_ctx["pricelist_id"] = wizard.pricelist_id.id
                report_ctx["product_list_name"] = _("Pricelist: %s") % wizard.pricelist_id.name
                
            
            product_ids = [p.id for p in products]
            datas = {
                 "ids": product_ids,
                 "model": "product.product"
            }       
                
            # return
            return  {
                "type": "ir.actions.report.xml",
                "report_name": "pos.product.list",
                "datas": datas,
                "context" : report_ctx
            }
            
        return True