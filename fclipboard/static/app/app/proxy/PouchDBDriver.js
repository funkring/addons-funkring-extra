/*global Ext:false,PouchDB:false*,openerplib:false, console:false*/

Ext.define('Ext.proxy.PouchDBDriver',{
    alternateClassName: 'PouchDBDriver',
    
    singleton: true,
    
    config: {        
    },
                
    constructor: function(config) {
        this.callParent(arguments);
        this.databases = {};
    },
        
    /**
     * @return database
     */
    getDB: function(dbName) {    
        var self = this;
        var db = this.databases[dbName];
        if ( !db ) {
            db = new PouchDB(dbName, {size: 1000,
                                      adapter: 'websql' });
            self.databases[dbName] = db;
        }
        return db;
    },    
    
    resetDB: function(dbName, callback) {
        var self = this;
        var db = self.getDB(dbName);        
        delete self.databases[dbName];
        db.destroy(callback);
    },


    resetSync: function(dbName, callback) {
        var self = this;
        var db = self.getDB(dbName);
        
        db.get("_local/odoo_sync", function(err, doc) {
            if ( !err ) {
                db.remove(doc,function(err) {
                    callback(err);            
                });
            } else {
                callback();    
            }
        });        
    },
    
     /**
     * sync odoo store
     */
    syncOdooStore: function(con, db, store, syncUuid, res_model, domain, log, callback) {        
        var syncName = syncUuid+"-{"+res_model+"}";
        if ( domain ) {
            syncName = syncName + "-{"+JSON.stringify(domain)+"}";
        }
        
        var jdoc_obj = con.get_model("jdoc.jdoc");
        
        // delete docs
        
        // download docs
        
        // load changes
        
        // publish change
        
        // fetch changes
        var syncChanges = function(syncPoint) {
            db.changes({
                include_docs: true,
                since: syncPoint.seq,
                filter: function(doc) {
                    return doc.fdoo__ir_model === res_model;
                }
            }).then(function(changes) {
                var fields =  store.getModel().getFields().keys;
                jdoc_obj.exec("jdoc_sync", 
                     [
                       {
                        "model" : res_model,
                        "domain" : domain,
                        "fields" : fields,
                        "lastsync" : syncPoint,
                        "changes" : changes.results || {}
                       },
                       con.user_context
                     ],                       
                     null, 
                     function(err, res) {
                         if ( err ) {                                                             
                             log.error(err);
                         } else {
                             var server_changes = res.changes;
                             var server_lastsync = res.lastsync;
                             var pending_server_changes = server_changes.length+1;
                             
                             var docDeleted = 0;
                             var docUpdated = 0;
                             var docInserted = 0;
                                                          
                             var serverChangeDone = function(err) {
                                pending_server_changes--;
                                
                                if ( err ) {
                                    log.warning(err);
                                }
                                
                                if ( !pending_server_changes ) {
                                    // update sync data                                   
                                    db.info().then(function(res) {
                                        server_lastsync.seq = res.update_seq;
                                        db.get("_local/odoo_sync", function(err, doc) {
                                           
                                           // new sync point 
                                           if (err) {
                                              doc={_id: "_local/odoo_sync"};
                                           } 
                                           
                                           // log statistik
                                           log.info("Synchronisation für <b>" + res_model + "</b> ausgeführt </br> " +
                                                    "<pre>" + 
                                                    "    " + docDeleted + " Dokumente gelöscht" +
                                                    "    " + docInserted + " Dokumente eingefügt" +
                                                    "    " + docUpdated + " Dokumente aktualisiert" +
                                                    "</pre>");
                                           
                                           doc[syncName]=server_lastsync;
                                           db.put(doc, function(err) {                                              
                                               callback(err, server_lastsync);                                               
                                           });
                                           
                                        });
                                    });           
                                }                              
                                 
                             };
                             
                             // iterate changes
                             Ext.each(server_changes, function(server_change) {
                                // handle delete
                                if ( server_change.deleted ) {
                                    
                                    // lösche dokument
                                    db.get(server_change.id, function(err, doc) {
                                         if ( !err ) {
                                            doc._deleted=true; 
                                            docDeleted++;                                         
                                            //log.info("Dokument " + server_change.id + " wird gelöscht");
                                            db.put(doc, serverChangeDone); //<- decrement pending operations
                                         } else {
                                            //log.warning("Dokument " + server_change.id + " nicht vorhanden zu löschen");
                                            // decrement operations
                                            serverChangeDone(); 
                                         }                                      
                                    });
                                    
                                //handle update
                                } else if ( server_change.doc ) {
                                    db.get(server_change.id, function(err, doc) {
                                         if ( err ) {
                                             docInserted++;
                                             //log.warning("Dokument " + server_change.id + " wird neu erzeugt");
                                         } else {
                                             docUpdated++;                                         
                                             server_change.doc._rev = doc._rev;
                                             //log.info("Dokument " + server_change.id + " wird aktualisiert");
                                         }
                                         db.put(server_change.doc, serverChangeDone); //<- decrement pending operations                                         
                                    });
                                }
                             });
                             
                             // changes done
                             serverChangeDone();
                         }
                     });                                
            }).catch(function(err) {
                log.error(err);
            });
        };
        
        
        // get last syncpoint or create new
        db.get("_local/odoo_sync", function(err, doc) {
            var syncpoint;
             
            if (!err) {
                syncpoint = doc[syncName];
            }
            
            if ( !syncpoint ) {
                syncpoint = {
                    "date" : null,
                    "sequence" : 0
                };
            }
            
            syncChanges(syncpoint);     
            
        });
      
    },
    
    /**
     * sync with odoo
     */
    syncOdoo: function(credentials, stores, log, callback) {
         var self = this;
         var con = openerplib.get_connection(credentials.host, 
                                            "jsonrpc", 
                                            parseInt(credentials.port,10), 
                                            credentials.db, 
                                            credentials.user, 
                                            credentials.password);
                           
         var syncuuid = "odoo_sync_{"+credentials.user + "}-{" + credentials.host + "}-{" + credentials.port.toString() + "}-{" + credentials.user +"}";
                 
         if ( !log ) {
             log = function() {
                 this.log = function(message) {
                     console.log(message);
                 };
                 this.error = this.log;
                 this.warning = this.log;
                 this.debug = this.log;
                 this.info = this.log;
             };
         }
        
         // prepare store sync
         var syncStore = function(store, callback) {
            var proxy = store.getProxy();
            if ( proxy instanceof Ext.proxy.PouchDB ) {                
                var domain = [];
                var res_model = null;
                
                // search model and domain
                Ext.each(proxy.getDomain(), function(val) {
                   if ( Ext.isArray(val) && val.length === 3 && ( val[0].indexOf("fdoo__") === 0 || val[0].indexOf("_") === 0 ) ) {                        
                       if (val[0] == "fdoo__ir_model" && val[1] === "=") {
                           res_model = val[2];
                       } 
                   } else {
                       domain.push(val);
                   } 
                });
            
                
                if ( res_model) {
                    // get database                    
                    var db = self.getDB(proxy.getDatabase());
                    // sync odoo store
                    self.syncOdooStore(con, db, store, syncuuid, res_model, domain, log, function(err, res) {
                        callback(err, res);
                    });
                }
            }
         };
        
                     
         // start sync                    
         con.authenticate( function(err)  {
             if (err) {
                 log.error(err);
             } else {
                 log.info("Authentifizierung erfolgreich");       
                 
                 var storeIndex = -1;
                 var storeLength = stores.length;
                 
                 // handle stores
                 var storeCallback = function(err, res) {
                     if ( ++storeIndex < storeLength ) {
                        syncStore(stores[storeIndex], storeCallback);
                     } else {
                        callback(err, res);                            
                     }
                 };
                 
                 storeCallback();
                    
             }
         } );
        
    }
    
});