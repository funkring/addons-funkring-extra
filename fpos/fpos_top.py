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
    
    name = fields.Char("Name")
    sequence = fields.Integer("Sequence", default=10)
    pos_color = fields.Selection(COLOR_NAMES, string="Color")
    pos_unavail = fields.Boolean("Unavailable")

    
class fpos_place(models.Model):
    _name = "fpos.place"
    _description = "Place"
    
    name = fields.Char("Name")
    sequence = fields.Integer("Sequence", default=10)
    top_id = fields.Many2one("fpos.top","Top")
    pos_color = fields.Selection(COLOR_NAMES, string="Color")
    pos_unavail = fields.Boolean("Unavailable")
    
