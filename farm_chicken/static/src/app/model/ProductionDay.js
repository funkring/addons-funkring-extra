/*global Ext:false */
Ext.define('ChickenFarm.model.ProductionDay', {
   extend: 'Ext.data.Model',
   requires: [
   ],
   config: {
       fields: [
            {name:'name', type:'string'},
            {name:'loss', type:'int'},
            {name:'eggs_total', type:'int'},
            {name:'eggs_broken', type:'int'},
            {name:'eggs_dirty', type:'int'},
            {name:'eggs_weight', type:'float'},
            {name:'weight', type:'float'},
            {name:'note', type:'string'},
            {name:'day', type:'string'},
            {name:'loss_fix', type:'boolean'},
            {name:'loss_fix_amount', type:'int'},
            {name:'valid', type:'boolean'},
            {name:'filled', type:'boolean'},
            {name:'overview'}
       ]
   } 
});