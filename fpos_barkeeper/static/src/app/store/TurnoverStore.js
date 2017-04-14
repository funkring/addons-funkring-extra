/*global Ext:false*/

Ext.define('BarKeeper.store.TurnoverStore', {
    extend: 'Ext.data.Store',      
    config: {
        model: 'BarKeeper.model.Turnover'
    }
});
