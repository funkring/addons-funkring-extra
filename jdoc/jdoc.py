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

from openerp.osv import fields, osv
from openerp.addons.at_base import util

from openerp.tools.translate import _

import simplejson
import openerp
import uuid
import couchdb
import hashlib

import re

PATTERN_REV = re.compile("^([0-9]+)-(.*)$")

META_ID = "_id"
META_REV = "_rev"
META_DELETE = "_deleted"
META_MODEL  = "fdoo__ir_model"

META_FIELDS = set([
 META_ID,
 META_MODEL,
 META_DELETE,
 META_REV 
])

from openerp import SUPERUSER_ID

# Helper

def isMetaField(name):
    """ :return: True if it is a meta data field """
    return name.startswith("_") or name in META_FIELDS

def isReference(vals):
    if vals and vals.get(META_ID):
        for field in vals.keys():
            if not isMetaField(field):
                return False
        return True
    return False

def getAttrOrNone(model_obj, name):
    try:
        return getattr(model_obj, name)
    except AttributeError:
        return None

class DefRecursionException(Exception):
    """ Recursion Exception """
    pass


class jdoc_jdoc(osv.AbstractModel):
    
    def _jdoc_create_def(self, cr, uid, model_obj, recursion_set=None, context=None):
        """
        Create jdoc Definition from Model
        
        Field Attribute(s): 
            
            composition 
            export
                        
            
        Class Attribute(s):
        
            _composition
        
        """
        if not context:
            context = {}
            
                               
        #check recursion
        if recursion_set and model_obj._name in recursion_set:
            raise DefRecursionException
                       
        #create result
        field_defs = {}
        res =  {
            "fields" : field_defs,
            "model" : model_obj._name            
        }

        # get fields
        def getFields(model_obj, m):
            for parent in model_obj._inherits:
                getFields(self.pool[parent], m=m)
            for name, field in model_obj._columns.iteritems():
                m[name]=field
            return m
        
        def isComputed(field_obj):
            return isinstance(field_obj, fields.function)
            
        all_fields = getFields(model_obj, {})
        for field, field_obj in all_fields.iteritems():
            if field == "id":
                continue
                 
            field_type = field_obj._type
            if field_type == "selection":
                field_type = "char"
                if field_obj.selection:
                    
                    selection = field_obj.selection
                    if hasattr(selection, '__call__'):
                        #selection = field_obj.selection()
                        selection = None
                        
                    if selection:
                        for sel in selection:
                            sel_value = sel[0]
                            if not sel_value:
                                continue
                            if isinstance(sel_value, basestring):
                                field_type = "char"
                                break
                            if isinstance(sel_value,(int,long)):
                                field_type = "integer"
                                break
                            elif isinstance(sel_value,float):
                                field_type = "float"
                                break
                            
            
            field_relation = field_obj._obj
            field_name = getAttrOrNone(field_obj,"alias") or field          
            field_def = {}
            
            # default hide function fields
            is_computed = isComputed(field_obj)
            if is_computed:
                field_def["hidden"]=True
            
            
            # get sub ltype    
            sub_ltype_hint = getAttrOrNone(field_obj,"composition") and "c" or "r"
            if field_relation:
                sub_model_obj = self.pool[field_relation]
                if getAttrOrNone(sub_model_obj,'_composition'):
                    sub_ltype_hint = "c"
                 

            # determine sub list type
            if getAttrOrNone(field_obj,"composition"):
                sub_ltype_hint = "c"
            sub_ltype = sub_ltype_hint or "r"
                
            # evaluate type
            if field_type == "many2one":
                field_def["dtype"]=sub_ltype
                if field_relation and not is_computed:
                    rel_fields = all_fields
                    if not field_relation == model_obj._name:
                        rel_fields = getFields(self.pool.get(field_relation), {})
                    for rel_field in rel_fields.itervalues():
                        if rel_field._obj == model_obj._name and rel_field._type == "one2many":
                            if rel_field._fields_id == field:
                                field_def["hidden"]=True
            elif field_type == "one2many":
                if not sub_ltype_hint and field_relation != model_obj._name:
                    #check recursion
                    if recursion_set is None:
                        recursion_set = set()
                    recursion_set.add(model_obj._name)
                    try:
                        sub_ltype="c"
                        
                        #check recursion
                        sub_model_obj = self.pool.get(field_relation)                        
                        sub_model_obj._jdoc_create_def(cr, uid, add_description=False,
                                                            recursion_set=recursion_set, 
                                                            context=context)
                        
                        #check for parent relation
                        rel_fields = getFields(self.pool.get(field_relation))
                        for rel_field in rel_fields.values():
                            if rel_field._type == "one2many" and not isComputed(rel_field) and rel_field._obj == field_relation:
                                sub_ltype="r"
                                break
                         
                    except DefRecursionException:
                        sub_ltype="r"
                    finally:
                        recursion_set.remove(model_obj._name)

                field_def["dtype"]="l"
                field_def["ltype"]=sub_ltype
                field_def["hidden"]=(sub_ltype=="r")
            elif field_type == "many2many":
                field_def["dtype"]="l"
                field_def["ltype"]=getAttrOrNone(field_obj,"composition") or "r"
            elif field_type == "char":
                field_def["dtype"]="s"
            elif field_type == "integer":
                field_def["dtype"]="i"
            elif field_type == "float":
                field_def["dtype"]="f"
            elif field_type == "text":
                field_def["dtype"]="t"
            elif field_type == "boolean":
                field_def["dtype"]="b"
            else:
                continue
            
            # check if field is not visible
            field_invisible = getAttrOrNone(field_obj,"invisible")
            if field_invisible:
                field_def["hidden"]=True
            else:            
                # if export is explicit set
                # correct hidden
                # field could not hidden
                field_export = getAttrOrNone(field_obj,"export")
                if field_export:
                    field_def["hidden"]=False
                elif field_export is False:
                    field_def["hidden"]=True
          
            field_def["name"]=field
            if field_relation:
                field_def["model"]=field_relation
            field_defs[field_name]=field_def        
        return res
    
    def _jdoc_get(self, cr, uid, obj, refonly=False, options=None, context=None):
        if not obj:
            return False
        
        if not options:
            options = {}
        
        mapping_obj = self.pool.get("res.mapping")       
        doc_uuid = mapping_obj.get_uuid(cr, uid, obj._name, obj.id)
        if refonly:
            return doc_uuid
      
        definition = self._jdoc_def(cr, uid, obj._name)
        model = definition["model"]        
        
        res = {META_ID : doc_uuid,
               META_MODEL : model}
        
        emptyValues = True
        onlyFields = None
        compositions = None
        
        # check options
        if options:
            emptyValues = options.get("empty_values", emptyValues)
            model_options = options.get("model")
            if model_options:
                model_options = model_options.get(model)
                if model_options:
                    onlyFields = model_options.get("fields", onlyFields)
                    compositions = model_options.get("compositions", compositions)
        
        fields = definition["fields"]
        for name, attrib in fields.items():
            if name == "required":
                pass
            # check for hidden attribute, or not in fields
            if attrib.get("hidden") or (onlyFields and not name in onlyFields):
                continue
            
            # get type
            dtype = attrib["dtype"]
            # reset value
            value = None
                  
            # evaluate composite, reference and list type
            if dtype in ("c","r","l"):
                # get model
                if dtype in ("c","r"):
                    # check compositions
                    if dtype == "r" and compositions and name in compositions:
                        dtype = "c"
                    dtype_obj = getattr(obj, attrib["name"])
                    if dtype_obj:                        
                        value = self._jdoc_get(cr, uid, dtype_obj, refonly=(dtype=="r"), options=options, context=context)                    
                # handle list type 
                else:
                    dtype_objs = getattr(obj, attrib["name"])
                    ltype = attrib.get("ltype")
                    # check compositions
                    if ltype == "r" and compositions and name in compositions:
                        ltype = "c"
                    for dtype_obj in dtype_objs:
                        list_value = self._jdoc_get(cr, uid, dtype_obj, refonly=(ltype=="r"), options=options, context=context)
                        if list_value:
                            if value is None:
                                value = []
                            value.append(list_value)
            
            # evaluate primitive values
            else:
                value = getattr(obj, attrib["name"])
               
            if emptyValues or value:
                res[name]=value    
                
        #res["write_date"]=obj.write_date    
        return res
    
    def _get_uuid(self, data):
        res = hashlib.md5()
        res.update(simplejson.dumps(data))
        return res.hexdigest()
    
    def jdoc_sync(self, cr, uid, data,  context=None):
        """
        jdoc_sync
        @param changes: changeset to sync 
                          { "model" : xyz
                            "view" : "_jdoc_get_fclipboard",
                            lastsync: {
                                "date" : "2014-01-01 00:00:01",   # date  
                                "id"  :  3                        # highest database id from last sync from change target (odoo),
                                "seq" :  1                        # highest sequence from change source for the last sync
                                "lastchange" : {
                                    model.xy : "2014-01-01 00:00:01"
                                }
                                
                            },
                            "changes" : [
                               {
                                  "id": "doc2",
                                  "changes": [ { "rev": "2-9b50a4b63008378e8d0718a9ad05c7af" } ],
                                  "doc": {
                                    "_id": "doc2",
                                    "_rev": "2-9b50a4b63008378e8d0718a9ad05c7af",
                                    "_deleted": true
                                  },
                                  "deleted": true,
                                  "seq": 3
                               }
                            ]
                            "actions" : [
                               {
                                   "field_id" : root_id,
                                   "model": "fclipboard.item",
                                   "domain" : [['state','!=','release']],
                                   "action" : action_release                               
                               }
                           ]
        
        """
        
        # get model
        model = data["model"]
        model_obj = self.pool[model]
        
        # get mapping
        mapping_obj = self.pool["res.mapping"]
        
        # get changes
        in_list = data.get("changes")        
        res_doc = data.get("result_format") == "doc"
                
        # get search domain
        search_domain = data.get("domain") or []
        
        # get options        
        fields = data.get("fields")
        compositions = data.get("compositions")
        options = {"empty_values" : False }
        model_options = {}
        
        if fields:
            model_options["fields"] = fields
        if compositions:
            model_options["compositions"] = compositions
        
        if model_options:
            options["model"] = {
                model : model_options
            }
            
        # get view
        view = None
        view_name = data.get("view")
        if view_name:
            view = getattr(model_obj,view_name)(cr, uid, context=context)
  
        # accelerate and use set 
        # instead of lists after
        # create domain_uuid
        if fields:
            model_options["fields"] = set(fields)
        if compositions:
            model_options["compositions"] = set(compositions)
        
        # get last sync attribs        
        lastsync = data.get("lastsync")
        
        # init last sync default
        last_date = None
        seq = 0
        lastsync_lastchange = None
        
        if lastsync:        
            last_date = lastsync.get("date", None)
            seq = lastsync.get("seq", 0)
            lastsync_lastchange = lastsync.get("lastchange", None)
              
        # create last change if not exist
        if lastsync_lastchange is None:
            lastsync_lastchange = {}
        
        # get actions
        actions = data.get("actions")
                          
        # Method GET
        method_get = view and view.get("get") or self._jdoc_get
        # Method PUT
        method_put = view and view.get("put") or self.jdoc_put
        # Method CHANGE
        method_lastchange = view and view.get("lastchange") or None

        # process input list    
        errors = []    
        if in_list:
            changed_models = {}
            changeset = {}
            resolved_uuid2id = {}
            
            # build changeset
            for change in in_list:
                doc = change["doc"]
                doc_uuid = doc[META_ID]
                if not doc.get(META_DELETE):
                    changeset[doc_uuid] = change
            
            def put_change(change, uuid2id_resolver=None):
                doc = change["doc"]               
                return method_put(cr, uid, doc, return_id=True, uuid2id_resolver=uuid2id_resolver, changed_models=changed_models, errors=errors, context=context)
            
            def get_dependency(uuid):
                # check if dependency was already processed
                res = resolved_uuid2id.get(uuid, False)
                if res or res is None:
                    return res
                
                # resolve
                res = None
                change = changeset.get(uuid)
                
                if change:
                    res = put_change(change)
                    
                resolved_uuid2id[uuid] = res
                return res
                
            
            # process changes
            for change in in_list:
                doc = change["doc"]
                doc_uuid = doc[META_ID]
                seq = max(change["seq"], seq)
                 
                # check if change was already put, resolved
                if doc_uuid in resolved_uuid2id:
                    resolved_change = changeset.get(doc_uuid)
                    if resolved_change and resolved_change["seq"] == change["seq"]:
                        continue
                
                put_change(change,uuid2id_resolver=get_dependency)

                
            if actions:
                for action in actions:
                    action_model = action.get("model")
                    if not action_model:
                        continue
                    
                    method = action.get("action")
                    if not method or method.startswith("_"):
                        continue
                    
                    action_obj = self.pool[action_model]
                    if not action_obj:
                        continue
                    
                    action_ids = changed_models.get(action_model)
                    if not action_ids:
                        continue
                    
                    # determine changed ids
                    action_ids = list(action_ids)
                    field_id = action.get("field_id")
                    if field_id:
                        if field_id.startswith("_"):
                            continue
                        
                        new_action_ids = set()
                        
                        for vals in action_obj.read(cr, uid, action_ids, [field_id], context=context):
                            new_changed_id = vals[field_id]
                            
                            if isinstance(new_changed_id,tuple) and len(new_changed_id) > 0:
                                new_changed_id = new_changed_id[0]
                                
                            if new_changed_id:
                                new_action_ids.add(new_changed_id)
                            
                        action_ids = list(new_action_ids)    
                    
                    if not action_ids:
                        continue
                    
                    # check domain
                    action_domain = action.get("domain")
                    if action_domain:
                        action_domain.insert(0,("id","in",action_ids))
                        action_ids = action_obj.search(cr, uid, action_domain)
                    
                    # execute action
                    getattr(model_obj, method)(cr, uid, action_ids, context=context)
        
        # process output list        
        out_list = []        
        
        # build search domain
        del_search_domain = [("res_model","=",model),("active","=",False)]
      
        # check for full sync due to changed dependency
        sync_inc = True
        lastchange = None
        if method_lastchange:            
            lastchange = method_lastchange(cr, uid, context=context)
            if lastchange:   
                for key, value in lastchange.items():
                    lastsync_lastchange_date = lastsync_lastchange.get(key)
                    if not lastsync_lastchange_date or value > lastsync_lastchange_date:                        
                        sync_inc = False
                        break
                        
            
      
        # only sync with last date  
        if last_date:
            # domain for search
            if sync_inc:
                search_domain.append(("write_date",">",last_date))
            # domain for search deleted
            del_search_domain.append(("write_date",">",last_date))
            
        
        #
        # search changes
        #
        
        out_ids = model_obj.search(cr, uid, search_domain, order="write_date asc, id asc")
        
        # resync errors
        if errors:
            for error in errors:
                oid = error.get("id")
                if oid and oid not in out_ids:
                    out_ids.append(oid)
        
        if out_ids:
            
            # get last change date
            cr.execute("SELECT MAX(write_date) FROM %s WHERE id IN %%s " % model_obj._table, (tuple(out_ids),))
            res = cr.fetchone()
            if res:
                last_date = max(last_date, res[0])
            
            # create docs
            for obj in model_obj.browse(cr, uid, out_ids, context=context):
                doc = method_get(cr, uid, obj, options=options, context=context)
                if doc:
                    if res_doc:
                        out_list.append(doc)
                    else:
                        out_list.append({ "id" : doc["_id"],                                 
                                          "doc" : doc 
                                        })
                
        #
        # search deleted
        #
        
        # process deleted
        mapping_obj.check_deleted(cr, uid, model)
        
        
        # read ids
        out_deleted_vals = mapping_obj.search_read(cr, uid, del_search_domain, 
                                                            ["uuid", "write_date", "res_id"],                                                             
                                                            order="write_date asc, res_id asc")
                      
        if out_deleted_vals:
            # get last change date
            cr.execute("SELECT MAX(write_date) FROM %s WHERE res_model=%%s AND id IN %%s" % mapping_obj._table, 
                                                                (model, tuple([v["id"] for v in out_deleted_vals]) ) ) 
            res = cr.fetchone()
            if res:            
                last_date = max(last_date, res[0])
                
            # get uuids
            for out_deleted_val in out_deleted_vals:
                if not last_date or out_deleted_val["write_date"] >= last_date:
                    last_date = out_deleted_val["write_date"]
                
                # uuid 
                uuid = out_deleted_val["uuid"]
                if res_doc:
                    out_list.append({
                       "_id" : uuid,
                       "_deleted" : True                                 
                     })
                else:
                    out_list.append({
                       "id" : uuid,
                       "deleted" : True                                 
                     })
        
        
        lastsync =  {
                       "date" : last_date,
                       "seq" : seq                  
                    }
    
        if lastchange:
            lastsync["lastchange"] = lastchange
        
        res =  {
           "model" : model,
           "lastsync" : lastsync,
           "changes" : out_list,
        }
        
        if errors:
            res["errors"] = errors
        
        return res
    
    def jdoc_by_id(self, cr, uid, res_model, oid, refonly=False, options=None, context=None):
        model_obj = self.pool[res_model]
        obj = model_obj.browse(cr, uid, oid, context=context)
        if not obj:
            return False
        return self._jdoc_get(cr, uid, obj, refonly=refonly, options=options, context=context)
    
    def jdoc_get(self, cr, uid, uuid, res_model=None, refonly=False, options=None, name=None, context=None):
        mapping_obj = self.pool["res.mapping"]
        obj = mapping_obj._browse_mapped(cr, uid, uuid, res_model=res_model, name=name, context=None)
        if not obj:
            return False
        return self._jdoc_get(cr, uid, obj, refonly=refonly, options=options, context=context)
    
    def jdoc_put(self, cr, uid, doc, return_id=False, uuid2id_resolver=None, changed_models=None, errors=None, context=None):
        if not doc:
            return False
        
        mapping_obj = self.pool.get("res.mapping")       
        
        obj_id = False
        obj = False
        model = False
        res = False

        if not model:
            model = doc.get(META_MODEL)
            
        if not model:
            raise osv.except_osv(_("Error"), _("Unable to determine model"))

        uuid = doc.get(META_ID, False)
        if uuid:
            obj = mapping_obj._browse_mapped(cr, uid, uuid, res_model=model, context=context)
            if obj:
                model = obj._name
                obj_id = obj.id
                
        
        model_obj = self.pool[model]
        
        # get database id 
        def get_id(value, attribs):
            res = None
            res_uuid = None
            if value:
                # check uuid
                if isinstance(value, basestring):
                    res_uuid = value
                    res = mapping_obj.get_id(cr, uid, attribs.get("model"), value)
                
                # check reference or document
                elif isinstance(value, dict):                                                        
                    if isReference(value):
                        # get reference
                        res_uuid = value[META_ID]
                        res = mapping_obj.get_id(cr, uid, value.get(META_MODEL), res_uuid)                        
                    else:
                        # update document and get reference
                        res = self.jdoc_put(cr, uid, value, return_id=True, changed_models=changed_models, errors=errors, context=context)
                        
            # if not found try uuid resolver
            if not res and res_uuid and uuid2id_resolver:
                res = uuid2id_resolver(res_uuid)
                
            return res
        
        # check for delete
        if doc.get("_deleted"):
            try:
                with cr.savepoint():             
                    mapping_obj.unlink_uuid(cr, uid, uuid, res_model=model, context=context)
                    obj_id = False
            except Exception as e:
                if not errors is None:
                    errors.append({
                       "model" : model,
                       "id" : obj_id,
                       "uuid" : uuid,
                       "error" : e.message,
                       "error_class" : e.__class__.__name__               
                    })
                else:
                    raise e
        
        # otherwise update        
        else:
        
            definition = self._jdoc_def(cr, uid, model)
            fields = definition["fields"]
            
            values = {}
            for field, value in doc.items():
                # check if it is meta field
                if isMetaField(field):
                    continue
                
                # check attribs
                attribs = fields.get(field)
                if not attribs:
                    # if no attribs exist, field not exist
                    continue
                
                dtype = attribs["dtype"]
                if dtype == "r":
                    values[field] = get_id(value, attribs)
                    
                elif dtype in ("c","l"):
                    # handle empty value
                    if not value:
                        if dtype == "l":
                            values[field] = [(6,0,[])]
                        else:
                            values[field] = None
                    # handle list
                    elif isinstance(value, list):
                        if not dtype == "l":
                            raise osv.except_osv(_("Error"), _("Using list for non list type"))
                        
                        sub_ids = []
                        for list_value in value:
                            sub_id = get_id(list_value, attribs)
                            if sub_id:
                                sub_ids.append(sub_id)
                                
                        values[field] = [(6,0,sub_ids)]                
                        
                else:
                    values[field] = value
                    
            if values:           
                if obj_id:
                    model_obj.write(cr, uid, obj_id, values, context=context)
                else:
                    obj_id = model_obj.create(cr, uid, values, context=context)
            
            # validate, create uuid
            # use uuid passed in values if new
            uuid = mapping_obj.get_uuid(cr, uid, model, obj_id, uuid=uuid)
            
            # update updated dict
            if not changed_models is None: 
                changed_ids =changed_models.get(model, None)
                if changed_ids is None:
                    changed_ids = set()
                    changed_models[model]=changed_ids
                changed_ids.add(obj_id)
                    
            

        # finished!
        if return_id:
            res = obj_id
        else:
            res = uuid
            
        return res
 
    
    def jdoc_couchdb_before(self, cr, uid, config, context=None):
        return self.jdoc_couchdb_sync(cr, uid, config, context=context)
    
    def jdoc_couchdb_after(self, cr, uid, config, context=None):
        return self.jdoc_couchdb_sync(cr, uid, config, context=context)
       
    def jdoc_couchdb_sync(self, cr, uid, config, context=None):
        """ Sync with CouchDB
        
            @param  config: {
                        name: "fclipboard",
                        models : [{
                            "model" : xyz
                            "view" : "_jdoc_get_fclipboard"
                            "domain" : ...
                        }]
                    }
        """
        config_name = config.get("name")
        if not config_name:
            raise osv.except_osv(_("Error"), _("No configuration name passed"))
        
        param_obj = self.pool.get("ir.config_parameter")
        db_uuid = param_obj.get_param(cr, uid, "database.uuid")
                
        couchdb_url = param_obj.get_param(cr, SUPERUSER_ID, "couchdb_url", "http://localhost:5894", context=context)
        couchdb_user = param_obj.get_param(cr, SUPERUSER_ID, "couchdb_user", context=context)
        couchdb_password = param_obj.get_param(cr, SUPERUSER_ID, "couchdb_password", context=context)
          
        # READ CONFIG      
        client_db =  "%s-%s-%s" % (config_name, db_uuid, uid)
        client_uuid = "%s-%s" % (db_uuid, uid)
        client_passwd = self.pool["res.users"].read(cr, uid, uid, {"password"}, context=context)["password"]
        if not client_passwd:
            raise osv.except_osv(_("Error"), _("Unable to get user password. Deinstall 'auth_crypt' Module"))
        
        couchdb_public_url = param_obj.get_param(cr, uid, "couchdb_public_url")
        if not couchdb_public_url:
            raise osv.except_osv(_("Error"), _("No public couchdb url defined"))
        
        # READ/UPDATE USER
        server = couchdb.Server(couchdb_url)
        if couchdb_user and couchdb_password:
            server.resource.credentials = (couchdb_user, couchdb_password)
            
        user_db = server["_users"]
        user_id = "org.couchdb.user:%s" % client_uuid
        
        user_doc = user_db.get(user_id)
        if not user_doc:
            user_doc = {
                "_id" :  user_id,
                "name" : client_uuid,
                "type" : "user",
                "roles" : []
            }
        
        user_doc["password"] = client_passwd
        user_db.save(user_doc)
        
        # CREATE/OPEN DB
        db = None
        if not client_db in server:
            db = server.create(client_db)
        else:
            db = server[client_db]
            
        # UPDATE/DB SECURITY
        permissions = db.get("_security") or {"_id" : "_security" }
        members = permissions.get("members")
        names = members and members.get("names")
        if not names or not client_uuid in names:
            permissions["admins"] = {}
            permissions["members"] = {"names" : [client_uuid] }
            db.put(permissions) 
            db.commit()
                    
        # SYNC DB
        models = config.get("models")
        for model_config in models:
            config_uuid = "_local/lastsync_%s" % (self._get_uuid(model_config),)
                       
            # get lastsync
            lastsync = db.get(config_uuid)
            if not lastsync:
                lastsync = { "_id" : config_uuid }
                            
            # check if filter exist
            model_obj = self.pool[model_config["model"]]
            model_api  ="model_%s" % model_obj._table
            model_api_id = "_design/%s" % model_api
            model_doc = db.get(model_api_id)
            if not model_doc:
                model_doc = {
                    "_id" : model_api_id,
                    "filters" : {
                        "model" : "function(doc, req) { if (doc.fdoo__ir_model == '%s') { return true; } else { return false; } }" %  model_obj._name                
                    }
                }
                db.save(model_doc)
            
                          
            # get changes
            options = {
              "filter" : "%s/model" % model_api,
              "include_docs" : True,
              "since" : lastsync.get("seq",0)
            }           
           
            sync_config = dict(model_config)
            sync_config["lastsync"] = lastsync
            db_changeset = db.changes(**options)
            sync_config["changes"] = db_changeset["results"]
            sync_config["result_format"] = "doc"

            # first sync 
            sync_res = self.jdoc_sync(cr, uid, sync_config, context=context)
            lastsync.update(sync_res["lastsync"])
            
            # update documents
            changed_revs = set()
            changes = sync_res["changes"]
            
            # determine revision
            for change in changes:
                uuid = change.get("_id")
                if uuid:
                    doc = db.get(uuid)
                    if doc:
                        change["_rev"] = doc["_rev"]
                
            # update
            for update_res in db.update(changes):
                if update_res[0]:
                    changed_revs.add((update_res[1], update_res[2]))
                else:
                    raise osv.except_osv(_("Error"), _("Sync Error: %s") % update_res[2])
                        
            # second sync            
            if changed_revs:           
                # get changes
                options["since"] = lastsync["seq"]
                db_changeset = db.changes(**options)
                
                # filter changes
                db_changes = []
                for db_change in db_changeset["results"]:
                    already_processed = False
                    for rev_change in db_change["changes"]:
                        if (db_change["id"], rev_change["rev"]) in changed_revs:
                            already_processed = True
                            break
                        
                    if not already_processed:
                        db_changes.append(db_change)

                # only sync if changes                    
                if db_changes:
                    sync_config["lastsync"] = lastsync                    
                    sync_config["changes"] = db_changes
                    sync_res = self.jdoc_sync(cr, uid, sync_config, context=context)
                    lastsync.update(sync_res["lastsync"])
                
                # update seq
                lastsync["seq"] = max(lastsync["seq"], db_changeset["last_seq"])
                    
            # commit
            cr.commit() 
            # update lastsync
            db.save(lastsync)
            db.commit()
                        
        return {
            "url" : couchdb_public_url,
            "db" : client_db,
            "user" : client_uuid
        }
    
    @openerp.tools.ormcache()
    def _jdoc_def(self, cr, uid, model):
        return self._jdoc_create_def(cr, SUPERUSER_ID, self.pool[model])
    
    _description = "JSON Document Support"    
    _name = "jdoc.jdoc"

 
    