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
    "name" : "WooCommerce Connector",
    "summary" : "Connects Odoo with WooCommerce",
    "description":"""
WooCommerce Connector
=====================

* Sync Categories
* Sync Products and availability
* Sync Orders
* Webhook for Realtime Updates

    """,
    "version" : "1.0",
    "author" :  "oerp.at",
    "website" : "http://oerp.at",
    "category" : "Sale",
    "depends" : ["at_base", 
                 "at_sale",
                 "at_stock",
                 "at_firstname",
                 "web",
                 "portal_download_product"],
    "data" : ["security.xml",
              "data/cron_wc_sync.xml",
              "view/profile_view.xml",
              "view/product_view.xml",
              "view/sale_view.xml"],
    "auto_install" : False,
    "installable": True
}