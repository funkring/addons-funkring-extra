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

class product_opt_wizard(models.TransientModel):
    _name = "product.opt.wizard"
    _description = "Product Optimizer"
    
    @api.multi
    def action_sort(self):
        product_obj = self.env["product.product"]
        product_obj._update_pos_rate()
      
        sequence = 0
        category_obj = self.env["pos.category"]      
          
        def sortProducts(categ_id, sequence):
            products = product_obj.search([("available_in_pos","=",True),("pos_categ_id","=",category.id),("pos_sec","in",["1","g"])], order="sequence asc")
            for product in products:
                sequence+=1
                product.sequence = sequence             
                
            products = product_obj.search([("available_in_pos","=",True),("pos_categ_id","=",category.id),("pos_sec","=",False)], order="pos_rate desc")
            for product in products:
                sequence+=1
                product.sequence =  sequence         
                
            products = product_obj.search([("available_in_pos","=",True),("pos_categ_id","=",category.id),("pos_sec","!=",False),'!',("pos_sec","in",["1","g"])], order="sequence asc")
            for product in products:
                sequence+=1                
                product.sequence = sequence
                
            return sequence
          
        # sort with category
        for category in category_obj.search([]):
            sequence = (category.sequence*1000)
            sequence = sortProducts(category.id, sequence)
            
        # sort without category
        sequence = sortProducts(None, sequence)
        return True
        