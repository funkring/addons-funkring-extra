/*global Ext:false, openerp:false, ViewManger:false, futil:false */

Ext.define('ChickenFarm.core.Core', {
    extend: 'Ext.core.Odoo',
    singleton : true,
    alternateClassName: 'Core',
    
    config : {       
      version : '2.0.1'
    }
    
});