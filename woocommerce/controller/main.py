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

import datetime
import werkzeug

from openerp import tools
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

class woocommerce(http.Controller):

    @http.route(["/wc/webhook"], type="http", auth="none", cors="*")
    def webhook(self, **kwargs):
      return ""
