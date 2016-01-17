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
from openerp.addons.jdoc.jdoc import META_MODEL

class product_product(osv.Model):
    _inherit = "product.product"
    
    def _fpos_product_get(self, cr, uid, obj, *args, **kwarg):
        mapping_obj = self.pool["res.mapping"]
        
        # read tax
        tax_name = None
        tax_incl = False
        tax_amount = 0.0
        tax_uuid = None
        
        for tax in obj.taxes_id:
            tax_name = tax.name
            tax_incl = tax.price_include
            tax_amount = tax.amount
            tax_uuid = mapping_obj._get_uuid(cr, uid, tax)
            break
        
        # build product
        return {
            "_id" : mapping_obj._get_uuid(cr, uid, obj),
            META_MODEL : obj._model._name,
            "name" : obj.name,
            "description" : obj.description,
            "description_sale" : obj.description_sale,
            "price" : obj.lst_price,
            "uom" : obj.uom_id.name,
            "uom_code" : obj.uom_id.code,
            "code" : obj.code,
            "ean13" : obj.ean13,
            "image" : obj.image_small,
            "pos_categ_id" : mapping_obj._get_uuid(cr, uid, obj.pos_categ_id),
            "income_pdt" : obj.income_pdt,
            "expense_pdt" : obj.expense_pdt,
            "to_weight" : obj.to_weight,
            "tax_name" : tax_name,
            "tax_amount" : tax_amount, 
            "tax_incl" : tax_incl,
            "tax_uuid" : tax_uuid
        }
    
    def _fpos_product_put(self, cr, uid, obj, *args, **kwarg):
        return None
    
    def _jdoc_product_lastchange(self, cr, uid, ids=None, context=None):
        lastchange = {}   
        
        cr.execute("SELECT MAX(p.write_date), MAX(pt.write_date), MAX(u.write_date) FROM product_product p "
                   " INNER JOIN product_template pt ON pt.id = p.product_tmpl_id "
                   " INNER JOIN product_uom u ON u.id = pt.uom_id ")
               
        res = cr.fetchone()
        if res:
            lastchange["product.product"] = res[0]
            lastchange["product.template"] = res[1]
            lastchange["product.uom"] = res[2]
            
        return lastchange
    
    def _fpos_product(self, cr, uid, *args, **kwargs):
        return {
            "get" : self._fpos_product_get,
            "put" : self._fpos_product_put,
            "lastchange" : self._jdoc_product_lastchange
        }
    
