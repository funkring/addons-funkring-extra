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
from openerp.tools.translate import _

from openerp.addons.at_base import util
from openerp.addons.at_base import helper
from openerp import api
from openerp import tools

from Crypto import Random
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
import OpenSSL.crypto

import base64
import re
import struct

import requests
import simplejson

import openerp.addons.decimal_precision as dp

AES_KEY_SIZE = 32
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
        "link_id" : fields.many2one("pos.category", "Link", ondelete="set null", select=True)
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

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            image_data = obj.image
            result[obj.id] = {                
                "image_80mm": tools.image_resize_image(image_data, (576,576), avoid_if_small=True, preserve_aspect_ratio=True),
                "image_58mm": tools.image_resize_image(image_data, (384,384), avoid_if_small=True, preserve_aspect_ratio=True),
                "image_format" : image_data and "png" or None
            }
        return result

    def _set_image(self, cr, uid, oid, name, value, args, context=None):
        image_data = tools.image_resize_image(value, (1024,2024), filetype="PNG", avoid_if_small=True, preserve_aspect_ratio=True)
        return self.write(cr, uid, [oid], {"image": image_data}, context=context)

    _inherit = "pos.config"
    _columns = {
        "fpos_prefix" : fields.char("Fpos Prefix"),
        "fpos_sync_clean" : fields.integer("Clean Sync Count", help="Resync all Data after the specified count. if count is 0 auto full sync is disabled"),
        "fpos_sync_count" : fields.integer("Sync Count", help="Synchronization count after full database sync", readonly=True),
        "fpos_sync_reset" : fields.boolean("Sync Reset"),
        "fpos_sync_version" : fields.integer("Sync Version", readonly=True),
        "fpos_sync_realtime" : fields.boolean("Realtime Online Sync", help="Realtime online order synchronisation"),
        "fpos_query_stock" : fields.boolean("Realtime Stock Query"),
        "iface_nogroup" : fields.boolean("No Grouping", help="If a product is selected twice a new pos line was created"),
        "iface_fold" : fields.boolean("Fold",help="Don't show foldable categories"),
        "iface_place" : fields.boolean("Place Management"),
        "iface_fastuswitch" : fields.boolean("Fast User Switch"),
        "iface_ponline" : fields.boolean("Search Partner Online"),
        "iface_nosearch" : fields.boolean("No Search"),
        "iface_printleft" : fields.boolean("Print Button Left"),
        "iface_receipt" : fields.selection([("s","Simple"),("d","Simple with Detail"),("n","Normal")], string="Receipt Format"),
        "iface_autofav" : fields.boolean("Auto Favorites"),
        "fpos_printer_ids" : fields.many2many("fpos.printer", "fpos_config_printer_rel", "config_id", "printer_id", "Printer", copy=True, composition=True),
        "fpos_dist_ids" : fields.many2many("fpos.dist","fpos_config_dist_rel","config_id","dist_id","Distributor", copy=True, composition=True),
        "fpos_income_id" : fields.many2one("product.product","Cashstate Income", domain=[("income_pdt","=",True)], help="Income product for auto income on cashstate"),
        "fpos_expense_id" : fields.many2one("product.product","Cashstate Expense", domain=[("expense_pdt","=",True)], help="Expense product for auto expense on cashstate"),
        "iface_trigger" : fields.boolean("Cashbox Trigger", help="External cashbox trigger"),
        "iface_user_nobalance" : fields.boolean("User: no Balancing",  help="Balancing deactivated for User"),
        "iface_user_printsales" : fields.boolean("User: print sales", help="User allowed to print own sales"),
        "iface_desktop" : fields.boolean("Desktop"),
        "iface_test" : fields.boolean("Test"),
        "iface_waiterkey" : fields.boolean("Waiter Key"),
        "liveop" : fields.boolean("Live Operation", readonly=True, select=True, copy=False),
        "fpos_dist" : fields.char("Distributor", copy=True, select=True),
        "user_id" : fields.many2one("res.users","Sync User", select=True, copy=False),
        "user_ids" : fields.many2many("res.users",
                                      "pos_config_user_rel",
                                      "config_id", "user_id",
                                      "Users",
                                      help="Allowed users for the Point of Sale"),
        "fpos_hwproxy_id" : fields.many2one("fpos.hwproxy","Hardware Proxy", copy=True, select=True, composition=True),
        "parent_user_id" : fields.many2one("res.users","Parent Sync User", help="Transfer all open orders to this user before pos is closing", copy=True, select=True),
        "payment_iface_ids" : fields.one2many("fpos.payment.iface","config_id","Payment Interfaces", copy=True, composition=True),

        "sign_method" : fields.selection([("card","Card"),
                                          ("online","Online")],
                                         string="Signature Method", copy=False),

        "sign_status" : fields.selection([("draft", "Draft"),
                                          ("config","Configuration"),
                                          ("active","Active"),
                                          ("react","(Re)Activation")],
                                          string="Signature Status", readonly=True, copy=False),

        "sign_serial" : fields.char("Serial"),
        "sign_cid" : fields.char("Company ID"),
        "sign_pid" : fields.char("POS ID", copy=False),
        "sign_key" : fields.char("Encryption Key", copy=False, help="AES256 encryption key, Base64 coded"),
        "sign_crc" : fields.char("Checksum", copy=False, readonly=True),
        "sign_certs" : fields.binary("Certificate", copy=False, readonly=True),

        "sign_user" : fields.char("Online Sign User"),
        "sign_password" : fields.char("Online Sign Password"),

        "dep_key" : fields.char("DEP Key", copy=False),

        "fpos_model" : fields.selection([
                ("hand", "Hand"),
                ("flex", "Flex"),
                ("flex2", "Flex 2"),
                ("mpos", "Fine"),
                ("npos", "Raw"),
                ("pos", "POS"),
                ("online","Online"),
                ("tablet","Tablet"),
                ("pc","PC"),
                ("jim","OrderJIM")
            ], "Fpos Model"),


        # image: all image fields are base64 encoded and PIL-supported
        "image": fields.binary("Image",
            help="Receipt Image", export=False),
        "image_format" : fields.function(_get_image, 
            string="Image Format", 
            type="char",
            multi="_get_image",
            readonly=True,
            export=True,
            store={
                "pos.config": (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            }),
        "image_80mm": fields.function(_get_image, fnct_inv=_set_image,
            string="Receipt Image 80mm", type="binary",
            multi="_get_image",
            export=True,
            store={
                "pos.config": (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            }),
        "image_58mm": fields.function(_get_image, fnct_inv=_set_image,
            string="Receipt Image 56mm", type="binary",
            multi="_get_image",
            export=True,
            store={
                "pos.config": (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            }),
                
        "fpos_profile_ids": fields.many2many("fpos.profile", "fpos_config_fpos_profile_rel", "config_id", "profile_id", string="Profiles", copy=True),
        "iface_hidecat": fields.boolean("Hide Categories"),
        
        "fpos_1nd_journal_id": fields.many2one("account.journal", "1nd Payment Method", domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]"),
        "fpos_2nd_journal_id": fields.many2one("account.journal", "2nd Payment Method", domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]"),
        "fpos_payment_id" : fields.many2one("product.product","Payment", domain=[("income_pdt","=",False),("expense_pdt","=",False)], help="Product for payment")
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
                if not key or len(key) != AES_KEY_SIZE:
                    raise Warning(_("Invalid AES Key"))

                checksum = SHA256.new(config.sign_key).digest()[:CRC_N]
                checksum = base64.encodestring(checksum).replace("=", "")

                values = {
                   "sign_crc": checksum,
                   "sign_status": "config",
                   "dep_key":  util.password()
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

        # check if oid is uuid
        if isinstance(oid, basestring):
            oid = self.pool["res.mapping"].get_id(cr, uid, self._name, oid)

        profile = self.browse(cr, uid, oid, context=context)
        if not profile.sign_status in ("config","react"):
            raise Warning(_("No activiation in this sign status possible"))
        if profile.user_id.id != uid:
            raise Warning(_("Card could only activated by Fpos"))
        if not certs:
            raise Warning(_("Card certifcate is empty"))

        certData = base64.b64decode(certs)
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, certData)
        cert_serial = "%x" % cert.get_serial_number()
        if cert_serial != profile.sign_serial:
            raise Warning(_("Invalid SerialNo: Expected is %s, but transmitted was %s") % (profile.sign_serial, cert_serial))

        self.write(cr, uid, oid, {
            "sign_certs": certs,
            "sign_status" : "active"
        })

        return True

    def action_sign_reactivate(self, cr, uid, ids, context=None):
        for config in self.browse(cr, uid, ids, context=context):
            if config.liveop and config.sign_status == "active":
                if config.sign_method == "online":
                    self.write(cr, uid, config.id, {"sign_status": "draft"}, context=context)
                else:
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

    def sign_data(self, cr, uid, data, build_hash=False, context=None):
        profile_data = self.search_read(cr, uid, [("user_id","=", uid)], ["sign_status",
                                                                          "sign_user",
                                                                          "sign_password",
                                                                          "sign_key"], context=context)
        if not profile_data:
            raise Warning(_("No profile for user %s") % uid)

        profile = profile_data[0]
        if profile["sign_status"] != "active":
            raise Warning(_("Signation is not configured for user %s") % uid)

        sign_user = profile["sign_user"]
        sign_password = profile["sign_password"]
        sign_key = profile["sign_key"]

        def floatToStr(val):
            return ("%0.2f" % val).replace(".",",")

        def dateToStr(val):
            val = helper.strToLocalTimeStr(cr, uid, val, context=context)
            return util.strToTime(val).strftime("%Y-%m-%dT%H:%M:%S")

        def encryptTurnover():
            st = data["st"]
            specialType = None
            if st == "c":
                specialType = "STO"
            elif st == "t":
                specialType = "TRA"

            if specialType:
                return base64.encodestring(specialType)
            else:
                receiptId = "%s%s" % (data["sign_pid"],data["seq"])
                turnoverHash = SHA256.new(receiptId).digest()[:16]
                cipher = AES.new(base64.b64decode(sign_key), counter=lambda: turnoverHash, mode=AES.MODE_CTR)
                turnover = struct.pack(">qq", long(data["turnover"] * 100.0), 0)
                return base64.b64encode(cipher.encrypt(turnover)[:8])

        def b64urldecode_nopadding(val):
            missing_padding = len(val) % 4
            if missing_padding != 0:
                val += b'='* (4 - missing_padding)
            return base64.urlsafe_b64decode(val)

        data["turnover_enc"] = encryptTurnover()
        prevHash = base64.b64encode(SHA256.new(data["last_dep"]).digest()[:8])
        payload = [
            "R1-AT1",                       # 0
            data["sign_pid"],               # 1
            "%s" % data["seq"],             # 2
            dateToStr(data["date"]),        # 3
            floatToStr(data["amount"]),     # 4
            floatToStr(data["amount_1"]),   # 5
            floatToStr(data["amount_2"]),   # 6
            floatToStr(data["amount_0"]),   # 7
            floatToStr(data["amount_s"]),   # 8
            data["turnover_enc"],           # 9
            data["sign_serial"],            # 10
            prevHash                        # 11
        ]

        payload = "_%s" % "_".join(payload)
        url = "https://www.a-trust.at/asignrkonline/v2/%s/Sign/JWS" % sign_user
        json = {
           "password": sign_password,
           "jws_payload" : payload
        }

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        resp = requests.post(url, data=simplejson.dumps(json), headers=headers, timeout=10)
        resp.raise_for_status()
        res = simplejson.loads(resp.text)
        res = res.get("result")

        if not res:
            raise Warning(_("Signation failed for user %s") % uid)

        signation = str(res.split(".")[-1])
        signation = b64urldecode_nopadding(signation)
        plaindata = "%s_%s" % (payload, base64.b64encode(signation))
        data["qr"] = plaindata
        data["dep"] = res
        data["sig"] = True
        data["hs"] = None

        if build_hash:
            data["hs"] = base64.urlsafe_b64encode(SHA256.new(plaindata).digest()[:8])

        return data

    def get_profile(self, cr, uid, action=None, context=None):
        """
        @return: Fpos Profile
        """
        profile_data = self.search_read(cr, uid, [("user_id","=", uid)], ["parent_user_id",
                                                                          "fpos_sync_count",
                                                                          "fpos_sync_clean",
                                                                          "fpos_sync_version"], context=context)
        if not profile_data:
            raise Warning(_("No profile for user %s") % uid)


        # eval data
        profile_data = profile_data[0]
        fpos_sync_count = profile_data["fpos_sync_count"] or 0
        fpos_sync_clean = profile_data["fpos_sync_clean"] or 0
        fpos_sync_version = profile_data["fpos_sync_version"] or 1
        profile_id = profile_data["id"]

        # get parent or childs
        parent_user_id = profile_data["parent_user_id"]
        parent_profile_id = None
        child_ids = None
        if parent_user_id:
            parent_user_id = parent_user_id[0]
            child_ids = []

            parent_profile_data = self.search_read(cr, uid, [("user_id","=",parent_user_id)],["fpos_sync_version"], context=context)
            if parent_profile_data:
                parent_profile_data = parent_profile_data[0]
                parent_profile_id = parent_profile_data["id"]

                # update child SYNC VERSION
                parent_sync_version = parent_profile_data["fpos_sync_version"] or 1
                if parent_sync_version != fpos_sync_version:
                    self.write(cr, uid, profile_id, {
                            "fpos_sync_version": parent_sync_version
                        }, context=context)

                    fpos_sync_version = parent_sync_version

        else:
            child_ids = self.search(cr, uid, [("parent_user_id","=",uid)], context=context)


        jdoc_obj = self.pool["jdoc.jdoc"]
        jdoc_options = {
            "model" : {
                "pos.config" : {
                    "compositions" : ["journal_ids","user_ids","company_id","sequence_id","fpos_1nd_journal_id","fpos_2nd_journal_id"]
                },
                "res.company" : {
                    "fields" : ["name",
                                "currency_id"],
                    "compositions" : ["currency_id"]
                }
            }
        }

        # check sync action
        if action:
            if action == "inc":
                # ONLY increment if MAIN POS
                fpos_sync_count += 1
                sync_data = {
                    "fpos_sync_count" : fpos_sync_count
                }

                # RESET MARK for MAIN POS
                if not parent_profile_id and fpos_sync_clean and fpos_sync_count >= fpos_sync_clean:
                    sync_data["fpos_sync_reset"] = True

                self.write(cr, uid, profile_id, sync_data, context=context)

            elif action == "reset":
                # new sync data
                sync_data = {
                    "fpos_sync_count" : 0,
                    "fpos_sync_reset" : False
                }

                # if MAIN POS increment VERSION
                if not parent_profile_id:
                    fpos_sync_version += 1
                    sync_data["fpos_sync_version"] = fpos_sync_version

                    # set RESET FLAG for all child POS
                    self.write(cr, uid, child_ids, {
                            "fpos_sync_version" : fpos_sync_version,
                            "fpos_sync_reset" : True
                    }, context=context)

                # write sync data
                self.write(cr, uid, profile_id, sync_data, context=context)
                
            elif action == "check":
               
                # check orders   
                fpos_order_obj = self.pool["fpos.order"]
                check_version = max(fpos_sync_version-1,0)
                
                fpos_order_vals = fpos_order_obj.search_read(cr, uid, [("fpos_user_id","=",uid),("sv",">=",check_version),("seq",">",0)], ["seq"], order="seq asc", context={"active_test":False})
                check_seq = 0
                
                for order_val in fpos_order_vals:
                    if not check_seq:
                        check_seq = order_val["seq"]
                    else:
                        check_seq += 1
                        if check_seq != order_val["seq"]:
                            raise Warning(_("Invalid Sequence %s/%s") % (uid,check_seq))
           


        # query config
        res = jdoc_obj.jdoc_by_id(cr, uid, "pos.config", profile_id, options=jdoc_options, context=context)
        res["dbid"]  = profile_id

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
            raise Warning(_('There is no company for user %s') % uid)

        # get company info
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
                value["sign_key"] = base64.b64encode(Random.new().read(AES_KEY_SIZE))

        res = {"value": value}
        return res

    def copy(self, cr, uid, oid, default, context=None):

        def incField(model_obj, oid, field, default):
            val = default.get(field)
            if not val and model_obj:
                val = model_obj.read(cr, uid, oid, [field], context=context)[field]
            if val:
                m = re.match("([^0-9]*)([0-9]+)(.*)", val)
                if m:
                    default[field]="%s%s%s" % (m.group(1), int(m.group(2))+1, m.group(3))

        incField(self, oid, "name", default)
        incField(self, oid, "fpos_prefix", default)
        incField(self, oid, "sign_pid", default)

        fpos_prefix =  default.get("fpos_prefix")
        if fpos_prefix:
            user_ref = self.read(cr, uid, oid, ["user_id"], context=context)["user_id"]
            if user_ref:
                userObj = self.pool["res.users"]
                userFields = ["name","email","login"]
                userDefaults = {}
                for userField in userFields:
                    incField(userObj, user_ref[0], userField, userDefaults)
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

    def _dep_export(self, cr, uid, profile, order_id=None, context=None):
        forder_obj = self.pool["fpos.order"]

        if context is None:
            export_context = {}
        else:
            export_context = dict(context)

        export_context["active_test"] = False

        receipts = []
        data = {
            "Signaturzertifikat" : "",
            "Zertifizierungsstellen" : [],
            "Belege-kompakt" : receipts
        }

        fpos_user = profile.user_id
        if fpos_user:
            # search start seq
            startSeq = 0
            
            # search form specific order
            fpos_order_id = None
            if order_id:
              fpos_order_id = self.pool["pos.order"].read(cr, uid, order_id, ["fpos_order_id"], context=context)
              if fpos_order_id:
                fpos_order_id =  fpos_order_id["fpos_order_id"][0]
                startSeq = forder_obj.read(cr, uid, fpos_order_id, ["seq"], context=context)["seq"]
            
            # search from start
            if not startSeq:
              orderEntries = forder_obj.search_read(cr, uid,  [("fpos_user_id","=", fpos_user.id),("st","=","s")], ["seq"], order="seq asc", limit=1, context=export_context)
              if orderEntries:
                startSeq = orderEntries[0]["seq"]
          
            # if start seq found, export
            if startSeq:
                # export other
                orderEntries = forder_obj.search_read(cr, uid, [("fpos_user_id", "=", fpos_user.id),("seq", ">=", startSeq)], ["dep"], order="seq asc", context=export_context)
                for entry in orderEntries:
                    receipts.append(entry["dep"])

        return {
             "Belege-Gruppe" : [data]
        }

    def action_dep_download(self, cr, uid, ids, context=None):
        for profile in self.browse(cr, uid, ids, context=context):

            if not profile.sign_status or profile.sign_status == "draft":
                raise Warning(_("No signation activated for %s") % profile.name)

            url = "/fpos/dep/%s" % profile.id
            return {
               'name': _('DEP Export %s') % profile.sign_pid,
               'type': 'ir.actions.act_url',
               'url': url,
               'target': 'self'
            }



class pos_order(osv.Model):

    _inherit = "pos.order"
    _columns = {
        "fpos_order_id": fields.many2one("fpos.order", "Fpos Order", select=True),
        "fpos_place_id": fields.many2one("fpos.place", "Place", select=True),
        "fpos_group_id": fields.many2one("fpos.order", "Grouped Order", select=True, ondelete="set null"),
        "fpos_ga": fields.related("fpos_order_id", "ga", type="boolean", readonly=True, string="Groupable"),        
        "fpos_amount_total": fields.related("fpos_order_id", "amount_total", readonly=True, type="float", digits_compute=dp.get_precision("Account"), string="Amount", active_test=False),
        "config_id": fields.related("session_id", "config_id", type="many2one", obj="pos.config", readonly=True, string="Point of Sale"),
        "fpos_st": fields.related("fpos_order_id", "st", type="selection", readonly=True, string="Type", 
                                  selection=[("s","Start"),
                                   ("0","Null"),
                                   ("c","Cancel"),
                                   ("m","Mixed"),
                                   ("t","Training")])
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
        
    def action_dep_export(self, cr, uid, ids, context=None):
      for order in self.browse(cr, uid, ids, context=context):
        url = "/fpos/dep/%s/%s" % (order.config_id.id, order.id)
        return {
             'name': _('DEP Export %s') % order.config_id.sign_pid,
             'type': 'ir.actions.act_url',
             'url': url,
             'target': 'self'
        }
      return True

    def action_invoice(self, cr, uid, ids, context=None):
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        inv_ids = []

        data_obj = self.pool["ir.model.data"]
        prod_balance_id = data_obj.xmlid_to_res_id(cr, uid, "fpos.product_fpos_balance", raise_if_not_found=True)

        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise osv.except_osv(_('Error!'), _('Please provide a partner for the sale.'))

            acc = order.partner_id.property_account_receivable.id
            
            order_name = [order.name]
            if order.pos_reference:
                order_name.append(order.pos_reference)
                
            inv = {
                'name': ' / '.join(order_name),
                'origin': order.name,
                'account_id': acc,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
                'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
                'perf_enabled': False
            }
            inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
            # FORWARDPORT TO SAAS-6 ONLY!
            inv.update({'fiscal_position': False})
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, uid, inv, context=context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=context)
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                }

                inv_name = line.name
                inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                               line.product_id.id,
                                                               line.product_id.uom_id.id,
                                                               line.qty, partner_id = order.partner_id.id)['value'])
                if not inv_line.get('account_analytic_id', False):
                    inv_line['account_analytic_id'] = \
                        self._prepare_analytic_account(cr, uid, line,
                                                       context=context)
                inv_line['price_unit'] = line.price_unit
                inv_line['discount'] = line.discount
                inv_line['name'] = inv_name

                # take taxes from fpos line
                # if available
                tax_ids = inv_line['invoice_line_tax_id']

                # add pos line specific
                fpos_line = line.fpos_line_id
                if fpos_line:
                    tax_ids = [o.id for o in fpos_line.tax_ids]
                    inv_line["uos_id"] = fpos_line.uom_id.id
                    if inv_line.get("product_id") == prod_balance_id:
                        inv_line["product_id"] = None

                inv_line['invoice_line_tax_id'] = [(6, 0, tax_ids)]
                inv_line_ref.create(cr, uid, inv_line, context=context)

            inv_ref.button_reset_taxes(cr, uid, [inv_id], context=context)
            self.signal_workflow(cr, uid, [order.id], 'invoice')
            inv_ref.signal_workflow(cr, uid, [inv_id], 'validate')

        if not inv_ids: return {}

        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False
        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }


class pos_order_line(osv.Model):

    @api.cr_uid_context
    def _get_taxes(self, cr, uid, line, context=None):
        fpos_line = line.fpos_line_id
        if fpos_line:
            return fpos_line.tax_ids
        return super(pos_order_line, self)._get_taxes(cr, uid, line, context=context)

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

