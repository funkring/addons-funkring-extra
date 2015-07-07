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
import openerp
import uuid

import simplejson
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
            field_type = field_obj._type
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
    
    
    def _jdoc_update(self, cr, uid, ids, delete=False, context=None):
        log_obj = self.pool["jdoc.log"]
        for obj in self.browse(cr, SUPERUSER_ID, ids, context=context):            
            new_doc = self._jdoc_get(cr, SUPERUSER_ID, obj, context=context)
            if delete:
                new_doc[META_DELETE]=True          
            
            uuid = new_doc[META_ID]
            cur_doc = log_obj._get_document(cr, SUPERUSER_ID, uuid, context=context)
            
            changed = True
            cur_rev = None
            
            if cur_doc:      
                cur_rev = cur_doc.get(META_REV)          
                changed = util.mergeDict(cur_doc, new_doc)                    
            else:
                cur_doc = new_doc
                
            if changed:                
                cur_rev = log_obj._next_rev(cr, SUPERUSER_ID, cur_rev) 
                cur_doc[META_REV] = cur_rev
                json_doc = simplejson.dumps(cur_doc)
                
                log_obj.create(cr, SUPERUSER_ID, {
                        "uuid" : uuid,
                        "rev" : cur_rev,
                        "doc" : json_doc,
                        "deleted" : delete,
                        "editor_uid" : uid
                })
                
    def _jdoc_get(self, cr, uid, obj, refonly=False, emptyValues=True, context=None):
        if not obj:
            return False
        
        mapping_obj = self.pool.get("res.mapping")       
        doc_uuid = mapping_obj.get_uuid(cr, uid, obj._name, obj.id)
        if refonly:
            return doc_uuid
      
        definition = self._jdoc_def(cr, uid, obj._name)
        model = definition["model"]        
               
        res = {META_ID : doc_uuid,
               META_MODEL : model}
        
        fields = definition["fields"]
        for name, attrib in fields.items():
            # check for hidden attribute
            if attrib.get("hidden"):
                continue
            # get type
            dtype = attrib["dtype"]
            # reset value
            value = None
            
            # evaluate composite, reference and list type
            if dtype in ("c","r","l"):
                # get model
                if dtype in ("c","r"):
                    dtype_obj = getattr(obj, attrib["name"])
                    if dtype_obj:                        
                        value = self._jdoc_get(cr, uid, dtype_obj, refonly=(dtype=="r"), emptyValues=emptyValues, context=context)
                # handle list type 
                else:
                    dtype_objs = getattr(obj, attrib["name"])
                    for dtype_obj in dtype_objs:
                        list_value = self._jdoc_get(cr, uid, dtype_obj, refonly=(attrib.get("ltype")=="r"), emptyValues=emptyValues, context=context)
                        if list_value:
                            if value is None:
                                value = []
                            value.append(list_value)
            
            # evaluate primitive values
            else:
                value = getattr(obj, attrib["name"])
               
            if emptyValues or value:
                res[name]=value    
                
        res["write_date"]=obj.write_date    
        return res
    
    def jdoc_sync(self, cr, uid, changes, context=None):
        """
        jdoc_sync
        @param changes: changeset to sync 
                          { "model" : xyz
                            "date" : "2014-01-01 00:00:01",   # date  
                            "id"  :  3                        # highest database id from last sync from change target (odoo),
                            "seq" :  1                        # highest sequence from change source for the last sync
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
        
        """
        
        mapping_obj = self.pool["res.mapping"]
        
        in_list = changes.get("changes")
        model = changes["model"]
        model_obj = self.pool[model] 

        lastsync = changes.get("lastsync") or {}
        last_date = lastsync.get("date",None)
        seq = lastsync.get("seq",0)
        
        #conflictDocs = {}
        
        # process input list
        if in_list:
            for change in in_list:
                doc = change["doc"]
                self.jdoc_put(cr, uid, doc, context=context)
                seq = max(change["seq"], seq)
                
        
        # process output list        
        out_list = []        
        
        # build search domain
        search_domain = []
        del_search_domain = [("res_model","=",model),("active","=",False)]
      
        # only sync with last date  
        if last_date:
            search_domain.append(("write_date",">",last_date))
            del_search_domain.append(("write_date",">",last_date))
            
        
        #
        # search changes
        #
        
        out_ids = model_obj.search(cr, uid, search_domain, order="write_date asc, id asc")
        if out_ids:
            
            # get last change date
            cr.execute("SELECT MAX(write_date) FROM %s WHERE id IN %%s " % model_obj._table, (tuple(out_ids),))
            res = cr.fetchall()
            if res:
                last_date = max(last_date, res[0])
            
            # create docs
            for obj in model_obj.browse(cr, uid, out_ids, context=context):
                doc = self._jdoc_get(cr, uid, obj, emptyValues=False, context=context)
                if doc:
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
            res = cr.fetchall()
            if res:            
                last_date = max(last_date, res[0])
                
            # get uuids
            for out_deleted_val in out_deleted_vals:
                if not last_date or out_deleted_val["write_date"] >= last_date:
                    last_date = out_deleted_val["write_date"]
                
                # uuid 
                uuid = out_deleted_val["uuid"]
                out_list.append({
                   "id" : uuid,
                   "deleted" : True                                 
                 })
        
        
        
        return {
           "model" : model,
           "lastsync" : {
                           "date" : last_date,
                           "seq" : seq
                        },
           "changes" : out_list
        }
    
    def jdoc_get(self, cr, uid, uuid, res_model=None, refonly=False, emptyValues=False, name=None, context=None):
        mapping_obj = self.pool["res.mapping"]
        obj = mapping_obj._browse_mapped(cr, uid, uuid, res_model=res_model, name=name, context=None)
        if not obj:
            return False
        return self._jdoc_get(cr, uid, obj, refonly=refonly, emptyValues=emptyValues, context=context)
    
    def jdoc_put(self, cr, uid, doc, return_id=False, context=None):
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
        
        # check for delete
        if doc.get("_deleted"):
            mapping_obj.unlink_uuid(cr, uid, uuid, res_model=model, context=context)
            obj_id = False
        
        # otherwise update        
        else:
        
            definition = self._jdoc_def(cr, uid, obj._model._name)
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
                if dtype in ("c","r","l"):
                    # handle empty value
                    if not value:
                        if dtype == "l":
                            values[field] = [(6,0,[])]
                        else:
                            value[field] = None
                    # handle list
                    elif isinstance(value, list):
                        if not dtype == "l":
                            raise osv.except_osv(_("Error"), _("Using list for non list type"))
                        
                        sub_ids = []
                        for list_value in value:
                            if not list_value:
                                continue
                            
                            sub_id = None
                            
                            # check uuid
                            if isinstance(list_value, basestring):
                                sub_id = mapping_obj.get_id(cr, uid, None, list_value)
                            
                            # check reference or document
                            elif isinstance(list_value, dict):                                                        
                                if isReference(list_value):
                                    # get reference
                                    sub_id = mapping_obj.get_id(cr, uid, list_value.get(META_MODEL), list_value)
                                else:
                                    # update document and get reference
                                    sub_id = self.jdoc_put(cr, uid, list_value, return_id=True, context=context)
                                
                            if sub_id:
                                sub_ids.append(sub_id)
                                
                        values[field] = [(6,0,sub_ids)]                
                        
                else:
                    values[field] = value
                    
            if values:           
                if obj:
                    model_obj.write(cr, uid, obj.id, values, context=context)
                else:
                    obj_id = model_obj.create(cr, uid, values, context=context)
            
            # validate, create uuid
            # use uuid passed in values if new
            uuid = mapping_obj.get_uuid(cr, uid, model, obj_id, uuid=uuid)

        # finished!
        if return_id:
            res = obj_id
        else:
            res = uuid
            
        return res
    
    @openerp.tools.ormcache()
    def _jdoc_def(self, cr, uid, model):
        return self._jdoc_create_def(cr, SUPERUSER_ID, self.pool[model])
    
    _description = "JSON Document Support"    
    _name = "jdoc.jdoc"
    


 
    