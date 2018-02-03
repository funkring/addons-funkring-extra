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

from openerp.osv import fields, osv

# class procurement_order(osv.Model):
#   _inherit = "procurement.order"
#   
#   def production_order_create_note(self, cr, uid, procurement, context=None):
#     # check dynamic bom
#     production = procurement.production_id
#     if production:
#       sale_order_line = procurement.sale_line_id
#       if sale_order_line:      
#         # check dynamic bom product
#         product = sale_order_line.product_id
#         if product and product.dynbom:
#           
#           # check dynamic bom order
#           order = sale_order_line.order_id
#           if order.dynbom_location_id:
#             prod_obj = self.pool["mrp.production"]
#             prod_line_obj = self.pool["mrp.production.product.line"]
#               
#             # update src 
#             prod_obj.write(cr, uid, production.id, 
#                            { "location_src_id": order.dynbom_location_id.id }, context=context)
#             
#             # add production line
#             for line in order.order_line:              
#               product = line.product_id              
#               if line.id != sale_order_line.id:                
#                   prod_line_obj.create(cr, uid, {
#                       "production_id": production.id,
#                       "name": line.name,
#                       "product_id": product.id,
#                       "product_qty": line.product_uom_qty,
#                       "product_uom": line.product_uom.id,
#                       "product_uos_qty": line.product_uos_qty,
#                       "product_uos": line.product_uos.id
#                     }, context=context)
#                          
#     super(procurement_order, self).production_order_create_note(cr, uid, procurement, context=context)
#     