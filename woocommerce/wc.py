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
from email.utils import parseaddr

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
  
  def __init__(self, wc, wc_old):
    self.wc = wc
    self.wc_old = wc_old
    
  def parse(self, res, logerror=False):
    if res.ok:
      return res.json()
    else:
      res = res.json()
      errors = res.get("errors")
      if errors:
        for error in errors:
          if logerror:
            _logger.error("[%s] %s" % (error["code"], error["message"]))
            return None
          else:
            raise Warning("[%s] %s" % (error["code"], error["message"]))
      message = res.get("message")
      if message:
        _logger.error(message)
        return None
      raise Warning(res.text)
    
  def get(self, resource):
    return self.parse(self.wc.get(resource))
  
  def get_filtered(self, resource):
    return self.parse(self.wc_old.get(resource))
    
  def post(self, resource, params, logerror=False):
    return self.parse(self.wc.post(resource, params), logerror=logerror)
  
  def put(self, resource, params, logerror=False):
    return self.parse(self.wc.put(resource, params), logerror=logerror)
  
  def put_force(self, resource, params, logerror=False):
    return self.parse(self.wc_old.put(resource, params), logerror=logerror)
    
  def delete(self, resource):
    return self.parse(self.wc.delete(resource))
  
  def delete_force(self, resource):
    return self.parse(self.wc_old.delete(resource))


