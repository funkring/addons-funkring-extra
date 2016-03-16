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

from openerp.osv import osv

class project_task(osv.Model):
    _inherit = "project.task"
    
    def do_delegate(self, cr, uid, ids, delegate_data=None, context=None):
        delegate_task_ids = super(project_task, self).do_delegate(cr, uid, ids, delegate_data=delegate_data, context=context)
        if delegate_data and delegate_data.get("share"):
            # correct planned hours
            self.write(cr, uid, ids, {"planned_hours" : delegate_data["planned_hours_me"]})
        return delegate_task_ids
            
        