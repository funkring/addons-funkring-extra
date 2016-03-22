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
        self.localcontext.update({
            "statistic" : self._statistic,
            "groupByConfig" : self._groupByConfig
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
        
    def _statistic(self, sessions):
        if not sessions:
            return []
        
        turnover_dict = {}
        expense_dict = {}
        income_dict = {}
        st_dict = {}
        tax_dict = {}
        
        statements = []      
        
        sum_turnover = 0.0
        sum_in = 0.0
        sum_out = 0.0
        sum_all = 0.0
        st_sum = 0.0
        
        first_session = sessions[0]
        last_session = sessions[-1]
        session_ids = [s.id for s in sessions]
        
        cash_statement = last_session.cash_register_id

        line_obj = self.pool.get("account.bank.statement.line")
        account_tax_obj = self.pool.get("account.tax")
        currency_obj = self.pool.get('res.currency')
        order_obj = self.pool.get("pos.order")            
        
        # add turnover
        def addTurnover(name, amount, line):          
            entry = turnover_dict.get(name, None)
            if entry is None:
                entry = { 
                    "name" : name,
                    "sum" : 0.0,
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
        order_ids = order_obj.search(self.cr, self.uid, [("session_id","in",session_ids),("state","in",["paid","done","invoiced"])])
        for order in order_obj.browse(self.cr, self.uid, order_ids, context=self.localcontext):
            # iterate line
            for line in order.lines:
                product = line.product_id                    
                if line.qty == 0.0:            
                    continue
                
                # get taxes
                taxes = tax_dict.get(product.id,None)
                if taxes is None:
                    taxes = [x for x in line.product_id.taxes_id if x.company_id.id == line.company_id.id]
                    tax_dict[product.id] = taxes
                
                # compute taxes     
                price = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
                computed_taxes = account_tax_obj.compute_all(self.cr, self.uid, taxes, price, line.qty)
                total_inc = currency_obj.round(self.cr, self.uid, first_session.currency_id, computed_taxes['total_included'])
                
                # add expense                                                
                if product.expense_pdt:
                    expense = expense_dict.get(product.id)
                    if not expense:                                        
                        expense = {
                            "name" : product.name,
                            "sum" : total_inc
                        }
                        expense_dict[product.id] = expense
                    else:
                        expense["sum"] = expense["sum"]+total_inc
                
                # add income
                if product.income_pdt:
                    income = income_dict.get(product.id)
                    if not income:
                        income = {
                            "name" : product.name,
                            "sum" : total_inc
                        }
                        income_dict[product.id] = income
                    else:
                        income["sum"] = income["sum"]+total_inc
                        
                # add turnover
                if not product.income_pdt and not product.expense_pdt:
                    sum_turnover += total_inc
                    if taxes:
                        for tax in taxes:
                            addTurnover(tax.name, total_inc, line)                                                        
                    else:
                        addTurnover(_("No Tax"), total_inc, line)
                
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
                
             
        # remember sum_in, sum_out which based
        # on the orders
        order_sum_in = sum_in
        order_sum_out = sum_out
             
        # determine in and out of statements
        unexpected_line_ids = line_obj.search(self.cr, self.uid, [("statement_id.pos_session_id","in",session_ids),("pos_statement_id","=",False)])
        for line in line_obj.browse(self.cr, self.uid, unexpected_line_ids, context=self.localcontext):
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
              
        name = first_session.name
        if first_session != last_session:
            name = "%s - %s" % (first_session.name, last_session.name)
              
        first_period = first_session.cash_register_id.period_id
        last_period = last_session.cash_register_id.period_id

        period = first_period.name        
        if first_period != last_period:
            period = "%s - %s" % (first_period.name, last_period.name)
              
        # stat
        stat = {
            "name" : name,
            "company" : cash_statement.company_id.name,
            "currency" : first_session.currency_id.symbol,
            "journal" : first_session.cash_journal_id.name,
            "user" : first_session.user_id.name,
            "period" :  period,
            "description" : description,
            "turnover" : sum_turnover,
            "statements" : statements,
            "statement_sum" : st_sum,
            "cash_income" : cashEntry["income"],
            "cash_expense" : cashEntry["expense"],
            "cash_sum" : cashEntry["sum"]+cashEntry["income"]+cashEntry["expense"],
            "cash_turnover" : cashEntry["turnover"],
            "balance" : last_session.cash_register_balance_start+last_session.cash_register_total_entry_encoding,
            "balance_diff" : last_session.cash_register_difference,
            "balance_start" : first_session.cash_register_balance_start,
            "balance_end" : last_session.cash_register_balance_end_real,
            "expenseList" : expense_dict.values(),
            "incomeList" : income_dict.values(),
            "turnoverList" : turnover_dict.values(),
            "details_start" : first_session.details_ids,
            "details_end" : last_session.details_ids
        }        
        return [stat]
            
    
        
       
   
