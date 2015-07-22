/*global Ext:false*, Fclipboard:false*/

Ext.define('Fclipboard.view.Main', {
    extend: 'Ext.navigation.View',
    xtype: 'main',
    id: 'mainView',
    requires: [
        'Ext.TitleBar', 
        'Ext.TabPanel',
        'Ext.dataview.List',
        'Ext.field.Search',
        'Ext.util.DelayedTask',
        'Ext.field.Password',
        'Ext.field.Text'
    ],
    config: {
        // **********************************************************
        //  Defaults
        // **********************************************************
        
        title: 'Dokumente',
        record: null,        

        // **********************************************************
        //  Navigation Bar
        // **********************************************************
        
        navigationBar: {
            items: [
                {
                    xtype: 'button',
                    id: 'deleteRecord',
                    iconCls: 'trash',
                    align: 'right',
                    action: 'deleteRecord',  
                    hidden: true
                }, 
                {
                    xtype: 'button',
                    id: 'saveViewButton',
                    text: 'OK',                                  
                    align: 'right',
                    action: 'saveView',
                    hidden: true                
                }      
            ]
        },           
        
        listeners : {
            activeitemchange : function(view, newCard) {
                var saveButton = view.down('button[action=saveView]');
                var deleteButton = view.down('button[action=deleteRecord]');
                
                if ( newCard instanceof Fclipboard.view.FormView ) {
                    saveButton.show();
                    
                    var record = newCard.getRecord();
                    if (newCard.getDeleteable() && record && !record.phantom ) {
                        deleteButton.show();
                    } else {
                        deleteButton.hide();
                    }
                } else {
                    saveButton.hide();
                    deleteButton.hide();
                }
            }
        },
             
           
        // **********************************************************
        // View Items
        // **********************************************************
                
        items: [
            {                
                xtype: 'tabpanel',
                tabBarPosition: 'bottom',      
                id: 'mainPanel',
                
                listeners: {
                    activeitemchange: function(view, value, oldValue, opts) {
                        Ext.getCmp("mainView").validateComponents();  
                    }  
                },
                                                                        
                items: [   
                    {
                        title: 'Dokumente',
                        id: 'itemTab',
                        iconCls: 'home',     
                        items: [{
                            docked: 'top',
                            xtype: 'toolbar',
                            ui: 'neutral',
                            items: [
                                {
                                    xtype: 'button',
                                    id: 'parentItemButton',
                                    ui: 'back',
                                    text: 'Zurück',       
                                    align: 'left',
                                    action: 'parentItem'  
                                },                               
                                {
                                    xtype: 'searchfield',
                                    placeholder: 'Suche',
                                    id: 'itemSearch',
                                    flex: 1,
                                    listeners: {
                                        keyup: function(field, key, opts) {
                                            Ext.getCmp("mainView").searchItemDelayed(field.getValue());
                                        },
                                        clearicontap: function() {
                                            Ext.getCmp("mainView").searchItemDelayed(null);
                                        }
                                    }                       
                                },
                                {
                                    xtype: 'button',
                                    id: 'editItemButton',
                                    iconCls: 'settings',                
                                    align: 'right',
                                    action: 'editItem'   
                                }, 
                                {
                                    xtype: 'button',
                                    id: 'newItemButton',
                                    iconCls: 'add',
                                    align: 'right',
                                    action: 'newItem'      
                                }
                                                         
                            ]                           
                        },
                        {
                            xtype: 'list',
                            height: '100%',
                            store: 'ItemStore',
                            id: 'itemList',
                            cls: 'ItemList',
                            itemTpl: Ext.create('Ext.XTemplate',
                                                '{name}'
                                               )  
                            /*
                            itemTpl: Ext.create('Ext.XTemplate',
                                            '<tpl if="dtype == \'res.partner\'">',
                                                '<span class="left-col">{name}</span>',
                                                '<span class="right-col">&ltKein(e)&gt</span>',                                                
                                            '<tpl else>',
                                                '{name}',
                                            '</tpl>')    */            
                        }]            
                    },
                    {
                        title: 'Partner',                        
                        id: 'partnerTab',
                        iconCls: 'team',        
                        items: [{
                            docked: 'top',                            
                            xtype: 'toolbar',
                            ui: 'neutral',
                            items: [                                
                                {
                                    xtype: 'searchfield',
                                    placeholder: 'Suche',
                                    id: 'partnerSearch',
                                    flex: 1,
                                    listeners: {
                                        keyup: function(field, key, opts) {
                                            Ext.getCmp("mainView").searchPartnerDelayed(field.getValue());
                                        },
                                        clearicontap: function() {
                                            Ext.getCmp("mainView").searchPartnerDelayed(null);
                                        }
                                    }
                                },
                                {
                                    xtype: 'button',
                                    id: 'newPartnerButton',
                                    iconCls: 'add',
                                    align: 'right',
                                    action: 'newPartner'      
                                }                              
                            ]                           
                        },
                        {
                            xtype: 'list',
                            id: 'partnerList',
                            height: '100%',
                            store: 'PartnerStore',
                            //disableSelection:true,                            
                            cls: 'PartnerList',
                            itemTpl: '{name}'                       
                        }]
                    },
                    {
                        title: 'Synchronisation',
                        id: 'syncTab',
                        iconCls: 'refresh',
                        items:  [
                            {
                                docked: 'top',                            
                                xtype: 'toolbar',
                                ui: 'neutral',
                                items: [
                                    {
                                        xtype: 'button',
                                        id: 'editConfigButton',
                                        text: 'Einstellungen',
                                        align: 'left',
                                        action: 'editConfig'   
                                    },
                                    {
                                        xtype: 'button',
                                        id: 'resetSync',
                                        text: 'Zurücksetzen',
                                        align: 'left',
                                        action: 'resetSync'  
                                    }, 
                                    {
                                        xtype: 'spacer',
                                        flex: 1
                                    },
                                    {
                                        xtype: 'button',
                                        id: 'syncButton',
                                        text: 'Starten',
                                        align: 'right',
                                        action: 'sync'                
                                    },                           
                                ]                           
                            },                          
                            {
                                xtype: 'scrolllist',
                                id: 'logList',
                                height: '100%',
                                store: 'LogStore',
                                disableSelection:true,                            
                                cls: 'LogList',
                                itemTpl: '{message}'                       
                            }                
                        ]
                        
                    }                   
                ]
            }
        ]
    },
    
    // init
   constructor: function(config) {
        var self = this;        
        self.callParent(config);
        
        self.partnerSearchTask = Ext.create('Ext.util.DelayedTask', function() {
            self.searchPartner();
        });
           
        self.itemSearchTask = Ext.create('Ext.util.DelayedTask', function() {
            self.searchItems();
        });
                   
        self.loadRecord();        
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
   
   searchPartner: function() {
       var partnerStore = Ext.StoreMgr.lookup("PartnerStore");
       
       if ( !Ext.isEmpty(this.partnerSearch) ) {
         partnerStore.load({
           params: {
                 limit: 100
           },
           filters : [{
                   property: 'name',
                   value: this.partnerSearch
           }]
         });
       } else {
         partnerStore.load({
             params : {
                 limit: 100
             }
         });
       }    
   },
   
   searchItems: function() {
       var record = this.getRecord();
       var domain = [['parent_id','=',record !== null ? record.getId() : null]];
             
       var options = {
           params : {
               domain : domain
           }
       };
              
       if ( !Ext.isEmpty(this.itemSearch) ) {
           options.filters = [{
              property: 'name',
              value: this.itemSearch   
           }];
       }
       
       // load data
       var itemStore = Ext.StoreMgr.lookup("ItemStore");
       itemStore.load(options);  
   },
   
        
   validateComponents: function(context) {
       var self = this;

       // create context
       if (!context) {
           context = {};
       }

       var activeItem = context.activeItem || Ext.getCmp("mainPanel").getActiveItem();
       var title = context.title || activeItem.title;
       var itemRecord = context.record || self.getRecord();              
       var itemData = itemRecord && itemRecord.data || null;

       var syncTabActive = (activeItem.getId() == "syncTab");
       var itemTabActive = (activeItem.getId() == "itemTab");
       var attachmentTabActive = (activeItem.getId() == "attachmentTab");
       
       // override title with name from data       
       if ( (itemTabActive || attachmentTabActive) && itemData !== null ) {
           title = itemData.name;
           if ( attachmentTabActive ) {
               title = title + " / Anhänge ";
           } 
       } 
    
       Ext.getCmp('parentItemButton').setHidden(itemRecord === null);
       Ext.getCmp('editItemButton').setHidden(itemRecord === null);
       // update button state
       /*
       Ext.getCmp('itemSearch').setValue(null);
       Ext.getCmp('partnerSearch').setValue(null);       
       Ext.getCmp('newItemButton').setHidden(syncTabActive);
       Ext.getCmp('editItemButton').setHidden(!itemTabActive || record === null || syncTabActive );
       
       Ext.getCmp('syncButton').setHidden(!syncTabActive);
       Ext.getCmp('editConfigButton').setHidden(!syncTabActive);
       Ext.getCmp('deleteRecord').setHidden(true);
       Ext.getCmp('resetSync').setHidden(!syncTabActive);*/
       
       // reset title      
       self.setTitle(title);
       this.getNavigationBar().setTitle(this.getTitle());  
   },
   
      
   loadRecord: function() {
       var self = this;
       
       // init
       self.partnerSearchTask.cancel();
       self.itemSearchTask.cancel();       
       self.partnerSearch = null;
       self.itemSearch = null;
        
       // validate components
       self.validateComponents();
       
       // load data
       self.searchItems();
       self.searchPartner();       
   },
   
   showNewItemSelection: function() {      
        var self = this;
        self.fireEvent('createItem', self, "d");
              
        /*        
            var newItemPicker = Ext.create('Ext.Picker',{
                doneButton: 'Erstellen',
                cancelButton: 'Abbrechen',
                modal: true,
                slots:[{
                    name: 'item_type',
                    title: 'Element',
                    displayField: 'name',
                    valueField: 'type',
                    data: recordCreateables
                }],               
                listeners: {
                    change: function(picker,button) {
                        var val = picker.getValue().item_type;
                        self.fireEvent('createItem', self, val);
                    }
                } 
            });
            
            Ext.Viewport.add(newItemPicker);
            newItemPicker.show();
        */
   },

      
   pop: function() {
       this.callParent(arguments);
       this.validateComponents();
   },
   
   leave: function() {
       var self = this;
       self.pop();
       
       var activeItem = Ext.getCmp("mainPanel").getActiveItem();
       var itemTabActive = (activeItem.getId() == "itemTab");
       if ( itemTabActive ) {
          self.fireEvent('parentItem', self);
       } else {
          self.loadRecord();
       }
   }
   
});
