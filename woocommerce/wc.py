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
from openerp.addons.at_base import format
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
    
    # COMMIT AFTER ADD
    self.mapper_obj._cr.commit()
    
    self.wc2oid[(model, wcid)] = oid
    self.oid2wc[(model, oid)] = wcid
    
  def getDeletedWcIds(self, model, ts):
    self.mapper_obj.check_deleted(model)
    wcids = []
    if ts:
      ts = util.getNextSecond(ts)
      for values in self.mapper_obj.with_context(active_test=False).search_read([("name","=",self.name),("res_model","=",model),("write_date",">=", ts),("active","=",False)], ["uuid","write_date"]):      
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
    
  def get(self, resource, logerror=False):
    return self.parse(self.wc.get(resource), logerror=logerror)
  
  def get_all(self, resource, limit=100, logerror=False):
    docs = []
    c = "?"
    if resource.find(c) >= 0:
      c = "&"
    offset = 0    
    while True:
      resource_url = "%s%s%s" % (resource, c, "offset=%s&per_page=%s" % (offset, limit))
      limited_docs = self.get(resource_url, logerror=logerror)
      if not limited_docs:
        break
      offset += limit
      docs.extend(limited_docs)
      if len(limited_docs) < limit:
        break
    return docs    
  
  def get_filtered(self, resource, logerror=False):
    return self.parse(self.wc_old.get(resource), logerror=logerror)
  
  def get_filtered_all(self, resource, entry, limit=100, logerror=False):
    docs = []
    c = "?"
    if resource.find(c) >= 0:
      c = "&"
    offset = 0    
    while True:
      resource_url = "%s%s%s" % (resource, c, "filter[offset]=%s&filter[limit]=%s" % (offset, limit))
      res = self.get_filtered(resource_url, logerror=logerror)
      if not res:
        break
      limited_docs = res[entry]
      if not limited_docs:
        break
      offset += limit
      docs.extend(limited_docs)
      if len(limited_docs) < limit:
        break
    return docs    
  
  def get_updated(self, resource):
    return []
  
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
               dependency=None, entry_name=None, entry_set=None, childs=None, name_field="name", 
               oldapi=False, template_field=None):
    
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
  
  def getOid(self, wcid):
    return self.mapper.getOid(self.model_name, wcid)
  
  def getWid(self, obj):
    return self.mapper.getWcId(self.model_name, obj.id)  
  
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
      res = self.wc.get_filtered_all("%s?filter[q]=%s" % (endpoint, urllib.quote_plus(name.encode("utf-8"))))
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
        
        
        # DELETE UNUSED
        
        childAllEndpoint = "%s/%s/%s" % (self.endpoint, wid, child_endpoint)
        if self.oldapi:
          # search with old api
          child_docs = self.wc.get_filtered_all(childAllEndpoint, child_entry_set)
        else:
          # search with new api
          child_docs = self.wc.get_all(childAllEndpoint)
        
        # iterate childs for delete  
        for child_doc in child_docs:
          if not child_doc["id"] in child_wcids:
              _logger.info("Delete in WooCommerce [model=%s,data=%s]" % (child_model, repr(child_doc)))
              if self.oldapi:
                self.wc.delete_force("%s/%s/%s/%s" % (self.endpoint, wid, child_endpoint, child_doc["id"]))
              else:
                self.wc.delete("%s/%s/%s/%s" % (self.endpoint, wid, child_endpoint, child_doc["id"]))
  
  def create(self, values, doc):
    template = getattr(self.profile, self.field_template)            
    obj = template.copy(values)
    self.mapper.addWcId(self.model_name, obj.id, doc["id"])
    return obj
  
  def update(self, obj, values, doc):
    return obj.write(values)
  
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
          params.append("filter[orderby]=last_update")
          params.append("filter[order]=asc")
        
        # get endpoint
        endpoint = self.getEndpoint(params)
        
        # add created docs
        docs = self.wc.get_filtered_all(endpoint, self.entry_set)
  
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
          # load wid
          if not wid:
            wid = self.mapper.loadWcId(self.model_name, obj.id)
            
          # update if wid found
          if wid:
            doc["id"] = wid
            updates_wids.add(wid)
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
          updated_at = doc.get("updated_at")
          if not updated_at:
            updated_at = doc.get("last_update")          
          updated_at = self.fromWcGMT(updated_at)
          
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
          obj = None
          if oid:
            obj = self.model.browse(oid)
          
          values = self.toOdoo(doc, obj)
          if values:
            changes = True          
            if obj:          
              _logger.info("Update in Odoo [model=%s,oid=%s,wid=%s,data=%s]" % (self.model_name, obj.id, wid, repr(values)))
              self.update(obj, values, doc)
            else:
              _logger.info("Create in Odoo [model=%s,wid=%s,data=%s]" % (self.model_name, wid, repr(values)))
              obj = self.create(values, doc)                        
            
          # add processed oid
          if obj:
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
                                          ("product", "product.product", "product_tmpl_id", [("wc_sync","=",True)]),
                                          ("product_attribute", "product.attribute.value", "product_ids", [("product_ids.wc_sync","=",True)])
                                        ],
                                        childs=[
                                          ("product.product", "product_variant_ids", "variations", "variations", "variation")
                                        ],
                                        domain=[("wc_sync","=",True),"|",("active","=",True),("active","=",False)])
  
  
  
  def fromOdoo(self, obj, wid=None):
    attributes = []
    variations = []
    
    sku = None
    ptype = "variable"
    if obj.product_variant_count <= 1:
      sku = obj.default_code or obj.ean13
      ptype = "simple"
    else:
      max_sku = None
      min_sku = None
      for variant in obj.product_variant_ids:
        sku = variant.default_code or obj.ean13
        if not min_sku:
          min_sku = sku
          max_sku = sku
        else:
          min_sku = min(sku, min_sku)
          max_sku = max(sku, max_sku)
          
      if min_sku:
        sku = "%s-%s" % (min_sku, max_sku)
        
    res =  {
      "name": obj.name,
      "type": ptype,
      "sku": sku or "",
      "regular_price": str(obj.list_price or 0.0),
      "virtual": False,
      "in_stock": obj.sale_ok,
      "attributes": attributes,  
      "variations": variations,
      "manage_stock": False,
      "backorders": "yes"
    }
    
    if not wid:
      res["status"] = "draft"
    
    # check if not active
    if not obj.active:
      # if to create, return empty
      if not wid:
        return {}
      # otherwise set to draft
      # and set to unavailable
      # and reset sku
      res["status"] = "draft"
      res["in_stock"] = False
      res["sku"] = ""
      
    
    # add attributes
    for att_line in obj.attribute_line_ids:
      att = att_line.attribute_id
      options = []
      for att_value in att_line.value_ids:
        options.append(att_value.name)
        
      attributes.append({
        "name": att.name,
        "options": options,
        "visible": True,
        "variation": True 
      })
        
    
    # stock
    if obj.type == "product":
      res["manage_stock"] = True
      res["stock_quantity"] = int(obj.qty_available)
      res["backorders"] = "notify"
    # consu
    elif obj.type == "consu":
      res["manage_stock"] = True
      res["stock_quantity"] = 0
      res["backorders"] = "notify"
    # virtual, service
    else:
      res["virtual"] = True
      
    return res
  
  def fromOdooChild(self, model_name, obj, wid=None):
    if obj.product_variant_count <= 1:
      return {}
    
    
    # basic
    variant_attributes = []
    res =  {
      "regular_price": str(obj.lst_price or 0.0),
      "sku": obj.default_code or obj.ean13,
      "attributes": variant_attributes,
      "virtual": False,
      "in_stock": True
    }
    
    # check inactive
    if not obj.active:
      res["sku"] = ""
      res["in_stock"] = False
    
    # stock
    if obj.type == "product":
      res["manage_stock"] = True
      res["stock_quantity"] = int(obj.qty_available)
      res["backorders"] = "notify"
    # consu
    elif obj.type == "consu":
      res["manage_stock"] = True
      res["stock_quantity"] = 0
      res["backorders"] = "notify"
    # virtual, service
    else:
      res["virtual"] = True
      
    # add variant values
    for att_value in obj.attribute_value_ids:
      variant_attributes.append({
        "name": att_value.attribute_id.name,
        "option": att_value.name 
      })
    
    return res
    
  def findDoc(self, obj, endpoint=None, name_field=None, entry_set=None):
    if obj._model._name == "product.product":
      return {}
    return WcSync.findDoc(self, obj, endpoint=endpoint, name_field=name_field, entry_set=entry_set)
    
   
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
  
  def getOrderPolicy(self, obj):
    return "prepaid"
    
  def getAddressData(self, partner):
    first_name = None
    last_name = None
    company = None
  
    if partner.is_person:
      first_name = partner.firstname
      last_name = partner.surname  
    else:
      company = partner.name
  
    
    return {
      "first_name": first_name or "",
      "last_name": last_name or "",
      "company":  company or "",
      "address_1": partner.street or "",
      "address_2": partner.street2 or "",
      "city": partner.city or "",
      "email": parseaddr(partner.email)[1] or "",
      "phone": partner.phone or None,
      "country":  partner.country_id.code or "AT"
    }  
    
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
      "first_name": "",
      "last_name": "",
      "username": obj.login,
      "password": password
    }
    
    if partner.is_person:
      res["first_name"] = partner.firstname or "" 
      res["last_name"] = partner.surname or ""
    
    # get billing address
    res["billing_address"] = self.getAddressData(partner)
    
    # get delivery address
    for child in partner.child_ids:
      if child.type == "delivery":
        res["shipping_address"] = self.getAddressData(child)
    
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
    is_person = surname and firstname and True

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
      "is_company": company and True,
      "is_person": is_person and not company and True
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
  

