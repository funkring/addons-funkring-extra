/* global Ext:false */
Ext.define('BarKeeper.view.StatusView', {
    extend: 'Ext.Panel',
    xtype: 'barkeeper_status',
    id: 'statusView',
    requires: [
        'Ext.dataview.DataView'    
    ],
    config: {
        reloadable: true,
        layout: 'vbox',
        items: [
            {
                xtype: 'dataview',
                id: 'statusFilterView',
                store: 'StatusStore',
                scrollable: null,
                cls: 'StatusFilter',
                itemCls: 'StatusItem',                
                itemTpl: ''
            },
            {
                xtype: 'dataview',
                id: 'statusDataView',
                scrollable: 'vertical',
                cls: 'StatusData',
                itemCls: 'StatusDataItem',
                store: 'StatusStore',
                itemTpl: '',
                flex: 1
            }
            
        ]
    }
});
