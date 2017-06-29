/* global Ext:false */
Ext.define('ChickenFarm.view.ProductionWeekSelView', {
    extend: 'Ext.Panel',
    xtype: 'chf_production_week_list',
    requires: [
        'Ext.dataview.List' 
    ],
    config: {
        reloadable: true,
        layout: 'vbox',
        items: [
            {
                xtype: 'list',
                store: 'ProductionWeekSelStore',
                scrollable: null,
                disableSelection: true,
                itemCls: 'ProductionWeekSelItem',                
                itemTpl:  ['<span class="WeekSelHeader">{name}</span>',
                           '<span class="WeekSelLabel">[{start} - {end}]</span>'],
                flex: 1,
                grouped: true,
                action: 'weekSelection'
            }            
        ]
    }
});
