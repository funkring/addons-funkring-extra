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

from openerp.osv import osv

class sale_make_invoice(osv.osv_memory):
    _inherit = "sale.make.invoice"
    _defaults = {
        "grouped": True
    }

    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        return False

    def make_invoices(self, cr, uid, ids, context=None):
        if context is None:
            context = {} 
            
        order_ids = context.get("active_ids", [])
        order_obj = self.pool["sale.order"]
        if order_ids:
            order_obj.confirm_force_all(cr, uid, order_ids, context=context)
        
        return super(sale_make_invoice, self).make_invoices(cr, uid, ids, context=context)
