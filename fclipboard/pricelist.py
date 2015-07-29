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

from openerp.osv import osv
from openerp.addons.jdoc.jdoc import META_MODEL
 
class product_sale_pricelist(osv.Model):
    
    def _jdoc_fclipboard_get(self, cr, uid, obj, *args, **kwargs):
        #context = kwargs.get("context",None)
        mapping_obj = self.pool["res.mapping"]
        products = []
        res = {
          "_id" : mapping_obj.get_uuid(cr, uid, obj._model._name, obj.id),
          META_MODEL : "product.pricelist",
          "name" : obj.name,
          "products" : products
        }
        
        def _jdoc_get_product(product):
            res = {
                "product_id" : mapping_obj.get_uuid(cr, uid, product._model._name, product.id),
                "name" : product.name,
                "uom" : product.uom_id.name,
                "code" : product.default_code,
                "category" : product.categ_id.name
                #"price" : self.price_get(cr, uid, [obj.id], product.id, 1, context=context)
            }
            return res
            
        
        version = obj.active_version_id
        if version:
            for item in version.items_id:
                if item.product_id:
                    product = _jdoc_get_product(item.product_id)
                    product["sequence"] = item.sequence
                    products.append(product)
        
        return res
    
    def _jdoc_fclipboard_lastchange(self, cr, uid, ids=None, context=None):
        lastchange = {}   
        
        cr.execute("SELECT MAX(pv.write_date), MAX(pi.write_date), MAX(pi.write_date), MAX(p.write_date) FROM product_pricelist pl "
                   " INNER JOIN product_pricelist_version pv ON pv.pricelist_id = pl.id "
                   " INNER JOIN product_pricelist_item pi ON pi.price_version_id = pv.id "
                   " INNER JOIN product_product p ON p.id = pi.product_id ")
        
               
        res = cr.fetchone()
        if res:
            lastchange["product.pricelist.version"] = res[0]
            lastchange["product.pricelist.item"] = res[1]
            lastchange["product.product"] = res[2]
        
        return lastchange
    
    def _jdoc_fclipboard(self, cr, uid, *args, **kwargs):
        return {
            "get" : self._jdoc_fclipboard_get,
            "lastchange" : self._jdoc_fclipboard_lastchange
        }
        
        
    _inherit = "product.pricelist"

