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

from openerp import models, fields, api, _
from openerp.addons.at_base import util
from openerp.addons.at_base import format
from openerp.addons.at_base import helper

from dateutil.relativedelta import relativedelta

class report_wizard(models.TransientModel):
    _name = "fpos.report.wizard"
    _description = "Report Wizard"
    
    range = fields.Selection([("month","Month"),
                              ("week","Week"),
                              ("day", "Day")],
                              string="Range", default="month", required=True)
    
    pos_ids = fields.Many2many("pos.config", "report_wizard_pos_config_rel", "wizard_id", "config_id", "POS", 
                               default=lambda self: self.env["pos.config"].search([]))
    
    detail = fields.Boolean("Detail")
    separate = fields.Boolean("Separate")
       
    date_from = fields.Date("From")
    date_till = fields.Date("Till")
    
    @api.multi
    def onchange_range(self, dtrange, date_from, date_till, resetRange=False):
        value = {}
        res = {
            "value" : value
        }
        
        if not date_from or resetRange:
            if dtrange == "month":
                date_from = util.getFirstOfLastMonth()
            elif dtrange == "week":
                day = util.strToDate(util.currentDate())
                day = day - relativedelta(days=(7+day.weekday()))
                date_from = util.dateToStr(day)
            else:
                day = util.strToDate(util.currentDate())
                day = day - relativedelta(days=1)
                date_from = util.dateToStr(day)
      
        if dtrange == "month":
            dt_date_from = util.strToDate(date_from)
            date_till = util.dateToStr(dt_date_from + relativedelta(months=1,days=-1))
        elif dtrange == "week":
            dt_date_from = util.strToDate(date_from)
            weekday = dt_date_from.weekday()
            date_till = util.dateToStr(dt_date_from + relativedelta(days=weekday+(6-weekday)))
        else:
            date_till = date_from
            
            
        value["date_from"] = date_from
        value["date_till"] = date_till
        return res
    
    @api.multi
    def action_report(self):        
        session_obj = self.pool["pos.session"]
        for wizard in self:
            # get ids
            config_ids = [p.id for p in wizard.pos_ids]            
            session_ids = session_obj.search(self._cr, self._uid, [("start_at",">=",wizard.date_from),("start_at","<=",wizard.date_till),("config_id","in",config_ids),("state","=","closed")], context=self._context)
            if not session_ids:
                return True
            
            datas = {
                 "ids": session_ids,
                 "model": "pos.session"
            }        
           
            # get context
            report_ctx = self._context and dict(self._context) or {}
            
            # format
            f = format.LangFormat(self._cr, self._uid, self._context)
            if wizard.range == "month":
                dt = util.strToDate(wizard.date_from)
                dt_till = util.strToDate(wizard.date_till)
                report_name = _("%s - %s / %s %s") % (f.formatLang(wizard.date_from, date=True), 
                                                                        f.formatLang(wizard.date_till, date=True),
                                                                        helper.getMonthName(self._cr, self._uid, dt.month, context=self._context),
                                                                        dt.year)
                
                if dt_till.year != dt.year or dt_till.month != dt.month:
                    report_name = _("%s - %s %s") % (report_name, 
                                                     helper.getMonthName(self._cr, self._uid, dt_till.month, context=self._context),
                                                     dt_till.year)
                     
                report_ctx["cashreport_name"] = report_name
                
            elif wizard.range == "week":
                dt = util.strToDate(wizard.date_from)
                dt_till = util.strToDate(wizard.date_till)
                kw = dt.isocalendar()[1]
                kw_till = dt_till.isocalendar()[1]
                
                report_name = _("%s - %s / CW %s %s") % (f.formatLang(wizard.date_from, date=True), 
                                                                        f.formatLang(wizard.date_till, date=True),
                                                                        kw, 
                                                                        dt.year)
                 
                if dt_till.year != dt.year or kw != kw_till:
                    report_name = _("%s - CW %s %s") % (report_name, kw_till, dt_till.year)
                    
                report_ctx["cashreport_name"] = report_name  
          
            # check options
            if wizard.detail:
                report_ctx["print_detail"] = True
            if wizard.separate:
                report_ctx["no_group"] = True
                                
            # return
            return  {
                "type": "ir.actions.report.xml",
                "report_name": "point_of_sale.report_sessionsummary",
                "datas": datas,
                "context" : report_ctx
            }
