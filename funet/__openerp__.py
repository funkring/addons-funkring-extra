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

{
    "name" : "FUNET Network Management",
    "summary" : "Framework for managing huge networks",
    "description":"""
FUNET Network Management
========================
* Database for network, nodes and devices
* Device Konfiguration
* Device/Node Monitoring

""",
    "version" : "1.0",
    "author" :  "oerp.at",
    "website" : "http://oerp.at",
    "category" : "Network",
    "depends" : ["at_base","mail","password_management"],
    "data" : ["security.xml",
              "menu.xml",
              "view/node_view.xml",
              "view/dev_view.xml",
              "view/dev_type_view.xml",
              "view/dev_fw_view.xml",
              "view/dev_driver_view.xml",
              "view/provider_view.xml",
              "view/vpn_view.xml",
              "view/network_view.xml",
              "view/port_type_view.xml",
              "wizard/connect_wizard.xml"],
    "auto_install" : False,
    "installable": True
}