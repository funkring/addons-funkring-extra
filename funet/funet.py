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
from openerp.exceptions import ValidationError
import re

class funet_node(models.Model):
    _name = "funet.node"
    _description = "Node"
    _sql_constraints = [('name_unique', 'unique(provider_id, name)','Node with the same name already exist')]

    name = fields.Char("Name", required=True)
    partner_id = fields.Many2one("res.partner", "Partner", required=True)
    provider_id = fields.Many2one("funet.provider", "Provider", required=True)
    device_ids = fields.One2many("funet.dev","node_id", "Devices")
    device_info = fields.One2many("funet.dev","node_id", "Device Infos")
    network_id = fields.Many2one("funet.network","Network")
    tag_ids = fields.Many2many("funet.node.tag", "funet_node_tag_rel", "node_id", "tag_id", "Tags")


    @api.one
    @api.constrains('name')
    def _check_name(self):
        if not re.match("^[a-z-_]*$", self.name):
            raise ValidationError(_("Field name must not contain special chars or whitespaces"))
        
class funet_node_tag(models.Model):
    _name = "funet.node.tag"
    _description = "Node Tag"
    
    name = fields.Char("Name")
    sequence = fields.Integer("Sequence", default=10)


class funet_dev(models.Model):
    _name = "funet.dev"
    _description = "Device"
    _inherit = ["mail.thread"]
    _inherits = {"password.entry" : "password_id"}


    name = fields.Char("Name", compute="_complete_name", store=True, indexed=True, readonly=True)
    code = fields.Char("Code", readonly=True, states={'draft': [('readonly', False)]})
    node_id = fields.Many2one("funet.node", "Node", required=True, readonly=True, states={'draft': [('readonly', False)]}, indexed=True)
    type_id = fields.Many2one("funet.dev.type", "Type", required=True, readonly=True, states={'draft': [('readonly', False)]}, indexed=True)
    coord_lat = fields.Float("Latitude", readonly=True, states={'draft': [('readonly', False)]})
    coord_long = fields.Float("Longitude", readonly=True, states={'draft': [('readonly', False)]})
    coord_dir = fields.Float("Direction", help="0 is North", readonly=True, states={'draft': [('readonly', False)]})
    coord_vert = fields.Float("Grade Vertical", help="0 is no fall", readonly=True, states={'draft': [('readonly', False)]})
    coord_horiz = fields.Float("Grade Horizontal", help= "0 is no fall", readonly=True, states={'draft': [('readonly', False)]})
    info = fields.Text("Info", compute="_build_info", readonly=True)
    last_config = fields.Datetime("Last Configuration", readonly=True)
    network_ids = fields.One2many("funet.dev.network", "device_id", "Networks")
    password_id = fields.Many2one("password.entry","Password", readonly=True, states={"draft" : [("readonly",False)]}, required=True, ondelete="restrict")
    port_ids = fields.One2many("funet.port", "device_id", "Port", readonly=True, states={"draft" : [("readonly",False)]}, required=True, ondelete="restrict")
    

    state = fields.Selection([
        ('draft','Draft'),
        ('valid','Validate'),
        ('active','Active'),
    ], string='State', index=True, readonly=True, default='draft', copy=False)

    @api.one
    @api.depends("password_id.login","password_id.password")
    def _build_info(self):
        infos = []
        password = self.password_id
        if password and (password.login or password.password):
            infos.append(_("Login: %s / %s") % (password.login or "", password.password or ""))
        self.info = "\n".join(infos)

    @api.multi
    def action_validate(self):
        self.state = "valid"

    @api.multi
    def action_activate(self):
        self.state = "active"

    @api.multi
    def action_reset(self):
        self.state = "draft"

    def _check_code(self):
        if not re.match("^[a-z-_]*$", self.code):
            raise ValidationError(_("Field code must not contain special chars or whitespaces"))

    @api.one
    @api.depends("code","node_id","type_id","node_id.name","type_id.code")
    def _complete_name(self):
        name = []
        node_name = self.node_id and self.node_id.name or None
        if node_name:
            name.append(node_name)
        type_code = self.type_id and self.type_id.code or None
        if type_code:
            name.append(type_code)
        if self.code:
            name.append(self.code)
        self.name = "-".join(name)


