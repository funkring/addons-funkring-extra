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
from openerp.addons.at_base import util

class funet_connect_wizard(models.TransientModel):
    _name = "funet.connect.wizard"
    _description = "Connection Wizard"

    node_id = fields.Many2one("funet.node","Node", required=True)
    device_id = fields.Many2one("funet.dev", "Device")
    dst_node_id = fields.Many2one("funet.node", "Destination Node", required=True)
    dst_device_id = fields.Many2one("funet.dev", "Destination Device")

    @api.model
    def default_get(self, fields_list):
        res =  models.TransientModel.default_get(self, fields_list)
        if res is None:
            res = {}

        # get active device
        active_dev_id = util.active_id(self._context, "funet.dev")
        if active_dev_id:
            dev_obj = self.env["funet.dev"]
            active_dev = dev_obj.browse(active_dev_id)
            if "node_id" in fields_list:
                res["node_id"] = active_dev.node_id.id
            if "device_id" in fields_list:
                res["device_id"] = active_dev.id

        return res