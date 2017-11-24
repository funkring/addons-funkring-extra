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

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID

import hmac
import hashlib
import base64

import logging
_logger = logging.getLogger(__name__)

class woocommerce(http.Controller):
 
    @http.route(["/http/wc/<int:profile_id>"], type="http", auth="none", methods=["GET","POST"])
    def webhook(self, profile_id=None, **kwargs):
      cr, uid, context = request.cr, request.uid, request.context
      profile_obj = request.registry["wc.profile"]
      profile = profile_obj.browse(cr, SUPERUSER_ID, profile_id, context=context)
      content = str(request.httprequest.stream.read())
      signature = request.httprequest.headers.get("X-Wc-Webhook-Signature")
      if signature:
        signature = str(signature)
        secret = str(profile.webhook_secret)
        digister = hmac.new(secret, content, hashlib.sha256)
        signature_calc = base64.encodestring(digister.digest()).strip()        
        if signature_calc == signature:
          try:
            profile_obj.schedule_sync(cr, SUPERUSER_ID, context=context)
            cr.commit()
          except:
            _logger.warning("Queue is currently used, unable to update")
          finally:
            cr.rollback()
            
      return "OK"
    
    
