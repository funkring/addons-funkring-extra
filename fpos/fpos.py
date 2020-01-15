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
from openerp.addons.at_base import util
from openerp.addons.at_base import helper
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp

from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class fpos_order(models.Model):
    _name = "fpos.order"
    _description = "Fpos Order"
    _order = "date desc"
    
    name = fields.Char("Name", readonly=True, states={'draft': [('readonly', False)]})
    
    sv = fields.Integer("Sync Version", readonly=True)
    
    st = fields.Selection([("s","Start"),
                           ("0","Null"),
                           ("c","Cancel"),
                           ("m","Mixed"),
                           ("t","Training")],
                          string="Special Type", readonly=True)
    
    tag = fields.Selection([("s","Status"),("t","Temp")], string="Tag", readonly=True, states={'draft': [('readonly', False)]}, index=True)    
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
    
    active = fields.Boolean("Active", default=True, index=True, readonly=True)
    
    note = fields.Text("Note")
    send_invoice = fields.Boolean("Send Invoice", index=True)
    
    amount_tax = fields.Float("Tax Amount")
    amount_total = fields.Float("Total")
    
    company_id = fields.Many2one("res.company", string='Company', required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env["res.company"]._company_default_get("fpos.order"))
    
    currency_id = fields.Many2one("res.currency", "Currency", related="company_id.currency_id", store=True, readonly=True)
    
    line_ids = fields.One2many("fpos.order.line", "order_id", "Lines", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    
    log_ids = fields.One2many("fpos.order.log", "order_id", "Order", readonly=True, states={'draft': [('readonly', False)]}, composition=True)
    
    cent_fix = fields.Float("Cent Correction", readonly=True)
       
    dep = fields.Char("DEP", help="Data Export Protocol Data", readonly=True)
    qr = fields.Char("QR Code", readonly=True)
    hs = fields.Char("Hash", readonly=True, index=True)
    sig = fields.Boolean("Signed", readonly=True)
    
    ga = fields.Boolean("Groupable", readonly=True)
    
    
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
        
        tax_obj = self.pool["account.tax"]
        
        for order in self:
            cash_payment = None
            payment_total = 0
            
            for payment in order.payment_ids:
                if payment.journal_id.type == "cash":            
                    cash_payment = payment
                payment_total += payment.amount
                
                
            # ###################################################
            # FIX invalid status flag
            # ###################################################
            
            has_status = False
            order_total = 0
            
            for line in order.line_ids:                
                if line.tag in ("b","r","c","s"):
                    has_status = True
                else:
                    order_total += line.subtotal_incl
                
            if not has_status:
                order.tag = ""    
            
            
            # ###################################################
            # FIX invalid calc
            # ###################################################
            
            if abs(payment_total-order_total) > 0.01:
                taxes = {}
                fpos_taxes = []
                order_tax = 0
                for line in order.line_ids:
                    taxes = line.tax_ids
                    price = line.price
                    calc = tax_obj.compute_all(self._cr, self._uid, taxes, price, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    if taxes:
                        tax_rec = taxes[0]
                        tax = taxes.get(tax_rec.id)
                        tax_amount = calc["total_included"] - calc["total"]
                        order_tax += tax_amount
                        if tax is None:                            
                            tax = {
                                "name" : tax_rec.name,
                                "amount_tax" : tax_amount,
                                "amount_netto" : calc["total"]                                
                            }
                            taxes[tax_rec.id] = tax
                            fpos_taxes.append(tax)
                        else:
                            tax["amount_tax"] =  tax["amount_tax"] + tax_amount
                            tax["amount_netto"] = tax["amount_netto"] + calc["total"]
                      
                # correct tax
                order.tax_ids.unlink()
                order.tax_ids = [(0,0,t) for t in fpos_taxes]
                
                # correct payment
                diff = order_total-payment_total
                for payment in order.payment_ids:
                    payment.amount = payment.amount + diff 
                    break
                
                order.amount_total = order_total
                order.amount_tax = order_tax

        return True
    
    @api.model
    def post_order_notify(self, uuid):
        return True
         
    @api.model
    def post_order(self, docs):
        if isinstance(docs, dict):
            docs = [docs]
        
        lastOrderEntry = self.with_context({"active_test" : False}).search_read([("fpos_user_id","=",self._uid),("state","!=","draft")],
                                                  ["seq"],
                                                  order="seq desc", limit=1, context={"active_test" : False})
        uuid = None
            
        nextSeq = 0
        if lastOrderEntry:
            nextSeq = lastOrderEntry[0]["seq"] or 0
        
        if docs:
            jdoc_obj = self.env["jdoc.jdoc"]
            mapping_obj = self.env["res.mapping"]
            for doc in docs: 
                # check user
                fpos_user_id = mapping_obj.get_id("res.users", doc.get("fpos_user_id"))
                if fpos_user_id != self._uid:
                    raise Warning(_("User %s cannot post order as user %s") % (self._uid, fpos_user_id))
                
                # check sequence            
                nextSeq += 1       
                if nextSeq != doc["seq"]:
                    break

                # check if order already exist
                order = mapping_obj._browse_mapped(doc["_id"], "fpos.order")
                if order and order.state != "draft":
                    # don't override order if it is not in draft state
                    uuid = doc["_id"]
                else:
                    # lock order
                    doc["fdoo__locked"] = True
                    uuid = jdoc_obj.jdoc_put(doc)
                    
                # notify post
                self.post_order_notify(uuid)
       
        # build res     
        res =  {
            "seq" : nextSeq,
        }
        
        if uuid:
            res["_id"] = uuid
            
        return res
        
    @api.multi
    def _post(self):
        # the right order for booking is expected !!!
        
        profileDict = {}
        sessionDict = {}      
        profile_obj = self.env["pos.config"]
        data_obj = self.env["ir.model.data"]
        
        session_obj = self.pool["pos.session"]                
        order_obj = self.pool["pos.order"]
        invoice_obj = self.pool["account.invoice"]
        st_obj = self.pool["account.bank.statement"]
        context = self._context and dict(self._context) or {}
            
        precision = self.pool.get('decimal.precision').precision_get(self._cr, self._uid, 'Account')       
        status_id = data_obj.xmlid_to_res_id("fpos.product_fpos_status",raise_if_not_found=True)
        
        # build fpos order to pos order map
        fpos_order_ids = [o.id for o in self]
        if not fpos_order_ids:
            return True
        
        self._cr.execute("SELECT fo.id, o.id FROM fpos_order fo "
                         " INNER JOIN pos_order o ON o.fpos_order_id = fo.id WHERE fo.id IN %s ", (tuple(fpos_order_ids),))
        
        fpos2posOrderMap = dict([(r[0],r[1]) for r in self._cr.fetchall()])
        
        # post orders
        for order in self:
            # check if order was already done
            # (prevent double creation)
            if fpos2posOrderMap.get(order.id):
                order.state = "done"
                continue
            
            # get profile
            profile = profileDict.get(order.fpos_user_id.id)
            if profile is None:
                profile = profile_obj.search([("user_id","=", order.fpos_user_id.id)])
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
                session_uid = order.fpos_user_id.id 
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
                
            if order.tag == "s":
                # finish session
                finish = True
                
            # get session and check statements  
            session = sessionCfg["session"]
            statements = sessionCfg["statements"]
            if not statements:
                for st in session.statement_ids:
                    statements[st.journal_id.id] = st

            # get user
            session_uid = session.user_id.id
            
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
            
            invoice_id = None
            if order.ref:
                inv_type = ["out_invoice","in_refund"]
                if order.amount_total < 0.0:
                    inv_type = ["in_invoice","out_refund"]
                invoice_vals = invoice_obj.search_read(self._cr, session_uid, [("number","=",order.ref),("type","in",inv_type),("state","=","open"),("residual","=",order.amount_total)], ["partner_id"], context=context)
                if invoice_vals:
                    invoice_vals = invoice_vals[0]   
                    invoice_id = invoice_vals["id"]
                    # connect invoice         
                    order_vals["partner_id"] =  invoice_vals["partner_id"][0]
      
            
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
                    price_unit = line.price or 0.0
                    if line.tax_ids:
                        # check if price conversion is needed
                        invalidTax=False
                        for tax in line.tax_ids:
                            if not tax.price_include and not line.netto:
                                invalidTax=True
                                break
                            
                        if invalidTax:
                            raise Warning(_("Unable to post order %s: tax 'price include/exclude' was changed or tax mixed") % order.name)
                            
                    if line.product_id:
                        # add line with product
                        lines.append((0,0,{
                            "fpos_line_id" : line.id,
                            "company_id" : order.company_id.id,
                            "name" : line.name or _("Empty"),
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
                            "name" : line.name or _("Empty"),
                            "product_id" : status_id,                    
                            "notice" : "\n".join(notice),
                            "price_unit" : 0.0,
                            "qty" : 0.0,
                            "discount" : 0.0,
                            "create_date" : order.date
                        }))
                
                
            # create order      
            pos_order_id = order_obj.create(self._cr, session_uid, order_vals, context=context)
            pos_order_ids = [pos_order_id]

            # correct name
            order_obj.write(self._cr, session_uid, pos_order_id, { 
                                    "name" : order.name          
                                  }, context)
            
            # check cent correction          
            payment_total = 0.0
            payments = []
            for payment in order.payment_ids:
                st = statements[payment.journal_id.id]
                payment_amount = round(payment.amount, precision)                
                payment_total += payment_amount
                payments.append((st, payment.journal_id, payment_amount))
                
            if payment_total:                
                order_total = order_obj.read(self._cr, session_uid, pos_order_id, ["amount_total"], context=context)["amount_total"]               
                diff = round(payment_total - order_total, precision) 
                if (diff >= 0.01 and diff < 0.1) or (diff <= -0.01 and diff > -0.1 ):
                    order.cent_fix = diff
                    order_obj.write(self._cr, session_uid, pos_order_ids, {
                                        "lines" : [(0,0,{
                                                    "company_id" : order.company_id.id,
                                                    "name" : _("Cent Correction"),
                                                    "product_id" : status_id,                    
                                                    "price_unit" : diff,
                                                    "qty" : 1.0,
                                                    "discount" : 0.0,
                                                    "create_date" : order.date
                                                    })]
                                         }, context=context)
                
            
            # add payment
            create_invoice = order.send_invoice
            for st, journal, amount in payments:
                
                if journal.fpos_invoice and amount:
                    create_invoice = True
                    
                order_obj.add_payment(self._cr, session_uid, pos_order_id, { 
                                    "payment_date" : order.date,
                                    "amount" : amount,
                                    "journal" : journal.id,
                                    "statement_id" : st.id              
                                  },
                                  context)
            
           
            # post order
            order_obj.signal_workflow(self._cr, session_uid, pos_order_ids, "paid")
            # check if invoice should be created
            if create_invoice:
                if order.partner_id:
                    # created invoice
                    order_obj.action_invoice(self._cr, session_uid, pos_order_ids, context)
                    pos_order = order_obj.browse(self._cr, session_uid, pos_order_id, context)
                    
                    # update invoice
                    invoice_ids = [pos_order.invoice_id.id]
                    invoice_obj.write(self._cr, session_uid, invoice_ids, {"user_id" : order.user_id.id }, context)
                    invoice_obj.signal_workflow(self._cr, session_uid, invoice_ids, "invoice_open")
                    
                    # call after invoice
                    order_obj._after_invoice(self._cr, session_uid, pos_order, context=context)
                else:
                    order.send_invoice = False
            # check pos reference
            elif invoice_id:
                # connect invoice            
                order_obj.write(self._cr, session_uid, [pos_order_id], {"invoice_id": invoice_id, 
                                                                        "state": "invoiced" }, context=context)
                # reread order and do after invoice
                pos_order = order_obj.browse(self._cr, session_uid, pos_order_id, context=context)
                order_obj._after_invoice(self._cr, session_uid, pos_order, context=context)
                
            # check order
            order_vals = order_obj.read(self._cr, session_uid, pos_order_id, ["state"], context=context)
            if not order_vals["state"] in ("done","paid","invoiced"):
                order_vals = order_obj.read(self._cr, session_uid, pos_order_id, ["name","amount_total","amount_tax"], context=context)
                raise Warning(_("Unable to book order %s/%s/%s") % (order_vals["name"],order_vals["amount_total"],order_vals["amount_tax"]))              

            # set new fpos order state                        
            order.state = "done"
        
            # check if session should finished
            if finish:
                session_obj.signal_workflow(self._cr, session_uid, [session.id], "close")
                session_obj.write(self._cr, session_uid, [session.id], {"stop_at" : order.date})
                sessionDict[profile.id] = False
                
                # search finished orders, but leave last order active
                self._cr.execute("SELECT fo.id FROM pos_order o "
                                 " INNER JOIN pos_session s ON s.id = o.session_id AND s.state = 'closed' "
                                 " INNER JOIN fpos_order fo ON fo.id = o.fpos_order_id "
                                 " WHERE fo.active AND fo.fpos_user_id = %s "
                                 " ORDER BY fo.seq DESC ", (order.fpos_user_id.id,))
                
                # set finished orders inactive, but leave last order active
                finish_orders_ids = [r[0] for r in self._cr.fetchall()][1:]
                if finish_orders_ids:
                    finish_orders = self.browse(finish_orders_ids)
                    finish_orders.write({'active': False})
                    
                # send report
                start_at = helper.strToLocalDateStr(self._cr, self._uid, session.start_at, context=self._context)
                self.env["fpos.report.email"]._send_report(start_at, session=session)
                
                # delete unused draft
                draft_orders = self.search([("date","<",session.start_at),("state","=","draft"),("fpos_user_id","=",order.fpos_user_id.id)])
                draft_orders.unlink()
                
                # delete double orders
                self._cr.execute("DELETE FROM pos_order WHERE fpos_order_id in (SELECT MAX(o.id) FROM fpos_order o group by o.name, o.date, o.qr having count(o.id) > 1)")       
                self._cr.execute("DELETE FROM fpos_order WHERE id in (SELECT MAX(o.id) FROM fpos_order o group by o.name, o.date, o.qr having count(o.id) > 1)")                
                double_rows = self._cr.rowcount
                if double_rows:
                  _logger.error("deleted %s double orders", double_rows)
                 
        return True
    

class fpos_order_line(models.Model):
    _name = "fpos.order.line"
    _description = "Fpos Order Line"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product", index=True)
    group_id = fields.Many2one("product.product", "Group", index=True)
    uom_id = fields.Many2one("product.uom", "Unit")
    tax_ids = fields.Many2many("account.tax", "fpos_line_tax_rel", "line_id", "tax_id", "Taxes")
    price = fields.Float("Price")
    netto = fields.Boolean("Netto")
    qty = fields.Float("Quantity", digits=dp.get_precision('Product UoS'))
    tara = fields.Float("Tara")
    subtotal_incl = fields.Float("Subtotal Incl.")
    subtotal = fields.Float("Subtotal")
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
                            ("i","Income"),
                            ("#","Comment")],
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
            if "b" in self.flags:
                config.append(_("Break"))
            if "d" in self.flags:
                config.append(_("Detail"))
            if "l" in self.flags:
                config.append(_("Line"))
            if "1" in self.flags:
                config.append(_("Section"))
            if "2" in self.flags:
                config.append(_("Subsection"))
            if "g" in self.flags:
                config.append(_("Group"))
            if "a" in self.flags:
                config.append(_("Addition"))
            if "x" in self.flags:
                config.append(_("Balance"))
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
    st = fields.Selection([("1","Reduced 1"),
                           ("2","Reduced 2"),
                           ("s","Special"),
                           ("0","Null")],
                          string="Special Type")
    amount_tax = fields.Float("Tax")
    amount_netto = fields.Float("Netto")
    
    
class fpos_payment(models.Model):
    _name = "fpos.order.payment"
    _description = "Fpos Payment"
    _rec_name = "journal_id"
    
    order_id = fields.Many2one("fpos.order", "Order", required=True, ondelete="cascade", index=True)
    journal_id = fields.Many2one("account.journal", "Journal", required=True, index=True)
    receipt_ids = fields.One2many("fpos.order.payment.receipt", "payment_id", "Receipts", composition=True)
    amount = fields.Float("Amount")
    payment = fields.Float("Payment")
    code = fields.Char("Code")

    
class fpos_payment_receipt(models.Model):
    _name = "fpos.order.payment.receipt"
    _description = "Payment Receipt"
    _rec_name = "payment_id"
    
    payment_id = fields.Many2one("fpos.order.payment","Payment", required=True, ondelete="cascade", index=True)
    name = fields.Char("Name")
    receipt = fields.Text("Receipt")
    tag = fields.Char("Tag")
    
    
class fpos_printer(models.Model):
    _name = "fpos.printer"
    _description = "Printer"
    _rec_name = "complete_name"
    _order = "description, id"
    
    name = fields.Char("Url", required=True)    
    description = fields.Char("Description")
    complete_name = fields.Char("Name", compute="_complete_name", store=True, index=True)
    local = fields.Boolean("Local", help="Print on local printer")
    font_size = fields.Selection([("small","Small"),
                                  ("standard","Standard")], "Font Size", default="standard")
    pos_category_ids = fields.Many2many("pos.category", "fpos_printer_pos_category_rel", "printer_id", "category_id", string="Categories", 
                                    help="If no category is given all products are printed, otherwise only the products in the categories")
    
    @api.one
    @api.depends("name","description")
    def _complete_name(self):
        if self.description:
            self.complete_name = "%s [%s]" % (self.name, self.description)
        else:
            self.complete_name = self.name

        
class fpos_hwproxy(models.Model):
    _name = "fpos.hwproxy"
    _description = "Hardware Proxy"
    _rec_name = "complete_name"
    _order = "description, id"
    
    name = fields.Char("Url", required=True)    
    description = fields.Char("Description")
    complete_name = fields.Char("Name", compute="_complete_name", store=True, index=True)
    
    @api.one
    @api.depends("name","description")
    def _complete_name(self):
        if self.description:
            self.complete_name = "%s [%s]" % (self.name, self.description)
        else:
            self.complete_name = self.name

    
class fpos_dist(models.Model):
    _name = "fpos.dist"
    _description =  "Distributor"
    _rec_name = "complete_name"
    _order = "description, id"
    
    name = fields.Char("Url", required=True, index=True)
    description = fields.Char("Description")
    complete_name = fields.Char("Name", compute="_complete_name", store=True, index=True)
    
    @api.one
    @api.depends("name","description")
    def _complete_name(self):
        if self.description:
            self.complete_name = "%s [%s]" % (self.name, self.description)
        else:
            self.complete_name = self.name


class fpos_order_log(models.Model):
    _name = "fpos.order.log"
    _description = "Order Log"
    _rec_name = "date"
    
    date = fields.Datetime("Date", required=True, index=True)
    order_id = fields.Many2one("fpos.order", "Order", required=True, index=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", "User", required=True, index=True)
    fpos_user_id = fields.Many2one("res.users", "Device", required=True, index=True)
    line_ids = fields.One2many("fpos.order.log.line", "log_id", "Lines", composition=True)
    
    
class fpos_order_log_line(models.Model):
    _name = "fpos.order.log.line"
    _description = "Order Log Line"
    
    log_id = fields.Many2one("fpos.order.log","Log", required=True, index=True, ondelete="cascade")
    name = fields.Char("Name")
    product_id = fields.Many2one("product.product", "Product", index=True)
    uom_id = fields.Many2one("product.uom", "Unit")
    qty = fields.Float("Quantity", digits=dp.get_precision('Product UoS'))
    notice = fields.Text("Notice")
    
    
class fpos_report_email(models.Model):
    _name = "fpos.report.email"
    _description = "E-Mail Report"
    _inherit = ['mail.thread']
    
    name = fields.Char("Name", required=True)
    range = fields.Selection([("month","Month"),
                              ("week","Week"),
                              ("day", "Day")],
                              string="Range", default="month", required=True)
    
    pos_ids = fields.Many2many("pos.config", "fpos_report_email_config_rel", "report_id", "config_id", "POS")
    pos_id = fields.Many2one("pos.config", "Finishing POS", help="Send email after finished this POS")
    
    detail = fields.Boolean("Detail")
    journal_ids = fields.Many2many("account.journal", "fpos_report_email_journal_rel", "report_id", "journal_id", "Journals", 
                                   help="Journals for which detail lines should be printed, if empty all are printed")
    
    separate = fields.Boolean("Separate")
    
    product = fields.Boolean("Products", help="Print product overview")
    product_summary = fields.Boolean("Products Summary", help="Print only product categories")
    product_intern = fields.Boolean("Intern Category", help="Group by intern category")
    
    irregular = fields.Boolean("Irregularities", help="Print irregularities")
    
    daily_overview = fields.Boolean("Daily Overview", help="Adds an daily overview")
    summary = fields.Boolean("Summary", help="Summary")
     
    bmd_export = fields.Boolean("BMD Export")
    rzl_export = fields.Boolean("RZL Export") 
    
    partner_id = fields.Many2one("res.partner","Partner", required=True)
    company_id = fields.Many2one("res.company", string="Company", change_default=True, required=True, 
                                 default=lambda self: self.env["res.company"]._company_default_get())
    
    range_start = fields.Date("Last Range")
    
    def _send_mail(self, start_date=None):
        if not start_date:
            start_date = start_date = util.currentDate()
        
        mail_obj = self.pool["mail.mail"]
        mail_tmpl_obj = self.pool["email.template"]    
        att_obj = self.pool["ir.attachment"]
        rzl_obj = self.env["fpos.wizard.export.rzl"]
        bmd_obj = self.env["fpos.wizard.export.bmd"]
        config_obj = self.env["pos.config"]
        
        data_obj = self.pool["ir.model.data"]        
        template_id = data_obj.xmlid_to_res_id(self._cr, self._uid, "fpos.email_report", raise_if_not_found=True)
       
        mail_range = self._cashreport_range(start_date)
        
        # check if session exist for these range
        session_ids = self._session_ids(mail_range)
        if session_ids:        
        
            mail_context = self._context and dict(self._context) or {}
            mail_context["start_date"] = start_date
            mail_context["cashreport_name"] = mail_range[2]
            
            # check options
            if self.detail:
                mail_context["print_detail"] = True            
            if self.separate:
                mail_context["no_group"] = True
            if self.product:
                mail_context["print_product"] = True
            if self.summary:
                mail_context["summary"] = True
            if self.daily_overview:
                mail_context["daily_overview"] = True
            if self.irregular:
                mail_context["irregular"] = True
            if self.product_summary:
                mail_context["print_product_summary"] = True
            if self.product_intern:
                mail_context["print_product_intern"] = True
            if self.journal_ids:
                mail_context["journal_ids"] = [j.id for j in self.journal_ids]
                
            # build config
            config_ids = []
            if self.pos_ids:
                for pos in self.pos_ids:
                    config_ids.append(pos.id)
            else:
                for config in config_obj.search([("liveop","=",True)]):
                    config_ids.append(config.id)
                
            # add report info                
            mail_context["pos_report_info"] = {            
                "from" : mail_range[0],
                "till" : mail_range[1],
                "name" : mail_range[2],
                "config_ids" : config_ids
            }
                
       
            attachment_ids = []
            if self.rzl_export or self.bmd_export:
                # export rzl
                if self.rzl_export:
                    rzl_data = rzl_obj.with_context(
                                    active_model="pos.session",
                                    active_ids = session_ids                        
                                ).default_get(["data","data_name"])
                    attachment_ids.append( att_obj.create(self._cr, self._uid, {
                                                'name': rzl_data["data_name"],
                                                'datas_fname': rzl_data["data_name"],
                                                'datas': rzl_data["data"]
                                            }, context=self._context))
                                                    
                # export bmd
                if self.bmd_export:
                    bmd_data = bmd_obj.with_context(
                                    active_model="pos.session",
                                    active_ids = session_ids                        
                                ).default_get(["data","data_name"])
                    attachment_ids.append( att_obj.create(self._cr, self._uid, {
                                                'name': "buerf",
                                                'datas_fname': "buerf",
                                                'datas': bmd_data["buerf"]
                                           }, context=self._context))
                
            # write
            msg_id = mail_tmpl_obj.send_mail(self._cr, self._uid, template_id, self.id, force_send=False, context=mail_context)
            if attachment_ids:
                mail = mail_obj.browse(self._cr, self._uid, msg_id, context=self._context )
                # link with message
                att_obj.write(self._cr, self._uid, attachment_ids, { 
                        "res_model": "mail.message",
                        "res_id": mail.mail_message_id.id }, context=self._context)
                # add attachment ids to message
                mail_obj.write(self._cr,  self._uid, [msg_id], {
                                "attachment_ids" : [(4,oid) for oid in attachment_ids]
                              }, context=self._context)
            # send
            mail_obj.send(self._cr,  self._uid, [msg_id], context=mail_context)
    
    def _session_ids(self, report_range):
        # get sessions
        session_obj = self.pool["pos.session"]
        # convert to time str
        report_start = helper.strDateToUTCTimeStr(self._cr, self._uid, report_range[0], self._context)
        report_end = helper.strDateToUTCTimeStr(self._cr, self._uid, util.getNextDayDate(report_range[1]), self._context)
        # build domain
        domain = [("start_at",">=",report_start),("start_at","<",report_end)]
        pos_list = self.pos_ids
        if pos_list:
            config_ids = [c.id for c in pos_list]
            domain.append(("config_id","in",config_ids))
        # search
        return session_obj.search(self._cr, self._uid, domain, context=self._context)
    
    def _cashreport_range(self, start_date=None, offset=0):
        if not start_date:
            start_date = util.currentDate()
        
        cashreport_name = _("Cashreport")
        date_from = start_date
        date_till = start_date
        f = format.LangFormat(self._cr, self._uid, self._context)
        
        # calc month
        if self.range == "month":
            dt_date_from = util.strToDate(util.getFirstOfMonth(start_date))
            if offset:
                dt_date_from += relativedelta(months=offset)
            
            date_from = util.dateToStr(dt_date_from)
            date_till = util.getEndOfMonth(dt_date_from)
                
            month_name = helper.getMonthName(self._cr, self._uid, dt_date_from.month, context=self._context)
            cashreport_name = "%s - %s %s" % (cashreport_name, month_name, dt_date_from.year)
            
        # calc week
        elif  self.range == "week":
            dt_date_from = util.strToDate(start_date)
            if offset:
                dt_date_from += relativedelta(weeks=offset)
                
            weekday = dt_date_from.weekday()
            dt_date_from  = dt_date_from + relativedelta(days=-weekday)
            kw = dt_date_from.isocalendar()[1]
            date_from = util.dateToStr(dt_date_from)
            date_till = util.dateToStr(dt_date_from + relativedelta(days=weekday+(6-weekday)))
            cashreport_name = _("%s - CW %s %s") % (cashreport_name, kw, dt_date_from.year)
            
        # calc date
        else:
            if offset:
                dt_date_from = util.strToDate(start_date)
                dt_date_from += relativedelta(days=offset)
                date_from = util.dateToStr(dt_date_from)
                date_till = date_from
                
            cashreport_name = "%s - %s" % (cashreport_name, f.formatLang(date_from, date=True))
            
        return (date_from, date_till, cashreport_name)
    
    def _send_report(self, start_date=None, session=None):
        if not start_date:
            start_date = util.currentDate()        
        for report_email in self.search([]):
            has_pos = False
            mail_range = None
            
            # check for main pos to send, or delay one day            
            pos = report_email.pos_id
            if pos and session:
                config_obj = self.env["pos.config"]
                mail_range = report_email._cashreport_range(start_date, 0)
                
                def all_finished():
                    if not pos.user_id:
                        return False
                    fpos_user_ids = [c.user_id.id for c in config_obj.search([("parent_user_id","=",pos.user_id.id)]) if c.user_id]
                    fpos_user_ids.append(pos.user_id.id)
                    return not self.env["fpos.order"].search_count([("fpos_user_id","in",fpos_user_ids),("state","=","paid")])
                
                # check if it is main pos
                if session.config_id.id == pos.id:
                    has_pos = all_finished()     
                               
                # check if it is child of main pos
                elif session.config_id.parent_user_id:
                    # get mail range with offset from current day                    
                    session_ids = self._session_ids(mail_range)
                    # check if main pos has finished,
                    #  and all child pos has finished
                    if session_ids:
                        session_obj = self.env["pos.session"]
                        
                        # query session count
                        session_domain = [("config_id","=",pos.id),("id","in",session_ids)]
                        session_count = session_obj.search_count(session_domain)
                        
                        # query closed session count
                        session_domain.append(("stop_at","!=",False))
                        session_count_closed = session_obj.search_count(session_domain)
                        
                        # check all main session finished
                        if session_count and session_count == session_count_closed:                                                
                            has_pos = all_finished()
                
            # send last... (offset from last day)
            if not has_pos or not mail_range:                    
                mail_range = report_email._cashreport_range(start_date, -1)
                
            has_report = report_email.range_start < mail_range[0] and mail_range[1] < start_date
            
            # ... or current
            if has_pos and mail_range[1] == start_date:
                has_report = True
            
            if has_report:
                report_email._send_mail(mail_range[0])
                range_start = mail_range[0]
                # send other
                if report_email.range_start:
                    while True:
                        mail_range = report_email._cashreport_range(mail_range[0], -1)
                        if report_email.range_start < mail_range[0]:
                            report_email._send_mail(mail_range[0])
                        else:
                            break
                report_email.range_start = range_start
    
    @api.multi
    def action_test_email(self):
        for report_mail in self:
            report_mail._send_mail(start_date=self.range_start)
        return True
      

class fpos_profile(models.Model):
    _name = "fpos.profile"
    _description = "Profile"

    name = fields.Char("Name", required=True)
    