/* global Ext:false, Core:false, ViewManager:false, console:false */

Ext.define('ChickenFarm.controller.ProductionCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.form.ViewManager',
         'Ext.ux.Deferred',
         'ChickenFarm.core.Core',
         'ChickenFarm.view.ProductionView',
         'ChickenFarm.view.ProductionDayView',
         'ChickenFarm.view.ProductionDayForm'
    ],
    config: {
         refs: {
             mainView: '#mainView',
             productionView: '#productionView',
             productionList: '#productionList'
         },
         control: {
             productionView: {
                initialize: 'prepare',
                reloadData: 'onReloadData'       
             },
             productionList: {
                 itemsingletap: 'onProductionTap'
             },
             'list[action=productionDayList]': {               
                itemsingletap: 'onDayTab'
             },
             'chf_production_week[action=productionDayView]': {
                reloadData: 'onReloadDayList',
                painted: 'onReloadDayList'
             }             
         }
    },
    
    // *******************************************************************
    // FUNCTIONS
    // *******************************************************************
    
    handleLoadError: function(err) {
         ViewManager.handleError(err, {name: 'Server Offline', message: 'Daten konnten nicht geladen werden'});
    },

    prepare: function() {
        var self = this;
        self.logbookStore = Ext.StoreMgr.lookup("ProductionStore");
        self.dayStore = Ext.StoreMgr.lookup("ProductionDayStore");
        self.reloadData();
        
    },
    
    reloadData: function() {
        var self = this; 
        ViewManager.startLoading('Lade Produktionen...');
        Core.getModel("farm.chicken.logbook")
            .call('search_read', [[['state','=','active']], ["name"]], {context: Core.getContext()}).then(function(res) {
            ViewManager.stopLoading();
            self.logbookStore.setData(res);
        }, function(err) {
            ViewManager.handleLoadError(err);
        });
        
    },
            
    reloadDayList: function() {
        var self = this;
        if ( !self.logbook ) return;
        
        ViewManager.startLoading('Lade Woche...');
        Core.getModel("farm.chicken.logbook")
            .call('logbook_week', [self.logbook.getId()], {context: Core.getContext()}).then(function(res) {
            ViewManager.stopLoading();
            var dayList = res[0];
            self.dayStore.setData(dayList.days);
        }, function(err) {
            ViewManager.handleLoadError(err);
        });
    },
    
    
    // *******************************************************************
    // EVENTS
    // ******************************************************************* 
    
    onReloadData: function() {
        this.reloadData();
    },
    
    onProductionTap: function(list, index, target, record, e, eOpts) {
        var self = this;
        var mainView = self.getMainView();
        
        self.logbook = record;
        self.reloadDayList();
        
        mainView.push({
            title: record.get('name'),
            xtype: 'chf_production_week'
        });
    },
    
    onDayTab: function(list, index, target, record, e, eOpts) {
        var self = this;
        var mainView = self.getMainView();
        
        mainView.push({
            'title' : record.get('name'),
            'xtype': 'chf_production_day_form' ,
            'record': record,
            'savedHandler': function() {
                var deferred = Ext.create('Ext.ux.Deferred');
                Core.getModel("farm.chicken.logbook")
                    .call('update_day', [self.logbook.getId(), {
                    day: record.get('day'),
                    loss: record.get('loss'),
                    eggs_total: record.get('eggs_total'),
                    eggs_broken: record.get('eggs_broken'),
                    eggs_dirty: record.get('eggs_dirty'),
                    eggs_weight: record.get('eggs_weight'),
                    weight: record.get('weight'),
                    note: record.get('note')
                }], {context: Core.getContext()}).then(function(res) {
                    record.commit();                    
                    deferred.resolve();
                }, function(err) {
                    record.reject();
                    deferred.reject(err);
                });            
                    
                return deferred.promise();
            }
        });
    },
    
    onReloadDayList: function() {
        this.reloadDayList();
    }
    
});