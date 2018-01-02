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
    "name" : "thenewsletter Connector",
    "summary" : "A connector to wordpress thenewsletter plugin",
    "description":"""
Newsletter Connector
====================
* Connect odoo with thenewsletter wordpress plugin
""",
    "version" : "1.0",
    "author" :  "oerp.at",
    "website" : "http://oerp.at",
    "category" : "Sale",
    "depends" : ["at_base", 
                 "at_firstname",
                 "at_sale",
                 "web"],
    "data" : ["security.xml",
              "data/cron_newsletter_sync.xml",
              "view/thenewsletter_view.xml"],
    "auto_install" : False,
    "installable": True
}