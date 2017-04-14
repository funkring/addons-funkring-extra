/* global Ext:false */
Ext.define('BarKeeper.view.TurnoverView', {
    extend: 'Ext.Panel',
    xtype: 'barkeeper_turnover',
    id: 'turnoverView',
    requires: [
        'Ext.dataview.DataView'    
    ],
    config: {       
        items: [
            {
                xtype: 'dataview',
                id: 'turnoverFilterView',
                store: 'TurnoverStore',
                scrollable: null,
                itemTpl: ''
            },
            {
                xtype: 'dataview',
                id: 'turnoverDataView',
                scrollable: 'vertical',                
                flex: 1,
                store: 'TurnoverStore',
                itemTpl: ''
            }
            
        ]
    }
});
