# -*- coding: utf-8 -*-
'''
Created on 17.05.2011

@author: martin
'''
from openerp.tools.translate import _
from openerp.addons.at_base import extreport
from openerp.addons.at_base import util
from collections import OrderedDict

class Parser(extreport.basic_parser):

    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        if context is None:
            context = {}
        self.localcontext.update({
            "statistic" : self._statistic,
            "groupByConfig" : self._groupByConfig,
            "getSessionGroups" : self._getSessionGroups,
            "getSessions" : self._getSessions,
            "print_detail" : context.get("print_detail",name == "fpos.report_session_detail"),
            "print_product" : context.get("print_product", False),
            "no_group" : context.get("no_group", False),
            "summary" : context.get("summary", False),
            "cashreport_name" : context.get("cashreport_name",""),
            "getCashboxNames" : self._getCashboxNames,
            "getLineName" : self._getLineName,
            "formatDetailAmount" : self._formatDetailAmount,
            "dailyRange" : self._dailyRange,
            "dailyEnd" : self._dailyEnd,
            "dailyStart" : self._dailyStart
        })

    def _groupByConfig(self, sessions):
        sessions = sorted(sessions, key=lambda session: session.id)
        sessionByConfig = OrderedDict()
        for session in sessions:
            config = session.config_id
            configSessions = sessionByConfig.get(config.id)
            if configSessions is None:
                configSessions = []
                sessionByConfig[config.id] = configSessions
            configSessions.append(session)
        return sessionByConfig

    def _getSessions(self, objects):
        sessions = objects
        if objects:
            model_name = objects[0]._model._name
            if model_name == "fpos.report.email":
                email_report = objects[0]
                report_range = email_report._cashreport_range(self.localcontext.get("start_date"))
                session_ids = email_report._session_ids(report_range)
                sessions = self.pool["pos.session"].browse(self.cr, self.uid, session_ids, self.localcontext)

        return sessions

    def _getCashboxNames(self, sessions):
        configNames = set()
        for session in sessions:
            configNames.add(session.config_id.name)
        return ", ".join(sorted(list(configNames)))

    def _formatTime(self, timeStr):
        return self.formatLang(timeStr, date_time=True).split(" ")[1]

    def _getSessionGroups(self, sessions):
        # group by config
        byConfig = self._groupByConfig(sessions)
        
        # get used config        
        domain = []
        report_info = self.localcontext.get("pos_report_info")
        if report_info:
            domain.append(("id","in",report_info["config_ids"]))
        else:
            domain.append(("id","in",byConfig.keys()))

        # query config
        config_obj = self.pool.get("pos.config")
        config_ids = config_obj.search(self.cr, self.uid, domain)

        # build result
        res = []
        for config in config_obj.browse(self.cr, self.uid, config_ids, context=self.localcontext):                            
            configSessions = byConfig.get(config.id)
            if configSessions:
                res.append({
                    "config" : config,
                    "sessions" : configSessions,
                    "description" : self._getName(configSessions)
                })

        return res

    def _getName(self, sessions):
        name = self.localcontext.get("cashreport_name","")
        if not name:
            report_info = self.localcontext.get("pos_report_info")
            if report_info:
                name = report_info["name"]

        if sessions and not name:
            first_session = sessions[0]
            last_session = sessions[-1]
            if first_session != last_session:
                name = "%s - %s" % (self.formatLang(first_session.start_at, date=True), self.formatLang(last_session.start_at, date=True))
            else:
                name = self.formatLang(first_session.start_at, date=True)

        return name

    def _getDetailName(self, detail, cur="€"):
        product = detail.get("product")
        qty = detail.get("qty",0.0)
        uom = product.uom_id
        if uom.nounit or product.income_pdt or product.expense_pdt:
            return product.name
        else:
            qtyStr = ""
            if product.pos_amount_dec < 0:
                qtyStr = str(int(qty))
            elif product.pos_amount_dec == 0:
                qtyStr = self.formatLang(qty, digits=3)
            else:
                qtyStr = self.formatLang(qty, digits=product.pos_amount_dec)
            priceStr = self.formatLang(detail.get("price"))
            discount = detail.get("discount")
            if discount:
                discountStr = self.formatLang(discount)
                return "%s %s * %s %s -%s%%" % (qtyStr, uom.name, priceStr, cur, discountStr)
            else:
                return "%s %s * %s %s" % (qtyStr, uom.name, priceStr, cur)

    def _formatDetailAmount(self, detail):
        qty = detail.get("qty",0.0)
        product = detail.get("product")
        uom = product.uom_id
        if uom.nounit or product.income_pdt or product.expense_pdt:
            return str(int(qty))
        else:
            qtyStr = ""
            if product.pos_amount_dec < 0:
                qtyStr = str(int(qty))
            elif product.pos_amount_dec == 0:
                qtyStr = self.formatLang(qty, digits=3)
            else:
                qtyStr = self.formatLang(qty, digits=product.pos_amount_dec)
            return qtyStr

    def _getLineName(self, line):
        product = line.product_id
        qty = line.qty
        uom = product.uom_id
        fpos_line = line.fpos_line_id
        flags = ""
        tag = ""
        if fpos_line:
            tag = fpos_line.tag or ""
            flags = fpos_line.flags or ""
        if uom.nounit or product.income_pdt or product.expense_pdt or tag or "u" in flags:
            return line.name
        else:
            qtyStr = ""
            if product.pos_amount_dec < 0:
                qtyStr = str(int(qty))
            elif product.pos_amount_dec == 0:
                qtyStr = self.formatLang(qty, digits=3)
            else:
                qtyStr = self.formatLang(qty, digits=product.pos_amount_dec)
            return "%s %s %s" % (qtyStr, uom.name, line.name)

    def _sortedDetail(self, details):
        return sorted(details, key=lambda val: (val.get("amount",0.0), val.get("name")), reverse=True)

    def _buildStatistic(self, sessions):
        if not sessions:
            return None

        turnover_dict = {}
        expense_dict = {}
        income_dict = {}
        io_dict = {}
        st_dict = {}
        st_user_dict = {}
        tax_dict = {}

        statements = []
        details = []

        sum_turnover = 0.0
        sum_in = 0.0
        sum_out = 0.0
        sum_all = 0.0
        st_sum = 0.0

        first_session = sessions[0]
        last_session = sessions[-1]
        session_ids = [s.id for s in sessions]

        first_cash_statement = first_session.cash_statement_id
        cash_statement = last_session.cash_statement_id

        line_obj = self.pool.get("account.bank.statement.line")
        account_tax_obj = self.pool.get("account.tax")
        currency_obj = self.pool.get('res.currency')
        order_obj = self.pool.get("pos.order")

        print_detail = self.localcontext["print_detail"]
        print_product = self.localcontext["print_product"]

        currency = first_session.currency_id.symbol
        status_id = self.pool["ir.model.data"].xmlid_to_res_id(self.cr, self.uid, "fpos.product_fpos_status", raise_if_not_found=True)

        # add turnover
        def addTurnover(name, amount, line, tax_amount, is_taxed):
            entry = turnover_dict.get(name, None)
            if entry is None:
                entry = {
                    "name" : name,
                    "sum" : 0.0,
                    "tax_sum" : 0.0,
                    "is_taxed" :  is_taxed,
                    "detail" : OrderedDict()
                }
                turnover_dict[name] = entry

            product = line.product_id
            if product.pos_report or print_product:
                detailDict = entry["detail"]
                # build key
                price = 0.0
                uom = product.uom_id
                if uom.nounit or product.pos_price:
                    key = (line.name, line.product_id, 0, 0)
                else:
                    fpos_line = line.fpos_line_id
                    if fpos_line:
                        price = fpos_line.price
                    elif line.qty:
                        price = product.amount / line.qty
                    key = (line.name, line.product_id, line.discount, price)
                # get detail
                detail = detailDict.get(key)
                if detail is None:
                    detail = {
                        "product" : product,
                        "qty" : line.qty,
                        "amount" : amount,
                        "discount" : line.discount,
                        "price" : price,
                        "name" : line.name
                    }
                    detailDict[key] = detail
                else:
                    detail["qty"] = detail["qty"] + line.qty
                    detail["amount"] = detail["amount"] + amount

            entry["sum"] = entry["sum"]+amount
            entry["tax_sum"] = entry["tax_sum"]+tax_amount
            return entry

        # cash entry
        cashEntry = {
            "name" :  first_session == last_session and cash_statement.name or "",
            "journal" : cash_statement.journal_id.name,
            "turnover" : 0.0,
            "sum" : 0.0,
            "income" : 0.0,
            "expense" : 0.0,
            "users" : {}

        }

        cashJournalId = cash_statement.journal_id.id
        st_dict[cashJournalId] = cashEntry
        statements.append(cashEntry)

        # iterate orders
        first_order = None
        last_order = None
        user = None
        order_ids = order_obj.search(self.cr, self.uid, [("session_id","in",session_ids),("state","in",["paid","done","invoiced"])], order="id asc")
        order_count = 0

        for order in order_obj.browse(self.cr, self.uid, order_ids, context=self.localcontext):
            # current sum in and out
            cur_sum_in = 0
            cur_sum_out = 0

            # add io
            def addIo(ioType, data, amount):
                fpos_order = order.fpos_order_id
                if order.pos_reference and (not fpos_order or not fpos_order.tag):
                    key = (ioType, order.date_order, order.pos_reference)
                    values = io_dict.get(key, None)
                    if values is None:
                        values = {
                            "name" : "%s - %s" % (self.formatLang(order.date_order, date=True), order.pos_reference),
                            "total" : amount,
                            "users" : {}
                        }
                        io_dict[key] = values
                        data["lines"].append(values)
                    else:
                        values["total"] = values["total"] + amount

                    # add user specific
                    user_entry = values["users"].get(order.user_id.id)
                    if user_entry is None:
                        user_entry = {
                            "user" : order.user_id,
                            "sum" : amount
                        }
                        values["users"][order.user_id.id] = user_entry
                    else:
                        user_entry["sum"] = user_entry["sum"] + amount


            # determine order first
            # and order last
            last_order = order
            if first_order is None:
                first_order = order
                user = order.user_id

            order_count += 1

            # details
            if print_detail:
                detail_lines = []
                detail_tax = {}
                detail = {
                    "order" : order,
                    "lines" : detail_lines
                }
                details.append(detail)

            # iterate line
            for line in order.lines:
                product = line.product_id
                if product.id == status_id:
                    continue
                #if line.qty == 0.0:
                #    continue

                # get taxes
                taxes = tax_dict.get(product.id,None)
                if taxes is None:
                    taxes = [x for x in line.product_id.taxes_id if x.company_id.id == line.company_id.id]
                    tax_dict[product.id] = taxes

                # compute taxes
                price = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
                computed_taxes = account_tax_obj.compute_all(self.cr, self.uid, taxes, price, line.qty)
                tax_details  = computed_taxes["taxes"]
                total_inc = currency_obj.round(self.cr, self.uid, first_session.currency_id, computed_taxes['total_included'])

                # add detail
                if print_detail:
                    if tax_details:
                        for tax in tax_details:
                            tax_name = tax["name"]
                            detail_tax[tax_name] = detail_tax.get(tax_name,0.0) + tax["amount"]

                    detail_lines.append({
                        "index" : len(detail_lines),
                        "line" : line,
                        "price" : price,
                        "brutto" : total_inc
                    })

                # add expense
                if product.expense_pdt:
                    sum_out += total_inc
                    cur_sum_out += total_inc
                    expense = expense_dict.get(line.name, None)
                    if expense is None:
                        expense = {
                            "name" : product.name,
                            "sum" : total_inc,
                            "lines" : []
                        }
                        expense_dict[line.name] = expense
                    else:
                        expense["sum"] =  expense["sum"] + total_inc

                    # add output
                    addIo("o", expense, total_inc)


                # add income
                if product.income_pdt:
                    sum_in += total_inc
                    cur_sum_in += total_inc
                    income = income_dict.get(line.name, None)
                    if income is None:
                        income = {
                            "name" : product.name,
                            "sum" : total_inc,
                            "lines" : []
                        }
                        income_dict[line.name] = income
                    else:
                        income["sum"] = income["sum"] + total_inc

                    # add input
                    addIo("i", income, total_inc)

                # add turnover
                if not product.income_pdt and not product.expense_pdt:
                    sum_turnover += total_inc
                    if tax_details:
                        for tax in tax_details:
                            addTurnover(tax["name"], total_inc, line, tax["amount"], True)
                    else:
                        addTurnover(_("No Tax"), total_inc, line, 0, False)

                # sum all
                sum_all += total_inc

            # sumup statements
            for st_line in order.statement_ids:
                st = st_line.statement_id
                entry = st_dict.get(st.journal_id.id, None)
                if entry is None:
                    entry = {
                        "journal" : st.journal_id.name,
                        "name" : first_session == last_session and st.name or "",
                        "sum" : 0.0,
                        "income" : 0.0,
                        "expense" : 0.0,
                        "users" : {}
                    }
                    statements.append(entry)
                    st_dict[st.journal_id.id] = entry
                # add line
                entry["sum"] = entry["sum"] + st_line.amount

                # add user line
                user_entry = entry["users"].get(order.user_id.id, None)
                if user_entry is None:
                    user_entry = {
                        "user": order.user_id,
                        "sum": 0.0
                    }
                    entry["users"][order.user_id.id] = user_entry

                # remove i/o payment
                user_amount = st_line.amount
                if st.journal_id.id == cashJournalId:
                    user_amount = user_amount - cur_sum_in - cur_sum_out

                user_entry["sum"] = user_entry["sum"] + user_amount

                # total user
                st_user_entry = st_user_dict.get(order.user_id.id, None)
                if st_user_entry is None:
                    st_user_entry = {
                        "user" : order.user_id,
                        "sum" : 0.0
                    }
                    st_user_dict[order.user_id.id] = st_user_entry

                st_user_entry["sum"] = st_user_entry["sum"] + user_amount

                # total
                st_sum += st_line.amount

            # details
            if print_detail:
                detail["taxes"] = sorted(detail_tax.items(), key=lambda v: v[0])


        # remember sum_in, sum_out which based
        # on the orders
        order_sum_in = sum_in
        order_sum_out = sum_out
        sum_unexpected = 0.0

        # determine in and out of statements
        unexpected_line_ids = line_obj.search(self.cr, self.uid, [("statement_id.pos_session_id","in",session_ids),("pos_statement_id","=",False)])
        for line in line_obj.browse(self.cr, self.uid, unexpected_line_ids, context=self.localcontext):
            sum_unexpected += line.amount
            if line.amount >= 0:
                sum_in+=line.amount
            else:
                sum_out+=line.amount

        # calc turnover
        for entry in st_dict.values():
            if entry == cashEntry:
                entry["turnover"] = entry["sum"] - order_sum_in - order_sum_out
                entry["income"] = sum_in
                entry["expense"] = sum_out
                entry["sum"] = entry["sum"] + sum_unexpected
            else:
                entry["turnover"] = entry["sum"]

        # description
        dates = []
        if first_session.start_at:
            dates.append(self.formatLang(first_session.start_at, date_time=True))
        if last_session.stop_at:
            dates.append(self.formatLang(last_session.stop_at, date_time=True))
        if cash_statement.state  != "confirm":
            dates.append(_("Open"))
        description  = " - ".join(dates)

        # name
        name = self._getName(sessions)

        # get period
        first_period = first_session.cash_statement_id.period_id
        last_period = last_session.cash_statement_id.period_id
        period = first_period.name
        if first_period != last_period:
            period = "%s - %s" % (first_period.name, last_period.name)

        # check user
        if not user:
            user = first_session.user_id

        # format users

        usersTurnover = sorted(st_user_dict.values(), key=lambda val: val.get("sum",0.0), reverse=True)
        for st in st_dict.values():
            users = st.get("users")
            st["users"] = sorted(users.values(), key=lambda val: val.get("sum",0.0), reverse=True)

        for io_value in io_dict.values():
            users = io_value.get("users")
            io_value["users"] = sorted(users.values(), key=lambda val: val.get("sum",0.0), reverse=True)

        # sort details
        turnoverDetails = []
        for to in turnover_dict.values():
            detailList = self._sortedDetail(to["detail"].values())
            for d in detailList:
                d["description"] = self._getDetailName(d, currency)
            to["detail"] = detailList
            turnoverDetails = turnoverDetails + detailList
        # overall detail
        turnoverDetails = self._sortedDetail(turnoverDetails)


        # stat
        stat = {
            "name" : name,
            "first_session" : first_session.name,
            "last_session" : last_session.name,
            "date_start" : first_session.start_at,
            "date_end" : last_session.stop_at,
            "first_order" : first_order,
            "last_order" : last_order,
            "company" : cash_statement.company_id.name,
            "currency" : currency,
            "journal" : cash_statement.journal_id.name,
            "pos" :  first_session.config_id.name,
            "user" : user.name,
            "users" : usersTurnover,
            "period" :  period,
            "description" : description,
            "turnover" : sum_turnover,
            "statements" : statements,
            "statement_sum" : st_sum,
            "cash_income" : cashEntry["income"],
            "cash_expense" : cashEntry["expense"],
            "cash_sum" : cashEntry["sum"],
            "cash_turnover" : cashEntry["turnover"],
            "balance" : cash_statement.balance_start+cash_statement.total_entry_encoding,
            "balance_diff" : cash_statement.difference,
            "balance_start" : first_cash_statement.balance_start,
            "balance_end" : cash_statement.balance_end_real,
            "expenseList" : expense_dict.values(),
            "incomeList" : income_dict.values(),
            "turnoverList" : turnover_dict.values(),
            "turnoverDetails" : turnoverDetails,
            "details_start" : first_session.details_ids,
            "details_end" : last_session.details_ids,
            "details" : details,
            "order_count" : order_count,
            "days" : []
        }
        return stat

    def _dailyRange(self, session):
        startTime = util.timeToStrHours(session.start_at)
        if not session.stop_at:
            return "%s - %s " % (startTime, _("Open"))
        
        startDate = util.timeToDateStr(session.start_at)
        stopDate = util.timeToDateStr(session.stop_at)
        stopTime = util.timeToStrHours(session.stop_at)
        
        if startDate != stopDate:
            return "%s - %s %s" % (startTime, self.formatLang(stopDate,date=True), stopTime)
        
        return "%s - %s" % (startTime, stopTime)
    
    def _dailyStart(self, session):
        return util.timeToStrHours(session.start_at)
    
    def _dailyEnd(self, session):
        if not session.stop_at:
            return _("Open")
        
        startDate = util.timeToDateStr(session.start_at)
        stopDate = util.timeToDateStr(session.stop_at)
        stopTime = util.timeToStrHours(session.stop_at)
        
        if startDate != stopDate:
            return "%s %s" % (self.formatLang(stopDate,date=True), stopTime)
        
        return stopTime

    def _statistic(self, sessions, daily=False, no_group=False):               
        sessions = sorted(sessions, key=lambda session: (session.start_at or "", session.stop_at or ""))
        
        # check no group
        if no_group:
            res = []
            for session in sessions:
                stat = self._buildStatistic([session])
                if stat:
                    res.append(stat)
            return res 
        
        stat = self._buildStatistic(sessions)
        if not stat:
            return []
        
        if not daily and self.localcontext.get("daily_overview"):
            sessionsPerDay = stat["days"]
            report_info = self.localcontext.get("pos_report_info")
            report_info["from"], report_info["till"]
            
            def selectDay(day):
                if not day:
                    return None
                
                selDay = None
                
                # get sel day
                if sessionsPerDay:
                    dayEntry = sessionsPerDay[-1]
                    selDay = dayEntry["day"]
                else:
                    selDay = day     
                    dayEntry = {
                        "day": selDay,
                        "sessions" : []
                    }           
                    sessionsPerDay.append(dayEntry)
                    
                # fill gap    
                while selDay < day:
                    selDay = util.getNextDayDate(selDay)
                    dayEntry = {
                        "day": selDay,
                        "sessions" : []
                    }
                    sessionsPerDay.append(dayEntry)                    

                # check result                
                if selDay == day:
                    return dayEntry
                
                return None
            
            selectDay(report_info.get("from"))
            for session in sessions:
                if not session.start_at:
                    continue
                dayEntry = selectDay(util.timeToDateStr(session.start_at))
                if dayEntry:
                    dayEntry["sessions"].append(session)
                
            selectDay(report_info.get("till"))
        
        return [stat]





