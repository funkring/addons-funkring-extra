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
    "name" : "oerp.at Fclipboard",
    "description":"""
Fclipboard
==========

Dynamic data support for mobile data recording 
 
""",

    "version" : "1.0",
    "author" :  "funkring.net",
    "category" : "Sales",
    "depends" : ["at_sale","jdoc"],
    "data" : ["view/fclipboard_view.xml",
              "security.xml"],
    "auto_install" : False,
    "installable": True
}