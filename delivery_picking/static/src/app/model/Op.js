/*global Ext:false, Config:false*/
Ext.define('DeliveryPicking.model.Op', {
   extend: 'Ext.data.Model',
   requires: [
       'Ext.data.proxy.Odoo'
   ],
   config: {
       fields: ['name',
                'uom',
                'qty',
                'qty_done',
                'package_count'
               ]
      
   }
});