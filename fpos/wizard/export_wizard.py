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
from collections import OrderedDict

class wizard_export_bmd(models.TransientModel):
    _name = "fpos.wizard.export.bmd"
    _description = "BMD Export Wizard"
    
    journal_ids = fields.Many2many("account.journal", "fpos_export_bmd_journal_rel", "wizard_id", "journal_id", "Journals")
    order_ids = fields.Many2many("pos.order", "fpos_export_bmd_order_rel", "wizard_id", "order_id", "Order")
    
    @api.multi
    def action_export(self):
        for wizard in self:
            wizard_type = self._name.split(".")[-1]
            url = "/fpos/export?wizard_type=%s&wizard_id=%s" % (wizard_type, wizard.id)
            return {
               'name': _('Download'),
               'type': 'ir.actions.act_url',
               'url': url,
               'target': 'self'
            }
        return True

    def _export(self, orders):
        res = []
        
        for order in orders:      
            # bookings
            
            # payment
            # filter journal
            pass
        
        res = "\r\n".join(res)
        charset = "cp1252"
        res = res.encode(charset)
        return ("buerf","text/plain; charset=%s" % charset, res)

    @api.multi
    def export(self):
        order_obj = self.env["pos.order"]
        for wizard in self:
            orders = order_obj.search([("id","in",[o.id for o in wizard.order_ids])], order="date_order asc")
            return wizard._export(orders)
        
        raise Warning(_("No data to export"))
