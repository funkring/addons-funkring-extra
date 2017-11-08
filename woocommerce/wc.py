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

from openerp import models, fields, api, _
from openerp.addons.at_base import util
from openerp.exceptions import Warning

import re
from datetime import datetime
import dateutil.parser
import woocommerce.api
import urllib

import logging
_logger = logging.getLogger(__name__)

regex_wc_name = re.compile(r"^[a-z0-9_.\\-]+$")


class WcMapper(object):
  """ Mapper Object """
  
  def __init__(self, profile):
    self.profile = profile
    self.name = "wc.%s" % profile.name
    self.mapper_obj = self.profile.env["res.mapping"]
    
    self.wc2oid = {}
    self.oid2wc = {}

    self.loaded = False
   
    
  def _load(self):
    if not self.loaded:
      self.loaded = True
      # load mapping    
      for values in self.mapper_obj.search_read([("name","=",self.name)], ["res_model",
                                                             "res_id",
                                                             "uuid"]):
        wcid = long(values["uuid"])
        self.wc2oid[(values["res_model"],wcid)] = values["res_id"]
        self.oid2wc[(values["res_model"],values["res_id"])] = wcid
    
  def getWcId(self, model, oid):
    self._load()
    return self.oid2wc.get((model, oid))
  
  def getOid(self, model, wcid):
    self._load()
    return self.wc2oid.get((model, wcid))
  
  def loadWcId(self, model, oid):
    res = self.mapper_obj.with_context(active_test=False).search_read([("name","=",self.name), 
                  ("res_model","=", model),
                  ("res_id","=", oid)],
                  ["uuid"])
    wcid = None
    if res:
      wcid = long(res[0]["uuid"])
      self.wc2oid[(model, wcid)] = oid
      self.oid2wc[(model, oid)] = wcid
      
    return wcid
  
  def addWcId(self, model, oid, wcid):
    has_mapping = self.mapper_obj.with_context(active_test=False).search([("name","=",self.name), 
                            ("res_model","=", model),
                            ("res_id","=", oid)], count=True)
    
    if has_mapping:
      raise Warning(_("Mapping already exist"))
    
    self.mapper_obj.create({
      "name": self.name, 
      "res_model": model,
      "res_id": oid,
      "uuid": str(wcid)
    })
    self.wc2oid[(model, wcid)] = oid
    self.oid2wc[(model, oid)] = wcid
    
  def getDeletedWcIds(self, model, ts):
    self.mapper_obj.check_deleted(model)
    wcids = []
    if ts:
      ts = util.getNextSecond(ts)
      for values in self.mapper_obj.with_context(active_test=False).search_read([("name","=",self.name),("write_date",">=", ts),("active","=",False)], ["uuid","write_date"]):      
        wcids.append((long(values["uuid"]), values["write_date"]))
    return wcids
  

class WcClient(object):
  """ Client Wrapper """
  
  def __init__(self, wc):
    self.wc = wc
    
  def parse(self, res):
    if res.ok:
      return res.json()
    else:
      errors = res.json().get("errors")
      if errors:
        for error in errors:
          raise Warning("[%s] %s" % (error["code"], error["message"]))
      raise Warning(res.text)
    
  def get(self, resource):
    return self.parse(self.wc.get(resource))
    
  def post(self, resource, params):
    return self.parse(self.wc.post(resource, params))
    
  def delete(self, resource):
    return self.parse(self.wc.delete(resource))


