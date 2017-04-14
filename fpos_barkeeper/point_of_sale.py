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
from openerp.tools.translate import _
from openerp.addons.at_base import util
from openerp.addons.at_base import helper
from openerp.addons.at_base import format

from dateutil.relativedelta import relativedelta


class pos_config(osv.Model):
    _inherit = "pos.config"

    def barkeeper_turnover(self, cr, uid, options, context=None):
        user_sale =  []
        journal_sale = []
        detail = []
        
        res = {
            "title" : _("No Data"),
            "currency" : "",
            "name" : "",
            "child_names" : "", 
            "sale_count" : 0.0,
            "sale_amount" : 0.0,
            "user_sale" : user_sale,
            "journal_sale" : journal_sale,
            "detail" : detail
        }
        
        order_obj = self.pool["pos.order"]
        mapping_obj = self.pool["res.mapping"]
        
        if not options:
            order_id = order_obj.search_id(cr, uid, [("session_id","!=",False)], order="id desc", context=None)
            order = order_obj.browse(cr, uid, order_id, context=context)
            options = {
                "mode" : "today",
                "config_id" : mapping_obj._get_uuid(order.session_id.config_id)                                
            }
            res["options"] = options
            
        mode = options.get("mode", "today")
              
        # get config
        config = mapping_obj._browse_mapped(cr, uid, options["config_id"], context=context)
        
        # determine start date
        startTime = mode != "today" and options.get("start") or None
        endTime = options.get("end")
        
        if not startTime:
            order_id = order_obj.search_id(cr, uid, [("session_id.config_id","=",config.id)], order="id desc", context=None)
            order = order_obj.browse(cr, uid, order_id, context=context)
            startDate = util.timeToDateStr(order.date_order)
            startTime = helper.strDateToUTCTimeStr(cr, uid, startDate, context)
        
        startTime = util.strToTime(startTime)
        if endTime:
            endTime = util.strToTime(endTime)
        
        f = format.LangFormat(cr, uid, context=context)       
        keyfunc = lambda date_order: helper.strToLocalDateStr(cr, uid, date_order, context=context)
        
        # get range
        ranges = []        
        if mode == "year":
            res["title"] = _("Year")
            if not endTime:
                endTime = startTime + relativedelta(years=1)
            curTime = startTime
            while curTime <= endTime:
                nextTime = curTime + relativedelta(month=1)
                localDate = helper.strToLocalDateStr(cr, uid, util.timeToStr(curTime), context=context)
                ranges.append((helper.getMonth(cr, uid, localDate, context=context), localDate))
                curTime = nextTime
                
        elif mode == "month":
            res["title"] = _("Month")
            if not endTime:
                endTime = startTime + relativedelta(months=1)        
            curTime = startTime
            while curTime <= endTime:
                nextTime = curTime + relativedelta(days=1)
                localDate = helper.strToLocalDateStr(cr, uid, util.timeToStr(curTime), context=context)
                ranges.append((f.formatLang(localDate, date=True), localDate))
                curTime = nextTime    
                
        elif mode == "week":
            res["title"] = _("Week")
            if not endTime:
                endTime = startTime + relativedelta(weeks=1)
            
            curTime = startTime
            while curTime <= endTime:
                nextTime = curTime + relativedelta(days=1)
                localDate = helper.strToLocalDateStr(cr, uid, util.timeToStr(curTime), context=context)
                ranges.append((f.formatLang(localDate, date=True), localDate))
                curTime = nextTime              
        else:
            curTime = startTime
            keyfunc = lambda date_order: helper.strToLocalTimeStr(cr, uid, date_order, context=context).split(" ")[1]
            
            while curTime <= endTime:
                nextTime = curTime + relativedelta(hours=1)
                localTime = helper.strToLocalTimeStr(cr, uid, curTime, context=context)
                timeStr = localTime.split(" ")[1]
                ranges.append((timeStr, timeStr))
                curTime = nextTime
            
            if mode == "today":
                res["title"] = _("Today")
            else:
                res["title"] = _("Day")
                if not endTime:
                    endTime = startTime + relativedelta(days=1)            
        
        domain = [("session_id.config_id","=",config.id), ("date_order",">=",startTime)]
        if endTime:
            domain.append(("date_order","<=",endTime))
            
        # add orders
        order_ids = order_obj.search(cr, uid, domain, order="date_order asc", context=context)

        def createTurnover():
            return {
                "count": 0,
                "turnover": 0.0,
                "io" : 0.0,
                "journal" : {},
                "users" : {}
            }
            
            
        turnover = createTurnover()
        turnover_group = {}
        
        def addLine(turnover, line):
            # check io
            if line.product_id.income_pdt or line.product_id.expense_pdt:
                turnover["io"] = turnover["io"] + line.price_subtotal_incl
            # normal
            else:
                turnover["turnover"] = turnover["turnover"] + line.price_subtotal_incl
        
        def addJournal(turnover, st):
            journal = st.statement_id.journal_id
            journal_turnover = turnover["journal"].get(journal.id)
            if journal_turnover is None:
                journal_turnover = {
                    "journal" : journal,
                    "turnover" : 0.0
                } 
            journal_turnover["turnover"] = journal_turnover["turnover"] + st.amount 
                
        def addOrder(turnover, order):
            # create user turnover
            user_id = order.user_id.id
            users = turnover["users"]
            turnover_user = users.get(user_id)
            if turnover_user is None:
                turnover[user_id] = turnover_user = createTurnover() 
                turnover_user["name"] = order.user_id.name
                
                
            turnover_user["count"] = turnover_user["count"] + 1
            turnover["count"] = turnover["count"] + 1
                
            # add turnover for journal
            for st in order.statement_ids:
                addJournal(turnover, st)
                addJournal(turnover_user, st)
                
            # add turnover for lines
            for line in order.lines:
                addLine(turnover, line)
                addLine(turnover_user, line)
                
        
        for order in order_obj.browse(cr, uid, order_ids, context=context):
            # add to order
            addOrder(turnover, order)
            
            # add to group
            key = keyfunc(order.date_order)            
            group = turnover_group.get(key)
            if group is None:
                turnover_group[key] = group = createTurnover()
            addOrder(group, order)
            
        def normalizeTurnover(turnover):
            # normalize journal, remove io
            journals = []
            for key, value in turnover["journal"].items():
                journal = value["journal"]
                turnover = value["turnover"]
                if journal.type == "cash":
                    turnover -= turnover["io"]
                journals.append({
                    "journal" : journal.name,
                    "turnover" : turnover
                })
                
            # sort
            journals.sort(key=lambda val: val["name"])
            turnover["journal"] = journals
            
            # normalize users
            userTurnover = turnover.get("users")
            if not userTurnover is None:
                users = []
                for key, value in userTurnover.items():
                    normalizeTurnover(value)
                    users.append(value)
                    
                users.sort(key=lambda val: val["name"])
                turnover["users"] = users
            
        # normalize
        normalizeTurnover(turnover)
        for value in turnover_group.values():
            normalizeTurnover(value)
        
        
        # add groups
        for name, key in ranges:
            group = turnover_group.get(key)
            if group and detail:
                group["name"] = name
                detail.append(group)
            
        return res
    
