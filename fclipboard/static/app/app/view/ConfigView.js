/*global Ext:false*/

Ext.define('Fclipboard.view.ConfigView', {
    extend: 'Fclipboard.view.FormView',    
    xtype: 'configform',
    config: {
        scrollable: true,
        items: [
            {
                xtype: 'fieldset',
                title: 'Verbindung',
                items: [
                    {
                        xtype: 'hiddenfield',
                        name: '_rev',
                        label: 'Version'
                    },
                    {
                        xtype: 'textfield',
                        name: 'host',
                        label: 'Server',
                        required: true
                    },
                    {
                        xtype: 'textfield',
                        name: 'port',
                        label: 'Port',
                        required: true
                    },
                    {
                        xtype: 'textfield',
                        name: 'db',
                        label: 'Datenbank',
                        required: true
                    },
                    {
                        xtype: 'textfield',
                        name: 'user',
                        label: 'Benutzer',
                        required: true
                    },
                    {
                        xtype: 'passwordfield',
                        name: 'password',
                        label: 'Passwort',
                        required: true
                    }
                ]   
            }
        ]       
    }
    
});