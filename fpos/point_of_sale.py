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

class pos_category(osv.osv):
    _inherit = "pos.category"
    _columns =  {
        "pos_color" : fields.selection(COLOR_NAMES, string="Color"),
        "pos_unavail" : fields.boolean("Unavailable")
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
            "pos_unavail" : obj.pos_unavail
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
        "iface_nogroup" : fields.boolean("No Grouping", help="If a product is selected twice a new pos line was created"),
        "iface_place" : fields.boolean("Place Management"),
        "iface_fastuswitch" : fields.boolean("Fast User Switch"),
        "iface_ponline" : fields.boolean("Search Partner Online"),
        "fpos_printer_ids" : fields.many2many("fpos.printer", "fpos_config_printer_rel", "config_id", "printer_id", "Printer", copy=True, composition=True),
        "fpos_dist_ids" : fields.many2many("fpos.dist","fpos_config_dist_rel","config_id","dist_id","Distributor", copy=True, composition=True),
        "fpos_income_id" : fields.many2one("product.product","Cashstate Income", domain=[("income_pdt","=",True)], help="Income product for auto income on cashstate"),
        "fpos_expense_id" : fields.many2one("product.product","Cashstate Expense", domain=[("expense_pdt","=",True)], help="Expense product for auto expense on cashstate"),
        "iface_trigger" : fields.boolean("Cashbox Trigger", help="External cashbox trigger"),
        "liveop" : fields.boolean("Live Operation", readonly=True, select=True, copy=False),
        "fpos_dist" : fields.char("Distributor", copy=True),
        "user_id" : fields.many2one("res.users","Sync User", select=True, copy=False),
        "user_ids" : fields.many2many("res.users",
                                      "pos_config_user_rel",
                                      "config_id", "user_id",
                                      "Users",
                                      help="Allowed users for the Point of Sale")
    }
    _sql_constraints = [
        ("user_uniq", "unique (user_id)","Fpos User could only assinged once")
    ]

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
                fpos_order_obj._post(cr, uid, order_ids, context=context)
        return True

    def run_scheduler(self, cr, uid, context=None): # run post in scheduler
        return self.action_post_all(cr, uid, context=context)

    def action_post_all(self, cr, uid, context=None):
        config_ids = self.search(cr, uid, [("liveop","=",True),("user_id","!=",False)])
        return self.action_post(cr, uid, config_ids, context=context)

    def get_profile(self, cr, uid, context=None):
        """
        @return: Fpos Profile
        """
        profile_id = self.search_id(cr, uid, [("user_id","=", uid)], context=context)
        if not profile_id:
            return False

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

        # query config
        res = jdoc_obj.jdoc_by_id(cr, uid, "pos.config", profile_id, options=jdoc_options, context=context)

        # get counting values
        fpos_order_obj = self.pool.get("fpos.order")
        last_order_values = fpos_order_obj.search_read(cr, uid,
                                    [("fpos_user_id","=",uid),("state","!=","draft")],
                                    ["seq", "turnover", "cpos", "date"],
                                    order="seq desc", limit=1, context={"active_test" : False})

        if last_order_values:
            last_order_values = last_order_values[0]
            res["last_seq"] = last_order_values["seq"]
            res["last_turnover"] = last_order_values["turnover"]
            res["last_cpos"] = last_order_values["cpos"]
            res["last_date"] = last_order_values["date"]
        else:
            profile = self.browse(cr, uid, profile_id, context=context)
            res["last_seq"] = -1.0 + profile.sequence_id.number_next
            res["last_turnover"] = 0.0
            res["last_cpos"] = 0.0
            res["last_date"] = util.currentDateTime()

        # add company
        user_obj = self.pool["res.users"]
        company_id = user_obj._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))

        # finished
        return res


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
            for st_line in order.statement_ids:
                data_lines += [x.id for x in st_line.journal_entry_id.line_id if x.account_id.id == invoice.account_id.id]
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



