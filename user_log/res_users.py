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
from openerp.http import request
from datetime import datetime
from openerp.addons.at_base import util

class res_users(osv.Model):
    _inherit = "res.users"
    _uid_lastlog = {}
    
    def check(self, db, uid, passwd):
        super(res_users, self).check(db, uid, passwd)
        lastLogKey = (db, uid)
        lastLog = self._uid_lastlog.get(lastLogKey)
        curTime = datetime.now()
        logAccess = not lastLog or (curTime - lastLog).seconds >= 600         
        if logAccess:
            url = request.httprequest.url
            self._uid_lastlog[lastLogKey] = curTime
            cr =  self.pool.cursor()
            try:
                self.pool.get("res.user.log").create(cr, uid, {"user_id" : uid, 
                                                               "date" :  util.timeToStr(curTime), 
                                                               "name" : url } )
                cr.commit()
            finally:
                cr.rollback()                
                cr.close()
            
        
        
class res_user_log(osv.Model):
    _name = "res.user.log"
    _description = "User Log"
    _columns = {
        "date" : fields.datetime("Timestamp", required=True, readonly=True, select=True),
        "user_id" : fields.many2one("res.users", "User", required=True, ondelete="cascade", readonly=True, select=True),
        "name" : fields.char("Site", readonly=True, select=True)
    }
    _order = "date desc"
    