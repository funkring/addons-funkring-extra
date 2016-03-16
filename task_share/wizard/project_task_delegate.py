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

class project_task_delegate(osv.osv_memory):
    _inherit = "project.task.delegate"
    _columns = {
        "share" : fields.boolean("Share")
    }
    
    def onchange_share(self, cr, uid, ids, share, planned_hours, context=None):
        value = {}
        res = {
            "value" : value
        }
        
        task_id = context.get("active_id", False)
        if task_id and share:
            task_obj = self.pool["project.task"]
            task = task_obj.browse(cr, uid, task_id, context=context)
            value["planned_hours_me"] = task.planned_hours - planned_hours
            value["prefix"] = task.name
            
        return res
