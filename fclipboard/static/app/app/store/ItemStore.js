/*global Ext:false*/

Ext.define('Fclipboard.store.ItemStore', {
    extend: 'Ext.data.Store',    
    config: {        
        model: 'Fclipboard.model.Item',
        sorters: [{
                      property: 'section',
                      direction: 'ASC'
                  },
                  {
                      property: 'sequence',
                      direction: 'ASC'
                  }]
    }
});
