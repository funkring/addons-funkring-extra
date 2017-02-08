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

from openerp.osv import fields, osv
from openerp.addons.jdoc.jdoc import META_MODEL
from openerp.exceptions import Warning
from openerp.addons.fpos.product import COLOR_NAMES

from openerp.addons.at_base import util
from openerp.addons.at_base import helper

from Crypto import Random
from Crypto.Hash import SHA256
import OpenSSL.crypto

import base64
import re

AES_BLOCK_SIZE = 32
CRC_N = 3

class pos_category(osv.osv):
    _inherit = "pos.category"
    _columns =  {
        "pos_main" : fields.boolean("Main Category"),
        "pos_color" : fields.selection(COLOR_NAMES, string="Color"),
        "pos_unavail" : fields.boolean("Unavailable"),
        "after_product" : fields.selection([("parent","to parent"),
                                            ("main","to main"),
                                            ("root","to root"),
                                            ("back","to recent category")],
                                         string="After product",
                                         help="Action after product selection"),
        "foldable" : fields.boolean("Foldable"),
        "link_id" : fields.many2one("pos.category", "Link", ondelete="set null", index=True)
    }

    def _fpos_category_get(self, cr, uid, obj, *args, **kwarg):
        mapping_obj = self.pool["res.mapping"]

        # build product
        return {
            "_id" : mapping_obj._get_uuid(cr, uid, obj),
            META_MODEL : obj._model._name,
            "name" : obj.name,
            "parent_id" : mapping_obj._get_uuid(cr, uid, obj.parent_id),
            "image_small" : obj.image_small,
            "sequence" : obj.sequence,
            "pos_color" : obj.pos_color,
            "pos_unavail" : obj.pos_unavail,
            "pos_main" : obj.pos_main,
            "after_product" : obj.after_product,
            "foldable" : obj.foldable,
            "link_id" :  mapping_obj._get_uuid(cr, uid, obj.link_id)
        }

    def _fpos_category_put(self, cr, uid, obj, *args, **kwarg):
        return None

    def _fpos_category(self, cr, uid, *args, **kwargs):
        return {
            "get" : self._fpos_category_get,
            "put" : self._fpos_category_put
        }


