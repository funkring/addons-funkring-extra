/*global Ext:false*/
Ext.define('Fclipboard.model.Item', {
   extend: 'Fclipboard.model.BasicItem',
   requires: [
       'Ext.proxy.PouchDB'
   ],
   config: {      
       proxy: {
            type: 'pouchdb',
            database: 'fclipboard',
            domain: [['fdoo__ir_model','=','fclipboard.item'],['is_template','=',false]]      
       }       
   }
});