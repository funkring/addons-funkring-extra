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

class jdoc_res_config(osv.TransientModel):
    _name = "jdoc.res.config"
    _description = "jDoc Configuration "
    _inherit = "res.config.settings"
    _columns = {
        "couchdb_url" : fields.char("CouchDB Url", help="CouchDB Url for intern synchronisation"),
        "couchdb_user" : fields.char("CouchDB User"),
        "couchdb_password" : fields.char("CouchDB Password"),
        "couchdb_public_url" : fields.char("CouchDB Public Url", help="CouchDB Url for extern/public synchronisation")
    }
    
    def get_default_couchdb_url(self, cr, uid, fields, context=None):
        return {"couchdb_url":self.pool.get("ir.config_parameter").get_param(cr, uid, "couchdb_url", default="http://localhost:5894")}
    
    def set_default_couchdb_url(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            self.pool.get("ir.config_parameter").set_param(cr, uid, "couchdb_url", config.couchdb_url, groups=["base.group_erp_manager"], context=context)
            
    def get_default_couchdb_user(self, cr, uid, fields, context=None):
        return {"couchdb_user":self.pool.get("ir.config_parameter").get_param(cr, uid, "couchdb_user")}
    
    def set_default_couchdb_user(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            self.pool.get("ir.config_parameter").set_param(cr, uid, "couchdb_user", config.couchdb_user, groups=["base.group_erp_manager"], context=context)

    def get_default_couchdb_password(self, cr, uid, fields, context=None):
        return {"couchdb_password":self.pool.get("ir.config_parameter").get_param(cr, uid, "couchdb_password")}
    
    def set_default_couchdb_password(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            self.pool.get("ir.config_parameter").set_param(cr, uid, "couchdb_password", config.couchdb_password, groups=["base.group_erp_manager"], context=context)

    def get_default_couchdb_public_url(self, cr, uid, fields, context=None):
        return {"couchdb_public_url":self.pool.get("ir.config_parameter").get_param(cr, uid, "couchdb_public_url")}
    
    def set_default_couchdb_public_url(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            self.pool.get("ir.config_parameter").set_param(cr, uid, "couchdb_public_url", config.couchdb_public_url, context=context)
