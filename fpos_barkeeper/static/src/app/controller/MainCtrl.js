/* global Ext:false, Core:false, ViewManager:false */

Ext.define('BarKeeper.controller.MainCtrl', {
    extend: 'Ext.app.Controller',
    requires:[
         'BarKeeper.core.Core',
         'Ext.form.ViewManager',
         'Ext.ux.Deferred'
    ],
    config: {
         refs: {
             mainView: '#mainView'
         },
         control: {
             mainView: {
                 initialize: 'mainViewInitialize'
             }
         }
    },

    mainViewInitialize: function() {
        var self = this;
        ViewManager.startLoading("Setup...");        
        Core.setup().then(function() {
            ViewManager.stopLoading();
            self.loadMainView();                
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
           
    }   
   
});
