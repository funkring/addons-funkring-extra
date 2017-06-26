/* global Ext:false */
Ext.define('ChickenFarm.view.ProductionWeekView', {
    extend: 'Ext.Panel',
    xtype: 'chf_production_week',
    requires: [
        'Ext.dataview.List',
        'Ext.dataview.DataView' 
    ],
    config: {
        reloadable: true,       
        layout: 'vbox',
        items: [
            {
                xtype: 'dataview',
                itemTpl: '<div>{name}</div>',
                itemCls: 'WeekItem',                
                store: 'ProductionWeekStore',
                scrollable: null
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
