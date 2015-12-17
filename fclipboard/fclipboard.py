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


class fclipboard_rules(models.Model):
    
    item_id = fields.Many2one("fclipboard.item","Item",ondelete="cascade")
    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence", default=10)
    xpath = fields.Char("Path", default="/")    
    type = fields.Selection([("folder","Folder"),
                             ("product","Product"),
                             ("none","None")],
                             string="Type", required=True)
        
    _name = "fclipboard.rule"
    _description = "Rules"
    _order = "sequence"
        

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
            
        if dtype_val != "c" and self.valc:
            values.append(self.valc)
            
        rtype_val = self._get_rtype_name()
        if rtype_val:
            values.append(rtype_val)
            
        self.value = " ".join(values)
            
    @api.multi
    def action_open(self):
        act_obj = self.env["ir.actions.act_window"]
        action = act_obj.for_xml_id("fclipboard","action_fclipboard_item_open")
        if action:
            for item in self:            
                action["res_id"] = item.id
                return action
        return True
    
    @api.one
    def action_draft(self):
        self.state = "draft"
    
    @api.one
    def action_release(self):
        self.state = "released"
    
    @api.one
    def action_processed(self):
        self.state = "processed"
    
    @api.one   
    @api.depends("parent_id")
    def _compute_root_id(self):
        parent = self.parent_id
        root = self
        while parent:
            root = parent
            parent = parent.parent_id
        self.root_id = root.id
            
    @api.one
    def _value_ref(self):
        rtype = self.rtype
        res = None        
        if rtype:
            obj = self[rtype]
            if obj:
                res = "%s,%s" % (obj._model._name, obj.id)
        self.value_ref = res
                
    @api.one
    def action_validate(self):
        self._compute_root_id()
        for child in self.child_ids:
            child.action_validate()
                
    @api.multi
    def action_link(self):
        rtype = self.rtype
        if rtype:
            obj = self[rtype]
            if obj:
                return {
                    "type": "ir.actions.act_window",
                    "res_model":  obj._model._name,
                    "views": [[False, "form"]],
                    "res_id": obj.id,
                    "target": "current"
                }
        return True
        
        
    # fields
    name = fields.Char("Name", required=True, index=True)
    code = fields.Char("Code", index=True)
    
    dtype = fields.Selection([("c","Char"),
                              ("t","Text"),
                              ("i","Integer"),
                              ("f","Float"),
                              ("b","Boolean"),    
                              ("d","Date"),
                             ],"Type", index=True)
                             
       
    rtype = fields.Selection([("partner_id","Partner"),
                              ("product_id","Product"),
                              ("order_id","Order"),
                              ("pricelist_id","Pricelist")],
                              "Reference Type", index=True)
    
    section = fields.Selection([(SECTION_HEADER,"Header"),
                                (SECTION_BODY,"Body")],
                                   "Section", index=True, required=True, default=SECTION_HEADER)
    
    rule_ids = fields.One2many("fclipboard.rule", "item_id", "Rules", composition=True)
    
    group = fields.Char("Group")
    owner_id = fields.Many2one("res.users", "Owner", ondelete="set null", index=True, default=lambda self: self._uid)
    active = fields.Boolean("Active", index=True, default=True)
    
    template_id = fields.Many2one("fclipboard.item","Template", index=True, ondelete="set null", export=True, composition=False)
    
    template = fields.Boolean("Template")
    required = fields.Boolean("Required")
    
    root_id = fields.Many2one("fclipboard.item","Root", index=True, compute="_compute_root_id", readonly=True, store=True)
    parent_id = fields.Many2one("fclipboard.item","Parent", index=True, ondelete="cascade", export=True, composition=False)
    child_ids = fields.One2many("fclipboard.item","parent_id", "Childs")
    
    sequence = fields.Integer("Sequence", index=True, default=20)
    
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
    
    value = fields.Text("Value", readonly=True, copy=False, compute="_compute_value")
  
    state = fields.Selection([('draft','Draft'),
                              ('released','Released'),
                              ('processed','Processed')]
                             , string='Status', index=True, readonly=True, default="draft", copy=False)
    
    value_ref = fields.Reference([("res.partner","Partner"),
                                  ("product.product","Product"),
                                  ("sale.order","Order"),
                                  ("product.pricelist","Pricelist")],
                                  string="Link",
                                  compute="_value_ref")
    
    write_date = fields.Datetime("Last Change", readonly=True, index=True)
        
    # main definition
    _name = "fclipboard.item"
    _description = "Item"  
    _order = "section, sequence, write_date desc"
    