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
from openerp.addons.at_base import util

from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import localcontext

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
        "pos_name" : fields.char("Point of Sale Name", copy=False),
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
                                         ("pact_scan","Scan"),
                                         ("pact_cancel","Cancel Order")
                                         ], string="Action", help="Action on product selection"),
        "pos_sec" : fields.selection([("1","Section 1"),
                                      ("2","Section 2"),
                                      ("g","Group"),
                                      ("a","Addition")], string="Section", help="Section Flag"),
        "tmpl_pos_rate" : fields.float("POS Rate %", readonly=True),
        "fpos_profile_ids": fields.many2many("fpos.profile", "product_tmpl_fpos_profile_rel", "prod_tmpl_id", "profile_id", string="Profiles", copy=True),
        
        "base_product_id": fields.many2one("product.template", "Base Product", copy=False)
    }
    _defaults = {
        "sequence" : 10
    }
    _order = "sequence, name"
      

class product_product(osv.Model):
    _inherit = "product.product"
    _columns = {
        "pos_rate" : fields.float("POS Rate %", readonly=True)
    }
    
    def _pos_product_overview(self, cr, uid, ids, pricelist=None, context=None):
        categories = {}
        
        products = self.browse(cr, uid, ids, context=context)
        category_ids = list(set([p.pos_categ_id.id for p in products if p.pos_categ_id]))
        category_names = dict(self.pool["pos.category"].name_get(cr, uid, category_ids, context=context))
        product_names = dict(self.name_get(cr, uid, ids, context=context))
        
        prices = {}
        
        pricelist_id = context.get("pricelist_id")
        pricelist_obj = self.pool["product.pricelist"]
        if pricelist_id:
            pricelist = pricelist_obj.browse(cr, uid, pricelist_id, context=context)
        
        if pricelist:
            prices = pricelist_obj._price_get_multi(cr, uid, pricelist, 
                                        [(p, 1.0, None) for p in products], context=context)
        
        for product in products:
            category = product.pos_categ_id
            category_name = ""
            if category:
                category_name = category_names.get(category.id, category.name),
            
            ncategory = categories.get(category_name)
            if ncategory is None:
                ncategory = {
                    "name" : category_name,
                    "category" : category,
                    "products" : []                     
                }
                categories[category_name] = ncategory
            
            # add for template
            nprod = {
                "product" : product,
                "name" : product_names.get(product.id, product.name),
                "price": prices.get(product.id) or product.lst_price
            }   
            ncategory["products"].append(nprod)

        def getName(v):
            return v["name"]
        
        categories = sorted(categories.values(), key=getName)
        for category in categories:
            category["products"] = sorted(category["products"], key=getName)
                
        return categories
    
    def _update_pos_rate(self, cr, uid, start_date=None, history_months=1, nofilter=False, context=None):
        
        ranges = []
        if not nofilter:
            
            if not start_date:
                cr.execute("SELECT MAX(date_order) FROM pos_order")
                res = cr.fetchone()
                start_date = res and res[0] and util.strToDate(res[0]) or datetime.now()
                start_date = start_date - relativedelta(months=history_months)
                start_date = util.dateToStr(start_date)
            
            ranges.append("o.date_order >= '%s'" % start_date)
            
            if history_months:
                history_start_dt = util.strToDate(start_date) - relativedelta(years=1)
                history_delta = relativedelta(weeks=(history_months*2))
                history_start = util.dateToStr(history_start_dt - history_delta)
                history_end =  util.dateToStr(history_start_dt + history_delta)
                ranges.append("(o.date_order >= '%s' AND o.date_order <= '%s')" % (history_start, history_end))
            
        rangeStr = ranges and "AND (%s)" % " OR ".join(ranges) or ""
        query = ("SELECT p.id, COUNT(l) FROM product_product p  "
                   " INNER JOIN product_template pt ON pt.id = p.product_tmpl_id " 
                   " LEFT JOIN pos_order_line l ON l.product_id = p.id "  
                   " LEFT JOIN pos_order o ON o.id = l.order_id "
                   " WHERE pt.available_in_pos %s " 
                   " GROUP BY 1 " % rangeStr)
        cr.execute(query)
        
        res = cr.fetchall()
        total = 0.0        
        
        for product_id, usage in res:
            if usage:
                total += usage
                
        if total:
            for product_id, usage in res:
                if usage:
                    rate = (usage / total)*100.0
                    self.write(cr, uid, [product_id], {"pos_rate" : rate}, context=context)
                else:
                    self.write(cr, uid, [product_id], {"pos_rate" : 0.0}, context=context)

        # reset non used
        cr.execute("UPDATE product_product SET pos_rate = 0 WHERE product_tmpl_id IN "
                   " (SELECT pt.id FROM product_template pt WHERE NOT pt.available_in_pos) ")
        
        # update templates
        cr.execute("UPDATE product_template SET tmpl_pos_rate = 0")
        cr.execute("UPDATE product_template "
                   " SET tmpl_pos_rate = t.pos_rate " 
                   " FROM ( "                   
                   "  SELECT product_tmpl_id, SUM(p.pos_rate) AS pos_rate "
                   "  FROM product_product p " 
                   "  GROUP BY 1 "
                   " ) t "
                   " WHERE t.product_tmpl_id = id AND t.pos_rate IS NOT NULL")
         

    def _fpos_product_bulk_get(self, cr, uid, objs, *args, **kwarg):
        mapping_obj = self.pool["res.mapping"]
        
        # prepare context
        context = kwarg.get("context")
        if not isinstance(context, dict):
            context = {}
        else:
            context = dict(context)            
        context["display_default_code"] = False
        
        # uuid cache
        uuids = {}
        def get_uuid(obj):
            if not obj:
                return None
            key = (obj._name, obj.id)
            uuid = uuids.get(key, False)
            if uuid is False:
                uuid = mapping_obj._get_uuid(cr, uid, obj) or None
                uuids[key] = uuid
            return uuid
        
        # tax mapping
        taxMap = {}
        prices = {}
        
        get_sale_ok = lambda obj: obj.sale_ok
        
        # build mappings from profile
        profile_obj = self.pool["pos.config"]
        profile_id = profile_obj.search_id(cr, uid, [("user_id","=", uid)], context=context)
        if profile_id:
            profile = profile_obj.browse(cr, uid, profile_id, context=context)
            partner = profile.company_id.partner_id

            # get fiscal position
            fiscal_obj = self.pool['account.fiscal.position']
              
            # find fiscal position
            fiscalpos_id = None
            fiscalpos = partner.property_account_position          
            if not fiscalpos:
                fiscalpos_id = fiscal_obj.get_fiscal_position(cr, uid, profile.company_id.id, partner.id, context=context)
                if fiscalpos_id:
                    fiscalpos = fiscal_obj.browse(cr, uid, fiscalpos_id, context=context)
            
            
            # create tax map
            if fiscalpos:
                tax_obj = self.pool["account.tax"]                
                taxes = tax_obj.browse(cr, uid, tax_obj.search(cr, uid, [], context=context), context=context)
                for tax in taxes:
                    mapped_taxes_ids = fiscal_obj.map_tax(cr, uid, fiscalpos, [tax], context=context)
                    if mapped_taxes_ids:
                        taxMap[tax.id] = tax_obj.browse(cr, uid, mapped_taxes_ids[0], context=context)
                    else:
                        taxMap[tax.id] = None
                        
            # create price list
            if profile.pricelist_id:
                prices = self.pool['product.pricelist']._price_get_multi(cr, uid, profile.pricelist_id, [(o, 1, None) for o in objs], context=context)
                        
            # product profiles
            fpos_profiles = profile.fpos_profile_ids
            if fpos_profiles:
              sale_product_ids = set(self.pool["product.product"].search(cr, uid, [("fpos_profile_ids","in",fpos_profiles.ids),("id","in",objs.ids)]))
              get_sale_ok = lambda obj: obj.sale_ok and obj.id in sale_product_ids
        
        # build docs
        docs = []
        names = dict(self.name_get(cr, uid, [o.id for o in objs], context=context))
        for obj in objs:
            
            # read tax        
            taxes_id = []
            price_include = 0
            for tax in obj.taxes_id:
                tax = taxMap.get(tax.id, tax)
                if tax:
                    if tax.price_include:
                        price_include += 1
                    taxes_id.append(get_uuid(tax));
                
            netto = price_include == 0 and len(taxes_id) > 0
                
            # get price
            price = prices.get(obj.id, obj.lst_price)       
            
            # calc sale ok
            sale_ok = get_sale_ok(obj)
                
            # build product
            values =  {
                "_id" : get_uuid(obj),
                META_MODEL : obj._model._name,                
                "name" : names.get(obj.id,obj.name),
                "pos_name" : obj.pos_name or obj.name,
                "description" : obj.description,
                "description_sale" : obj.description_sale,
                "price" : price,
                "netto" : netto, 
                "uom_id" : get_uuid(obj.uom_id), 
                "nounit" : obj.uom_id.nounit,
                "code" : obj.code,
                "ean13" : obj.ean13,
                "image_small" : obj.image_small,
                "pos_categ_id" : get_uuid(obj.pos_categ_id),
                "income_pdt" : obj.income_pdt,
                "expense_pdt" : obj.expense_pdt,
                "to_weight" : obj.to_weight,
                "taxes_id" : taxes_id,
                "sequence" : obj.sequence,
                "active": obj.active,
                "available_in_pos" : obj.available_in_pos,
                "sale_ok" : sale_ok,
                "pos_color" : obj.pos_color,
                "pos_report" : obj.pos_report,
                "pos_fav" : obj.pos_fav,
                "pos_categ2_id" : get_uuid(obj.pos_categ2_id),
                "pos_rate" : obj.pos_rate,
                "type": obj.type
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
        
            docs.append(values)
            
        return docs  
    
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
            "bulk_get" : self._fpos_product_bulk_get,
            "put" : self._fpos_product_put,
            "lastchange" : self._jdoc_product_lastchange
        }
        
    def fpos_scan(self, cr, uid, code, context=None):
        # check for product
        product_id = self.search_id(cr, uid, [("ean13","=",code)], context=context)
        if not product_id:
            product_id = self.search_id(cr, uid, [("default_code","=",code)], context=context)
            if not product_id:
                raise Warning(_('Product with EAN %s not found') % code)    
        
        product = self.browse(cr, uid, product_id, context=context)
        if not product:
            raise Warning(_('No access for product with EAN %s') % code)
        
        jdoc_obj = self.pool["jdoc.jdoc"]
        jdoc_obj._jdoc_access(cr, uid, "product.product", product_id, auto=True, context=context)
        
        docs = self._fpos_product_bulk_get(cr, uid, [product], context=context)
        if not docs:
            raise Warning(_('No access for product with EAN %s') % code)

        return docs[0]
    
    def fpos_product_info(self, cr, uid, product_id, pricelist_id=None, partner_id=None, amount=1.0, context=None):
        mapping_obj = self.pool["res.mapping"]
        pricelist_obj = self.pool["product.pricelist"]
        
        pricelist = None
        product = None
        
        # product
        if product_id:
            if isinstance(product_id, basestring):
                product = mapping_obj._browse_mapped(cr, uid, product_id, "product.product", context=context)
                product_id = product.id
            else:
                product = self.browse(cr, uid, product_id, context=context)
            
        # pricelist
        if pricelist_id:
            if isinstance(pricelist_id, basestring):
                pricelist = mapping_obj._browse_mapped(cr, uid, pricelist_id, "product.pricelist", context=context)
                pricelist_id = pricelist.id
            else:
                pricelist = pricelist_obj.browse(cr, uid, pricelist_id, context=context)
            
        # partner
        if partner_id:
            if isinstance(partner_id, basestring):
                partner_id = mapping_obj.get_id(cr, uid, "res.partner", partner_id)
                
            
        prices = pricelist_obj._price_get_multi(cr, uid, pricelist, [(product, amount, partner_id)], context=context)
        return {            
            "product_id": product_id,
            "price": prices[product_id],
            "amount": amount        
        }
        
    def fpos_stock(self, cr, uid, product_id, context=None):
        # product
        if product_id:
          if isinstance(product_id, basestring):
              product = self.pool["res.mapping"]._browse_mapped(cr, uid, product_id, "product.product", context=context)
              product_id = product.id
          else:
              product = self.browse(cr, uid, product_id, context=context)
        return product.qty_available