class WcSync(object):
  """ Synchronisation Base Class """

  def __init__(self, mapper, wc, prefix, model, endpoint, direction="up", domain=None, 
               dependency=None):
    self.wc = wc
    self.mapper = mapper
    self.profile = self.mapper.profile
    self.prefix = prefix
    self.model = self.profile.env[model]
    self.model_name = model
    self.endpoint = endpoint
    self.field_odoo_timestamp = self.prefix + "_date"
    self.field_wc_timestamp = self.prefix + "_date_wc"
    self.field_odoo_del_timestamp = self.prefix + "_date_del"
    self.field_template = self.prefix + "_template_id"
    self.direction = direction
    self.domain = domain
    self.dependency = dependency
  
  def fromOdoo(self, obj, wid=None):
    return {}
  
  def toOdoo(self, doc, obj=None):
    return {}
  
  def toWcGMT(self, ts):
    ts = util.strToTime(ts)
    return datetime.strftime(ts, "%Y-%m-%dT%H:%M:%SZ")
  
  def fromWcGMT(self, ts):
    ts = dateutil.parser.parse(ts)
    # parse ISO 8601
    return util.timeToStr(ts)
  
  def getEndpoint(self, params):
    endpoint = self.endpoint
    if params:
      endpoint = "%s?%s" % (endpoint, "&".join(params))
    return endpoint
  
  def findDoc(self, obj):   
    return None
  
  def afterUpdate(self, obj, wid):
    pass
  
  def sync(self):
    
    processed_oid = set()
    processed_wid = set()
    changes = True
    
    while changes:
      changes = False
      
      # Get Odoo Changes
      dep_ids = set()
      
      # query dependency changes
      if self.dependency:
        for dep_prefix, dep_model, dep_field, dep_domain in self.dependency:
          dep_date_field = "%s_date" % dep_prefix
          dep_timestamp = getattr(self.profile, dep_date_field)
          dep_model_obj = self.profile.env[dep_model]
          domain = []
          if dep_timestamp:
            domain.append(("write_date",">=",util.getNextSecond(dep_timestamp)))
          if dep_domain:
            domain.extend(dep_domain)            
          
          # search objects
          dep_objs = dep_model_obj.search(domain)
          for dep_obj in dep_objs:
            dep_timestamp = max(dep_timestamp, dep_obj.write_date)
            dep_field_value = getattr(dep_obj, dep_field)
            if dep_field_value:
              for dep_field_obj in dep_field_value:
                dep_ids.add(dep_field_obj.id)
            
          # update dependency time stamp
          setattr(self.profile, dep_date_field, dep_timestamp)
            
      
      # query odoo changes
      odoo_timestamp = getattr(self.profile, self.field_odoo_timestamp)
      domain = []
      if odoo_timestamp:
        domain.append(("write_date",">=",util.getNextSecond(odoo_timestamp)))
      if self.domain:
        domain.extend(self.domain)
            
      # insert dependend ids
      if dep_ids:
        dep_ids = list(dep_ids)
        if domain:
          domain.insert(0, (1,"=",1))
          domain.insert(0, "&")
          domain.insert(0, ("id","in",dep_ids))
          domain.insert(0, "|")
        else:
          domain.append(("id","in",dep_ids))
      
      # search changed odoo objects
      objs = self.model.search(domain)
      
      ## Get WooCommerce Changes
      wc_timestamp = None
      if self.direction == "both":    
        # CREATED   
        # query wc creates
        wc_timestamp = getattr(self.profile, self.field_wc_timestamp)
        params = []
        if wc_timestamp:
          wc_ts_param = self.toWcGMT(util.getNextSecond(wc_timestamp))
          params.append("filter[updated_at_min]=%s" % wc_ts_param)
          params.append("filter[created_at_min]=%s" % wc_ts_param)
          params.append("filter[limit]=100000")
          params.append("filter[orderby]=last_update")
          params.append("filter[order]=asc")
        
        # get endpoint
        endpoint = self.getEndpoint(params)
        
        # add created docs
        docs = self.wc.get(endpoint)[self.endpoint]
  
      else:
        docs = []
        
        
      ## Process Odoo Changes
  
      updates = []
      updates_wids = set()
        
      # query mapping
      for obj in objs:          
        # update timestamp
        odoo_timestamp = max(obj.write_date, odoo_timestamp)
        
        # check if already processed
        proc_key = (obj.id, obj.write_date)
        if proc_key in processed_oid:
          continue
        processed_oid.add(proc_key)
   
        # convert/update/create
        wid = self.mapper.getWcId(self.model_name, obj.id)
        if not wid:          
          doc = self.findDoc(obj)
          if doc:
            wid = doc["id"]
            self.mapper.addWcId(self.model_name, obj.id, wid)
                      
        doc = self.fromOdoo(obj, wid)   
        if doc:
          if wid:
            doc["id"] = wid
            updates_wids.add(wid)
  
          # check no or to create
          if wid:
            updates.append(doc)
          else:                  
            # create new document
            wid = self.mapper.loadWcId(self.model_name, obj.id)            
            if wid:
              updates.append(doc)
            else:
              _logger.info("Create in WooCommerce: %s [oid=%s]" % (obj.name, obj.id))
              
              res_doc = self.wc.post("%s/bulk" % self.endpoint, {self.endpoint:[doc]})[self.endpoint][0]
              res_error = res_doc.get("error")
              if res_error:
                _logger.error("Import in WooCommerce FAILED: %s [oid=%s], %s" % (obj.name, obj.id, res_error))
              else:
                wid = res_doc["id"]
                updated_at = self.fromWcGMT(res_doc["last_update"])
                
                self.mapper.addWcId(self.model_name, obj.id, wid)              
                
                # add processed 
                processed_wid.add((wid, updated_at))
                changes = True
  
            
      ## Process WooCommerce Changes
      
      if docs:
        for doc in docs:
          # update wc_timestamp
          updated_at = self.fromWcGMT(doc["last_update"])
          wc_timestamp = max(updated_at, wc_timestamp)
          wid = doc["id"]
        
          # check if already processed
          proc_key = (wid, wc_timestamp)
          if proc_key in processed_wid:
            continue
          processed_wid.add(proc_key)
        
          # check if also handled by server (conflict)
          if wid in updates_wids:
            continue
          
          oid = self.mapper.getOid(self.model_name, wid)
          obj = oid and self.model.browse(oid) or None
          
          values = self.toOdoo(doc, obj)
          changes = True
          
          if obj:
            obj.write(values)
            _logger.info("Update in Odoo: [wid=%s,model=%s]" % (wid, self.model_name))
          else:
            _logger.info("Create in Odoo: [wid=%s,model=%s]" % (wid, self.model_name))
            template = getattr(self.profile, self.field_template)
            obj = template.copy(values)
            self.mapper.addWcId(self.model_name, obj.id, wid)            
            
          # add processe doid
          processed_oid.add((oid, obj.write_date))
  
        
      ## Post WooCommerce Changes
        
      if updates:
        _logger.info("Bulk Update in WooCommerce [model=%s]" % self.model_name)
        res = self.wc.post("%s/bulk" % self.endpoint, {self.endpoint:updates})          
        changes = True
        
        docs = res[self.endpoint]
        for doc in docs:
          processed_wid.add((doc["id"], self.fromWcGMT(doc["last_update"])))
        
        
        
      # Handle Deleted
      odoo_del_timestamp = getattr(self.profile, self.field_odoo_del_timestamp)
      deleted_wcids = self.mapper.getDeletedWcIds(self.model_name, odoo_del_timestamp)      
      for deleted in deleted_wcids:
        # update timestamp
        odoo_del_timestamp = max(odoo_del_timestamp, deleted[1])
        # check already processed        
        if deleted in processed_wid:
          continue
        processed_wid.add(deleted)
        # delete
        _logger.info("Delete in WooCommerce [model=%s,wid=%s]" % (self.model_name, deleted[0]))
        self.wc.delete("%s/%s" % (self.endpoint,deleted[0]))
        changes = True
        
        
      ## Update Timestamps
      setattr(self.profile, self.field_odoo_del_timestamp, odoo_del_timestamp or odoo_timestamp)
      setattr(self.profile, self.field_odoo_timestamp, odoo_timestamp)
      setattr(self.profile, self.field_wc_timestamp, wc_timestamp)
    

