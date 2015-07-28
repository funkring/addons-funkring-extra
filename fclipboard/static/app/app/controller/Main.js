/*global Ext:false, PouchDB:false, PouchDBDriver:false, openerplib:false, futil:false*/
Ext.define('Fclipboard.controller.Main', {
    extend: 'Ext.app.Controller',
    requires: [
        'Ext.field.Hidden',
        'Ext.field.Select',
        'Ext.form.FieldSet',
        'Ext.proxy.PouchDBDriver',
        'Ext.util.DelayedTask',
        'Fclipboard.view.PricelistView'
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
                //tap: 'testNumberInput'
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
                parentItem: 'parentItem',
                searchPartner: 'searchPartnerDelayed',
                searchItem: 'searchItemDelayed',
                doDataReload: 'dataReload',
                editItem: 'editItem',
                addProduct: 'addProduct',
                showNumberInput: 'showNumberInput'
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
        self.partnerSearch = null;
        self.itemSearch = null;
        self.pricelist = null;
                
        self.partnerSearchTask = Ext.create('Ext.util.DelayedTask', function() {
            self.searchPartner();
        });
           
        self.itemSearchTask = Ext.create('Ext.util.DelayedTask', function() {
            self.searchItems();
        });
        
    },
    
    searchDelayed: function(task) {
        task.delay(500);
    },
    
    searchPartnerDelayed: function(text) {
        this.partnerSearch = text;
        this.searchDelayed(this.partnerSearchTask);
    },
    
    searchItemDelayed: function(text) {
        this.itemSearch = text;
        this.searchDelayed(this.itemSearchTask);    
    },   
    
    searchPartner: function(callback) {
       var partnerStore = Ext.StoreMgr.lookup("PartnerStore");
       
       var options = {   
           params : {
              limit: 100
           } 
       };
       
       if (callback) {
           options.callback = callback; 
       }
       
       if ( !Ext.isEmpty(this.partnerSearch) ) {
         options.filters = [{
                   property: 'name',
                   value: this.partnerSearch
         }];
       }   
       
       partnerStore.load(options);
    },
    
    searchItems: function(callback) {
       var record = this.getMainView().getRecord();
       var domain = [['parent_id','=',record !== null ? record.getId() : null]];
             
       var options = {
           params : {
               domain : domain
           }
       };
       
       if ( callback ) {
            // check for callback
           var afterLoadCallbackCount = 0;
           var afterLoadCallback = function() {
               if ( ++afterLoadCallbackCount >= 2 ) {
                   callback();
               }
           };
           options.callback=afterLoadCallback;
       }
              
       if ( !Ext.isEmpty(this.itemSearch) ) {
           options.filters = [{
              property: 'name',
              value: this.itemSearch   
           }];
       }
       
       // load data
       var itemStore = Ext.StoreMgr.lookup("ItemStore");
       itemStore.load(options);
       
       // load header item
       var headerItemStore =  Ext.StoreMgr.lookup("HeaderItemStore");
       headerItemStore.load(options);
    },
  
    createItem: function(view) {
        var self = this;
        var mainView = self.getMainView();
        var parentRec = mainView.getRecord();
        
       
         // new view
         
        var itemForm = Ext.create("Fclipboard.view.FormView",{
            title: 'Neues Dokument',        
            xtype: 'formview',            
            saveHandler: function(view, callback) {
                // get values
                var values = view.getValues();
                values.fdoo__ir_model = 'fclipboard.item';
                values.section = 20;
                values.dtype = null;
                values.parent_id = parentRec !== null ? parentRec.getId() : null;
                values.template = false;
                            
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
                           var newDocId = res.id;
                           PouchDBDriver.deepCopy(db, res.id, template_id, "parent_id", {template:false}, function(err,res) {
                              mbox.hide();
                              if (!err && template_id) {
                                // open view if template was defined
                                callback(err,function() {
                                   var item = Ext.getStore("ItemStore").getById(newDocId);
                                   if ( item ) {
                                        self.getMainView().fireEvent("editItem",item);
                                        //self.editItem(item);                                        
                                   }
                                });
                              } else {
                                // do normal callback
                                callback(err);
                              }
                           });
                           return; // no callback       
                        } 
                    } 
                    callback(err);                    
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
      
    loadRecord: function(callback) {
        var self = this;

        // init
        self.partnerSearchTask.cancel();
        self.itemSearchTask.cancel();       
        self.partnerSearch = null;
        self.itemSearch = null;
        self.pricelist = null;
         
        // validate components
        self.getMainView().validateComponents();
        
        var db = self.getDB();
        var record = self.getMainView().getRecord();
                
        // check for callback
        var afterLoadCallbackCount = 0;
        var afterLoadCallback = function() {
            if ( ++afterLoadCallbackCount >= 2 ) {                
                if ( record ) {
                    // search pricelist
                    PouchDBDriver.findFirstChild(self.getDB(), record.getId(), "parent_id", [["rtype","=","pricelist_id"]], function(err, doc) {
                       // check error or no pricelist found
                       if ( err || !doc || !doc.pricelist_id ) {                       
                          if ( callback ) {  
                              callback(err);
                          }
                       } else {
                          db.get(doc.pricelist_id).then(function(pricelist) {
                              // set pricelist
                              self.pricelist = pricelist;                              
                              if ( callback ) {
                                 callback();
                              }  
                          }).catch(function(err) {
                              if ( callback ) {
                                 callback(err);
                              } 
                          });
                       } 
                    });
                
                // if no record search no pricelist
                } else if ( callback ) {
                    callback();
                }
            }
        };
        
        // load data
        self.searchItems(afterLoadCallback);
        self.searchPartner(afterLoadCallback);       
    },
    
    editCurrentItem: function() {
        var mainView = this.getMainView();
        var record = mainView.getRecord();
        if ( record ) {
            this.editItem(mainView.getRecord());
        } 
    },
           
    editItem: function(record) {
        // edit only if non type
        if ( record.dtype ) {
            return;
        }

        var self = this;
        var db = self.getDB();
        var store = Ext.getStore("HeaderItemStore");
        
        store.load({
            params : {
               domain : [["parent_id","=",record.getId()]]
            },    
            scope: self,
            callback: function(itemRecords, operation, success) {
                if (success) {
                
                    var items = [{
                        xtype: 'textfield',
                        name: 'name',
                        label: 'Name',
                        required: true
                    }];
                    
                    var values = {
                        name: record.getData().name 
                    };
                    
                    
                    // check show view funciton
                    var showViewBarrier = new futil.barrier( function() {
                    
                        var view = Ext.create("Fclipboard.view.FormView", {
                            title: values.name,
                            record: record,
                            items: items,
                            editable: true,
                            deleteable: true,
                            saveHandler: function(view, callback) {
                            
                                            var newValues = view.getValues();
                                            var db = self.getDB();
                                            
                                            db.get(record.getId()).then(function(doc) {     
                                                                                   
                                                //field update
                                                var updateItemIndex=0;
                                                var updateItem = function() {
                                                    if ( updateItemIndex < itemRecords.length ) {
                                                        
                                                        // get field data
                                                        var itemRecord = itemRecords[updateItemIndex++];
                                                        var itemName = itemRecord.getId();
                                                        var field = view.query("field[name='"+itemName+"']");
                                                        
                                                        // only update if field exist
                                                        if ( field.length > 0 ) {
    
                                                            db.get(itemName).then(function(doc) {
                                                                var newValue = newValues[itemName];
                                                                var valueName = field[0].valueName;
                                                                doc[valueName]=newValue;
                                                                
                                                                // update 
                                                                db.put(doc).then(function(res) {
                                                                    updateItem();
                                                                }).catch(function(err) {
                                                                    callback(err);
                                                                });     
                                                                                                                   
                                                            }).catch(function(err) {
                                                                callback(err);      
                                                            });
                                                            
                                                        }
                                                    } else {
                                                        callback();
                                                    }
                                                };
                                            
                                                // update name
                                                doc.name = newValues.name;
                                                db.put(doc).then(function(res) {
                                                    updateItem();
                                                }).catch(function(err) {
                                                    callback(err);
                                                });
                                            }).catch(function(err) {
                                                callback(err);
                                            });
                                        }
                        });
                        
                        // set values
                        view.setValues(values);
                        
                        // show view
                        self.getMainView().push(view);      
                    });        
                    
                    // build mask                    
                    Ext.each(itemRecords, function(itemRecord) {                        
                        var name = itemRecord.getId();
                        var data = itemRecord.getData();
                        var dtype = data.dtype;
                        var field = null;
                        
                        if ( dtype ) {
                            switch (dtype) {                                
                                case "i":
                                    field = {
                                        xtype: 'numberfield',
                                        valueName: "vali"
                                    };
                                    values[name]=data.vali;
                                    break;
                                case "f":
                                    field = {
                                        xtype: 'textfield',
                                        valueName: "valf"
                                    };
                                    values[name]=data.valf;
                                    break;
                                case "c":
                                    field = {
                                        xtype: 'textfield',
                                        valueName: "valc"
                                    };
                                    values[name]=data.valc;
                                    break;
                                case "t":
                                    field = {
                                        xtype: 'textareafield',
                                        valueName: "valt"
                                    };
                                    values[name]=data.valt;
                                    break;
                                case "b":
                                    field = {
                                        xtype: 'togglefield',
                                        valueName: "valb"
                                    };
                                    values[name]=data.valb;
                                    break;    
                                case "d":
                                    field = {
                                        xtype: 'datepickerfield',
                                        valueName: "vald"
                                    };
                                    values[name]=data.vald;
                                    break; 
                            }
                            
                        } else { 
                            var rtype = data.rtype;
                            switch (rtype) {
                                case "partner_id":
                                    field = {
                                        xtype: 'listselect',
                                        autoSelect: false,
                                        navigationView: self.getMainView(),
                                        store: 'PartnerStore',
                                        displayField: 'name',
                                        valueName: 'partner_id',
                                        pickerToolbarItems: [{
                                            xtype: 'button',
                                            iconCls: 'add',
                                            align: 'right',
                                            action: 'newPartner'      
                                        }]
                                    };
                                    values[name]=data.partner_id;
                                    break;
                                    
                                case "pricelist_id":
                                    field = {
                                        xtype: 'listselect',
                                        autoSelect: false,
                                        navigationView: self.getMainView(),
                                        store: 'PricelistStore',
                                        displayField: 'name',
                                        valueName: 'pricelist_id'           
                                    };
                                    values[name]=data.pricelist_id;
                                    break;
                            }
                        }
                        
                        // finalize field
                        if ( field ) {
                            field.name = name;
                            field.label = data.name;
                            field.item = data;
                            
                            if ( data.required ) {
                                field.required = true;
                            }
                            items.push(field);
                            
                            // check if is an model value                                                    
                            if (field.xtype == 'listselect' && values[name]) {
                                var store = Ext.getStore(field.store);
                                var proxy = store.getProxy();
                                if ( proxy instanceof Ext.proxy.PouchDB ) {
                                    // increment barrier
                                    showViewBarrier.add();
                                    proxy.readDocument(values[name], function(err, rec) {
                                        values[name] = rec;
                                        // test barrier
                                        showViewBarrier.test();
                                    });                            
                                }
                            }
                               
                        }
                    }); 
                    
                    // test barrier
                    showViewBarrier.test();
                }
            }
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
        var db = self.getDB();
        
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
       
        // check fields for errors
        
        var isValid = true;
        var fields = view.query("field");
        
        for (var i=0; i<fields.length; i++) {
            var field = fields[i];
            var value = field.getValue();
            
            if ( value && typeof value == "string") {
                value = field.getValue().trim();
            }
            
            if ( field.getRequired() && (value === null || value === "") )  {
                 fields[i].addCls('invalidField');
                 isValid = false;
            } else {
                fields[i].removeCls('invalidField');
            }
        }
        
        if ( !isValid ) {
            return;
        }
        
        // check for save handler
        var saveHandler = null;
        try { 
            saveHandler = view.getSaveHandler();
        } catch (err) {            
        }        
        
        var reloadHandler = function(err, callback) {
            mainView.pop();
            self.loadRecord(callback);
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
    },
    
    selectItem: function(list, record) {
        list.deselect(record);
        var mainView = this.getMainView();
        
        var lastRecord = mainView.getRecord();
        if (lastRecord !== null) {
            this.path.push(lastRecord);
        }
        
        mainView.setRecord(record);
        this.loadRecord();
    },
    
    parentItem: function() {
        var parentRecord = null;
        if ( this.path.length > 0 ) {
            parentRecord = this.path.pop();           
        } 
        var mainView = this.getMainView();
        mainView.setRecord(parentRecord);
        this.loadRecord();
    },
    
    newItem: function() {      
        var self = this;
        var mainView = self.getMainView();
        var record = mainView.getRecord();
    
        if ( !record || !self.pricelist ) {        
            self.createItem();
        } else {
        
            var itemStore = Ext.getStore("ItemStore");
            var productItems = itemStore.queryBy(function(record) {
                if ( record.getRtype() == "product_id") {
                    return true;
                }
                return false;
            });
            
            if ( productItems.length === 0 ) {
                 var newItemPicker = Ext.create('Ext.Picker',{
                    doneButton: 'Erstellen',
                    cancelButton: 'Abbrechen',
                    modal: true,
                    slots:[{
                        name: 'option',
                        title: 'Element',
                        displayField: 'name',
                        valueField: 'option',
                        data: [
                            {
                                "name" : "Produkt",
                                "option" : 1
                            },
                            {
                                "name" : "Ordner",
                                "option" : 0  
                            }
                        ]
                    }],               
                    listeners: {
                        change: function(picker,button) {
                            var option = picker.getValue().option;
                            if ( option === 1) {
                                self.addProduct();                                
                            } else {
                                self.createItem();
                            }
                        }
                    } 
                });
                
                Ext.Viewport.add(newItemPicker);
                newItemPicker.show();
                
            } else {
                self.addProduct();
            }
            
        }  
    },

    getDB: function() {
        var db = PouchDBDriver.getDB('fclipboard');
        return db;
    },

    getLog: function() {
        return Ext.getStore("LogStore");
    },
    
    dataReload: function() {
        this.loadRecord();  
    },
    
    addProduct: function() {
        var self = this;
        if ( self.pricelist ) {
            var view = Ext.create("Fclipboard.view.PricelistView", {
                           title: self.pricelist.name,
                           pricelist: self.pricelist
                       });
            self.getMainView().push(view);         
        }
    },

    sync: function() {        
        var self = this;
                
        if ( !self.syncActive ) {
            self.syncActive = true;
        
            // start dialog
            var mbox = Ext.Msg.show({
                title: "Synchronisation",
                message: "Datenabgleich mit Server",
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
                                                    Ext.getStore("BasicItemStore"),
                                                    Ext.getStore("PricelistStore")
                                                   ], log, callback );
                } else {
                    callback(err);
                }                
            });
        }  
       
    },
    
    testNumberInput: function(c) {
        this.showNumberInput(c, 0.0);
    },
    
    showNumberInput: function(nextTo, val, callback) {
        var self = this;
        
        //check number view
        if ( !self.numberInputView ) {
            self.numberInputView = Ext.create('Fclipboard.view.NumberInputView');
        }
        
        // show
        self.numberInputView.showBy(nextTo, 'tl-tr?', false, val, callback);
    },
    
    
    resetSync: function(nextTo) {
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
        
        if ( nextTo ) {
            syncPopover.showBy(nextTo, 'tl-tr?', false);
        } else {
            syncPopover.show('pop');
        }
    }
    
    
    
});