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

class product_template(models.Model):
  _inherit = "product.template"
  
  wc_state = fields.Selection([("draft","Draft"),("review","Review"),("published","Published")], readonly=True, string="WooCommerce Status")
  wc_name = fields.Char("WooCommerce Name")

  @api.multi
  def action_wc_draft(self):
    for product in self:
      product.wc_state = "draft"
    return True
    
  @api.multi
  def action_wc_review(self):
    for product in self:
      product.wc_state = "review"
    return True
  
  @api.multi
  def action_wc_publish(self):
    for product in self:
      product.wc_state = "published"
    return True

