'''
Created on 17.05.2011

@author: martin
'''
from openerp.tools.translate import _
from openerp.addons.at_base import extreport

class Parser(extreport.basic_parser):
    
    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            "statistic": self.statistic
        })
        
    def statistic(self, session):
        stat_per_tax = {}
        expense_dict = {}
        income_dict = {}
        
        turnover = 0.0
        refund_sum = 0.0
        income_sum = 0.0
            
        #line_obj = self.pool.get("pos.order.line")
        account_tax_obj = self.pool.get("account.tax")
        currency_obj = self.pool.get('res.currency')
        order_line_obj = self.pool.get("pos.order.line")        
        
        # iterate pos lines
        line_ids = order_line_obj.search(self.cr, self.uid, [("order_id.session_id","=",session.id),
                                                             ("order_id.state","in",["paid","done","invoiced"])])
                
        
        for line in order_line_obj.browse(self.cr, self.uid, line_ids, context=self.localcontext):
            product = line.product_id
            taxes = [x for x in line.product_id.taxes_id]
            if line.qty == 0.0:            
                continue
                        
            price = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
            computed_taxes = account_tax_obj.compute_all(self.cr, self.uid, taxes, price, line.qty)
            cur = line.order_id.pricelist_id.currency_id                       
            total_inc = currency_obj.round(self.cr, self.uid, cur, computed_taxes['total_included'])
            
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
                
            payment_type = "in" #revenue
            if total_inc < 0:
                payment_type = "out"
                
            if product.income_pdt or product.expense_pdt:    #not taxes:#produkt einzahlung oder produkt auszahlung:
                turnover+=total_inc
            else:
                turnover+=total_inc        
                if total_inc > 0:
                    income_sum+=total_inc
                elif total_inc < 0:
                    refund_sum+=total_inc        
      
      
            def add_tax_stat(tax_id,tax_name):          
                tax_stat = stat_per_tax.get(tax_id)
                if not tax_stat:
                    tax_stat = { 
                        "name" : tax_name,
                        "in" : { "detail" : {}, "sum" : 0.0 }, 
                        "out"  : { "detail" : {}, "sum" : 0.0 } }                    
                    stat_per_tax[tax_id] = tax_stat
                
                payment_stat = tax_stat.get(payment_type)                
                tax_sum = payment_stat.get("sum", 0.0)
                tax_sum += total_inc
                payment_stat["sum"]=tax_sum
                
                #should shown as detail
#                 if product.detail_pdt:
#                     detail = payment_stat.get("detail")
#                     detail_get = detail.get(product.id)
#                     if detail_get:
#                         detail_get["total"] = detail_get["total"] + total_inc
#                     else:
#                         detail_dict = {
#                             "name" : product.name,
#                             "total" : total_inc
#                         }
#                         detail[product.id] = detail_dict
                        
            #add to taxes
            if not product.income_pdt and not product.expense_pdt:
                if taxes:            
                    for tax in taxes:
                        add_tax_stat(tax.id, tax.name)                  
        
        
        # get vars
        cash_statement = session.cash_register_id
        period = cash_statement.period_id
        
        # iterate statement lines
        
        cash_stat = {
            "income" : 0.0,
            "expense" : 0.0,
            "sum" : 0.0
        }
        
        statements = []        
        st_obj = self.pool.get("account.bank.statement")
        st_ids = st_obj.search(self.cr, self.uid, [("pos_session_id","=",session.id)], context=self.localcontext)
        st_sum = 0.0
        st_sum_in = 0.0
        st_sum_out = 0.0
        
        for st in st_obj.browse(self.cr, self.uid, st_ids, self.localcontext):             
            payment_in = 0.0
            payment_out = 0.0
            payment_sum = 0.0
            st_stat = {
                "st" : st,
                "journal" : st.journal_id.name,
                "name" : st.name
            }
            statements.append(st_stat)
            for st_line in st.line_ids:
                if st_line.amount < 0:
                    payment_out += st_line.amount
                    st_sum_out += st_line.amount
                elif st_line.amount > 0:
                    payment_in += st_line.amount
                    st_sum_in += st_line.amount
                
                payment_sum += st_line.amount
                st_sum += st_line.amount
                
                            
            st_stat["income"] = payment_in
            st_stat["expense"] = payment_out
            st_stat["sum"] = payment_sum
            
            # set cash statement if it is 
            if st.id == cash_statement.id:
                cash_stat = st_stat
         
        # description
        dates = []   
        if session.start_at:
            dates.append(self.formatLang(session.start_at, date_time=True))
        if session.stop_at:
            dates.append(self.formatLang(session.stop_at, date_time=True))
        if cash_statement.state  != "confirm":
            dates.append(_("Open"))
        description  = " - ".join(dates)
              
        # stat
        stat = {
            "name" : session.name,
            "company" : cash_statement.company_id.name,
            "currency" : session.currency_id.symbol,
            "journal" : session.cash_journal_id.name,
            "user" : session.user_id.name,
            "period" :  period and period.name or "",
            "description" : description,
            "turnover" : turnover,
            "statements" : statements,
            "statement_sum" : st_sum,
            "statement_sum_income" : st_sum_in,
            "statement_sum_expense" : st_sum_out,
            "cash_income" : cash_stat["income"],
            "cash_expense" : cash_stat["expense"],
            "cash_sum" : cash_stat["sum"],
            "balance" : session.cash_register_balance_start+session.cash_register_total_entry_encoding,
            "balance_diff" : session.cash_register_difference,
            "balance_start" : session.cash_register_balance_start,
            "balance_end" : session.cash_register_balance_end_real
        }        
                
        # taxes
        tax_stats = []
        stat["tax_statistic"] = tax_stats
        stat["expense"] = expense_dict.values()
        stat["income"] = income_dict.values()
        stat["refund_sum"] = refund_sum
        stat["income_sum"] = income_sum
            
        if stat_per_tax:    
            
            def append_tax_stat(tax_stat):
                name = tax_stat["name"]
                for cur_stat in tax_stats:            
                    if name == cur_stat["name"]:
                        cur_stat["sum"] = cur_stat["sum"]+tax_stat["sum"]
                        cur_detail = cur_stat["detail"]
                        cur_detail += tax_stat["detail"]                
                        return                                    
                tax_stats.append(tax_stat)
            
            for tax_id in stat_per_tax.keys():
                tax_stat = stat_per_tax[tax_id]
                
                tax_stat_in=tax_stat["in"] #income
                append_tax_stat({
                     "name" : _("Receipts (%s)") % (tax_stat["name"],),
                     "sum" : tax_stat_in["sum"],
                     "detail" : tax_stat_in["detail"].values()
                })
                

                tax_stat_out=tax_stat["out"] #refund
                append_tax_stat({
                     "name" : _("Credits (%s)") % (tax_stat["name"],),
                     "sum" : tax_stat_out["sum"],
                     "detail" : tax_stat_out["detail"].values()
                })                
                
        return [stat]
            
    
        
       
   
