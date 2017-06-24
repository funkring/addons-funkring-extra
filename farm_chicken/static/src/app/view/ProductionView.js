/* global Ext:false */
Ext.define('ChickenFarm.view.ProductionView', {
    extend: 'Ext.Panel',
    xtype: 'chf_production',
    id: 'productionView',
    requires: [
        'Ext.dataview.List' 
    ],
    config: {
        reloadable: true,
        layout: 'vbox',
        items: [
            {
                xtype: 'list',
                id: 'productionList',
                store: 'ProductionStore',
                scrollable: null,
                disableSelection: true,
                cls: 'ProductionStore',
                itemCls: 'ProductionItem',                
                itemTpl: '{name}',
                flex: 1
            }            
        ]
    }
});
