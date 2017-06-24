/* global Ext:false */
Ext.define('ChickenFarm.view.ProductionDayView', {
    extend: 'Ext.Panel',
    xtype: 'chf_production_week',
    requires: [
        'Ext.dataview.List',
        'Ext.dataview.DataView' 
    ],
    config: {
        reloadable: true,       
        layout: 'vbox',
        action: 'productionDayView',
        items: [
            {
                xtype: 'dataview'
            },
            {
                xtype: 'list',
                action: 'productionDayList',
                store: 'ProductionDayStore',
                scrollable: null,
                disableSelection: true,
                itemTpl: '{name}',
                flex: 1
            }            
        ]
    }
});
