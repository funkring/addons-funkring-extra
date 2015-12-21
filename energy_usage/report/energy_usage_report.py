# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.at_base import extreport

class Parser(extreport.basic_parser):
    
    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            "energy_usage": self._energy_usage,
        })
        
    def _energy_usage_order(self, order):
        lines = []
        amount = 0.0
        
        for line in order.energy_usage_ids:
            lines.append(line)
            amount += line.amount
            
        order = {
            "order" : order,
            "lines" : lines,
            "amount" : amount
        }
        return order
        
    def _energy_usage(self, o):
        res = []
        if o._name == "sale.order":
            res.append(self._energy_usage_order(o)) 
        if o._name == "account.invoice":
            for order in o.sale_order_ids:
                res.append(self._energy_usage_order(order))
        return res
    
    
    