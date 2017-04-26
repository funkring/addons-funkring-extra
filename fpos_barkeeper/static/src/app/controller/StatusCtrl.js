/* global Ext:false, Core:false, ViewManager:false, futil:false */

Ext.define('BarKeeper.controller.StatusCtrl', {
    extend: 'Ext.app.Controller',
    requires:[         
         'Ext.form.ViewManager',
         'Ext.ux.Deferred',
         'Ext.dataview.List',
         'BarKeeper.core.Core',
         'BarKeeper.view.StatusView',
         'BarKeeper.model.Status'
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
        Core.getModel('pos.config').call('barkeeper_status',[options],{context:Core.getContext()}).then(function(data) {
            ViewManager.stopLoading();
            self.data.set('status', data);  
        }, function(err) {            
            ViewManager.handleError(err);
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
        }
    },
    
    selectPosConfig: function() {
        var self = this;
        ViewManager.startLoading('Lade Daten...');
        Core.getModel('pos.config').call('search_read', [[['parent_user_id','=',null],['state','=','active']], ['name']],{context:Core.getContext()}).then(function(rows) {
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
           ViewManager.handleError(err);
        });
       
    }
    
});
