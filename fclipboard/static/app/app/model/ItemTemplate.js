/*global Ext:false*/
Ext.define('Fclipboard.model.ItemTemplate', {
   extend: 'Fclipboard.model.BasicItem',
   config: {       
       proxy: {
            type: 'pouchdb',
            database: 'fclipboard',
            domain: [['fdoo__ir_model','=','fclipboard.item'],['is_template','=',true]]      
       }       
   }
});