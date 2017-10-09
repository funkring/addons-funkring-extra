/*global Ext:false */
Ext.define('BarKeeper.model.FilterModel', {
   extend: 'Ext.data.Model',
   requires: [
   ],
   config: {
       fields: [
            'name',
            'date',
            'group',
            'action',
            'mode',
            'next'
       ]
   } 
});