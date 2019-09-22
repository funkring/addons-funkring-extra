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
    "version" : "1.3",
    "api" : [8],
    "author" :  "funkring.net",
    "category" : "Point of Sale",
    "depends" : ["at_product",
                 "at_account",
                 "jdoc",
                 "point_of_sale",
                 "at_sale",
                 "automation"
                ],
    "data" : ["security.xml",
              "menu.xml",              
              "view/pos_config_view.xml",
              "view/user_view.xml",
              "view/fpos_order_view.xml",
              "view/product_view.xml",
              "view/pos_order_view.xml",
              "view/product_view_simple.xml",
              "view/pos_top.xml",
              "view/pos_place.xml",     
              "view/pos_category.xml",
              "view/fpos_dist_view.xml",
              "view/fpos_printer_view.xml", 
              "view/fpos_report_email_view.xml",
              "view/fpos_hwproxy_view.xml",
              "view/journal_view.xml",
              "view/account_tax_view.xml",              
              "view/partner_view.xml",
              "view/invoice_view.xml",
              "view/fpos_order_report_view.xml",
              "view/fpos_profile.xml",
              "view/fpos_post_task.xml",
              "wizard/product_list_wizard.xml",            
              "wizard/export_wizard.xml",
              "wizard/export_wizard_rzl.xml",
              "wizard/report_wizard.xml",
              "wizard/product_opt_wizard.xml",
              "wizard/product_ean_wizard.xml",
              "report/account_invoice_report.xml",
              "report/pos_invoice_report.xml",
              "report/session_summary_report.xml",              
              "report/report_receipt.xml",
              "report/pos_config_report.xml",
              "report/pos_order_delivery.xml",
              "report/payment_overview_report.xml",
              "report/product_list.xml",
              "report/pos_sale_report_view.xml",
              "data/cron_fpos_post.xml",
              "data/cron_fpos_product.xml",
              "data/product_fpos_status.xml",
              "data/report_email_template.xml",
              "data/internal_product_seq.xml"
             ],
    "auto_install" : False,
    "installable": True
}