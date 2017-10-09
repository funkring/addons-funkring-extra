/*global Ext:false, openerp:false, ViewManger:false */

Ext.define('BarKeeper.core.Core', {
    extend: 'Ext.core.Odoo',
    singleton : true,
    alternateClassName: 'Core',
    
    requires: [
        'Ext.ux.Deferred'
    ],
    
    config : {       
         version : '2.0.1',
         profileName: 'BarKeeper'
    }
    
});