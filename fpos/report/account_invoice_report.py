# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-

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


from openerp.addons.at_account.report import account_invoice_report

class Parser(account_invoice_report.Parser):
    
    def __init__(self, cr, uid, name, context):
      super(Parser, self).__init__(cr, uid, name, context)
      self.localcontext.update({
        "pos_order": self._pos_order
      })
    
    def _pos_order(self, inv):
      res = {
        "order": None,
        "fpos_order": None,
        "qrimage": None,
        "journal": None,
        "term": self._payment_term(inv)
      }
       
      self.cr.execute("SELECT o.id FROM pos_order o"
                       " WHERE o.invoice_id = %s ", (inv.id,))
      
      sql_res = self.cr.fetchone()    
      if not sql_res or not sql_res[0]:
        return [res]
      
      pos_order = self.pool["pos.order"].browse(self.cr, self.uid, sql_res[0], context=self.localcontext)
      if not pos_order:
        return [res]
      
      res["order"] = pos_order
      
      statements = pos_order.statement_ids
      if len(statements) > 1:
        statements = [st for st in statements if st.amount]        
      if len(statements) == 1:
        journal = statements[0].statement_id.journal_id
        res["journal"] = journal
        
      fpos_order = pos_order.fpos_order_id
      res["fpos_order"] = fpos_order
      
      if fpos_order:
        if fpos_order.qr:
          res["qrimage"] = self.get_qrimage(fpos_order.qr) 
                      
      return [res]
        