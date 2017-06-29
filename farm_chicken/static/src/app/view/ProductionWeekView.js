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
                itemTpl:[   '<div class="WeekName">',
                                '<span class="WeekNameHeader">{week}</span>',
                                '<span class="WeekNameLabel">[{start} - {end}]</span>',
                            '</div>',
                            '<tpl for="overview">',
                                '<div class="WeekInfo">',
                                    '<div class="WeekInfoValue">{value}</div>',
                                    '<div class="WeekInfoLabel">{name}</div>',
                                '</div>',
                            '</tpl>'
                        ],
                itemCls: 'WeekItem',                
                store: 'ProductionWeekStore',
                scrollable: null,
                action: 'productionWeekDataView'
            },
            {
                xtype: 'list',
                action: 'productionDayList',
                store: 'ProductionDayStore',
                itemCls: 'DayItem',         
                scrollable: null,
                disableSelection: true,
                itemTpl: [  '<div class="{dayClass}">',
                                '<div class="DayName">{name}</div>',
                                '<tpl for="overview">',
                                    '<div class="DayInfo">',
                                        '<div class="DayInfoValue">{value}</div>',
                                        '<div class="DayInfoLabel">{name}</div>',
                                    '</div>',
                                '</tpl>',
                            '<div>'                                
                        ],
                prepareData: function(data, recordIndex, record){
                    if(record.get('valid')){
                        data.dayClass = 'DayItemValid';
                    } else if (record.get('filled')) {
                        data.dayClass = 'DayItemFilled';
                    } else {
                        data.dayClass = 'DayItemNormal';
                    }
                    return data;
                },
                flex: 1
            }            
        ]
    }
});
