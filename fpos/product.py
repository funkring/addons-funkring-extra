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
from openerp.exceptions import Warning
from openerp.tools.translate import _

COLOR_NAMES = [("white", "White"),
               ("silver","Silver"),
               ("grey", "Gray"),
               ("black","Black"),
               ("red","Red"),
               ("maroon","Maroon"),
               ("yellow","Yellow"),
               ("olive","Olive"),
               ("lime","Lime"),
               ("green","Green"),
               ("aqua","Aqua"),
               ("teal","Teal"),
               ("blue","Blue"),
               ("navy","Navy"),
               ("fuchsia","Fuchsia"),
               ("purple","Purple"),
               #("orange","Orange"),
               ("darkbrown","Dark Brown"),
               ("brown","Brown"),
               ("lightbrown","Light Brown"),
               ("lightred","Light Red"),
               ("lightyellow","Light-Yellow"),
               ("lightgreen","Light Green"),
               ("lightblue","Light Blue"),
               ("lightestblue","Lightest Blue"),
               ("lightteal","Light Teal"),
               ("lightestteal","Lightest Teal"),
               ("darkestbrown","Darkest Brown"),
               ("darkestred","Darkest Red"),
               ("lightestyellow","Lightest-Yellow"),
               ("lightestgreen","Lightest Green"),
               ("lightestred","Lightest Red"),
               ("lightestgrey","Lightest Grey"),
               ("darkestgrey","Darkest Grey"),
               ("schoko","Schoko"),
               ("lightgold","Light Gold"),
               ("lightestgold","Lightest Gold")] 


class product_template(osv.Model):
    _inherit = "product.template"    
    _columns = {
        "sequence" : fields.integer("Sequence"),
        "pos_name" : fields.char("Point of Sale Name"),
        "pos_report" : fields.boolean("Show on Report"),
        "pos_color" : fields.selection(COLOR_NAMES, string="Color"),
        "pos_nogroup" : fields.boolean("No Grouping", help="If product selected again a extra line was created"),
        "pos_minus" : fields.boolean("Minus", help="Value is negative by default"),
        "pos_price_pre": fields.integer("Price Predecimal",help="Predicimal digits, -1 is no predecimal, 0 is no restriction"),
        "pos_price_dec" : fields.integer("Price Decimal",help="Decimal digits, -1 is no decimal, 0 is no restriction"),
        "pos_amount_pre" : fields.integer("Amount Predecimal",help="Predicimal digits, -1 is no predecimal, 0 is no restriction"),
        "pos_amount_dec" : fields.integer("Amount Decimal",help="Decimal digits, -1 is no decimal, 0 is no restriction"),
        "pos_price" : fields.boolean("Price Input"),
        "pos_categ2_id" : fields.many2one("pos.category","Category 2",help="Show the product also in this category"),
        "pos_fav" : fields.boolean("Favorite"),        
        "pos_cm" : fields.boolean("Comment"),
        "pos_action" : fields.selection([("pact_partner","Show Partner"),
                                         ("pact_scan","Scan")
                                         ], string="Action", help="Action on product selection"),
        "pos_sec" : fields.selection([("1","Section 1"),
                                      ("2","Section 2"),
                                      ("g","Group"),
                                      ("a","Addition")], string="Section", help="Section Flag")
    }
    _defaults = {
        "sequence" : 10
    }
    _order = "sequence, name"
      

