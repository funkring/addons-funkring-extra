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
from openerp.exceptions import Warning
from openerp.addons.at_base import util
from openerp.addons.at_base import helper
from collections import OrderedDict
import re

import base64

class wizard_export_bmd(models.TransientModel):
    _name = "fpos.wizard.export.bmd"
    _description = "BMD Export Wizard"
    
    buerf = fields.Binary("BMD Export", readonly=True)
    buerf_name = fields.Char("buerf_name", default="buerf")
   
    _beleg_patterns =  [re.compile("^.*[^0-9]([0-9]+)$"),
                       re.compile("^([0-9]+)$")]

    @api.model
    def default_get(self, fields_list):
        res = super(wizard_export_bmd, self).default_get(fields_list)
        order_obj = self.env["pos.order"]
        line_obj = self.env["pos.order.line"]
        orders = []
        status_id = self.env["ir.model.data"].xmlid_to_res_id("fpos.product_fpos_status",raise_if_not_found=True)
        
        session_ids = util.active_ids(self._context, "pos.session")
        if session_ids:
            orders = order_obj.search([("session_id","in",session_ids)], order="date_order asc")
        else:
            order_ids = util.active_ids(self._context, "pos.order")
            if order_ids:
                orders = order_obj.search([("id","in",order_ids)], order="date_order asc")
                
        lines = []
        
        # formats
        
        def formatFloat(inValue):
            return ("%.2f" % inValue).replace(".",",")
        
        def formatSymbol(value):
            if value:
                value = value.replace("/","")
                return value
            return None 
     
        
        # write header
        line = ";".join(["konto", "gkto", "belegnr", "belegdat", "betrag", "mwst", "steuer", "steucod", "verbuchkz","symbol","text"]) + ";"
        lines.append(line)
          
        #internal_account_id
        for order in orders:      
            # config            
            cash_statement = order.session_id.cash_statement_id
            if not cash_statement:
                raise Warning(_("No cash statement for order %s found") % order.name)
            
            config = order.session_id.config_id
            symbol = formatSymbol(config.fpos_prefix or config.sequence_number.prefix)
            belegnr = order.name.split(config.fpos_prefix)[-1]
            belegdat = helper.strToLocalTimeFormat(self._cr, self._uid, order.date_order,"%Y%m%d", context=self._context)
            journal = cash_statement.journal_id
            debit_account = journal.default_debit_account_id
            credit_account = journal.default_credit_account_id
            internal_account = journal.internal_account_id
            if not internal_account:
                raise Warning(_("No internal account defined on Journal %s for cash transfers") % journal.name)
             
            name = []
            if order.pos_reference:
                name.append(order.pos_reference)
            if order.partner_id:
                name.append(order.partner_id.name)          
            name = " ".join(name)
             
            bookings = OrderedDict()
            def post(account, betrag, mwst, steuer, text):
                # change sign
                betrag *= -1
                steuer *= -1
                key = (account.code, account.user_type.code, mwst, text)
                booking = bookings.get(key)
                if booking is None:
                    booking = (betrag, steuer)
                else:
                    booking = (booking[0] + betrag, booking[1] + steuer)
                bookings[key] = booking
            
            # post sale            
            for line in order.lines:
                product = line.product_id
                if product.id == status_id:
                    continue
                
                # get tax
                tax = 0
                taxes = line_obj._get_taxes(line) 
                if taxes:
                    tax = int(taxes[0].amount * 100)
                
                tax_amount = line.price_subtotal_incl - line.price_subtotal
                if product.income_pdt or product.expense_pdt:
                    income_account = product.property_account_income
                    if not income_account:
                        income_account = internal_account
                    post(income_account, line.price_subtotal, tax, tax_amount, name)
                else:
                    income_account = product.property_account_income
                    if not income_account:
                        income_account = product.categ_id.property_account_income_categ
                    if not income_account:
                        raise Warning(_("No income account for product %s defined") % product.name)
                    post(income_account, line.price_subtotal, tax, tax_amount, name)
        
            # post payment
            for payment in order.statement_ids:                
                if payment.statement_id.id != cash_statement.id:
                    payment_internal_account = payment.statement_id.journal_id.internal_account_id
                    payment_account = payment_internal_account or internal_account
                    post(payment_account, -payment.amount, 0, 0, payment.statement_id.journal_id.name)
                    
            # write bookings            
            for (account, user_type_code, mwst, text), (betrag, steuer) in bookings.iteritems():                
                # thin about changed sign                
                journal_account = betrag > 0 and credit_account or debit_account                
                steuer = mwst and formatFloat(steuer) or ""
                steucod = ""
                if steuer:
                    if user_type_code == "expense":
                        steucod = "00" # VST
                    else:
                        steucod = "03" # UST
                steuerproz = mwst and str(mwst) or ""
                line = ";".join([account, journal_account.code, belegnr, belegdat, formatFloat(betrag), steuerproz, steuer, steucod, "A", symbol, text]) + ";"
                lines.append(line)
        
        lines = "\r\n".join(lines) + "\r\n"
        charset = "cp1252"
        
        res["buerf"] = base64.encodestring(lines.encode(charset,"replace"))
        return res