class pos_config(osv.Model):

    _inherit = "pos.config"
    _columns = {
        "fpos_prefix" : fields.char("Fpos Prefix"),
        "fpos_sync_clean" : fields.integer("Clean Sync Count", help="Resync all Data after the specified count. if count is 0 auto full sync is disabled"),
        "fpos_sync_count" : fields.integer("Sync Count", help="Synchronization count after full database sync", readonly=True),
        "fpos_sync_version" : fields.integer("Sync Version", readonly=True),
        "iface_nogroup" : fields.boolean("No Grouping", help="If a product is selected twice a new pos line was created"),
        "iface_fold" : fields.boolean("Fold",help="Don't show foldable categories"),
        "iface_place" : fields.boolean("Place Management"),
        "iface_fastuswitch" : fields.boolean("Fast User Switch"),
        "iface_ponline" : fields.boolean("Search Partner Online"),
        "iface_nosearch" : fields.boolean("No Search"),
        "iface_printleft" : fields.boolean("Print Button Left"),
        "iface_autofav" : fields.boolean("Auto Favorites"),
        "fpos_printer_ids" : fields.many2many("fpos.printer", "fpos_config_printer_rel", "config_id", "printer_id", "Printer", copy=True, composition=True),
        "fpos_dist_ids" : fields.many2many("fpos.dist","fpos_config_dist_rel","config_id","dist_id","Distributor", copy=True, composition=True),
        "fpos_income_id" : fields.many2one("product.product","Cashstate Income", domain=[("income_pdt","=",True)], help="Income product for auto income on cashstate"),
        "fpos_expense_id" : fields.many2one("product.product","Cashstate Expense", domain=[("expense_pdt","=",True)], help="Expense product for auto expense on cashstate"),
        "iface_trigger" : fields.boolean("Cashbox Trigger", help="External cashbox trigger"),
        "iface_user_nobalance" : fields.boolean("User: no Balancing",  help="Balancing deactivated for User"),
        "iface_user_printsales" : fields.boolean("User: print sales", help="User allowed to print own sales"),
        "iface_test" : fields.boolean("Test"),
        "iface_waiterkey" : fields.boolean("Waiter Key"),
        "liveop" : fields.boolean("Live Operation", readonly=True, select=True, copy=False),
        "fpos_dist" : fields.char("Distributor", copy=True, index=True),
        "user_id" : fields.many2one("res.users","Sync User", select=True, copy=False),
        "user_ids" : fields.many2many("res.users",
                                      "pos_config_user_rel",
                                      "config_id", "user_id",
                                      "Users",
                                      help="Allowed users for the Point of Sale"),
        "fpos_hwproxy_id" : fields.many2one("fpos.hwproxy","Hardware Proxy", copy=True, index=True, composition=True),
        "parent_user_id" : fields.many2one("res.users","Parent Sync User", help="Transfer all open orders to this user before pos is closing", copy=True, index=True),           
        "payment_iface_ids" : fields.one2many("fpos.payment.iface","config_id","Payment Interfaces", copy=True, composition=True),
        
        "sign_method" : fields.selection([("card","Card"),
                                          ("online","Online")],
                                         string="Signature Method"),
                
        "sign_status" : fields.selection([("draft", "Draft"),
                                          ("config","Configuration"),
                                          ("active","Active"),
                                          ("react","(Re)Activation")], 
                                          string="Signature Status", readonly=True),
        
        "sign_serial" : fields.char("Serial"),
        "sign_cid" : fields.char("Company ID"),
        "sign_pid" : fields.char("POS ID"),
        "sign_key" : fields.char("Encryption Key", help="AES256 encryption key, Base64 coded"),
        "sign_crc" : fields.char("Checksum", readonly=True),
        "sign_certs" : fields.binary("Certificate", readonly=True)
    }
    _sql_constraints = [
        ("user_uniq", "unique (user_id)", "Fpos User could only assinged once"),
        ("sign_pid", "unique (sign_pid)", "Signature POS-ID could only used once")
    ]
    _defaults = {
        "fpos_sync_clean" : 15,
        "fpos_sync_version" : 1,
        "sign_status" : "draft"
    }
    _order = "company_id, name"
    
    def action_sign_config(self, cr, uid, ids, context=None):
        fpos_order_obj = self.pool["fpos.order"]
        for config in self.browse(cr, uid, ids, context=context):
            
            if config.liveop and config.sign_status == "draft":
                                
                key = base64.decodestring(config.sign_key)
                if not key or len(key) != AES_BLOCK_SIZE:
                    raise Warning(_("Invalid AES Key"))
                
                checksum = SHA256.new(config.sign_key).digest()[:CRC_N]
                checksum = base64.encodestring(checksum).replace("=", "")
                
                values = {
                   "sign_crc": checksum, 
                   "sign_status": "config"
                }
                
                if config.sign_method == "online":
                    values["sign_status"] = "active"
                
                self.write(cr, uid, config.id, values, context=context)
                
                # update turnover
                lastOrderEntries = fpos_order_obj.search_read(cr, uid,
                                    [("fpos_user_id","=",uid),("state","!=","draft")],
                                    ["seq", "turnover", "cpos", "date"],
                                    order="seq desc", limit=1, context={"active_test" : False})
        

                # reset turn over
                for lastOrderEntry in lastOrderEntries:
                    if lastOrderEntry["turnover"]:
                        fpos_order_obj.write(cr, uid, lastOrderEntry["id"], {"turnover": 0.0}, context=context)
                
        return True
    
    def activate_card(self, cr, uid, oid, certs, context=None):
        profile = self.browse(cr, uid, oid, context=context)
        if not profile.sign_status in ("config","react"):
            raise Warning(_("No activiation in this sign status possible"))
        if profile.fpos_user_id.id != uid:
            raise Warning(_("Card could only activated by Fpos"))
        if not certs:
            raise Warning(_("Card certifcate is empty"))
        
        certData = base64.b64decode(certs)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, certData)
        if cert.get_serial_number() != profile.sign_serial:
            raise Warning(_("Invalid SerialNo: Expected is %s, but transmitted was %s") % (profile.sign_serial, cert.get_serial_number()))
        
        self.write(cr, uid, oid, {
            "sign_certs": certs,
            "sign_status" : "active"    
        })
        
        return True
    
    def action_sign_reactivate(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            if config.liveop and config.sign_status == "active":
                self.write(cr, uid, config.id, {"sign_status": "react"}, context=context)
        return True

    def action_liveop(self, cr, uid, ids, context=None):
        user_obj = self.pool["res.users"]
        if not user_obj.has_group(cr, uid, "base.group_system"):
            raise Warning(_("Only system admin could set pos system into live operation"))

        for config in self.browse(cr, uid, ids, context):
            if not config.liveop and config.user_id:
                cr.execute("DELETE FROM fpos_order WHERE fpos_user_id = %s AND state IN ('draft','paid')", (config.user_id.id,))
                self.write(cr, uid, config.id, {"liveop" : True}, context=context)

    def action_post(self, cr, uid, ids, context=None):
        fpos_order_obj = self.pool["fpos.order"]
        for config in self.browse(cr, uid, ids, context=context):
            if config.liveop and config.user_id:
                order_ids = fpos_order_obj.search(cr, uid, [("fpos_user_id","=",config.user_id.id),("state","=","paid")], order="seq asc")
                if order_ids:
                    fpos_order_obj._post(cr, uid, order_ids, context=context)
        return True

    def run_scheduler(self, cr, uid, context=None): # run post in scheduler
        return self.action_post_all(cr, uid, context=context)

    def action_post_all(self, cr, uid, context=None):
        config_ids = self.search(cr, uid, [("liveop","=",True),("user_id","!=",False)])
        return self.action_post(cr, uid, config_ids, context=context)

    def get_profile(self, cr, uid, action=None, context=None):
        """
        @return: Fpos Profile
        """
        profile_data = self.search_read(cr, uid, [("user_id","=", uid)], ["parent_user_id"], context=context)
        if not profile_data:
            return False
        
        profile_data = profile_data[0]
        profile_id = profile_data["id"]
        
        # get parent profile id
        parent_profile_id = profile_data["parent_user_id"]
        if parent_profile_id:
            parent_profile_id = self.search_id(cr, uid, [("user_id","=",parent_profile_id[0])], context=context)
            

        jdoc_obj = self.pool["jdoc.jdoc"]
        jdoc_options = {
            "model" : {
                "pos.config" : {
                    "compositions" : ["journal_ids","user_ids","company_id","sequence_id"]
                },
                "res.company" : {
                    "compositions" : ["currency_id"]
                }
            }
        }
        
        # check sync action
        if action:
            if action == "inc":
                cr.execute("UPDATE pos_config SET fpos_sync_count=fpos_sync_count+1 WHERE id=%s", (profile_id,))
            elif action == "reset":
                cr.execute("UPDATE pos_config SET fpos_sync_count=0 WHERE id=%s", (profile_id,))
                # update parents sync version
                if not parent_profile_id:
                    cr.execute("UPDATE pos_config SET fpos_sync_version=fpos_sync_version+1 WHERE id=%s", (profile_id,))
        
        # update childs sync version
        if parent_profile_id:
            cr.execute("UPDATE pos_config SET fpos_sync_version=(SELECT MIN(p.fpos_sync_version) FROM pos_config p WHERE p.id=%s) WHERE id=%s", (parent_profile_id, profile_id))
                

        # query config
        res = jdoc_obj.jdoc_by_id(cr, uid, "pos.config", profile_id, options=jdoc_options, context=context)

        # get counting values
        fpos_order_obj = self.pool.get("fpos.order")
        last_order_values = fpos_order_obj.search_read(cr, uid,
                                    [("fpos_user_id","=",uid),("state","!=","draft")],
                                    ["seq", "turnover", "cpos", "date", "dep"],
                                    order="seq desc", limit=1, context={"active_test" : False})
        

        if last_order_values:
            last_order_values = last_order_values[0]
            res["last_seq"] = last_order_values["seq"]
            res["last_turnover"] = last_order_values["turnover"]
            res["last_cpos"] = last_order_values["cpos"]
            res["last_date"] = last_order_values["date"]
            res["last_dep"] = last_order_values["dep"]
        else:
            profile = self.browse(cr, uid, profile_id, context=context)
            res["last_seq"] = -1.0 + profile.sequence_id.number_next
            res["last_turnover"] = 0.0
            res["last_cpos"] = 0.0
            res["last_date"] = util.currentDateTime()
            res["last_dep"] = None

        # add company
        user_obj = self.pool["res.users"]
        company_id = user_obj._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))

        # get company infos
        company = self.pool["res.company"].browse(cr, uid, company_id, context=context)
        banks = company.bank_ids
        if banks:
            accounts = []
            for bank in banks:
                accounts.append(bank.acc_number)
            res["bank_accounts"] = accounts
        

        # finished
        return res

    def _get_orders_per_day(self, cr, uid, config_id, date_from, date_till, context=None):
        order_obj = self.pool("pos.order")
        res = []
        while date_from <= date_till:

            # calc time
            time_from = helper.strDateToUTCTimeStr(cr, uid, date_from, context=context)
            next_date = util.getNextDayDate(date_from)
            time_to = helper.strDateToUTCTimeStr(cr, uid, next_date, context=context)

            # get orders
            order_ids = order_obj.search(cr, uid, [("session_id.config_id","=",config_id),("date_order",">=",time_from),("date_order","<",time_to)], order="name asc")
            orders = order_obj.browse(cr, uid, order_ids, context=context)
            res.append((date_from, orders))

            # go to next
            date_from = next_date

        return res
    
    def onchange_sign_method(self, cr, uid, ids, sign_method, sign_status, sign_serial, sign_cid, sign_pid, sign_key, fpos_prefix, company_id, context=None):
        value =  {}
        
        if sign_method and sign_status == "draft":
            if not sign_cid and company_id:
                company = self.pool["res.company"].browse(cr, uid, company_id, context=context)
                value["sign_cid"] = company.vat
            if not sign_pid and fpos_prefix:
                value["sign_pid"] = re.sub("[^0-9A-Za-z]", "", fpos_prefix)
            if not sign_key:
                value["sign_key"] = base64.b64encode(Random.new().read(AES_BLOCK_SIZE))
        
        res = {"value": value}
        return res
            
    def copy(self, cr, uid, oid, default, context=None):
                        
        def incField(model_obj, field, default):
            val = default.get(field)
            if not val and model_obj:
                val = model_obj.read(cr, uid, oid, [field], context=context)[field]
            if val:
                m = re.match("([^0-9]*)([0-9]+)(.*)", val)
                if m:
                    default[field]="%s%s%s" % (m.group(1), int(m.group(2))+1, m.group(3))

        incField(self, "name", default)
        incField(self, "fpos_prefix", default)
        
        fpos_prefix =  default.get("fpos_prefix")
        if fpos_prefix:
            user_ref = self.read(cr, uid, oid, ["user_id"], context=context)["user_id"]
            if user_ref:
                userObj = self.pool["res.users"]
                userFields = ["name","email","login"]
                userDefaults = {}                
                for userField in userFields:
                    incField(userObj, userField, userDefaults)
                if userDefaults:
                    default["user_id"] = userObj.copy(cr, uid, user_ref[0], userDefaults, context=context)
                    
        return super(pos_config, self).copy(cr, uid, oid, default, context=context)
    
    def create(self, cr, uid, values, context=None):
        
        fpos_prefix = values.get("fpos_prefix")
        long_name = None
        if fpos_prefix:
            short_name = re.sub("[^0-9A-Za-z]", "", fpos_prefix)
            if short_name:
                long_name = values["name"]
                values["name"] = short_name
            
        config_id = super(pos_config, self).create(cr, uid, values, context=context)
        
        if long_name:
            self.write(cr, uid, config_id, {"name": long_name}, context=context)
        
        return config_id


