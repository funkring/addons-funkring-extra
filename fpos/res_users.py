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

class res_users(osv.Model):
    _inherit = "res.users"
    _columns = {
        "pin" : fields.char("PIN", help="User PIN for fast authentication on Fpos hardware", copy=False),
        "pos_role" : fields.selection([("user","User"),
                                       ("manager","Manager"),
                                       ("admin","Administrator")], "POS Role"),
        
        "fpos_disable_price": fields.boolean("Disable Price"),
        "fpos_disable_cancel": fields.boolean("Disable Cancellation"),
        "fpos_disable_payment": fields.boolean("Disable Payment Methods"),
        
        "code" : fields.char("Code"),
        "child_config_ids" : fields.one2many("pos.config", "parent_user_id", "POS Childs")
    }
    _sql_constraints = [
        ("pin_uniq", "unique (pin)","PIN have to be unique for User")
    ]