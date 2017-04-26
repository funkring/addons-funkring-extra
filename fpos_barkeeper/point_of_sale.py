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
from openerp.tools.translate import _
from openerp.addons.at_base import util
from openerp.addons.at_base import helper
from openerp import tools

from dateutil.relativedelta import relativedelta

class pos_config(osv.Model):
    _inherit = "pos.config"

    def barkeeper_status(self, cr, uid, options, context=None):
        order_obj = self.pool["pos.order"]
        session_obj = self.pool["pos.session"]
        config_obj = self.pool["pos.config"]
        company_obj = self.pool["res.company"]
        
        company_id = company_obj._company_default_get(cr, uid, context=context)
        company = company_obj.browse(cr, uid, company_id, context=context)
        currency = company.currency_id.symbol
        
        # result 
        stat = {
            "title" : _("No Data"),
            "currency" : currency,
            "name" : "",
            "group" : "",
            "range" : ""
        }
        
        # search first order if 
        # and build default options 
        # if no options are passed
        config_id = None
        date = None
        if options:
            config_id = options.get("config_id")
            date = options.get("date")
        
        nodata = False
        if not config_id or not date:
            # get latest order
            order_id = None
            if config_id:
                order_id = order_obj.search_id(cr, uid, [("session_id.config_id","=",config_id)], order="date_order desc", context=None)
            else:
                order_id = order_obj.search_id(cr, uid, [("session_id","!=",False)], order="date_order desc", context=None)
            
            # check if order exist
            if order_id:
                order = order_obj.browse(cr, uid, order_id, context=context)
                
                # get parent
                config = order.session_id.config_id
                while config.parent_user_id: 
                    parent_config_id = config_obj.search_id(cr, uid, [("user_id","=",config.parent_user_id.id)], context=context)
                    if not parent_config_id or parent_config_id == config.id:
                        break
                    config = config_obj.browse(cr, uid, parent_config_id, context=context)
                
                config_id = config.id
                options = {
                    "mode" : "today",
                    "date" : util.timeToDateStr(order.date_order),
                    "config_id" : config_id                               
                }                
            else: 
                nodata = True

        # set options        
        stat["options"] = options
            
        # if not data return
        if not config_id:
            return stat
        
        # get current mode
        config = config_obj.browse(cr, uid, config_id, context=context)
        config_ids = [config_id]

        # build title and group description
        stat["name"] = config.name
        if config.user_id:
            group = []
            childEntries = config_obj.search_read(cr, uid, [("parent_user_id","=",config.user_id.id)], ["name","sign_pid"], context=context)            
            for childEntry in childEntries:
                group.append(childEntry["sign_pid"] or childEntry["name"])
                config_ids.append(childEntry["id"])                
            if group:
                group.insert(0, config.sign_pid or config.name)
            stat["group"] = ", ".join(group)
            
        # return if no default data
        if nodata:
            return stat
        
        # find start
        statDate = options.get("date")
        if not statDate:
            options["date"] = statDate = util.currentDate()
            
        # get mode
        mode = options.get("mode")
        if not mode:
            options["mode"] = mode = "today"
        
        
        # add amount
        orderDicts = []
        def addAmount(amount, amountStat, sections, count=False):
            for section in sections:
                
                subsections = None
                sectionStat = None
                
                if len(section) == 1:
                    key = section[0]
                    sectionStat = amountStat.get(key)                    
                    if sectionStat is None:
                        sectionStat = {
                            "amount" : 0.0,
                            "count" : 0,
                            "currency" : currency
                        }
                        amountStat[key] = sectionStat
                        
                elif len(section) >= 2:
                    field = section[0]
                    key = section[1]
                    
                    if len(section) >= 3:
                        subsections = section[2]
                    
                    keyStat = amountStat.get(field)
                    if keyStat is None:
                        keyStat = {}                        
                        amountStat[field] = keyStat
                        orderDicts.append((amountStat, field, keyStat))

                    sectionStat = keyStat.get(key)                    
                    if sectionStat is None:
                        sectionStat = {
                            "key" : key,
                            "amount" : 0.0,
                            "count" : 0,
                            "currency" : currency                        
                        }
                        keyStat[key] = sectionStat                        
                    
                sectionStat["amount"] = sectionStat["amount"] + amount
                if count:
                    sectionStat["count"] = sectionStat["count"] + 1
                
                if subsections:
                    addAmount(amount, sectionStat, subsections, count=count)
         
        
        # setup range
        time_keyfunc = lambda date_order: helper.strToLocalDateStr(cr, uid, date_order, context=context)  
        if mode == "year":
            stat["title"] = _("Year")
            startDate = util.getFirstOfYear(statDate)
            endDate = util.getFirstOfNextYear(statDate)
            dt_delta = relativedelta(years=1)
        elif mode == "month":
            stat["title"] = _("Month")
            startDate = util.getFirstOfMonth(statDate)
            endDate = util.getFirstOfNextMonth(statDate)
            dt_delta = relativedelta(months=1)            
        elif mode == "week":
            stat["title"] = _("Week")
            startDate = util.getFirstOfWeek(statDate)
            endDate = util.getFirstOfWeek(statDate)
            dt_delta = relativedelta(weeks=1)        
        else:
            time_keyfunc = lambda date_order: "%s:00" % helper.strToLocalTimeStr(cr, uid, date_order, context=context).split(" ")[1][:2]
            stat["title"] = _("Day")
            startDate = statDate
            endDate = util.getNextDayDate(statDate)
            dt_delta = relativedelta(hours=1)
        
        # query session build range
        session_ids = session_obj.search(cr, uid, [("start_at",">=",startDate),("start_at","<",endDate),("config_id","=",config_id)], order="start_at asc", context=context)
        stat["range"] = helper.getRangeName(cr, uid, startDate, util.getPrevDayDate(endDate), context=context) 

        # query orders
        order_ids = order_obj.search(cr, uid, [("session_id","in",session_ids)], order="date_order asc", context=context)
        orders = order_obj.browse(cr, uid, order_ids, context=context)
       
        # build base
        addAmount(0, stat, [("total",)]) 
        if orders:
            firstOrder = orders[1]
            lastOrder = orders[-1]
            
            curTime = util.strToTime(firstOrder.date_order)
            timeEnd = util.strToTime(lastOrder.date_order)
            while curTime <= timeEnd:
                time_key = time_keyfunc(util.timeToStr(curTime))
                addAmount(0, stat, [("byTime", time_key)])
                curTime += dt_delta
        
        
        # iterate orders       
        for order in orders:
            # check if it is relevant
            fpos_order = order.fpos_order_id
            if fpos_order.tag:
                continue
            
            user = order.user_id
            
            # add turnover for journal
            for st in order.statement_ids:
                journal = st.journal_id
                amount = st.amount
                addAmount(amount, stat, [("byJournal", journal.name),("byUser", user.name, [("byJournal", journal.name)])], True)
                
            # add to order
            time_key = time_keyfunc(order.date_order) 
            addAmount(order.amount_total, stat, [("total",),("byTime", time_key, [("byUser", user.name)])], True)

        # sort dicts            
        for (parent, key, value) in orderDicts:
            parent[key] = value and sorted(value.values(), key=lambda en: en["key"]) or []
            
        return stat
    