class pos_order(osv.Model):

    _inherit = "pos.order"
    _columns = {
        "fpos_order_id" : fields.many2one("fpos.order", "Fpos Order"),
        "fpos_place_id" : fields.many2one("fpos.place", "Place")
    }

    def reconcile_invoice(self, cr, uid, ids, context=None):
        ids = self.search(cr, uid, [('state','=','invoiced'),('invoice_id.state','=','open'),("id","in",ids)])
        move_line_obj = self.pool.get('account.move.line')
        st_line_obj = self.pool.get("account.bank.statement.line")

        # check move lines
        for order in self.browse(cr, uid, ids, context):
            st_line_obj.confirm_statement(cr, uid, [s.id for s in order.statement_ids], context=context)

        # reconcile
        for order in self.browse(cr, uid, ids, context):
            invoice = order.invoice_id
            data_lines = [x.id for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id]

            partial = False
            for st_line in order.statement_ids:
                if not st_line.journal_id.fpos_noreconcile:
                    data_lines += [x.id for x in st_line.journal_entry_id.line_id if x.account_id.id == invoice.account_id.id]
                else:
                    partial = True

            if partial:
                move_line_obj.reconcile_partial(cr, uid, data_lines, context=context)
            else:
                move_line_obj.reconcile(cr, uid, data_lines, context=context)


    def _after_invoice(self, cr, uid, order, context=None):
        self.reconcile_invoice(cr, uid, [order.id], context=context)


class pos_order_line(osv.Model):

    _inherit = "pos.order.line"
    _columns = {
        "fpos_line_id" : fields.many2one("fpos.order.line", "Fpos Line")
    }


class pos_session(osv.Model):

    def _cash_statement_id(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids)
        for session in self.browse(cr, uid, ids, context):
            for st in session.statement_ids:
                if st.journal_id.type == "cash":
                    res[session.id] = st.id
        return res

    _inherit = "pos.session"
    _columns = {
        "cash_statement_id" : fields.function(_cash_statement_id,
                             type='many2one', relation='account.bank.statement',
                             string='Cash Statement', store=True)
    }


class fpos_payment_iface(osv.Model):
    _name = "fpos.payment.iface"
    _rec_name = "journal_id"
    _columns = {
        "config_id" : fields.many2one("pos.config","Config", required=True, select=True),
        "journal_id" : fields.many2one("account.journal","Journal", required=True),
        "iface" : fields.selection([("mcashier","mCashier"),
                                    ("tim","TIM")], string="Interface", required=True)
    }

