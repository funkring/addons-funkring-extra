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
from openerp import SUPERUSER_ID

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
                    "compositions" : ["journal_ids","user_ids","company_id"]
                },
                "res.company" : {
                    "compositions" : ["currency_id"]
                }
            }
        }
            
        # add last seq    
        res = jdoc_obj.jdoc_by_id(cr, uid, "pos.config", profile_id, options=jdoc_options, context=context)
        res["last_seq"] = self.fpos_cur_seq(cr, uid, context=context)

        # add company        
        user_obj = self.pool["res.users"]
        company_id = user_obj._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        
        return res
    
    def fpos_cur_seq(self, cr, uid, context=None):
        cr.execute("SELECT MAX(seq) FROM fpos_order WHERE fpos_user_id = %s", (uid,))
        row = cr.fetchone()
        return row and row[0] or 0
    
    def fpos_seq_check(self, cr, uid, fpos_seq, context=None):
        """ Is called after the end of a sync 
            Action after Sync could be done HERE            
        """
        last_seq = self.fpos_cur_seq(cr, uid, context=context)
        if last_seq != fpos_seq:
            raise osv.except_osv(_("Error"), _("Last sequence number differs from server!\nOn device it is %s, on server it is %s\nContact immediately your administrator!") % (last_seq, fpos_seq))
        return True
        
