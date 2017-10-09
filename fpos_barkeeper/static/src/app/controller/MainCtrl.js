/* global Ext:false, Core:false, ViewManager:false, console:false */

Ext.define('BarKeeper.controller.MainCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.form.ViewManager',
         'Ext.ux.Deferred',
         'BarKeeper.core.Core',
         'BarKeeper.view.StatusView'
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
        Core.getClient().then(function(client) {
            ViewManager.stopLoading();
            self.loadMainView();
        }, function(err) {
            ViewManager.handleError(err, {
              name: 'connection_error',
              message: 'Keine Verbindung zum Server möglich'
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
          try {
            self.basePanel = Ext.create('Ext.Panel', {
                title: Core.getStatus().company,
                layout: 'card',
                items: [
                    {
                        xtype: 'barkeeper_status'
                    }
                ]
            });                        
            self.getMainView().push(self.basePanel);
          } catch (err) {
            ViewManager.handleError(err, {
              name: 'loadview_failed',
              message: 'Ansicht konnte nicht geladen werden'
            });
          }
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
    
    onActiveItemChange: function() {
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
