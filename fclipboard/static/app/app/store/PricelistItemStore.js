/*global Ext:false*/

Ext.define('Fclipboard.store.PricelistItemStore', {
    extend: 'Ext.data.Store',    
    config: {        
        model: 'Fclipboard.model.PricelistItem',
        grouper: function(record) {
            return record.get('category');
        } 
    }
});
