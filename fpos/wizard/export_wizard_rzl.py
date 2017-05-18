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
    _name = "fpos.wizard.export.rzl"
    _description = "RZL Export Wizard"
    
    data = fields.Binary("RZL Export", readonly=True)
    data_name = fields.Char("Export Name", default="kassa.csv")
   
    _beleg_patterns =  [re.compile("^.*[^0-9]([0-9]+)$"),
                       re.compile("^([0-9]+)$")]

   
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_export_bmd, self).default_get(fields_list)
        order_obj = self.env["pos.order"]
        line_obj = self.env["pos.order.line"]
        orders = []
        
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
        
        #internal_account_id
        for order in orders:      
            # config            
            cash_statement = order.session_id.cash_statement_id
            if not cash_statement:
                raise Warning(_("No cash statement for order %s found") % order.name)
            
            config = order.session_id.config_id
            currency = order.pricelist_id.currency_id
            belegkreis = formatSymbol(config.fpos_prefix or config.sequence_number.prefix)
            belegnr = order.name.split(config.fpos_prefix)[-1]
            belegdat = helper.strToLocalTimeFormat(self._cr, self._uid, order.date_order,"%d%m%Y", context=self._context)
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
            def post(konto, betrag, betrag_gegenbuchung, mwst, steuer, text):
                # change sign
                key = (konto, mwst, text)
                booking = bookings.get(key)
                if booking is None:
                    booking = (betrag, steuer, betrag_gegenbuchung)
                else:
                    booking = (booking[0] + betrag, booking[1] + steuer, booking[2] + betrag_gegenbuchung)
                bookings[key] = booking
            
            # post sale            
            for line in order.lines:
                product = line.product_id
                
                # get tax
                tax = 0
                taxes = line_obj._get_taxes(line) 
                if taxes:
                    tax = int(taxes[0].amount * 100)
                
                tax_amount =  line.price_subtotal_incl - line.price_subtotal
                if product.income_pdt or product.expense_pdt:
                    account = internal_account
                    partner = order.partner_id
                    if partner:
                        if product.income_pdt:
                            account = partner.property_account_receivable
                        else:
                            account = partner.property_account_payable
                    post(account.code, line.price_subtotal, line.price_subtotal_incl, tax, tax_amount, name)
                else:
                    income_account = product.property_account_income
                    if not income_account:
                        income_account = product.categ_id.property_account_income_categ
                    if not income_account:
                        raise Warning(_("No income account for product %s defined") % product.name)
                    account = income_account
                    if not line.price_subtotal:
                        account = internal_account
                    post(account.code, line.price_subtotal, line.price_subtotal_incl, tax, tax_amount, name)
        
            # post payment
            for payment in order.statement_ids:                
                if payment.statement_id.id != cash_statement.id:
                    post(internal_account.code, -payment.amount, -payment.amount, 0, 0, payment.statement_id.journal_id.name)
                    
            # write bookings            
            for (konto, mwst, text), (betrag, steuer, betrag_gegenbuchung) in bookings.iteritems():
                sollbetrag = ""
                habenbetrag = ""
                sollbetrag_gegenbuchung = ""
                habenbetrag_gegenbuchung = ""
                gegenkonto = None
                
                if betrag < 0:
                    gegenkonto = credit_account.code
                    sollbetrag = formatFloat(abs(betrag))
                    habenbetrag_gegenbuchung = formatFloat(abs(betrag_gegenbuchung))
                else:
                    gegenkonto = debit_account.code
                    habenbetrag = formatFloat(abs(betrag))
                    sollbetrag_gegenbuchung = formatFloat(abs(betrag_gegenbuchung))
                    
                opnummer = ""
                valuta_datum = ""
                waehrung = currency.name
                fremdwaehrung = ""
                fremdwaehrung_sollbetrag = ""
                fremdwaehrung_habenbetrag = ""
                kostenstelle = ""
                ust_land = "1"
                ust_prozentsatz = ""
                ust_code = ""
                ust_sondercode = "0"
                buchungsart = "1"
                steuerbetrag = formatFloat(steuer)
                if mwst:
                    ust_prozentsatz = str(mwst)
                    ust_code = "2"
                    
                abweichende_zahlungsfrist = ""
                abweichende_kontofrist = ""
                abw_skontoprozentsatz = ""
                buchungstext = order.name
                buchungstext2 = text
                uid_nummer = ""
                dienstleistungsnummer = ""
                dienstleistungsland = ""
                dienstleistungsexport = ""
                dms_schluessel = ""
                kostentraeger = ""
                fremdbelegnummer = ""
                wert1 = ""
                wert2  = ""
                mahnsperre = ""
                kundendatenfeld = ""
                
                # buchung
                line = ";".join([konto,             #1 
                                 gegenkonto,        #2
                                 opnummer,          #3
                                 belegdat,          #4 
                                 valuta_datum,      #5
                                 waehrung,          #6
                                 sollbetrag,        #7
                                 habenbetrag,       #8
                                 steuerbetrag,      #9
                                 fremdwaehrung,     #10
                                 fremdwaehrung_sollbetrag,  #11
                                 fremdwaehrung_habenbetrag, #12
                                 kostenstelle,      #13
                                 belegkreis,        #14
                                 belegnr,           #15
                                 ust_land,          #16
                                 ust_prozentsatz,   #17
                                 ust_code,           #18
                                 ust_sondercode,     #19
                                 buchungsart,        #20
                                 abweichende_zahlungsfrist, #21
                                 abweichende_kontofrist, #22
                                 abw_skontoprozentsatz, #23
                                 buchungstext, #24
                                 buchungstext2, #25
                                 uid_nummer, #26
                                 dienstleistungsnummer, #27
                                 dienstleistungsland, #28
                                 dienstleistungsexport, #29
                                 dms_schluessel, #30
                                 kostentraeger, #31
                                 fremdbelegnummer, #32
                                 wert1, #33
                                 wert2, #34
                                 mahnsperre, #35
                                 kundendatenfeld #36
                                ]) + ";"
                                                                 
                lines.append(line)
                
                # gegen buchung
                line = ";".join([gegenkonto,        #1 
                                 konto,             #2
                                 opnummer,          #3
                                 belegdat,          #4 
                                 valuta_datum,      #5
                                 waehrung,          #6
                                 sollbetrag_gegenbuchung,        #7
                                 habenbetrag_gegenbuchung,       #8
                                 "",                #9
                                 fremdwaehrung,     #10
                                 fremdwaehrung_sollbetrag,  #11
                                 fremdwaehrung_habenbetrag, #12
                                 kostenstelle,       #13
                                 belegkreis,         #14
                                 belegnr,            #15
                                 ust_land,           #16
                                 "",                 #17
                                 "",                 #18
                                 ust_sondercode,     #19
                                 buchungsart,        #20
                                 abweichende_zahlungsfrist, #21
                                 abweichende_kontofrist,    #22
                                 abw_skontoprozentsatz,     #23
                                 buchungstext,  #24
                                 buchungstext2, #25
                                 uid_nummer,    #26
                                 dienstleistungsnummer, #27
                                 dienstleistungsland,   #28
                                 dienstleistungsexport, #29
                                 dms_schluessel,   #30
                                 kostentraeger,    #31
                                 fremdbelegnummer, #32
                                 wert1, #33
                                 wert2, #34
                                 mahnsperre,     #35
                                 kundendatenfeld #36
                                ]) + ";"

                lines.append(line)
                
        
        lines = "\r\n".join(lines) + "\r\n"
        charset = "cp1252"
        
        res["data"] = base64.encodestring(lines.encode(charset,"replace"))
        return res
