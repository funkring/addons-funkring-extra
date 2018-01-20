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
from openerp import SUPERUSER_ID
import urlparse

class Parser(extreport.basic_parser):
    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext["info"] = self._info
        
    def _info(self, config):
        config_obj = self.pool("pos.config")
        fpos_order_obj = self.pool("fpos.order")
        
        fpos_model_map = dict(config_obj.fields_get(self.cr, self.uid, allfields=["fpos_model"], context=self.localcontext)["fpos_model"]["selection"])
        url = self.pool["ir.config_parameter"].get_param(self.cr, SUPERUSER_ID, 'web.base.url', 'http://localhost:8069')
        
        info = {
            "cloud" : ".oerp.at" in url,
            "fpos_model" : fpos_model_map.get(config.fpos_model, ""),
            "sign_type" : "",
            "dep_start" : "",
            "dep_start_image" : None,
            "dep_download" : "",
            "dep_download_image" : None,
            "sign_key_image" : self.get_qrimage(config.sign_key)        
        }
           
        if config.dep_key:
            dep_download = urlparse.urljoin(url, "fpos/dep/%s/%s" % (config.id, config.dep_key))
            info["dep_download"] = dep_download
            info["dep_download_image"] = self.get_qrimage(dep_download)
            
        if config.user_id:
            start_order_id = fpos_order_obj.search_id(self.cr, self.uid, [("fpos_user_id","=",config.user_id.id),("st","=","s")], order="seq desc", context={"active_test" : False})
            if start_order_id:
                start_order = fpos_order_obj.browse(self.cr, self.uid, start_order_id, context=self.localcontext)
                info["dep_start_image"] = self.get_qrimage(start_order.qr)
                if start_order.hs:                    
                    info["dep_start"] = urlparse.urljoin(url, "fpos/code/%s/%s" % (config.id, start_order.hs)) 
                else:
                    info["dep_start"] = start_order.qr
        
        return [info]