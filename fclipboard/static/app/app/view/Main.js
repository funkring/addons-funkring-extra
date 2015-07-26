/*global Ext:false*, Fclipboard:false, futil*/

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
                                            Ext.getCmp('mainView').fireEvent('searchItem',field.getValue());
                                        },
                                        clearicontap: function() {
                                            Ext.getCmp('mainView').fireEvent('searchItem',null);
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
                                                '{name}')
                                                
                            /*
                            itemTpl: Ext.create('Ext.XTemplate',
                                                '{name} {[this.f(1.0)]}',
                                               {
                                                 f: futil.formatFloat
                                               })*/
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
                                            Ext.getCmp('mainView').fireEvent('searchPartner',field.getValue());
                                        },
                                        clearicontap: function() {
                                            Ext.getCmp('mainView').fireEvent('searchPartner',null);
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
                        title: 'Abgleich',
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
                                    }                           
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
        self.fireEvent("doDataReload");      
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
      
       
       // reset title      
       self.setTitle(title);
       this.getNavigationBar().setTitle(this.getTitle());  
   },
   
   showNewItemSelection: function() {      
        var self = this;
        var record = self.getRecord();

        if ( !record ) {        
            self.fireEvent("createItem", self);
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
                        data: [{
                            "name" : "Ordner",
                            "option" : 0  
                        }, {
                            "name" : "Produkt",
                            "option" : 1
                        }]
                    }],               
                    listeners: {
                        change: function(picker,button) {
                            var option = picker.getValue().option;
                            if ( option === 1) {
                                self.fireEvent("addProduct", self);
                            } else {
                                self.fireEvent('createItem', self);
                            }
                        }
                    } 
                });
                
                Ext.Viewport.add(newItemPicker);
                newItemPicker.show();
            } else {
                self.fireEvent("addProduct", self);
            }
            
        }  
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
          self.fireEvent('parentItem');
       } else {
          self.fireEvent('doDataReload');
       }
   }
   
});
