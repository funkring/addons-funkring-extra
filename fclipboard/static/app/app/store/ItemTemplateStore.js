/*global Ext:false*/

Ext.define('Fclipboard.store.ItemTemplateStore', {
    extend: 'Ext.data.Store',    
    config: {
        autoLoad: true,
        model: 'Fclipboard.model.ItemTemplate'       
    }
});
