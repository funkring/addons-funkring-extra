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

from openerp import models, fields, api
from openerp.addons.at_base import util
import re
import urllib
import requests

REGEX_THENEWSLETTER_PROFILE_NAME = re.compile(r"^[a-z0-9_.\\-]+$")

import logging
_logger = logging.getLogger(__name__)

class TheNewsLetterProfile(models.Model):
  _name = "thenewsletter.profile"
  _description = "thenewsletter Profile"
  
  @api.multi
  def _check_name(self):
    for profile in self:
      if not profile.name or not REGEX_THENEWSLETTER_PROFILE_NAME.match(profile.name):
        return False
    return True
  
  _constraints =  [ 
    (_check_name,"Profile name have to be lower case without spaces and special chars",["name"])  
  ]
  
  name = fields.Char("Name", required=True, states={'draft': [('readonly', False)]})
  url = fields.Char("Url", required=True, states={'draft': [('readonly', False)]})
  api_key = fields.Char("API Key", required=True, states={'draft': [('readonly', False)]})    
  
  last_sync = fields.Datetime("Last Sync", states={'draft': [('readonly', False)]})
  
  state = fields.Selection([("draft","Draft"),
                            ("active","Active")],
                           string="Status", required=True, default="draft")
  
  @api.model
  def _get_partner_domain(self, domain=None):
    res = domain and list(domain) or []
    res.append(("email","!=",False))
    res.append(("customer","=",True))
    return res
  
  @api.one
  def action_sync(self):
    domain = self.last_sync and [("create_date",">",self.last_sync)] or []
    partner_domain = self._get_partner_domain(domain)
          
    last_sync = self.last_sync
    for values in self.env["res.partner"].search_read(partner_domain, 
                                                      ["surname","firstname","email", "create_date"], 
                                                      order="create_date asc"):
      email = values["email"]
      if not email:
        continue
      
      data = {
        "ne": email,
        "nn": values["surname"],
        "ns": values["firstname"]
      }
    
      url = urllib.basejoin(self.url, "wp-content/plugins/newsletter-api/add.php?nk=%s" % self.api_key)
      res = requests.post(url, data=data)
      if res.ok:
        _logger.info("Registered newsletter for %s" % email)
        last_sync = max(last_sync, values["create_date"])
      else:
        _logger.error("Unable to register newsletter for %s" % email)
        _logger.error(res.text)
        
    self.last_sync = last_sync

  @api.one
  def action_activate(self):
    if self.state == "draft":
      self.state = "active"
      
  @api.one
  def action_draft(self):
    if self.state == "active":
      self.state = "draft"
  
  @api.multi
  def action_schedule_sync(self):
    self.schedule_sync()
    return True
  
  @api.model
  def sync(self):
    self.search([("state","=","active")]).action_sync()
    return True

  @api.model
  def schedule_sync(self):
    cron = self.env.ref("thenewsletter.cron_thenewsletter_sync", False)
    if cron:
      cron.nextcall = util.nextMinute()
    return True
