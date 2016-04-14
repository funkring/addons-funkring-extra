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
    "name" : "oerp.at Fpos",
    "summary" : "Extensions for Fpos Software",
    "description":"""
oerp.at Fpos
============

* A module which adds additional features to the original point of sale
  for the Fpos software

    """,
    "version" : "1.2",
    "api" : [8],
    "author" :  "funkring.net",
    "category" : "Point of Sale",
    "depends" : ["at_product",
                 "at_account",
                 "jdoc",
                 "point_of_sale",
                 "at_sale"
                ],
    "data" : ["security.xml",
              "menu.xml",
              "report/invoice_report.xml",
              "view/pos_config_view.xml",
              "view/user_view.xml",
              "view/fpos_order_view.xml",
              "view/product_view.xml",
              "view/pos_order_view.xml",
              "report/session_summary_report.xml",
              "report/session_detail_report.xml",
              "data/cron_fpos_post.xml",
              "data/product_fpos_status.xml"
             ],
    "auto_install" : False,
    "installable": True
}