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
from openerp.addons.fpos.product import COLOR_NAMES

class fpos_top(models.Model):
    _name = "fpos.top"
    _description = "Top"
    _order = "sequence, name"
    
    name = fields.Char("Name", required=True, index=True)
    complete_name = fields.Char("Name", compute="_complete_name", store=True)
    parent_id = fields.Many2one("fpos.top","Parent", index=True)
    sequence = fields.Integer("Sequence", default=10)
    pos_color = fields.Selection(COLOR_NAMES, string="Color")
    pos_unavail = fields.Boolean("Unavailable")
    active = fields.Boolean("Active", default=True)
        
    @api.one
    @api.depends('name', 'parent_id.name')
    def _complete_name(self):
        res = []
        obj = self
        while obj:
            res.append(obj.name)
            obj = obj.parent_id
        self.complete_name =  " / ".join(reversed(res))
        
    @api.multi
    def name_get(self):
        res = []
        for obj in self:
            res.append((obj.id, obj.complete_name))
        return res
    
    
class fpos_place(models.Model):
    _name = "fpos.place"
    _description = "Place"
    _order = "sequence, name"
    
    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence", default=10)
    top_id = fields.Many2one("fpos.top","Top", index=True)
    pos_color = fields.Selection(COLOR_NAMES, string="Color")
    pos_unavail = fields.Boolean("Unavailable")
    complete_name = fields.Char("Name", compute="_complete_name", store=True)
    active = fields.Boolean("Active", default=True)
    
    @api.multi
    def name_get(self):
        res = []
        for obj in self:
            res.append((obj.id, obj.complete_name))
        return res
        
    @api.one
    @api.depends('name', 'top_id.complete_name')
    def _complete_name(self):
        top = self.top_id
        if top:
            self.complete_name =  "%s / %s" % (top.complete_name, self.name)
        else:
            self.complete_name = self.name 
        
    
