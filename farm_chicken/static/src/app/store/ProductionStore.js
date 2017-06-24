/*global Ext:false*/

Ext.define('ChickenFarm.store.ProductionStore', {
    extend: 'Ext.data.Store',      
    config: {
        model: 'ChickenFarm.model.Production'
    }
});
