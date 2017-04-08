/* global Ext:false */
Ext.define('BarKeeper.view.Main', {
    extend: 'Ext.navigation.View',
    xtype: 'main',
    id: 'mainView',
    requires: [
    ],
    config: {
        tabBarPosition: 'bottom',
        defaultBackButtonText: 'Zurück',        
        layout: {
            type: 'card',
            animation: false            
        }
    }
});
