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
from openerp.addons.at_base import util
import re

class product_ean_wizard(models.TransientModel):
    _name = "fpos.product.ean.wizard"
    _description = "Product EAN Wizard"
    
    @api.multi
    def action_product_ean(self):
        context = self._context
        active_model = context.get("active_model")
        active_ids = context.get("active_ids")
                
        if not active_ids:
            return True
        
        if active_model == "product.template":
            self._cr.execute("SELECT pt.id, p.id FROM product_template pt "
                             " INNER JOIN product_product p ON p.product_tmpl_id = pt.id "
                             " WHERE pt.id IN %s ORDER BY 1 ",(tuple(active_ids),))

            active_model = "product.product"            
            active_ids = [r[1] for r in self._cr.fetchall()]
            
            
        if active_model == "product.product":
            seq_obj = self.env["ir.sequence"]
            product_obj = self.env["product.product"]
            for product in product_obj.search([("ean13","=",False),("id","in",active_ids)]):
                found = False
                next_seq = None
                while not found:
                    next_seq = seq_obj.get("internal.product.ean")
                    found = not product_obj.search([("ean13","=", next_seq)])
                
                ean13 = util.calcEanCRC(next_seq)
                product.ean13 = ean13
        
        return True