class WcSync(object):
  """ Synchronisation Base Class """

  def __init__(self, mapper, wc, prefix, model, endpoint, direction="up", domain=None, 
               dependency=None, entry_name=None, entry_set=None, childs=None, name_field="name", oldapi=False, template_field=None):
    
    self.wc = wc
    self.mapper = mapper
    self.profile = self.mapper.profile
    self.prefix = prefix
    self.model = self.profile.env[model]
    self.model_name = model
    self.endpoint = endpoint   
    self.direction = direction
    self.domain = domain
    self.dependency = dependency
    self.entry_name = entry_name or endpoint
    self.entry_set = entry_set or endpoint
    self.childs = childs
    self.name_field = name_field
    self.oldapi = oldapi
    self.field_template = template_field
    
    # checkpoints
    self.checkpoints = {}
    self.checkpoint_odoo = self.prefix
    self.checkpoint_odoo_del = self.prefix + "_delete"
    self.checkpoint_wc = self.prefix + "_wc"
    
  def parseEmail(self, email):
    if not email:
      return None
    email = parseaddr(email)[1]
    if email and email.find("@") >= 0:
      return email
    return None
    
  def fromOdoo(self, obj, wid=None):
    return {}
  
  def fromOdooChild(self, model_name, obj, wid=None):
    return {}
  
  def toOdoo(self, doc, obj=None):
    return {}
  
  def toWcGMT(self, ts):
    ts = util.strToTime(ts)
    return datetime.strftime(ts, "%Y-%m-%dT%H:%M:%SZ")
  
  def fromWcGMT(self, ts):
    if ts.find("Z") < 0:
      ts = ts + "Z"
    ts = dateutil.parser.parse(ts)
    # parse ISO 8601
    return util.timeToStr(ts)
  
  def getEndpoint(self, params):
    endpoint = self.endpoint
    if params:
      endpoint = "%s?%s" % (endpoint, "&".join(params))
    return endpoint
  
  def getChildEndpoint(self, endpoint, params):
    if params:
      endpoint = "%s?%s" % (endpoint, "&".join(params))
    return endpoint
  
  
  def findDoc(self, obj, endpoint=None, name_field=None, entry_set=None):
    if not endpoint:
      endpoint = self.endpoint
    if not name_field:
      name_field = self.name_field
    if not entry_set:
      entry_set = self.entry_set
      
    try:
      name = getattr(obj, self.name_field)
      res = self.wc.get_filtered("%s?filter[q]=%s&filter[limit]=1000" % (endpoint, urllib.quote_plus(name.encode("utf-8"))))
      docs = res[entry_set]
      for doc in docs:
        if doc[self.name_field] == name:
          return doc
    except:
      pass
    return None
  
  def getCheckpoint(self, name):
    checkpoint = self.checkpoints.get(name)
    if not checkpoint:
      checkpoint_obj = self.profile.env["wc.profile.checkpoint"]
      checkpoint = checkpoint_obj.search([("profile_id","=",self.profile.id),("name","=",name)])
      if checkpoint:
        checkpoint = checkpoint[0]
      else:        
        checkpoint = checkpoint_obj.create({
          "profile_id": self.profile.id,
          "name": name
        })                              
      self.checkpoints[name] = checkpoint      
    return checkpoint
  
  def afterWcUpdate(self, obj, wid):
    if self.childs:
      for child_model, child_field, child_endpoint, child_entry_set, child_entry_name in self.childs:
        child_objs = getattr(obj, child_field)
        child_wcids = set()
        for child_obj in child_objs:
          child_wcid = self.mapper.getWcId(child_model, child_obj.id)
          
          # search 
          if not child_wcid:
            child_doc = self.findDoc(child_obj, "%s/%s/%s" % (self.endpoint, wid, child_endpoint), entry_set=child_entry_set)
            if child_doc:
              child_wcid = child_doc["id"]
              self.mapper.addWcId(child_model, child_obj.id, child_wcid)
            
          child_doc = self.fromOdooChild(child_model, child_obj, child_wcid)
          if child_doc:
            if not child_wcid:
              # create new
              _logger.info("Create in WooCommerce [model=%s,oid=%s,data=%s]" % (child_model, child_obj.id, repr(child_doc)))
              child_doc = self.wc.post("%s/%s/%s" % (self.endpoint, wid, child_endpoint), child_doc, logerror=True)
              if child_doc:
                child_wcid = child_doc["id"]
                self.mapper.addWcId(child_model, child_obj.id, child_wcid)
            else:
              # update current
              _logger.info("Update in WooCommerce [model=%s,oid=%s,data=%s]" % (child_model, child_obj.id, repr(child_doc)))
              if self.oldapi:
                self.wc.put_force("%s/%s/%s/%s" % (self.endpoint, wid, child_endpoint, child_wcid), {child_entry_name:child_doc}, logerror=True)
              else:
                self.wc.put("%s/%s/%s/%s" % (self.endpoint, wid, child_endpoint, child_wcid), child_doc, logerror=True)

            if child_wcid:
              child_wcids.add(child_wcid)
        
        # delete unused childs
        childAllEndpoint = self.getChildEndpoint("%s/%s/%s" % (self.endpoint, wid, child_endpoint),
                                                ["filter[limit]=100000"])
          
        child_docs = self.wc.get_filtered(childAllEndpoint)[child_entry_set]
        for child_doc in child_docs:
          if not child_doc["id"] in child_wcids:
              _logger.info("Delete in WooCommerce [model=%s,data=%s]" % (child_model, repr(child_doc)))
              if self.oldapi:
                self.wc.delete_force("%s/%s/%s/%s" % (self.endpoint, wid, child_endpoint, child_doc["id"]))
              else:
                self.wc.delete("%s/%s/%s/%s" % (self.endpoint, wid, child_endpoint, child_doc["id"]))
  
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
          dep_checkpoint = self.getCheckpoint("%s_%s" % (self.prefix, dep_prefix))
          dep_timestamp = dep_checkpoint.ts
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
          dep_checkpoint.ts = dep_timestamp
            
      
      # query odoo changes
      odoo_checkpoint = self.getCheckpoint(self.checkpoint_odoo)
      odoo_timestamp = odoo_checkpoint.ts
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
      wc_checkpoint = None
      if self.direction == "both":    
        # CREATED   
        # query wc creates
        wc_checkpoint = self.getCheckpoint(self.checkpoint_wc) 
        wc_timestamp = wc_checkpoint.ts
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
        docs = self.wc.get_filtered(endpoint)[self.entry_set]
  
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
          else:
            wid = self.mapper.loadWcId(self.model_name, obj.id)       
          
          # update
          if wid:
            updates.append((obj,doc))
          else:                  
            # create new
            _logger.info("Create in WooCommerce [model=%s,oid=%s,data=%s]" % (self.model_name, obj.id, doc))
            res_doc = self.wc.post(self.endpoint, doc, logerror=True)
            if res_doc:
              wid = res_doc["id"]                                
              self.mapper.addWcId(self.model_name, obj.id, wid)              
                  
              # changed
              changes = True
              self.afterWcUpdate(obj, wid)
                  
              # add processed 
              last_update = res_doc.get("date_modified_gmt")
              if last_update:
                updated_at = self.fromWcGMT(last_update)
                processed_wid.add((wid, updated_at))
                
              
  
            
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
            _logger.info("Update in Odoo [model=%s,oid=%s,wid=%s,data=%s]" % (self.model_name, obj.id, wid, repr(values)))
          else:
            _logger.info("Create in Odoo [model=%s,wid=%s,data=%s]" % (self.model_name, wid, repr(values)))
            template = getattr(self.profile, self.field_template)
            obj = template.copy(values)
            self.mapper.addWcId(self.model_name, obj.id, wid)            
            
          # add processe doid
          processed_oid.add((oid, obj.write_date))
  
        
      ## Post WooCommerce Changes
        
      for obj, doc in updates:
        wid = doc["id"]
        _logger.info("Send WooCommerce Update [model=%s,oid=%s,wid=%s,data=%s]" % (self.model_name, obj.id, wid, repr(doc)))

        # update
        if self.oldapi:
          doc = self.wc.put_force("%s/%s" % (self.endpoint, wid), {self.entry_name: doc}, logerror=True)
          if doc:
            doc = doc[self.entry_name]
        else:
          doc = self.wc.put("%s/%s" % (self.endpoint, wid), doc, logerror=True)
          
        self.afterWcUpdate(obj, wid)
        
        if doc:
          # mark changed
          changes = True
                   
          # it could be that last update
          # isn't supported, therefore only direction up is valid
          last_update = doc.get("date_modified_gmt")
          if last_update:                
            processed_wid.add((doc["id"], self.fromWcGMT(last_update)))
      
        
        
      # Handle Deleted
      odoo_del_checkpoint = self.getCheckpoint(self.checkpoint_odoo_del)
      odoo_del_timestamp = odoo_del_checkpoint.ts
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
        
        
      ## Update Odoo Timestamp
      odoo_del_checkpoint.ts = odoo_del_timestamp or odoo_timestamp
      odoo_checkpoint.ts = odoo_timestamp
      # Update WooCommerce Timestamp
      if wc_timestamp:
        wc_checkpoint.ts = wc_timestamp
    

