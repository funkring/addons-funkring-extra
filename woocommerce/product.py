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
from openerp import SUPERUSER_ID

class product_template(osv.Model):
  _inherit = "product.template"
  _columns = {
    "wc_sync": fields.boolean("WooCommerce Synchronisation", readonly=True, copy=False, index=True)    
  }
  
  def action_wc_sync_enable(self, cr, uid, ids, context=None):
    self.write(cr, uid, ids, {"wc_sync":True}, context=context)
    self.pool["wc.profile"].schedule_sync(cr, SUPERUSER_ID, context=context)
    return True
  
  def action_wc_sync_disable(self, cr, uid, ids, context=None):
    self.write(cr, uid, ids, {"wc_sync":False}, context=context)
    self.pool["wc.profile"].schedule_sync(cr, SUPERUSER_ID, context=context)
    return True
  
  
class product_product(osv.Model):
  _inherit = "product.product"
   
  def action_wc_sync_enable(self, cr, uid, ids, context=None):
    return self.pool["product.template"].action_wc_sync_enable(cr, uid, [o.product_tmpl_id.id for o in self.browse(cr, uid, ids, context)], context=context)
  
  def action_wc_sync_disable(self, cr, uid, ids, context=None):
    return self.pool["product.template"].action_wc_sync_disable(cr, uid, [o.product_tmpl_id.id for o in self.browse(cr, uid, ids, context)], context=context)
    
