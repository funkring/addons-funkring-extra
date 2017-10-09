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

class account_journal(osv.Model):
    _inherit = "account.journal"
    _columns = {
        "fpos_noreconcile": fields.boolean("No invoice reconciliation"),
        "fpos_noturnover": fields.boolean("No Turnover"),
        "fpos_invoice" : fields.boolean("Create Invoice"),
        "fpos_invoice_email": fields.boolean("E-Mail Invoice"),
        "fpos_atomic": fields.boolean("Atomic Payment"),
        "fpos_group": fields.boolean("Group Order"),
        "fpos_partner_id": fields.many2one("res.partner", "Default Partner", domain=[("available_in_pos","=",True)]) 
    }