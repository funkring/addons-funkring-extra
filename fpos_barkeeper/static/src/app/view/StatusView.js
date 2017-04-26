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
                height: '100%',               
                cls: 'StatusData',
                itemCls: 'StatusDataItem',
                store: 'StatusStore',
                itemTpl: ''
            }
            
        ]
    }
});
