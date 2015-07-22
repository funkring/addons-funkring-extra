/*global Ext:false, PouchDB:false, PouchDBDriver:false, openerplib:false */
Ext.define('Fclipboard.controller.Main', {
    extend: 'Ext.app.Controller',
    requires: [
        'Ext.field.Hidden',
        'Ext.field.Select',
        'Ext.form.FieldSet',
        'Ext.proxy.PouchDBDriver'
    ],
    config: {
        refs: {
            mainView: '#mainView',
            mainPanel: '#mainPanel',
            partnerList: '#partnerList',
            itemList: '#itemList'
        },
        control: {
            'button[action=editItem]': {
                tap: 'editCurrentItem'   
            },
            'button[action=newItem]': {
                tap: 'newItem'
            },
            'button[action=saveView]': {
                tap: 'saveRecord'
            },         
            'button[action=newPartner]': {
                tap: 'newPartner'
            },
            'button[action=parentItem]': {
                tap: 'parentItem'  
            },
            'button[action=sync]': {
                tap: 'sync'  
            },
            'button[action=editConfig]' : {
                tap: 'editConfig'
            },
            'button[action=deleteRecord]' : {
                tap: 'deleteRecord'  
            },
            'button[action=resetSync]' : {
                tap: 'resetSync'  
            },
            mainView: {
                createItem: 'createItem',
                parentItem: 'parentItem'
            },
            partnerList: {
                select: 'selectPartner'
            },
            itemList: {
                select: 'selectItem'
            }
        }
    },
    
    init: function() {
        var self = this;        
        self.callParent(arguments);
        self.path = [];  
        self.syncActive = false;
    },

    newItem: function() {
        this.getMainView().showNewItemSelection();
    },
    
    createItem: function(view, item_type) {
        var self = this;
        var mainView = self.getMainView();
        var parentRec = mainView.getRecord();
        
//         var newItem = Ext.create('Fclipboard.model.Item',
//                 {'type': item_type || 'directory',
//                  'parent_id' : record !== null ? record.getId() : null
//                 });
       
         // new view
         
        var itemForm = Ext.create("Fclipboard.view.FormView",{
            title: 'Neues Dokument',        
            xtype: 'formview',            
            saveHandler: function(view, callback) {
                // get values
                var values = view.getValues();
                values.fdoo__ir_model = 'fclipboard.item';
                values.dtype = item_type || 'd';
                values.parent_id = parentRec !== null ? parentRec.getId() : null;
                values.is_template = false;
                            
                // get template
                var template_id = values.template_id;
                delete values.template_id;
                
                var db = self.getDB();
                db.post(values, function(err, res) {
                    if( !err ) {
                       if ( template_id ) {
                           // clone template
                           var mbox = Ext.Msg.show({
                                title: "Neues Dokument",
                                message: "Erstelle Struktur...",
                                buttons: []
                           });
                           PouchDBDriver.deepCopy(db, res.id, template_id, "parent_id", {is_template:false}, function(err,res) {
                              mbox.hide();
                              callback(err, res);
                           });
                           return;       
                        } 
                    } 
                    callback(err, res);                    
                });
            }, 
            items: [{
                        xtype: 'textfield',
                        name: 'name',
                        label: 'Name',
                        required: true
                    },
                    {
                        xtype: 'listselect',
                        autoSelect: false,
                        name: 'template_id',
                        label: 'Vorlage',
                        navigationView: self.getMainView(),
                        store: 'ItemTemplateStore',
                        displayField: 'name'                
                    }                    
                   ],
            editable: true,
            deleteable: true
        });
        self.getMainView().push(itemForm);
    },
    
    editCurrentItem: function() {
        var mainView = this.getMainView();
        var record = mainView.getRecord();
        if ( record ) {
            this.editItem(mainView.getRecord());
        } 
    },
           
    editItem: function(record) {        
        var self = this;
            
        // new view
        self.getMainView().push({
            title: record.data.name,
            xtype: 'formview',
            record: record,
            items: [{
                        xtype: 'textfield',
                        name: 'name',
                        label: 'Name',
                        required: true
                    }],
            editable: true,
            deleteable: true
        });
        
    },
        
    newPartner: function() {        
        var newPartner = Ext.create('Fclipboard.model.Partner',{});       
        this.editPartner(newPartner);
    },
    
    editPartner: function(record) {
        var self = this;       
        self.getMainView().push({
            title: 'Partner',
            xtype: 'partnerform',
            record: record,
            deleteable: true
        });
    },
    
    editConfig: function(record) {
        var self = this;
        var db = PouchDBDriver.getDB('fclipboard');
        
        var load = function(doc) {
            var configForm = Ext.create("Fclipboard.view.ConfigView",{
                title: 'Konfiguration',
                xtype: 'configform',
                saveHandler: function(view, callback) {
                    var newValues = view.getValues();
                    newValues._id = '_local/config';
                    db.put(newValues).then( function() {
                         callback();
                    });
                }
            });

            configForm.setValues(doc);                    
            self.getMainView().push(configForm);
        };
        
        db.get('_local/config').then( function(doc) {
            load(doc);
        }).catch(function (error) {
            load({});
        });        
        
    },
    
    saveRecord: function() {
        var self = this;
        var mainView = self.getMainView();
        var view = mainView.getActiveItem();
        
        // check for save handler
        var saveHandler = null;
        try { 
            saveHandler = view.getSaveHandler();
        } catch (err) {            
        }        
        
        var reloadHandler = function(err) {
            mainView.pop();
            mainView.loadRecord();
        };
        
        // if save handler exist use it
        if ( saveHandler ) {
            saveHandler(view, reloadHandler);          
        } else {
            // otherwise try to store record
            var record = view.getRecord();
            if ( record !== null ) {
                var values = view.getValues(); 
                record.set(values);
                record.save();
            }
            reloadHandler();
        }
    },
    
    deleteRecord: function() {
        var self = this;
        var record = self.getMainView().getActiveItem().getRecord();

        if ( record !== null ) {
            Ext.Msg.confirm('Löschen', 'Soll der ausgewählte Datensatz gelöscht werden?', function(choice)
            {
               if(choice == 'yes')
               {                    
                   var db = self.getDB();
                   db.get( record.getId() ).then( function(doc) { 
                        doc._deleted=true;
                        db.put(doc).then( function() {
                           self.getMainView().leave();
                        });
                   });
                       
               }         
            });
        }
        
    },
        
    
    selectPartner: function(list, record) {
        list.deselect(record);
        this.editPartner(record);
        return false;                                
    },
    
    selectItem: function(list, record) {
        list.deselect(record);
        var mainView = this.getMainView();
        
        var lastRecord = mainView.getRecord();
        if (lastRecord !== null) {
            this.path.push(lastRecord);
        }
        
        mainView.setRecord(record);
        mainView.loadRecord();
        return false;
    },
    
    parentItem: function() {
        var parentRecord = null;
        if ( this.path.length > 0 ) {
            parentRecord = this.path.pop();           
        } 
        var mainView = this.getMainView();
        mainView.setRecord(parentRecord);
        mainView.loadRecord();
    },

    getDB: function() {
        var db = PouchDBDriver.getDB('fclipboard');
        return db;
    },

    getLog: function() {
        return Ext.getStore("LogStore");
    },
    
    refresh: function() {
        this.getMainView().loadRecord();  
    },

    sync: function() {        
        var self = this;
                
        if ( !self.syncActive ) {
            self.syncActive = true;
        
            // start dialog
            var mbox = Ext.Msg.show({
                title: "Synchronisation",
                message: "Synchronisiere...",
                buttons: []
            });
            
            // clear log
            var log = self.getLog();
            log.removeAll();
            
            // define callback
            var callback = function(err) {
                if (err) {
                     log.error(err);
                     log.warning("<b>Synchronisation mit Fehlern abgeschlossen!</b>");
                } else {
                     log.info("<b>Synchronisation beendet!</b>");
                }
                
                mbox.hide();
                self.refresh();
                self.syncActive = false;
            };
            
            // fetch config and sync
            var db = self.getDB();
            db.get('_local/config', function(err,config) {
                if ( !err ) {                    
                    log.info("Hochladen auf <b>" + config.host + ":" + config.port + "</b> mit Benutzer <b>" + config.user +"</b>");
                    
                    // reload after sync
                    PouchDBDriver.syncOdoo(config, [Ext.getStore("PartnerStore"),
                                                    Ext.getStore("BasicItemStore")
                                                   ], log, callback );
                } else {
                    callback(err);
                }                
            });
        }  
       
    },
    
    resetSync: function() {
        var self = this;
        var log = this.getLog();
        log.removeAll();
        
        var syncPopover = Ext.create('Ext.Panel',{
            title: "Zurücksetzen",
            floating: true,
            hideOnMaskTap : true,
            modal: true,
            width: '300px',
            defaults: {
                defaults: {
                    xtype: 'button',
                    margin: 10,
                    flex : 1
                } 
            },                      
            items: [
                {
                    xtype: 'fieldset',
                    title: 'Zurücksetzen',
                    items: [
                         {
                             text: 'Synchronisation',
                             handler: function() {
                                 PouchDBDriver.resetSync('fclipboard', function(err) {
                                    if (err) {
                                        log.error(err);
                                    } else {
                                        log.info("Sync-Daten zurückgesetzt!");                                      
                                    }         
                                    
                                    self.refresh();
                                    syncPopover.hide();                           
                                });
                             }                  
                         },
                         {
                             text: 'Datenbank',
                             handler: function() {
                                  Ext.Msg.confirm('Löschen', 'Soll die Datenbank wirklich gelöscht werden?', function(choice)
                                  {
                                       var callback = function(err) {
                                           if (err) {
                                              log.error(err); 
                                           }
                                           self.refresh();
                                           syncPopover.hide();
                                           log.info("Datenbank zurückgesetzt!");
                                       };    
                                                                
                                       if( choice == 'yes' ) {
                                             self.getDB().get('_local/config', function(err, doc) {
                                                PouchDBDriver.resetDB('fclipboard', function(err) {
                                                    if ( doc ) {
                                                        delete doc._rev;
                                                        self.getDB().put(doc, function(err) {
                                                            callback(err);                                                               
                                                        });                                                                
                                                    } else {
                                                        callback(err);
                                                    }
                                                });    
                                                
                                            });                                           
                                       } else {
                                           syncPopover.hide();
                                       }
                                  });                                 
                             }
                         }
                    ]            
                }
            ]            
        });
        
        syncPopover.show('pop');        
    }
    
    
    
});