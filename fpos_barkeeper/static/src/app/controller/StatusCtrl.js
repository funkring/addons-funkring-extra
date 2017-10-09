/* global Ext:false, Core:false, ViewManager:false, futil:false */

Ext.define('BarKeeper.controller.StatusCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.form.ViewManager',
         'Ext.ux.Deferred',
         'Ext.dataview.List',
         'Ext.form.Panel',
         'Ext.data.Store',
         'BarKeeper.core.Core',
         'BarKeeper.view.StatusView',
         'BarKeeper.model.Status',
         'BarKeeper.model.FilterModel'
    ],
    config: {
         refs: {            
             mainView: '#mainView',
             view: '#statusView',
             filterView: '#statusFilterView',
             statusView: '#statusDataView'
         },

         control: {            
            view: {
                initialize: 'prepare',
                reloadData: 'onReloadData'                        
            },
            filterView: {
                itemsingletap: 'onFilterSelect'
            }      
         }
    },
    
    
    prepare: function() {
        this.loadData({});
    },
    
    loadData: function(options) {
        var self = this;
        if ( !self.data ) {
            // init filter
            var filterTpl = Ext.create('Ext.XTemplate',
                '<div class="StatusItemTable">',
                    '<div class="StatusItemTitle">',
                        '{status.title}',
                    '</div>',
                    '<div class="StatusItemRange">',
                        '{status.range}',
                    '</div>',
                '</div>',
                '<div class="StatusItemName">',
                    '{status.name}',
                    '<div class="StatusItemGroup">',
                        '{status.group}',                    
                    '</div>',                    
                '</div>'
            );
            self.getFilterView().setItemTpl(filterTpl);
                   
            // init stat
            var statusTpl = Ext.create('Ext.XTemplate',
                '<tpl if="status.total.amount">',
                    '<div class="StatusDataTotal">',
                        '<div class="StatusDataTotalTable">',                        
                            '<div class="StatusDataTotalTitle">',
                                'Verkäufe ({status.total.count})',
                            '</div>',
                            '<div class="StatusDataTotalAmount">',
                                "{[futil.formatFloat(values.status.total.amount)]} {status.total.currency}",
                            '</div>',
                        '</div>',
                    '</div>',
                '</tpl>',     
                '<tpl if="(status.byJournal && status.byJournal.length &gt; 0) || (status.byUser && status.byUser.length &gt; 0)">',
                    '<div class="StatusDataSaleBy">',
                        '<tpl for="status.byJournal">',
                            '<div class="StatusDataTable">',
                                '<div class="StatusDataTotalTitle">',
                                    '{key} ({count})',
                                '</div>',
                                '<div class="StatusDataTotalAmount">',
                                    "{[futil.formatFloat(values.amount)]} {currency}",
                                '</div>',                            
                            '</div>',
                        '</tpl>',                        
                    '</div>',
                    '<div class="StatusDataSaleBy">',
                        '<tpl for="status.byUser">',
                            '<div class="StatusDataTable">',
                                '<div class="StatusDataTotalTitle">',
                                    '{key} ({count})',
                                '</div>',
                                '<div class="StatusDataTotalAmount">',
                                    "{[futil.formatFloat(values.amount)]} {currency}",
                                '</div>',                            
                            '</div>',
                            '<div class="StatusDataSaleByInner">',
                                '<tpl for="byJournal">',
                                    '<div class="StatusDataTable">',
                                        '<div class="StatusDataTotalTitle">',
                                            '{key} ({count})',
                                        '</div>',
                                        '<div class="StatusDataTotalAmount">',
                                            "{[futil.formatFloat(values.amount)]} {currency}",
                                        '</div>',    
                                    '</div>',       
                                '</tpl>',                 
                            '</div>',                    
                        '</tpl>',                    
                    '</div>',
                    '<div class="StatusByTime">',
                        '<tpl for="status.byTime">',                            
                            '<div class="StatusTimeTable">',
                                '<div class="StatusTimeTableRow">',
                                    '<div class="StatusDataTotalTitle">',
                                        '{key} ({count})',
                                    '</div>',
                                    '<div class="StatusDataTotalAmount">',
                                        "{[futil.formatFloat(values.amount)]} {currency}",
                                    '</div>',    
                                '</div>',
                                '<div class="StatusDataSaleByInner">',
                                    '<tpl for="byUser">',
                                        '<div class="StatusDataTable">',
                                            '<div class="StatusDataTotalTitle">',
                                                '{key} ({count})',
                                            '</div>',
                                            '<div class="StatusDataTotalAmount">',
                                                "{[futil.formatFloat(values.amount)]} {currency}",
                                            '</div>',    
                                        '</div>',       
                                    '</tpl>',                 
                                '</div>',      
                            '</div>',       
                        '</tpl>',      
                        '<div class="StatusTimeTable">',
                        '</div>',
                    '</div>',   
                '</tpl>'   
            );
            self.getStatusView().setItemTpl(statusTpl);
                    
            // data
            self.data = Ext.StoreMgr.lookup("StatusStore").add({
                status : {
                    title: 'Keine Daten',
                    group: '',
                    range: '',
                    name: '',
                    options: options                    
                }
            })[0];
            
           
        }
        
        // load status
        ViewManager.startLoading('Lade Daten...');
        Core.call('pos.config', 'barkeeper_status', [options]).then(function(data) {
            ViewManager.stopLoading();
            self.data.set('status', data);  
        }, function(err) {            
            ViewManager.handleError(err, {name: 'Server Offline', message: 'Daten konnten nicht geladen werden'});
        });        
    },
    
    onReloadData: function() {
        var status = this.data.get('status');
        var options = status.options || {};
        //options.date = futil.dateToStr(new Date());
        this.loadData(options);
    },
    
    onFilterSelect: function(view, index, target, data, e, opts) {
        var element = Ext.get(e.target);
        if ( element.hasCls('StatusItemName') || element.up('div.StatusItemName') ) {
            this.selectPosConfig();
        } else if ( element.hasCls('StatusItemTable') || element.up('div.StatusItemTable') ) {
            this.selectRangeConfig();
        }
    },
    
    selectPosConfig: function() {
        var self = this;
        ViewManager.startLoading('Lade Daten...');
        Core.call('pos.config', 'search_read', [[['parent_user_id','=',null],['state','=','active']], ['name']]).then(function(rows) {
            ViewManager.stopLoading();
            Ext.StoreMgr.lookup("PosConfigStore").setData(rows);
            self.getMainView().push({
                title: 'Kassen',
                xtype: 'list',
                store: 'PosConfigStore',
                itemTpl: '{name}',
                listeners: {
                    itemsingletap: function(list, index, target, record) {
                        var status = self.data.get('status');
                        var options = status.options || {};
                        options.config_id = record.getId();
                        options.date = null;
                        self.loadData(options);
                        self.getMainView().pop();                          
                    }
                }
            });
        }, function(err) {
           ViewManager.handleError(err, {name: 'Server Offline', message: 'Daten konnten nicht geladen werden'});
        });
    },
    
    
    selectRangeConfig: function() {
        var self = this;
        
        var status = this.data.get('status');
        var options = status.options || {};
        
        // mode
        var mode = options.mode || 'today';
        
        /*
        // date
        var date = new Date();
        if ( options.date ) {
            date = futil.strToDate(options.date);
        }*/
        
        var filterMode = null;
        var level = 0;
                
        var createListView = function(filter_data) {
          level++;
          
          var filterStoreConfig = {
            model: 'BarKeeper.model.FilterModel',
            data: filter_data.data           
          };
          
          var grouped = false;
          if ( filter_data.group ) {
            grouped = true;
            filterStoreConfig.sorters = {
              property: 'date',
              direction: 'DESC'
            };
            filterStoreConfig.grouper = {
              property: 'group',
              direction: 'DESC'
            };
          }
          
          return {
              xtype: 'list',
              itemTpl: '{name}',
              store: Ext.create("Ext.data.Store", filterStoreConfig),
              grouped: grouped,
              fullscreen: true,
              title: filter_data.title,
              disableSelection: true,
              listeners: {
                itemtap: function(list, index, target, record)  {
                  // load filter
                  var next = record.get('next');
                  if ( !next || filterMode == record.get('mode')) {
                    options.mode = record.get('mode');
                    options.date = record.get('date');
                    self.getMainView().pop(level);
                    self.loadData(options);                  
                  } else { 
                    // go deeper
                    ViewManager.startLoading("Lade Daten...");
                    Core.call("pos.config", next, [record.get('date')]).then(function(filter_data) {
                      ViewManager.stopLoading();
                      self.getMainView().push(createListView(filter_data));
                    }, function(err) {
                      ViewManager.handleError(err);                      
                    });
                  }
                  if ( !filterMode ) {
                    filterMode = record.get('mode');
                  }
                }
              }
            };
        };
        
        ViewManager.startLoading("Lade Filter...");
        Core.call("pos.config","barkeeper_range_filter").then(function(filter_data) {
          ViewManager.stopLoading();
          self.getMainView().push(createListView(filter_data));
        }, function(err) {
          ViewManager.handleError(err);
        });
    }
    
});
