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

from openerp import models, fields, api
from openerp.exceptions import ValidationError
from openerp.tools.translate import _ 

class farm_house(models.Model):
    _name = "farm.house"
    _description = "House"
    
    name = fields.Char("Name", required=True)
    parent_id = fields.Many2one("farm.house","Parent House")
    child_ids = fields.One2many("farm.house","parent_id","Houses")
    user_ids = fields.Many2many("res.users", "farm_house_user_rel", "user_id", "house_id", string="Users")
    hidden = fields.Boolean("Hidden")

    @api.one
    @api.constrains('parent_id')
    def _check_parent(self):
        if self.parent_id and self.id == self.parent_id.id:
            raise ValidationError(_("Parent could not be the same farm"))