class WcProductSync(WcSync):
  """ PRODUCT SYNC """
  def __init__(self, mapper, wc):
    super(WcProductSync, self).__init__(mapper, wc, "product", "product.template", "products", 
                                        direction="up",
                                        domain=[("wc_state","!=",False)])  
    
    
  def fromOdoo(self, obj):
    res = {}
    
    return res
  
class WcUserSync(WcSync):
  """ USER SYNC """
  def __init__(self, mapper, wc):
    super(WcUserSync, self).__init__(mapper, wc, "user", "res.users", "customers", 
                                        direction="both",
                                        domain=[("share","=",True)],
                                        dependency=[
                                          ("partner", "res.partner","user_ids",['|',("user_ids.share","=",True),("user_ids.user_id.share","=",True)])
                                        ])  
    
    
  def fromOdoo(self, obj, wid=None):    
    # get password
    self.profile._cr.execute("SELECT password FROM res_users WHERE id=%s", (obj.id,))
    password = self.profile._cr.fetchone()[0]
    
    # get other
    partner = obj.partner_id
    res = {
      "email": partner.email,
      "first_name": partner.firstname,
      "last_name": partner.surname,
      "username": obj.login,
      "password": password
    }
    
    def getAddressData(partner):
      return {
        "first_name": partner.firstname or "",
        "last_name": partner.surname or "",
        "company":  partner.name,
        "address_1": partner.street or "",
        "address_2": partner.street2 or "",
        "city": partner.city or "",
        "email": partner.email or "",
        "phone": partner.phone or "",
        "country":  partner.country_id.code or "AT"
      }
    
    # get billing address
    res["billing_address"] = getAddressData(partner)
    
    # get delivery address
    for child in partner.child_ids:
      if child.type == "delivery":
        res["shipping_address"] = getAddressData(child)
    
    return res
  
  def findDoc(self, obj):
    try:
      res = self.wc.get("customers/email/%s" % urllib.quote_plus(obj.login))
      return res["customer"]
    except:
      return None
  
  def toOdoo(self, doc, obj=None):
    name = []
      
    firstname = doc["first_name"]
    if firstname:
      name.append(firstname)
      
    surname = doc["last_name"]
    if surname:
      name.append(surname)

    email = doc["email"]
    name = " ".join(name)

    street = None
    street2 = None
    city = None
    phone = None
    country = None
    country_id = None
    
    billing_address = doc.get("billing_address")    
    if billing_address:
      company = doc.get("company")
      if company:
        name = doc.get("company")
      
      street = doc.get("address_1")
      street2 = doc.get("address_2")
      city = doc.get("city")
      phone = doc.get("phone")
      country = doc.get("country")
      if country:
        countries = self.pool["res.country"].search(["code","ilike",country])
        if countries:
          country_id = countries[0].id
      
    values = {
      "email": email,
      "name": name,
      "login": doc["username"]
    }    
    
    if billing_address:
      values["street"] = street
      values["street2"] = street2
      values["city"] = city
      values["phone"] = phone      
      if country_id:
        values["country_id"] = country_id
        
    # NOT SYNC DELIVERY ADDRESS
    # SYNC DELIVERY ADDRESS ON ORDER
    
    if not obj:
      values["active"] = True
      
    return values
  

