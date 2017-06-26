/*global Ext:false */
Ext.define('ChickenFarm.model.ProductionWeek', {
   extend: 'Ext.data.Model',
   requires: [
   ],
   config: {
       fields: [
            'name',
            'week',
            'date',
            'start',
            'end',
            'days'
       ]
   } 
});