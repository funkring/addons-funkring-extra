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
from openerp.addons.jdoc.jdoc import META_MODEL

class pos_category(osv.osv):
    _inherit = "pos.category"
    
    def _fpos_category_get(self, cr, uid, obj, *args, **kwarg):
        mapping_obj = self.pool["res.mapping"]
        
        # build product
        return {
            "_id" : mapping_obj._get_uuid(cr, uid, obj),
            META_MODEL : obj._model._name,
            "name" : obj.name,
            "parent_id" : mapping_obj._get_uuid(cr, uid, obj.parent_id),
            "image_small" : obj.image_small,
            "sequence" : obj.sequence
        }
    
    def _fpos_category_put(self, cr, uid, obj, *args, **kwarg):
        return None
    
    def _fpos_category(self, cr, uid, *args, **kwargs):
        return {
            "get" : self._fpos_category_get,
            "put" : self._fpos_category_put
        }
    
    
class pos_config(osv.Model):

    _inherit = "pos.config"
    _columns = {        
        "fpos_seq" : fields.integer("Fpos Sequence", readonly=True),
        "fpos_prefix" : fields.char("Fpos Prefix"),
        "iface_nogroup" : fields.boolean("No Grouping", help="If a product is selected twice a new pos line was created"),
        "user_id" : fields.many2one("res.users","Sync User", select=True),
        "user_ids" : fields.many2many("res.users", 
                                      "pos_config_user_rel", 
                                      "config_id", "user_id", 
                                      "Users", 
                                      help="Allowed users for the Point of Sale")
    }
    _sql_constraints = [
        ("user_uniq", "unique (user_id)","Fpos User could only assinged once")
    ]
    
    def get_profile(self, cr, uid, context=None):
        """
        @return: Fpos Profile
        """
        profile_id = self.search_id(cr, uid, [("user_id","=", uid)], context=context)
        if not profile_id:
            return False
        
        jdoc_obj = self.pool["jdoc.jdoc"]
        jdoc_options = {
            "model" : {
                "pos.config" : {
                    "compositions" : ["journal_ids","user_ids","company_id","sequence_id"]
                },
                "res.company" : {
                    "compositions" : ["currency_id"]
                }
            }
        }
            
        # query config
        res = jdoc_obj.jdoc_by_id(cr, uid, "pos.config", profile_id, options=jdoc_options, context=context)
        
        # get counting values
        fpos_order_obj = self.pool.get("fpos.order")
        last_order_values = fpos_order_obj.search_read(cr, uid, 
                                    [("fpos_user_id","=",uid),("state","!=","draft")], 
                                    ["seq", "turnover", "cpos"], 
                                    order="seq desc", limit=1)
        
        if last_order_values:
            last_order_values = last_order_values[0]
            res["last_seq"] = last_order_values["seq"]
            res["last_turnover"] = last_order_values["turnover"]
            res["last_cpos"] = last_order_values["cpos"]
        else:
            res["last_seq"] = 0.0
            res["last_turnover"] = 0.0
            res["last_cpos"] = 0.0

        # add company        
        user_obj = self.pool["res.users"]
        company_id = user_obj._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        
        # finished
        return res
    

class pos_order(osv.Model):
    
    _inherit = "pos.order"
    
    def reconcile_invoice(self, cr, uid, ids, context=None):
        ids = self.search(cr, uid, [('state','=','invoiced'),('invoice_id.state','=','open'),("id","in",ids)])
        move_line_obj = self.pool.get('account.move.line')
        st_line_obj = self.pool.get("account.bank.statement.line")
        
        # check move lines
        for order in self.browse(cr, uid, ids, context):
            st_line_obj.confirm_statement(cr, uid, [s.id for s in order.statement_ids], context=context)

        # reconcile
        for order in self.browse(cr, uid, ids, context):
            invoice = order.invoice_id
            data_lines = [x.id for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id]
            for st_line in order.statement_ids:
                data_lines += [x.id for x in st_line.journal_entry_id.line_id if x.account_id.id == invoice.account_id.id]
            move_line_obj.reconcile(cr, uid, data_lines, context=context)              
       
    def _after_invoice(self, cr, uid, order, context=None):
        self.reconcile_invoice(cr, uid, [order.id], context=context)
        