class WcProductAttribSync(WcSync):
  """ ATTRIBUTE SYNC """
  def __init__(self, mapper, wc):
    super(WcProductAttribSync, self).__init__(mapper, wc, "product_attribute", "product.attribute", "products/attributes", 
                                        direction="up",
                                        entry_name="product_attribute",
                                        entry_set="product_attributes",
                                        dependency=[
                                          ("product_attribute_value", "product.attribute.value", "attribute_id",[])
                                        ],
                                        childs=[
                                          ("product.attribute.value", "value_ids", "terms", "product_attribute_terms", "product_attribute_term")
                                        ],
                                        oldapi=True)
  
  
  def fromOdoo(self, obj, wid=None):
    return {
      "name": obj.name,
      "type": "select" 
    }
    
  def fromOdooChild(self, model_name, obj, wid=None):
    return {
      "name": obj.name
    }
    
    
class WcProductSync(WcSync):
  """ ATTRIBUTE SYNC """
  def __init__(self, mapper, wc):
    super(WcProductSync, self).__init__(mapper, wc, "product_tmpl", "product.template", "products", 
                                        direction="up",
                                        entry_name="product",
                                        entry_set="products",
                                        dependency=[
                                          ("product", "product.product", "product_tmpl_id", [("wc_state","!=",False)]),
                                          ("product_attribute", "product.attribute.value", "product_ids", [("product_ids.wc_state","!=",False)])
                                        ],
                                        domain=[("wc_state","!=",False)],                                        
                                        oldapi=True)
  
  
  def fromOdoo(self, obj, wid=None):
    attributes = []
    variations = []
    res =  {
      "title": obj.name,
      "description": obj.description_sale,
      "type": "simple",
      "sku": obj.default_code or obj.ean13,
      "regular_price": str(obj.list_price or 0.0),
      "virtual": False,
      "in_stock": False,
      "attributes": attributes,  
      "variations": variations,
      "status": obj.wc_state
    }
    
    # add attributes
    for att_line in obj.attribute_line_ids:
      att = att_line.attribute_id
      options = []
      for att_value in att_line.value_ids:
        options.append(att_value.name)
        
      attributes.append({
        "name": att.name,
        "options": options 
      })
    
    # add variants
    variant_count = obj.product_variant_count
    if variant_count > 1:
      res["type"] = "variable"
      for variant in obj.product_variant_ids:
        variant_attributes = []
        variations.append({
          "regular_price": str(variant.lst_price or 0.0),
          "sku": obj.default_code or obj.ean13,
          "attributes": variant_attributes
        })
        
        # add variant values
        for att_value in variant.attribute_value_ids:
          variant_attributes.append({
            "name": att_value.attribute_id.name,
            "option": att_value.name 
          })
    
    # update stock
    if obj.type == "service":
      res["virtual"] = True
      res["in_stock"] = True
    elif obj.type == "product":
      if obj.qty_available > 0:
        res["in_stock"] = True
        
    return res
    
   