class wc_profile(models.Model):
  _name = "wc.profile"
  _description = "WooCommerce Profile"

  @api.multi
  def _check_name(self):
    for profile in self:
      if not profile.name or not regex_wc_name.match(profile.name):
        return False
    return True
  
  _constraints =  [ 
    (_check_name,"Profile name have to be lower case without spaces and special chars",["name"])  
  ]
    
  _sql_constraints = [
        ('name', 'unique(name)',
            'The profile name has to be unique'),
    ]
  
    
  name = fields.Char("Name", required=True)
  url = fields.Char("Url", required=True)
  consumer_key = fields.Char("Consumer Key", required=True)
  consumer_secret = fields.Char("Consumer Secret", required=True)
  state = fields.Selection([("draft","Draft"),
                            ("active","Active")],
                           string="Status", required=True, default="draft")
  
  company_id = fields.Many2one("res.company", "Company", required=True, default=lambda self: self.env.user.company_id.id)

  # product sync  
  product_date = fields.Datetime("Product Modification Date")
  product_date_del = fields.Datetime("Product Delete Date")
  product_date_wc = fields.Datetime("WooCommerce Product Modification Date")
  
  # user sync  
  user_date = fields.Datetime("User Modification Date")
  user_date_del = fields.Datetime("User Delete Date")
  user_date_wc = fields.Datetime("WooCommerce User Modification Date")
  user_template_id = fields.Many2one("res.users", "User Template", required=True)
  
  # partner sync  
  partner_date = fields.Datetime("Partner Modification Date")
  
  def _get_client(self):
    return WcClient(woocommerce.api.API(self.url, self.consumer_key, self.consumer_secret))
  
  @api.model
  def _sync_user(self, mapper, wc):
    return WcUserSync(mapper, wc).sync()
  
  @api.one
  def _sync(self):
    # create context
    mapper = WcMapper(self)    
    wc = self._get_client()
    # SYNC
    self._sync_user(mapper, wc)
    return True
    
  @api.multi
  def action_sync(self):
    self._sync()
    return True
  
  @api.multi
  def action_activate(self):
    for profile in self:
      if profile.state == "draft":
        wc = profile._get_client()
        res = wc.get("webhooks")
        profile.state = "active"
        # install webhook
    return True
  
  @api.multi
  def action_draft(self):
    self.state = "draft"
    return True
