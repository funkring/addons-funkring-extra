/*global Ext:false, futil:false */

/**
 * reader
 */
Ext.define('Ext.data.reader.JsonOdoo', {
    extend: 'Ext.data.reader.Json',
    alias : 'reader.odoo',

    createFieldAccessExpression: function(field, fieldVarName, dataName) {
        var me     = this,
            re     = me.objectRe,
            hasMap = (field.getMapping() !== null),
            map    = hasMap ? field.getMapping() : field.getName(),
            result, operatorSearch;

        if (typeof map === 'function') {
            result = fieldVarName + '.getMapping()(' + dataName + ', this)';
        }
        else if (me.getUseSimpleAccessors() === true || ((operatorSearch = String(map).search(re)) < 0)) {
            if (!hasMap || isNaN(map)) {
                // If we don't provide a mapping, we may have a field name that is numeric
                map = '"' + map + '"';
            }
            result = dataName + "[" + map + "]";
        }
        else {
            result = dataName + (operatorSearch > 0 ? '.' : '') + map;
        }

        return result + " || null";
    }
});


/**
 * proxy
 */
Ext.define('Ext.data.proxy.Odoo',{
    extend: 'Ext.data.proxy.Ajax',
    alias: 'proxy.odoo',
    requires: [ 'Ext.data.reader.Json', 
                'Ext.data.writer.Json'],
    config: {
        
        startParam: null,
        limitParam: null,
        pageParam: null,
        batchActions: false,
                
        reader: {
             type: 'odoo',
             rootProperty: 'result'
        },
        
        writer: {
             type: 'json',
             encodeRequest: true            
        }, 
         
        
        sortParam: null,
        filterParam: null,
        
        resModel: null,
        client: null,
        recordDefaults: null,
        core: null
    },
   
    constructor: function(config) {
        this.callParent(arguments);        
    },
    
    buildRequest: function(operation) {
        var me = this,
            params = Ext.applyIf(operation.getParams() || {}, me.getExtraParams() || {}),
            request;

        //copy any sorters, filters etc into the params so they can be sent over the wire
        params = Ext.applyIf(params, me.getParams(operation));

        request = Ext.create('Ext.data.Request', {
            params   : params,
            action   : operation.getAction(),
            records  : operation.getRecords(),
            url      : operation.getUrl(),
            operation: operation,
            proxy    : me
        });

        operation.setRequest(request);
        return request;
    },
    
    setException: function(operation, response) {
        if (Ext.isObject(response)) {
            operation.setException({
                status: response.status,
                statusText: response.statusText
            });
        }
    },
    
    doRequest: function(operation, callback, scope) {
        var self = this;
        var action = operation.getAction();
        var model = operation.getModel();
        
        var args = null;
        var cmd = null;
        var kwargs = {};
        
        if ( action === 'read' ) {
            cmd = 'search_read';
            var domain = [];
            
            // add filter
            var filters = operation.getFilters();
            if ( filters ) {
                Ext.each(filters, function(filter) {
                    var op = '=';
                    if (filter.anyMatch ) {
                        if ( filter.caseSensitive ) {
                            op = 'like';
                        } else {
                            op = 'ilike';                            
                        }
                    } 
                    domain.push([filter.property,op,filter.value]);
                });
            }
            
            // add sort
            var sorters = operation.getSorters();
            if ( sorters ) {
                var order = '';
                Ext.each(sorters, function(sorter) {
                    if ( order.length > 0 ) {
                        order += ", ";
                    }
                    
                    order += sorter.property;
                    order += ' ';
                    
                    if (sorter.direction) order += sorter.direction;
                });
                
                if ( order.length > 0 ) kwargs.order = order;
            }
            
            var fields = [];
            Ext.each(model.getFields().items, function(field) {
               fields.push(field.getName()); 
            });

            // add args
            args = [
                domain,
                fields
            ];
            
            var op_params = operation.getParams();
            if ( op_params ) {
                kwargs.limit = op_params.limit || 100;
            }
        } else if ( action == 'update' ) {
           cmd = 'write';
           // handle only one record
           Ext.each(operation.getRecords(), function(record) {
               args = [
                    record.getData().id,
                    record.getData()
               ];
           });
        } else if ( action == 'create' ) {
            cmd = 'create';
            // handle only one record
            Ext.each(operation.getRecords(), function(record) {
               args = [                   
                    record.getData()
               ];
            });
            
            
        }
        
        if ( !self.modelSvc ) {
            self.modelSvc = self.getCore().getModel(this.getResModel());
        }
        
        var afterCallback = function() {
            if (typeof callback == 'function') {
               callback.call(scope || self, operation);
            }
        };
        
        var request = self.buildRequest(operation);    
        self.modelSvc.call(cmd, args, kwargs).then(function(res) {
            // handle result
            var reader = self.getReader();
            var resultSet = null;
            try {
                resultSet = reader.process(res);
            } catch (e) {
                // handle exception during processing
                operation.setException(e.message);
                self.fireEvent('exception', self, res, operation);
                return;
            }
            
            afterCallback();            
        }, function(err) {
            // handle exception from server
            self.modelSvc = null;
            self.setException(operation, err);
            self.fireEvent('exception', self, err, operation);            
            afterCallback();
        });    
        
        return request;
    }
    
});