class WcUserSync(WcSync):
  """ USER SYNC """
  def __init__(self, mapper, wc):
    super(WcUserSync, self).__init__(mapper, wc, "user", "res.users", "customers", 
                                        direction="both",
                                        domain=[("share","=",True)],
                                        dependency=[
                                          ("partner","res.partner","user_ids",['|',("user_ids.share","=",True),("user_ids.user_id.share","=",True)])
                                        ],
                                        template_field="user_template_id")  
    
    
  def fromOdoo(self, obj, wid=None):    
    # get password
    self.profile._cr.execute("SELECT password FROM res_users WHERE id=%s", (obj.id,))
    password = self.profile._cr.fetchone()[0]
        
    # correct email
    email = self.parseEmail(obj.email)
    email_login = self.parseEmail(obj.login)
    if email_login and not email:
      email = email_login
    
    # get other
    partner = obj.partner_id
    res = {
      "email": email,
      "first_name": partner.firstname,
      "last_name": partner.surname,
      "username": obj.login,
      "password": password
    }
    
    def getAddressData(partner):
      return {
        "first_name": partner.firstname or "",
        "last_name": partner.surname or "",
        "company":  partner.is_company and partner.name or "",
        "address_1": partner.street or "",
        "address_2": partner.street2 or "",
        "city": partner.city or "",
        "email": parseaddr(partner.email)[1] or "",
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
      doc = self.fromOdoo(obj)
      email = doc["email"]
      if email:
        email = email.encode("utf-8")
        res = self.wc.get_filtered("customers/email/%s" % urllib.quote_plus(email))
        return res["customer"]
    except:
      pass
    return None
  
  def toOdoo(self, doc, obj=None):
    name = []
        
    surname = doc["last_name"]
    if surname:
      name.append(surname)
    
    firstname = doc["first_name"]
    if firstname:
      name.append(firstname)

    email = doc["email"]
    name = " ".join(name)

    street = None
    street2 = None
    city = None
    phone = None
    country = None
    country_id = None
    company = None
    
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
      "login": doc["username"],
      "is_company": company and True or False
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
  
    
  name = fields.Char("Name", required=True, readonly=True, states={'draft': [('readonly', False)]})
  url = fields.Char("Url", required=True, readonly=True, states={'draft': [('readonly', False)]})
  consumer_key = fields.Char("Consumer Key", required=True, readonly=True, states={'draft': [('readonly', False)]})
  consumer_secret = fields.Char("Consumer Secret", required=True, readonly=True, states={'draft': [('readonly', False)]})
  
  state = fields.Selection([("draft","Draft"),
                            ("active","Active")],
                           string="Status", required=True, default="draft")
  
  company_id = fields.Many2one("res.company", "Company", required=True, default=lambda self: self.env.user.company_id.id,
                               readonly=True, states={'draft': [('readonly', False)]})
  
  user_template_id = fields.Many2one("res.users", "User Template", required=True, readonly=True, states={'draft': [('readonly', False)]})
  checkpoint_ids = fields.One2many("wc.profile.checkpoint", "profile_id", "Checkpoints", readonly=True, states={'draft': [('readonly', False)]})
  
  def _get_client(self):
    return WcClient(woocommerce.api.API(self.url, self.consumer_key, self.consumer_secret,
                                        version="wc/v2", wp_api=True),
                    woocommerce.api.API(self.url, self.consumer_key, self.consumer_secret))
  
  @api.model
  def _sync_user(self, mapper, wc):
    return WcUserSync(mapper, wc).sync()
  
  @api.model
  def _sync_product_attributes(self, mapper, wc):
    return WcProductAttribSync(mapper, wc).sync()
  
  @api.model
  def _sync_product(self, mapper, wc):
    return WcProductSync(mapper, wc).sync()
  
  @api.one
  def _sync(self):
    # create context
    mapper = WcMapper(self)    
    wc = self._get_client()
    # SYNC
    #self._sync_user(mapper, wc)
    #self._sync_product_attributes(mapper, wc)
    self._sync_product(mapper, wc)
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
  
  
class wc_profile_checkpoint(models.Model):
  _name = "wc.profile.checkpoint"
  _description = "WooCommerce Checkpoint"
  
  name = fields.Char("Name", required=True, index=True)
  profile_id = fields.Many2one("wc.profile", "Profile", required=True, index=True)
  ts = fields.Datetime("Checkpoint")

