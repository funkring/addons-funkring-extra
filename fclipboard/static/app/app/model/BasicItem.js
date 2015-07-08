/*global Ext:false*/
Ext.define('Fclipboard.model.BasicItem', {
   extend: 'Ext.data.Model',
   requires: [
       'Ext.proxy.PouchDB'
   ],
   config: {
       fields: ['name','code','is_template','parent_id','type',
                'section','code','sequence',
                'valc','valt','valf','vali','valb','vald'],
       identifier: 'uuid',
       proxy: {
            type: 'pouchdb',
            database: 'fclipboard',
            domain: [['fdoo__ir_model','=','fclipboard.item']]      
       }       
   }
});