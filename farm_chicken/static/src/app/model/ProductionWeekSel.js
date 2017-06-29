/*global Ext:false */
Ext.define('ChickenFarm.model.ProductionWeekSel', {
   extend: 'Ext.data.Model',
   requires: [
   ],
   config: {
       fields: [
            'name',
            'date_start',
            'start',
            'end',
            'group'
       ]
   } 
});