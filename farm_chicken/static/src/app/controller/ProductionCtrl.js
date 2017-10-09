/* global Ext:false, Core:false, ViewManager:false, console:false */

Ext.define('ChickenFarm.controller.ProductionCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.view.ViewManager',
         'Ext.ux.Deferred',
         'Ext.XTemplate',
         'ChickenFarm.core.Core',
         'ChickenFarm.view.ProductionView',
         'ChickenFarm.view.ProductionWeekView',
         'ChickenFarm.view.ProductionDayForm',
         'ChickenFarm.view.ProductionWeekSelView',
         'ChickenFarm.view.ProductionDayManagerForm'
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
             'list[action=weekSelection]': {
                itemsingletap: 'onWeekSelTab'
             },
             'dataview[action=productionWeekDataView]': {
                itemsingletap: 'onWeekTab'
             },
             'chf_production_week': {
                 reloadData: 'onReloadDayList'
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
        self.weekStore = Ext.StoreMgr.lookup("ProductionWeekStore");
        self.weekSelStore = Ext.StoreMgr.lookup("ProductionWeekSelStore");
        self.reloadData();
        
    },
    
    reloadData: function() {
        var self = this; 
        ViewManager.startLoading('Lade Produktionen...');
        Core.call('farm.chicken.logbook','search_read', [[['state','=','active'],["house_id.hidden","=",false]], ["name"]]).then(function(res) {            
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
        Core.call('farm.chicken.logbook','logbook_week', [self.logbook.getId()], {date_start: self.date_start, context: Core.getContext()}).then(function(res) {
            ViewManager.stopLoading();            
            // set header
            self.weekStore.setData(res);        
			// set days
            var week = res[0];
            self.dayStore.setData(week.days);
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
    
    onReloadDayList: function() {
        this.reloadDayList();
    },
    
    onProductionTap: function(list, index, target, record, e, eOpts) {
        var self = this;
        var mainView = self.getMainView();
        
        self.logbook = record;
        self.manager = false;
        
        Core.call('res.users', 'has_group',['farm.group_manager'], {}).then(function(res) {
            self.manager = res;
            self.reloadDayList();
        
            mainView.push({
                title: record.get('name'),
                xtype: 'chf_production_week'
            });              
        }, function(err) {
            ViewManager.handleLoadError(err);
        });        
    },
    
    onDayTab: function(list, index, target, record, e, eOpts) {
        var self = this;
        var mainView = self.getMainView();
        
        mainView.push({
            title : record.get('name'),
            xtype: self.manager ? 'chf_production_day_manager_form' : 'chf_production_day_form',
            record: record,
            savedHandler: function() {
                var deferred = Ext.create('Ext.ux.Deferred');
                var values = {
                    day: record.get('day'),
                    loss: record.get('loss'),
                    eggs_total: record.get('eggs_total'),
                    eggs_broken: record.get('eggs_broken'),
                    eggs_dirty: record.get('eggs_dirty'),
                    eggs_weight: record.get('eggs_weight'),
                    weight: record.get('weight'),
                    note: record.get('note')
                };
                
                var next_state="";
                if ( self.manager ) {
                    values.loss_fix = record.get('loss_fix');
                    values.loss_fix_amount = record.get('loss_fix_amount');
                    
                    // check valid flag
                    if (record.get('valid')) {
                        next_state = 'valid';
                    } else {
                        next_state = 'draft';
                    }
                }
                
                Core.call('farm.chicken.logbook', 'update_day', [self.logbook.getId(), values], {next_state: next_state, context: Core.getContext()}).then(function(res) {
                    record.commit();                    
                    deferred.resolve();
                    self.reloadDayList();
                }, function(err) {
                    record.reject();
                    deferred.reject(err);
                });            
                    
                return deferred.promise();
            }
        });
    },
    
    onWeekTab: function(list, index, target, record, e, eOpts) {
        var self = this;
        
        if ( !self.logbook ) {
            Core.restart();
        }
        
        ViewManager.startLoading("Lade Wochen...");
        
        Core.call('farm.chicken.logbook', 'logbook_weeks', [self.logbook.getId()]).then(function(res) {
            ViewManager.stopLoading();
            
            var weeks = res[0];
            if ( weeks.length > 0 ) {
                self.weekSelStore.setData(weeks);
                var mainView = self.getMainView();
                mainView.push({
                    title: self.logbook.get('name'),
                    xtype: 'chf_production_week_list'                            
                });
            }
            
        }, function(err) {
            ViewManager.handleLoadError(err);
        });
    },
    
    onWeekSelTab: function(list, index, target, record, e, eOpts) {    
        var self = this;
        self.date_start = record.get('date_start');
                
        self.reloadDayList();
        self.getMainView().pop();        
    }
    
});