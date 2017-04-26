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
    "name" : "oerp.at Simple Sale",
    "summary" : "Simple sale module with template for customer",
    "description":"""
Fpos Sale
=========
* adds simple template based sale within point of sale
""",
    "version" : "1.0",
    "author" :  "oerp.at",
    "website" : "http://oerp.at",
    "depends" : ["point_of_sale",
                 "sale",
                 "at_sale",
                 "fpos",
                 "fast_sale"],
    "data" : ["security.xml",
              "view/partner_view.xml",
              "view/sale_view.xml"],
    "auto_install" : False,
    "installable": True
}