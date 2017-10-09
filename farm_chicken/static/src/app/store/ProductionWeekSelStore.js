/*global Ext:false*/

Ext.define('ChickenFarm.store.ProductionWeekSelStore', {
    extend: 'Ext.data.Store',      
    config: {
        model: 'ChickenFarm.model.ProductionWeekSel',
        groupDir: "DESC",
        groupField: 'group',
        sorters: [{property:'date_start', direction: 'DESC'}]
    }
});
