/* global Ext:false, Core:false, ViewManager:false, console:false */

Ext.define('ChickenFarm.controller.MainCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
        'Ext.view.ViewManager',
        'Ext.ux.Deferred',
        'ChickenFarm.core.Core',
        'ChickenFarm.view.ProductionView',
        'Ext.dataview.List' 
    ],
    config: {
         refs: {
             mainView: '#mainView',
             refreshButton: '#refreshButton',
             saveButton: '#saveButton'
         },
         control: {
             mainView: {
                 initialize: 'prepare',
                 activeitemchange : 'onActiveItemChange'
             },
             'button[action=reloadData]': {
                release: 'onReloadData'
             },
             'button[action=saveRecord]': {
                release: 'onSaveRecord'
             }
         }
    },

    prepare: function() {
        var self = this;
        ViewManager.startLoading("Setup...");        
        Core.setup().then(function() {
            try {
                ViewManager.stopLoading();
                self.loadMainView();                
            } catch (err) {
                console.error(err);
            }
        }, function(err) {
            ViewManager.stopLoading();
            Ext.Msg.alert('Verbindungsfehler','Keine Verbindung zum Server möglich', function() {
                self.restart();
            });            
        });
    },
    
    restart: function() {
        ViewManager.startLoading("Neustart...");
        Core.restart();  
    },

    loadMainView: function() {
        var self = this;
        if ( !self.basePanel ) {
            self.basePanel = Ext.create('Ext.Panel', {
                title: Core.getStatus().company,
                layout: 'card',
                items: [
                    {
                        xtype: 'chf_production'
                    }
                ]
            });                        
            self.getMainView().push(self.basePanel);
        }
    },
    
    getActiveMainView: function() {            
        var activeItem = this.getMainView().getActiveItem(); 
        if ( activeItem == this.basePanel ) return this.basePanel;
        return this.getMainView();
    },
    
    getActiveItem: function() {
        var activeItem = this.getMainView().getActiveItem(); 
        if ( activeItem == this.basePanel ) activeItem = this.basePanel.getActiveItem();
        return activeItem;  
    },
    
    onActiveItemChange: function(mainView, newView, oldView, eOpts) {
        var self = this;
        var view = self.getActiveItem();
        var reloadable = ViewManager.hasViewOption(view, 'reloadable');
        this.getRefreshButton().setHidden(!reloadable);
        
        ViewManager.updateButtonState(view, {
            saveButton: self.getSaveButton()            
        });
    },
    
    onReloadData: function() {
        this.getActiveItem().fireEvent('reloadData');
    },
    
    onSaveRecord: function() {
        ViewManager.saveRecord(this.getActiveMainView());
    } 
});
