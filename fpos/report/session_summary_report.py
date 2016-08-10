'''
Created on 17.05.2011

@author: martin
'''
from openerp.tools.translate import _
from openerp.addons.at_base import extreport
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
            "no_group" : context.get("no_group", False),
            "cashreport_name" : context.get("cashreport_name",""),
            "getCashboxNames" : self._getCashboxNames
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
    
    def _getSessionGroups(self, sessions):
        if self.localcontext.get("no_group"):
            res = []
            for session in sessions:
                res.append([session])
            return res
        else:
            return self._groupByConfig(sessions).values()
    
    def _statistic(self, sessions):
        if not sessions:
            return []
        
        turnover_dict = {}
        expense_dict = {}
        income_dict = {}
        st_dict = {}
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
            if product.pos_report:
                detailDict = entry["detail"]
                detail = detailDict.get(product.id)
                if detail is None:
                    detail = {
                        "product" : product,
                        "qty" : line.qty,
                        "amount" : amount
                    }
                    detailDict[product.id] = detail
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
                 
        }
        st_dict[cash_statement.journal_id.id] = cashEntry
        statements.append(cashEntry)
        
        # iterate orders        
        first_order = None
        last_order = None
        user = None
        order_ids = order_obj.search(self.cr, self.uid, [("session_id","in",session_ids),("state","in",["paid","done","invoiced"])], order="id asc")
        order_count = 0
        
        for order in order_obj.browse(self.cr, self.uid, order_ids, context=self.localcontext):
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
                    expense = expense_dict.get(line.name)
                    if not expense:                                        
                        expense = {
                            "name" : product.name,
                            "sum" : total_inc
                        }
                        expense_dict[line.name] = expense
                    else:
                        expense["sum"] = expense["sum"]+total_inc
                    
                
                # add income
                if product.income_pdt:
                    sum_in += total_inc
                    income = income_dict.get(line.name)
                    if not income:
                        income = {
                            "name" : product.name,
                            "sum" : total_inc
                        }
                        income_dict[line.name] = income
                    else:
                        income["sum"] = income["sum"]+total_inc                        
                        
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
                        "expense" : 0.0
                    }
                    statements.append(entry)
                    st_dict[st.journal_id.id] = entry
                # add line 
                entry["sum"] = entry["sum"] + st_line.amount
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
             
        name = ""
        if self.localcontext.get("no_group"):
            name = self.formatLang(first_session.start_at, date=True)
        else: 
            name = self.localcontext.get("cashreport_name")
            if not name:
                if first_session != last_session:
                    name = "%s - %s" % (self.formatLang(first_session.start_at, date=True), self.formatLang(last_session.start_at, date=True))
                else:
                    name = self.formatLang(first_session.start_at, date=True)
              
        first_period = first_session.cash_statement_id.period_id
        last_period = last_session.cash_statement_id.period_id

        period = first_period.name        
        if first_period != last_period:
            period = "%s - %s" % (first_period.name, last_period.name)
       
        if not user:
            user = first_session.user_id
            
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
            "currency" : first_session.currency_id.symbol,
            "journal" : cash_statement.journal_id.name,
            "pos" :  first_session.config_id.name,
            "user" : user.name,
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
            "details_start" : first_session.details_ids,
            "details_end" : last_session.details_ids,
            "details" : details,
            "order_count" : order_count
        }        
        return [stat]
            
    
        
       
   
