/* global Ext:false, Core:false, ViewManager:false */

Ext.define('BarKeeper.controller.TurnoverCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.form.ViewManager',
         'Ext.ux.Deferred',
         'BarKeeper.core.Core',
         'BarKeeper.view.TurnoverView',
         'BarKeeper.model.Turnover'
    ],
    config: {
         refs: {            
             view: '#turnoverView',
             filterView: '#turnoverFilterView',
             turnoverView: '#turnoverDataView'
         },

         control: {
             view: {
                 initialize: 'prepare'                                
             }            
         }
    },
    

    prepare: function() {
        this.loadData({
            dateFrom: '2017-04-12',
            dateTo: '2017-04-12'
        });
    },
    
    loadData: function(filter) {
        var self = this;
        if ( !self.data ) {        
            self.data = Ext.StoreMgr.lookup("TurnoverStore").add({
                filter: filter,
                turnover: []
            });
        }        
    }
   
});
