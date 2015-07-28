/*global Ext:false, futil:false*/
Ext.define('Fclipboard.view.PricelistView', {
    extend: 'Ext.Container',
    xtype: 'pricelist',
    requires: [
        'Ext.data.Store',
        'Ext.data.StoreManager',
        'Ext.dataview.List',
        'Ext.field.Search',
        'Ext.util.DelayedTask'
    ],
    id: 'pricelistView',
    config: {
        
        searchValue: null,
        
        pricelist: null,
        
        productAmount: {},
        
        title: 'Preisliste',
        
        items: [{
            docked: 'top',
            xtype: 'toolbar',
            ui: 'neutral',
            items: [{
                    xtype: 'searchfield',
                    placeholder: 'Suche',
                    flex: 1,
                    listeners: {
                        keyup: function(field, key, opts) {
                            Ext.getCmp('pricelistView').searchDelayed(field.getValue());
                        },
                        clearicontap: function() {
                            Ext.getCmp('pricelistView').searchDelayed(null);
                        }
                    }                       
                }                                         
            ]                           
        },                        
        {
            xtype: 'list',
            height: '100%',
            id: 'pricelist',
            store: 'PricelistItemStore',
            cls: 'PriceListItem',
            grouped: true,
            listeners: {
                itemtap: function(list, index, element, record) {
                    setTimeout(function() {
                       list.deselect(index); 
                    },500);
                    Ext.getCmp('pricelistView').showNumberInput(element, record.get('product_id') );
                }
            }         
        }]
             
        
    },
              
    initialize: function() {
         var self = this;
         self.callParent(arguments);
         
         var pricelist = Ext.getCmp("pricelist");
         
         
         pricelist.setItemTpl(Ext.create('Ext.XTemplate', 
                                '<div class="col-10 {cls}">{code}</div>',
                                '<div class="col-70 {cls}">{name}</div>',
                                '<div class="col-10 {cls}">{uom}</div>',
                                '<div class="col-10-right {cls}">{amount}</div>',
                                '<div class="col-last {cls}"></div>',
                            {
                              apply: function(values, parent) {
                                 var amount = self.getProductAmount()[values.product_id];
                                 if ( !amount ) {
                                        amount = 0.0;
                                 }
                                 
                                 var cls='';
                                 if (amount > 0.0) {
                                    cls = ' col-positive';
                                 }
                                 
                                 values.cls = cls;
                                 values.amount = futil.formatFloat(amount);
                                 return this.applyOut(values, [], parent).join('');
                              }      
                            }));
         
         //
         self.searchTask = Ext.create('Ext.util.DelayedTask', function() {
             self.search();
         });
         
         //store
         var store = Ext.getStore("PricelistItemStore");
         store.setData(self.getPricelist().products);

         // search
         self.search();
    },
    
    searchDelayed: function(searchValue) {
        this.setSearchValue(searchValue);
        this.searchTask.delay(500);
    },
       
    search: function() {        
       var self = this;
       
       var store = Ext.getStore("PricelistItemStore");
       
       
       
       var searchValue = self.getSearchValue();
       var pricelist = self.getPricelist();
       
       var options = {
           params : {
              limit: 100
           }
       };
       
       if ( !Ext.isEmpty(searchValue) ) {
         store.filter([{
            property: "name",
            value: searchValue,
            anyMatch: true
         }]);         
       } else {
           store.clearFilter();
       }       
       
       
       store.load(options);
   },
   
    showNumberInput: function(nextTo, product_id) {
        var self = this;
        
        //check number view
        if ( !self.numberInputView ) {
            self.numberInputView = Ext.create('Fclipboard.view.NumberInputView');
        }
        
        // show
        self.numberInputView.showBy(nextTo, 'tl-tr?', false, self.getProductAmount()[product_id], function(numInput, newVal) { 
            self.getProductAmount()[product_id]=newVal;
            self.search();
        });
    },
  
});