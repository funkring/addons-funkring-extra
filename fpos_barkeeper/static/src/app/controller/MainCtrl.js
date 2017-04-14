/* global Ext:false, Core:false, ViewManager:false, console:false */

Ext.define('BarKeeper.controller.MainCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.form.ViewManager',
         'Ext.ux.Deferred',
         'BarKeeper.core.Core',
         'BarKeeper.view.TurnoverView'
    ],
    config: {
         refs: {
             mainView: '#mainView'
         },
         control: {
             mainView: {
                 initialize: 'prepare'
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
                        xtype: 'barkeeper_turnover'                        
                    }
                ]
            });                        
            self.getMainView().push(self.basePanel);
        }
    }   
   
});
