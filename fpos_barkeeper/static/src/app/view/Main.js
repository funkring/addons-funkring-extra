/* global Ext:false */
Ext.define('BarKeeper.view.Main', {
    extend: 'Ext.navigation.View',
    xtype: 'main',
    id: 'mainView',
    requires: [
    ],
    config: {
        defaultBackButtonText: 'Zurück',        
        layout: {
            type: 'card',
            animation: false            
        },
        navigationBar: {            
            items: [
                {
                    xtype: 'button',
                    id: 'refreshButton',
                    iconCls: 'refresh',                                  
                    align: 'right',
                    action: 'reloadData',
                    hidden: true
                },
                {
                    xtype: 'button',
                    id: 'saveButton',
                    text: 'Speichern',                                  
                    align: 'right',
                    action: 'saveRecord',
                    hidden: true
                }
            ]
        }
    }
});
