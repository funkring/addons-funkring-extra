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


class pos_config(osv.Model):

    _inherit = "pos.config"
    _columns = {
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
                    "compositions" : set(("journal_ids","user_ids"))
                }
            }
        }
        return jdoc_obj.jdoc_by_id(cr, uid, "pos.config", profile_id, options=jdoc_options, context=context)
    

#class pos_order(osv):
        