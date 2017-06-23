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

class Parser(extreport.basic_parser):
    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            "prepare": self._prepare
        })
        
    def _prepare(self, objects):
        if not objects:
            return []

        log_ids = []        
        if objects[0]._model._name == "farm.chicken.logbook":
            for logbook in objects:
                for log in logbook.log_ids:
                    log_ids.append(log.id)
        else:
            log_ids = [o.id for o in objects]
            
        log_obj = self.pool["farm.chicken.log"]
        log_ids = log_obj.search(self.cr, self.uid, [("id","in",log_ids)], order="day asc", context=self.localcontext)
        logs = log_obj.browse(self.cr, self.uid, log_ids, context=self.localcontext)
        
        logbooks = {}
        for log in logs:
            logbook = logbooks.get(log.logbook_id.id)
            if logbook is None:
                logbook = {
                    "name": log.logbook_id.name,
                    "logs": [] 
                }
                logbooks[log.logbook_id.id] = logbook
                
            logbook_logs = logbook["logs"]
            logbook_logs.append(log)
        
        logbooks = sorted(logbooks.values(), key=lambda p: p["name"])
        return logbooks
