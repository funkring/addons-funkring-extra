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
from openerp.addons.at_base import util

class energy_usage(models.Model):
    _name = "energy.usage"
    _description = "Energy Usage"
        
    sale_order_id = fields.Many2one("sale.order","Sale Order")
    product_id = fields.Many2one("product.product", "Product", required=True)
    date_from = fields.Date("From", help="Start of usage", required=True)
    date_to = fields.Date("To", help="End of usage", required=True)
    amount = fields.Float("kWh", compute="_amount", readonly=True)
    days = fields.Integer("Days", compute="_amount", readonly=True)
    
    @api.one
    @api.depends("date_from","date_to","product_id")
    def _amount(self):
        if ( self.product_id and self.date_from and self.date_to and self.date_to >= self.date_from ):
            dt_from = util.strToDate(self.date_from)
            dt_to = util.strToDate(self.date_to)
            dt_diff = dt_to - dt_from
            self.days = dt_diff.days + 1
            self.amount = self.days * self.product_id.kw * 24
        else:
            self.amount = 0.0
            self.days = 0.0
    