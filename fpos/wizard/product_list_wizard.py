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
    sumup = fields.Boolean("Intelligent Sumup", default=True, help="Print only products are used with the selected price list")
    name = fields.Char("Name")
    description = fields.Text("Description")
    
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
                
            # intelligent product search      
            if wizard.sumup and self.pricelist_id:       
              partners = self.env["res.partner"].search([("property_product_pricelist","=",self.pricelist_id.id)])
              if partners:
                self._cr.execute("SELECT pt.pos_categ_id FROM pos_order_line l "
                                 " INNER JOIN pos_order o ON o.id = l.order_id AND o.partner_id IN %s"
                                 " INNER JOIN product_product p ON p.id = l.product_id "
                                 " INNER JOIN product_template pt ON pt.id = p.product_tmpl_id AND NOT pt.pos_categ_id IS NULL AND pt.active"
                                 " GROUP BY 1", (tuple(partners.ids),))
                
                pos_category_ids = [r[0] for r in self._cr.fetchall()]
                if pos_category_ids:
                  idomain = list(domain)
                  idomain.append(("pos_categ_id","in",pos_category_ids))
                  products = product_obj.search(idomain)
              
            if not products:     
              products = product_obj.search(domain)
           
            # get context
            pricelist_name = wizard.name
            report_ctx = self._context and dict(self._context) or {}
            if wizard.pricelist_id:
                report_ctx["pricelist_id"] = wizard.pricelist_id.id
                if not pricelist_name:
                  pricelist_name = _("Pricelist: %s") % wizard.pricelist_id.name
              
            if pricelist_name:
              report_ctx["product_list_name"] = pricelist_name
            if wizard.description:
              report_ctx["product_list_description"] = wizard.description 
                
            
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