class WcOrderSync(WcSync):
  """ ATTRIBUTE SYNC """
  def __init__(self, mapper, wc):    
    super(WcOrderSync, self).__init__(mapper, wc, "order", "sale.order", "orders", 
                                        direction="both",
                                        entry_name="order",
                                        entry_set="orders",
                                        domain=[("state","not in",["draft","sent"]),("partner_id.user_ids.share","=",True)],                                        
                                        oldapi=True)
    
    self.user_sync = self.profile._sync_user(mapper, wc)
    self.product_sync = self.profile._sync_product(mapper, wc)
    self.dummy_wid = self.product_sync.getWid(self.profile.dummy_product_tmpl_id)
    self.payments = self.profile.payment_ids
    self.default_payment = None
    self.update_lines = False
    self.create = False
    if self.payments:
      self.default_payment = self.payments[0]
      self.default_payment_details = {
        "method_id": self.default_payment.code,
        "method_title": self.default_payment.name,
        "paid": False
      }
  
  def fromOdoo(self, obj, wid=None):
    return {}
  
    # only update?
    if not wid and not self.create:
      return {}
    
    # get customer wid
    customer_wid = self.user_sync.getWid(obj.partner_id)
    if not customer_wid:
      return {}
   
    # status
    status = "pending"
    if obj.state in ("progress","manual","waiting_date","shipping_except","invoice_except"):
      status = "processing"
    elif obj.state == "cancel":
      status = "cancelled"
      if not wid:
        return {}
    elif obj.state == "done":
      if obj.invoiced:
        status = "completed"
      else:
        status = "processing"
    
    res =  {      
      "status": status,
      "currency": obj.currency_id.name,
      "billing" : self.user_sync.getAddressData(obj.partner_invoice_id),
      "shipping": self.user_sync.getAddressData(obj.partner_shipping_id),
      "customer_id": customer_wid
    }
    
    # get current state
    item_dict = {}
    if wid:
      cur_doc = self.wc.get("orders/%s" % wid)
      
      # check payment
      if obj.invoiced:
        payment_details = cur_doc.get("payment_details")
        if payment_details and not payment_details.get("paid"):
          payment_details["paid"] = True
          res["payment_details"] = payment_details
              
      # build item dict
      if self.update_lines:
        cur_items = cur_doc.get("items")
        if cur_items:
          for cur_item in cur_items:
            meta_datas = cur_items.get("meta_data")
            if meta_datas:
              for meta_data in meta_datas:
                if meta_data["key"] == "oid":
                  item_dict[int(meta_data["value"])] = cur_item
                 
    else:
      
      # check payment      
      payment_details = self.default_payment_details.copy()
      res["payment_details"] = payment_details
      if obj.invoiced:        
        payment_details["paid"] = True
        
      
    # update lines
    if self.update_lines:
      items = []
      coupon_product_id = self.profile.coupon_product_id.id
      for line in obj.order_line:
        # add lines
        if line.product_id and line.product_id.id != coupon_product_id:  
          product_tmpl_wid = self.mapper.getWcId("product.template", line.product_id.product_tmpl_id.id)
          item_values = item_dict.get(line.id)
          if not item_values:
            # check if product exist
            if product_tmpl_wid:            
              item_values = {
                "product_id": product_tmpl_wid,
                "quantity": str(line.product_uom_qty),
                "total": str(line.price_subtotal),
                "subtotal": str(line.price_subtotal),
                "variation_id": 0         
              }
               
              variation_wid = self.mapper.getWcId("product.product", line.product_id.id)
              if variation_wid:
                item_values["variation_id"] = variation_wid          
               
            # create line with dummy
            else:
              item_values = {
                "product_id": self.dummy_wid,
                "quantity": str(line.product_uom_qty),
                "total": str(line.price_subtotal),
                "subtotal": str(line.price_subtotal),
              }
               
          else:
            # del unused line
            del item_dict[line.id]
   
          # add lines
          items.append(item_values)      
   
        # delete unused items
        for item in item_dict.values():
          items.append({
            "id": item["id"],
            "product_id": None          
          })  
           
        # set items
        if items:
          res["line_items"] = items
    
    return res
  
  def toOdoo(self, doc, obj=None):
    if obj:
      return {}
    
    user_id = self.user_sync.getOid(doc["customer_id"])
    if not user_id:
      return {}
    
    user = self.profile.env["res.users"].browse(user_id)
    if not user:
      return {}
    
    partner = user.partner_id
    partner_obj = self.profile.env["res.partner"]
    
    # get or crate partner
    def getPartnerId(data, atype="delivery"):
      if not data:
        return partner.id      
      domain = []
      
      company = data.get("company")
      firstname = data.get("first_name")
      surname = data.get("last_name")
      
      domain.append(('|',("name","=",company),
                    '&',("firstname","=",firstname),("surname","=",surname)))
      
      street = data.get("address_1","")
      domain.append(("street","=",street))
      
      street2 =  data.get("address_2")
      if street2:
        domain.append(("street2","=",street2))
        
      city = data.get("city")
      if city:
        domain.append(("city","=",city))
        
      zip_code = data.get("postcode")
      if zip_code:
        domain.append(("zip","=",zip_code))
        
      res = partner_obj.search(domain)
      if res:
        return res[0].id
      elif street and street2 and city and zip_code and (company or (firstname and surname)):
        values = self.user_sync.getAddressData(data)
        values["is_company"] = False
        values["type"]=atype
        values["parent_id"]=partner.id
        return partner_obj.create(values).id
      else:
        partner.id
      
    res = {
      "partner_id": partner.id,
      "partner_invoice_id": getPartnerId(doc.get("billing_address"), "invoice"),
      "partner_shipping_id": getPartnerId(doc.get("shipping_address"), "delivery"),
      "order_policy": self.user_sync.getOrderPolicy(partner),
      "date_order": self.fromWcGMT(doc["created_at"])      
    }
    
    if not obj:
      res["wc_order"] = True
    
    order_obj = self.profile.env["sale.order"]
    value = order_obj.onchange_partner([],partner.id)["value"]
    res.update(value)
  
    # add note
    note = doc.get("note")
    if note:
      notes = []
      cur_note = res.get("note","")
      if cur_note:
        notes.append(note)
      notes.append(note)
      res["note"] = "\n".join(notes)
      
      
    # add lines
    lines = []
    items = doc.get("items")
    if items:
      product_obj = self.profile.env["product.product"]
      for item in items:
        product_tmpl_id = self.mapper.getOid("product.template",item["product_id"])
        variation_id = item.get("variation_id")
        if variation_id:
          product_id = self.mapper.getOid("product.product",variation_id)
          
        if not variation_id:
          product_id = product_obj.search([("product_tmpl_id","=",product_tmpl_id)])[0].id
        
        line_values = {
          "product_id": product_id,
          "product_uom_qty": float(item.get("quantity","0.0")),
          "price_unit": float(item.get("price","0.0")),
          "price_nocalc": True
        }
        
        lines.apppend(line_values)
      
    coupons = doc.get("coupon_lines")
    if coupons:
      f = format.LangFormat(self.profile._cr, self.profile._uid, self.profile._context)
      for coupon in coupons:
        name = [self.profile.coupon_product_id.name_get()[0]]
        coupon_code = coupon.get("code")
        if coupon_code:
          name.append(coupon_code)
        
        coupon_discount = float(coupon.get("amount",0.0)) * -1.0
        name.append(f.formatLang(coupon_discount, monetary=True))
        name.append(self.profile.company_id.currency_id.symbol)
          
        line_values = {
          "product_id": self.profile.coupon_product_id.id,
          "product_uom_qty": 1,
          "wc_coupon": coupon.get("code") or "",
          "price_unit": 0,
          "price_nocalc": True,
          "name": " ".join(name) 
        }
        lines.apppend(line_values)
    
    line_obj = self.profile.env["sale.order.line"]
    for line in lines:      
      value = line_obj.product_id_change_with_wh_price(self._cr, self._uid, [], 
            pricelist=res["pricelist_id"], product=line["product_id"], qty=line["product_uom_qty"],
            name=line.get("name"), partner_id=res.get("partner_id"),
            date_order=res.get("date_order"), 
            fiscal_position=res.get("fiscal_position"), flag=True, price_unit=line.price_unit, price_nocalc=line.price_nocalc, context=self._context)["value"]
      line.update(value)
          
    res["order_line"] = [(0,0,l) for l in lines]     
    return res
  

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
  order_template_id = fields.Many2one("sale.order", "Order Template", required=True, readonly=True, states={'draft': [('readonly', False)]})
  dummy_product_tmpl_id = fields.Many2one("product.template","Dummy Product", required=True, readonly=True, states={'draft': [('readonly', False)]},
                                     help="This Product is used if product not synced to Server")
  coupon_product_id = fields.Many2one("product.product", "Coupon Product", required=True, readonly=True, states={'draft': [('readonly', False)]})
  checkpoint_ids = fields.One2many("wc.profile.checkpoint", "profile_id", "Checkpoints", readonly=True, states={'draft': [('readonly', False)]})
  
  payment_ids = fields.One2many("wc.profile.payment", "profile_id", "Payment Methods", readonly=True, states={'draft': [('readonly', False)]})
  
  webhook_url = fields.Char("Webhook Url", readonly=True, states={'draft': [('readonly', False)]})
  webhook_secret = fields.Char("Webhook Secret", readonly=True, states={'draft': [('readonly', False)]})
  
  def _get_client(self):
    return WcClient(woocommerce.api.API(self.url, self.consumer_key, self.consumer_secret,
                                        version="wc/v2", wp_api=True),
                    woocommerce.api.API(self.url, self.consumer_key, self.consumer_secret))
  
  @api.model
  def _sync_user(self, mapper, wc):
    return WcUserSync(mapper, wc)
  
  @api.model
  def _sync_product_attribute(self, mapper, wc):
    return WcProductAttribSync(mapper, wc)
  
  @api.model
  def _sync_product(self, mapper, wc):
    return WcProductSync(mapper, wc)
  
  @api.model
  def _sync_order(self, mapper, wc):
    return WcOrderSync(mapper, wc)
  
  @api.one
  def _sync(self):
    # create context
    mapper = WcMapper(self)    
    wc = self._get_client()
    # SYNC
    self._sync_user(mapper, wc).sync()    
    self._sync_product_attribute(mapper, wc).sync()
    self._sync_product(mapper, wc).sync()
    #self._sync_order(mapper, wc).sync()
    return True
    
  @api.multi
  def action_sync(self):
    self._sync()
    return True
  
  @api.multi
  def action_activate(self):
    for profile in self:
      if profile.state == "draft":
        profile.dummy_product_tmpl_id.wc_sync = True
        wc = profile._get_client()
        res = wc.get("webhooks")
        profile.state = "active"
        # install webhook
    return True
  
  @api.multi
  def action_draft(self):
    self.state = "draft"
    return True
  
  @api.model
  def sync_all(self):
    self.search([("state","=","active")]).action_sync()
    return True
  
class wc_profile_checkpoint(models.Model):
  _name = "wc.profile.checkpoint"
  _description = "WooCommerce Checkpoint"
  
  name = fields.Char("Name", required=True, index=True)
  profile_id = fields.Many2one("wc.profile", "Profile", required=True, index=True)
  ts = fields.Datetime("Checkpoint")
  

class wc_profile_payment(models.Model):
  _name = "wc.profile.payment"
  _descripton = "WooCommerce Payment"
  _sql_constraints = [
    ("uniq_journal_code", "unique(profile_id,journal_id,code)", "Journal could only assigned once to WooCommerce Profile!")
  ]
  _order = "sequence"
  
  name = fields.Char("Name", required=True)
  profile_id = fields.Many2one("wc.profile", "Profile", required=True, index=True)
  journal_id = fields.Many2one("account.journal", "Journal", required=True, index=True)
  sequence = fields.Integer("Sequence", default=10, required=True)
  code = fields.Char("MethodId", required=True, index=True)
  
  