class product_product(osv.Model):
    _inherit = "product.product"
    _columns = {
        "pos_rate" : fields.float("POS Sale Rate %", select=True)
    }
    
    def _update_pos_rate(self, cr, uid, context=None):
        cr.execute("SELECT pt.id, COUNT(l) FROM product_product p  "
                   " INNER JOIN product_template pt ON pt.id = p.product_tmpl_id " 
                   " LEFT JOIN pos_order_line l ON l.product_id = p.id "  
                   " WHERE pt.available_in_pos " 
                   " GROUP BY 1 ")
        
        res = cr.fetchall()
        total = 0.0        
        
        for product_id, qty in res:
            if qty:
                total += qty
                
        if total:
            for product_id, qty in res:
                if qty:
                    rate = qty / total
                    self.write(cr, uid, [product_id], {"pos_rate" : rate}, context=context)
                else:
                    self.write(cr, uid, [product_id], {"pos_rate" : 0.0}, context=context)
        
    def _fpos_product_get(self, cr, uid, obj, *args, **kwarg):
        mapping_obj = self.pool["res.mapping"]
        
        # read tax        
        taxes_id = []
        price_include = 0
        for tax in obj.taxes_id:
            if tax.price_include:
                price_include += 1
            taxes_id.append(mapping_obj._get_uuid(cr, uid, tax));
            
        netto = price_include == 0 and len(taxes_id) > 0
            
        # build product
        values =  {
            "_id" : mapping_obj._get_uuid(cr, uid, obj),
            META_MODEL : obj._model._name,
            "name" : obj.name,
            "pos_name" : obj.pos_name or obj.name,
            "description" : obj.description,
            "description_sale" : obj.description_sale,
            "price" : obj.lst_price or 0.0,
            "netto" : netto, 
            "brutto_price" : obj.brutto_price,
            "uom_id" : mapping_obj._get_uuid(cr, uid, obj.uom_id), 
            "nounit" : obj.uom_id.nounit,
            "code" : obj.code,
            "ean13" : obj.ean13,
            "image_small" : obj.image_small,
            "pos_categ_id" : mapping_obj._get_uuid(cr, uid, obj.pos_categ_id),
            "income_pdt" : obj.income_pdt,
            "expense_pdt" : obj.expense_pdt,
            "to_weight" : obj.to_weight,
            "taxes_id" : taxes_id,
            "sequence" : obj.sequence,
            "active": obj.active,
            "available_in_pos" : obj.available_in_pos,
            "sale_ok" : obj.sale_ok,
            "pos_color" : obj.pos_color,
            "pos_report" : obj.pos_report,
            "pos_fav" : obj.pos_fav,
            "pos_categ2_id" : mapping_obj._get_uuid(cr, uid, obj.pos_categ2_id),
            "pos_rate" : obj.pos_rate
        }
        
        if obj.pos_nogroup:
            values["pos_nogroup"] = True
        if obj.pos_minus:
            values["pos_minus"] = True
        if type(obj.pos_price_pre) in (int,long):
            values["pos_price_pre"] = obj.pos_price_pre
        if type(obj.pos_price_dec) in (int,long):
            values["pos_price_dec"] = obj.pos_price_dec
        if type(obj.pos_amount_pre) in (int,long):
            values["pos_amount_pre"] = obj.pos_amount_pre
        if type(obj.pos_amount_dec) in (int,long):
            values["pos_amount_dec"] = obj.pos_amount_dec            
        if obj.pos_price:
            values["pos_price"] = obj.pos_price
        if obj.pos_sec:
            values["pos_sec"] = obj.pos_sec
        if obj.pos_cm:
            values["pos_cm"] = obj.pos_cm
        if obj.pos_action:
            values["pos_action"] = obj.pos_action
        
        return values  
    
    def _fpos_product_put(self, cr, uid, obj, *args, **kwarg):
        return None
    
    def _jdoc_product_lastchange(self, cr, uid, ids=None, context=None):
        lastchange = {}   
        
        cr.execute("SELECT MAX(p.write_date), MAX(pt.write_date), MAX(u.write_date) FROM product_product p "
                   " INNER JOIN product_template pt ON pt.id = p.product_tmpl_id "
                   " INNER JOIN product_uom u ON u.id = pt.uom_id ")
               
        res = cr.fetchone()
        if res:
            lastchange["product.product"] = max(max(res[0],res[1]),res[2]) or res[0] or res[1] or res[2]
            lastchange["product.template"] = res[1]
            lastchange["product.uom"] = res[2]
            
        return lastchange
    
    def _fpos_product(self, cr, uid, *args, **kwargs):
        return {
            "get" : self._fpos_product_get,
            "put" : self._fpos_product_put,
            "lastchange" : self._jdoc_product_lastchange
        }
        
    def fpos_scan(self, cr, uid, code, context=None):
        # check for product
        product_id = self.search_id(cr, uid, [("ean13","=",code)], context=context)
        if not product_id:
            raise Warning(_('Product with EAN %s not found') % code)    
        
        product = self.browse(cr, uid, product_id, context=context)
        if not product:
            raise Warning(_('No access for product with EAN %s') % code)
        
        jdoc_obj = self.pool["jdoc.jdoc"]
        jdoc_obj._jdoc_access(cr, uid, "product.product", product_id, auto=True, context=context)
        return self._fpos_product_get(cr, uid, product, context=context)
