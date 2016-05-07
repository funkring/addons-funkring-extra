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
from openerp.addons.at_base import format
from openerp import SUPERUSER_ID

class fpos_order(models.Model):
    _name = "fpos.order"
    _description = "Fpos Order"
    _order = "date desc"
    
    name = fields.Char("Name")
    tag = fields.Selection([("s","Status")], string="Tag", readonly=True, states={'draft': [('readonly', False)]}, index=True)    
    fpos_user_id = fields.Many2one("res.users", "Device", required=True, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    user_id = fields.Many2one("res.users", "User", required=True, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    place_id = fields.Many2one("fpos.place","Place", readonly=True, states={'draft': [('readonly', False)]}, index=True, ondelete="restrict")
    partner_id = fields.Many2one("res.partner","Partner", readonly=True, states={'draft': [('readonly', False)]}, index=True)
    date = fields.Datetime("Date", required=True, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    seq = fields.Integer("Internal Sequence", readonly=True, index=True)
    cpos = fields.Float("Cash Position", readonly=True)
    turnover = fields.Float("Turnover Count", readonly=True)
    ref = fields.Char("Reference", readonly=True, states={'draft': [('readonly', False)]})
    tax_ids = fields.One2many("fpos.order.tax", "order_id", "Taxes", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    payment_ids = fields.One2many("fpos.order.payment","order_id", "Payments", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    state = fields.Selection([("draft","Draft"),
                              ("paid","Paid"),
                              ("done","Done")], "Status", default="draft", readonly=True, index=True)
    
    note = fields.Text("Note")
    send_invoice = fields.Boolean("Send Invoice", index=True)
    amount_tax = fields.Float("Tax Amount")
    amount_total = fields.Float("Total")
    
    company_id = fields.Many2one("res.company", string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env["res.company"]._company_default_get("fpos.order"))
    
    currency_id = fields.Many2one("res.currency", "Currency", related="company_id.currency_id", store=True, readonly=True)
    
    line_ids = fields.One2many("fpos.order.line", "order_id", "Lines", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state not in ("draft"):
                raise Warning(_("You cannot delete an order which are not in draft state"))
        return super(fpos_order, self).unlink()
    
    @api.multi
    def correct(self):
        if self._uid != SUPERUSER_ID:
            raise Warning(_("Only Administrator could correct Fpos orders"))
        
        for order in self:
            cash_payment = None
            payment_total = 0
            
            for payment in order.payment_ids:
                if payment.journal_id.type == "cash":
                    cash_payment = payment
                payment_total += payment.amount
                
            # ###################################################
            # FIX invalid payment BUG, DELETE KASSASTURZ LINES 
            # ###################################################
            if cash_payment and not payment_total and order.amount_total:
                cash_payment.amount = order.amount_total
                cash_payment.payment = order.amount_total
                order.cpos = order.cpos + order.amount_total
                                
                next_orders = order.search([("fpos_user_id","=",order.fpos_user_id.id),("name",">",order.name)],order="name asc")
                for next_order in next_orders:
                    next_order.cpos = next_order.cpos + order.amount_total
            
            
            # ###################################################
            # FIX invalid status flag
            # ###################################################
            has_status = False
            for line in order.line_ids:
                if line.tag in ("b","r","c","s"):
                    has_status = True
                    
            if not has_status:
                order.tag = None
            
    
    @api.model
    def create(self, vals):
        return super(fpos_order, self).create(vals)
    
    @api.multi
    def _post(self):
        profileDict = {}
        sessionDict = {}      
        profile_obj = self.env["pos.config"]
        data_obj = self.env["ir.model.data"]
        
        session_obj = self.pool["pos.session"]                
        order_obj = self.pool["pos.order"]
        invoice_obj = self.pool["account.invoice"]
        st_obj = self.pool["account.bank.statement"]
        context = self._context and dict(self._context) or {}
            
        status_id = data_obj.xmlid_to_res_id("fpos.product_fpos_status",raise_if_not_found=True)
        for order in self:
            # get profile
            profile = profileDict.get(order.fpos_user_id.id)
            if profile is None:
                profile = profile_obj.search( [("user_id","=", order.fpos_user_id.id)])
                if not profile or not profile[0].liveop:
                    profile = False
                else:
                    profile = profile[0]   
                profileDict[order.fpos_user_id.id] = profile
            
            # check if an profile exist
            # and order is in paid state
            if not profile or order.state != "paid":
                continue
            
            # init finish flag
            finish = False
            
            # get session
            sessionCfg = sessionDict.get(profile.id)
            if sessionCfg is None:
                # query first from database
                fpos_uid = profile.user_id.id
                session_ids = session_obj.search(self._cr, fpos_uid, [("config_id","=",profile.id),("state","=","opened")], context=context)
                if session_ids:
                    session = session_obj.browse(self._cr, fpos_uid, session_ids[0], context=context)
                    sessionCfg = {"session" : session,
                                  "statements" : {}}
                    sessionDict[profile.id] = sessionCfg
                else:
                    sessionDict[profile.id] = False

            # create session if not exist
            if not sessionCfg:
                # new session         
                session_uid = order.user_id.id  
                session_id = session_obj.create(self._cr, session_uid, {
                    "config_id" : profile.id,
                    "user_id" : session_uid,
                    "start_at" : order.date,
                    "sequence_number" : order.seq
                }, context=context)
                
                # write balance start
                session = session_obj.browse(self._cr, session_uid, session_id, context=context)
                cash = 0.0
                for payment in order.payment_ids:
                    if payment.journal_id.type == "cash":
                        cash += payment.amount
                    
                st_obj.write(self._cr, session_uid, [session.cash_statement_id.id],  {"balance_start" : order.cpos - cash})
                
                # open                
                session_obj.signal_workflow(self._cr, session_uid, [session_id], "open")
                session = session_obj.browse(self._cr, session_uid, session_id, context=context)
                
                # set new session
                sessionCfg =  {"session" : session,
                               "statements" : {}}
                sessionDict[profile.id] = sessionCfg
                
            elif order.tag == "s":
                # finish session
                finish = True
                
            # get session and check statements  
            session = sessionCfg["session"]
            statements = sessionCfg["statements"]
            if not statements:
                for st in session.statement_ids:
                    statements[st.journal_id.id] = st

            # handle order 
            # and payment

            lines = []
            order_vals = {
                "fpos_order_id" : order.id, 
                "fpos_place_id" : order.place_id.id,
                "name" : order.name,
                "company_id" : order.company_id.id,
                "date_order" : order.date,
                "user_id" : order.user_id.id,
                "partner_id" : order.partner_id.id,
                "sequence_number" : order.seq,
                "session_id" : session.id,
                "pos_reference" : order.ref,
                "note" : order.note,
                "nb_print" : 1,
                "lines" : lines
            }
            
            if not order.line_ids:
                # if no products book add empty state
                lines.append((0,0,{
                    "fpos_line_id" : None,
                    "company_id" : order.company_id.id,
                    "name" : _("Empty"),
                    "product_id" : status_id,                    
                    "price_unit" : 0.0,
                    "qty" : 0.0,
                    "discount" : 0.0,
                    "create_date" : order.date
                }))
                
            else:
                for line in order.line_ids:
    
                    # calc back price per unit
                    price_unit = line.brutto_price
                    if line.tax_ids:
                        # check if price conversion is needed
                        convert=False
                        for tax in line.tax_ids:
                            if not tax.price_include:
                                convert=True
                                break
                            
                        if convert:
                            raise Warning(_("Fpos could only use price with tax included"))
                            
                    if line.product_id:
                        # add line with product
                        lines.append((0,0,{
                            "fpos_line_id" : line.id,
                            "company_id" : order.company_id.id,
                            "name" : line.name,
                            "product_id" : line.product_id.id,                    
                            "notice" : line.notice,
                            "price_unit" : price_unit,
                            "qty" : line.qty,
                            "discount" : line.discount,
                            "create_date" : order.date
                        }))
                    else:                    
                        f = format.LangFormat(self._cr, order.user_id.id, context=context)
                        notice = []
                        if price_unit:
                            notice.append("%s %s" % (f.formatLang(price_unit, monetary=True), order.currency_id.symbol))
                        if line.notice:
                            notice.append(line.notice)
                        
                        # add status
                        lines.append((0,0,{
                            "fpos_line_id" : line.id,
                            "company_id" : order.company_id.id,
                            "name" : line.name,
                            "product_id" : status_id,                    
                            "notice" : "\n".join(notice),
                            "price_unit" : 0.0,
                            "qty" : 0.0,
                            "discount" : 0.0,
                            "create_date" : order.date
                        }))
                
                
            # create order      
            order_uid = order.user_id.id      
            pos_order_id = order_obj.create(self._cr, order_uid, order_vals, context=context)
            pos_order_ids = [pos_order_id]

            # correct name
            order_obj.write(self._cr, order_uid, pos_order_id, { 
                                    "name" : order.name          
                                  }, context)
            
            # add payment
            for payment in order.payment_ids:
                st = statements[payment.journal_id.id]                
                order_obj.add_payment(self._cr, order_uid, pos_order_id, { 
                                    "payment_date" : order.date,
                                    "amount" : payment.amount,
                                    "journal" : payment.journal_id.id,
                                    "statement_id" : st.id              
                                  },
                                  context)
            
           
            # post order
            order_obj.signal_workflow(self._cr, order_uid, pos_order_ids, "paid")
            # check if invoice should be crated
            if order.send_invoice:
                # created invoice
                order_obj.action_invoice(self._cr, order_uid, pos_order_ids, context)
                pos_order = order_obj.browse(self._cr, order_uid, pos_order_id, context)                
                invoice_obj.signal_workflow(self._cr, order_uid, [pos_order.invoice_id.id], "invoice_open")
                # call after invoice
                self._after_invoice(self._cr, order_uid, pos_order, context=context)
                
            # check order
            order_vals = order_obj.read(self._cr, order_uid, pos_order_id, ["state","name"], context=context)
            if not order_vals["state"] in ("done","paid","invoiced"):
                raise Warning(_("Unable to book order %s") % order_vals["name"])              

            # set new fpos order state                        
            order.state = "done"
        
            # check if session should finished
            if finish:
                session_obj.signal_workflow(self._cr, session.user_id.id, [session.id], "close")
                session_obj.write(self._cr, session.user_id.id, [session.id], {"stop_at" : order.date})
                sessionDict[profile.id] = False
                 
        return True
    

class fpos_order_line(models.Model):
    _name = "fpos.order.line"
    _description = "Fpos Order Line"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product", index=True)
    uom_id = fields.Many2one("product.uom", "Unit")
    tax_ids = fields.Many2many("account.tax", "fpos_line_tax_rel", "line_id", "tax_id", "Taxes")
    brutto_price = fields.Float("Brutto Price")
    qty = fields.Float("Quantity")
    tara = fields.Float("Tara")
    subtotal_incl = fields.Float("Subtotal")
    discount = fields.Float("Discount %")
    notice = fields.Text("Notice")
    sequence = fields.Integer("Sequence")
    flags = fields.Text("Flags")
    p_pre = fields.Integer("Price Predecimal")
    p_dec = fields.Integer("Price Decimal")
    a_pre = fields.Integer("Amount Predecimal")
    a_dec = fields.Integer("Amount Decimal")
    tag = fields.Selection([("b","Balance"),
                            ("r","Real"),
                            ("c","Counter"),
                            ("s","Status"),
                            ("o","Expense"),
                            ("i","Income")],
                            string="Tag",
                            index=True)
    
    config = fields.Text("Config", compute="_config")
    
    @api.one
    @api.depends("flags","p_pre", "p_dec", "a_pre", "a_dec")
    def _config(self):
        config = []
        if self.flags:
            if "-" in self.flags:
                config.append(_("Minus"))
            if "u" in self.flags:
                config.append(_("No Unit"))
            if "p" in self.flags:
                config.append(_("Price"))
        if self.p_pre or self.p_dec:
            config.append(_("*-Format: %s,%s") % (self.p_pre or 0, self.p_dec or 0))
        if self.a_pre or self.a_dec:
            config.append(_("€-Format: %s,%s") % (self.a_pre or 0, self.a_dec or 0))
        self.config = ", ".join(config)
 

class fpos_tax(models.Model):
    _name = "fpos.order.tax" 
    _description = "Fpos Order Tax"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    name = fields.Char("Name")
    amount_tax = fields.Float("Tax")
    amount_netto = fields.Float("Netto")
    
    
class fpos_payment(models.Model):
    _name = "fpos.order.payment"
    _description = "Fpos Payment"
    _rec_name = "journal_id"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    journal_id = fields.Many2one("account.journal", "Journal", required=True)
    amount = fields.Float("Amount")
    payment = fields.Float("Payment")
    
    
    