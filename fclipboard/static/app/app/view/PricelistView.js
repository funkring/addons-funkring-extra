/*global Ext:false*/
Ext.define('Fclipboard.view.PricelistView', {
    extend: 'Ext.Container',
    xtype: 'pricelistview',
    config: {
        title: 'Dokumente',
        items: [{
            docked: 'top',
            xtype: 'toolbar',
            ui: 'neutral',
            items: [                                       
                {
                    xtype: 'searchfield',
                    placeholder: 'Suche',
                    id: 'itemSearch',
                    flex: 1,
                    listeners: {
                        keyup: function(field, key, opts) {
                            Ext.getCmp("mainView").searchItemDelayed(field.getValue());
                        },
                        clearicontap: function() {
                            Ext.getCmp("mainView").searchItemDelayed(null);
                        }
                    }                       
                }                                         
            ]                           
        },                        
        {
            xtype: 'list',
            height: '100%',
            store: 'ItemStore',
            id: 'itemList',
            cls: 'ItemList',
            itemTpl: Ext.create('Ext.XTemplate',
                                '<table>',
                                '<tr>',
                                    '<td>{code}</td>',
                                    '<td>{name}</td>',
                                    '<td>{valc}</td>',
                                    '<td>{valf}</td>',                                
                                '</tr>',
                                '</table>'
                               )  
            /*
            itemTpl: Ext.create('Ext.XTemplate',
                            '<tpl if="dtype == \'res.partner\'">',
                                '<span class="left-col">{name}</span>',
                                '<span class="right-col">&ltKein(e)&gt</span>',                                                
                            '<tpl else>',
                                '{name}',
                            '</tpl>')    */            
        }]
             
        
    }
});