class funet_dev_type(models.Model):
    _name = "funet.dev.type"
    _description = "Device Type"

    name = fields.Char("Name", required=True)
    driver_id = fields.Many2one("funet.dev.driver", "Driver")
    firmware_id = fields.Many2one("funet.dev.fw", "Firmware")
    code = fields.Char("Code", required=True)

    @api.one
    @api.constrains('code')
    def _check_code(self):
        if not re.match("^[a-z-_]*$", self.code):
            raise ValidationError(_("Field code must not contain special chars or whitespaces"))

class funet_dev_fw(models.Model):
    _name = "funet.dev.fw"
    _description = "Device Firmware"

    name = fields.Char("Name", required=True)
    code = fields.Char("Code")
    url = fields.Char("Firmware")
    init_url = fields.Char("Initiale Firmware")

class funet_dev_driver(models.Model):
    _name = "funet.dev.driver"
    _description = "Device Driver"

    name = fields.Char("Name", required=True)
    code = fields.Char("Code", required=True)

class res_partner(models.Model):
    _inherit = "res.partner"

    coord_lat = fields.Float("Latitude" )
    coord_long = fields.Float("Longitude")

class funet_provider(models.Model):
    _name = "funet.provider"
    _description = "Provider"
    _rec_name = "partner_id"
    _sql_constraints = [('code_unique', 'unique(partner_id, code)','Provider with the same code already exist')]

    partner_id = fields.Many2one("res.partner", "Partner", required=True)
    code = fields.Char("Code", required=True)

class funet_network(models.Model):
    _name = "funet.network"
    _description = "Network"

    name = fields.Char("Name",required=True)
    parent_id = fields.Many2one("funet.network","Network")

    @api.one
    @api.constrains('name')
    def _check_name(self):
        if not re.match("^[a-z-_]*$", self.name):
            raise ValidationError(_("Field name must not contain special chars or whitespaces"))

class funet_dev_network(models.Model):
    _name = "funet.dev.network"
    _description = "Device Network"

    device_id = fields.Many2one("funet.dev", "Device", required=True)
    network_id = fields.Many2one("funet.network", "Network", required=True)
    type = fields.Selection([
        ('local','Local'),
        ('connection','Connection'),
    ], string='Type', default='local', store=True)
    name = fields.Char("Name", compute="_complete_name", store=True, readonly=True)

    @api.one
    @api.depends("device_id","network_id","device_id.name","network_id.name")
    def _complete_name(self):
        name = []
        if self.device_id:
            name.append(self.device_id.name)
        if self.network_id:
            name.append(self.network_id.name)
        self.name = ".".join(name)

class funet_vpn(models.Model):
    _name = "funet.vpn"
    _description = "VPN"

    name = fields.Char("Name")
    network_id = fields.Many2one("funet.network", "Network", required=True)
    
class funet_port(models.Model):
    _name = "funet.port"
    _description = "Port"
    
    name = fields.Char("Name")
    type_id = fields.Many2one("funet.port.type", "Port Type", required=True)
    device_id = fields.Many2one("funet.dev", "Device", required=True)
    code = fields.Char("Code", required=True)
    sequence = fields.Integer("Sequence", default=10)
    port = fields.Integer("Port", default=10)

    @api.one
    @api.constrains('code')
    def _check_code(self):
        if not re.match("^[a-z-_]*$", self.code):
            raise ValidationError(_("Field code must not contain special chars or whitespaces"))
    
class funet_port_type(models.Model):
    _name = "funet.port.type"
    _description = "Port Type"
    
    name = fields.Char("Name")
    