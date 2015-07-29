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
from openerp.addons.at_base.format import LangFormat

SECTION_HEADER = 10
SECTION_BODY = 20

class fclipboard_item(models.Model):
    
    def _get_dtype_name(self):
        if self.dtype == "c":
            return self.valc
        elif self.dtype == "t":
            return self.valt
        elif self.dtype == "i":
            if type(self.vali) in (int,long):
                return str(self.vali)            
        elif self.dtype == "f":
            f = LangFormat(self._cr, self._uid, self._context)
            return f.formatLang(self.valf)
        elif self.dtype == "d":
            f = LangFormat(self._cr, self._uid, self._context)
            return f.formatLang(self.vald,date=True)
        elif self.dtype == "b":
            return self.valb and _("Yes") or _("No")
        return None
    
    def _get_rtype_name(self):
        if self.rtype:
            obj = self[self.rtype]
            name = obj.name_get()
            if name:
                return name[0][1]         
        return None
        
    @api.one
    def _compute_value(self):
        values = []
        
        dtype_val = self._get_dtype_name()
        if dtype_val:
            values.append(dtype_val)
            
        rtype_val = self._get_rtype_name()
        if rtype_val:
            values.append(rtype_val)
            
        self.value = " ".join(values)
            
    
    @api.one   
    @api.depends("parent_id")
    def _compute_root_id(self):
        if self.parent_id:
            self.root_id = self.parent_id.root_id.id
        else:
            self.root_id = self.id
        
    # fields
    name = fields.Char("Name", required=True, select=True)
    code = fields.Char("Code", select=True)
    
    dtype = fields.Selection([("c","Char"),
                              ("t","Text"),
                              ("i","Integer"),
                              ("f","Float"),
                              ("b","Boolean"),    
                              ("d","Date"),
                             ],"Type", select=True)
                             
       
    rtype = fields.Selection([("partner_id","Partner"),
                              ("product_id","Product"),
                              ("order_id","Order"),
                              ("pricelist_id","Pricelist")],
                              "Reference Type", select=True)
    
    section = fields.Selection([(SECTION_HEADER,"Header"),
                                (SECTION_BODY,"Body")],
                                   "Section", select=True, required=True)
    
    group = fields.Char("Group")
    owner_id = fields.Many2one("res.users", "Owner", ondelete="set null", select=True, default=lambda self: self._uid)
    active = fields.Boolean("Active", select=True)
    
    template = fields.Boolean("Template")
    required = fields.Boolean("Required")
    
    root_id = fields.Many2one("fclipboard.item","Root", select=True, compute="_compute_root_id", readonly=True)
    parent_id = fields.Many2one("fclipboard.item","Parent", select=True, ondelete="cascade", export=True, composition=False)
    child_ids = fields.One2many("fclipboard.item","parent_id", "Childs")
    
    sequence = fields.Integer("Sequence", select=True)
    
    valc = fields.Char("Info", help="String Value")
    valt = fields.Text("Description", help="Text Value")
    
    valf = fields.Float("Value", help="Float Value")
    vali = fields.Integer("Value", help="Integer Value")
    valb = fields.Boolean("Value", help="Boolean Value")
    vald = fields.Date("Value", help="Date Value")
        
    partner_id = fields.Many2one("res.partner","Partner", ondelete="restrict")
    product_id = fields.Many2one("product.product","Product", ondelete="restrict")
    order_id = fields.Many2one("sale.order","Sale Order", ondelete="restrict")
    pricelist_id = fields.Many2one("product.pricelist","Pricelist", ondelete="restrict")
    
    value = fields.Text("Value", readonly=True, compute="_compute_value")
  
    # main definition
    _name = "fclipboard.item"
    _description = "Item"  
    _order = "section, sequence"
    _defaults = {
        "sequence" : 20,
        "section" : 10,
        "active" : True
    }
    