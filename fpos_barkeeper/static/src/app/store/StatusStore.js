/*global Ext:false*/

Ext.define('BarKeeper.store.StatusStore', {
    extend: 'Ext.data.Store',      
    config: {
        model: 'BarKeeper.model.Status'
    }
});
