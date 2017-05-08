/*global Ext:false, openerp:false*/

Ext.define('DeliveryPicking.core.Core', {
    singleton : true,
    alternateClassName: 'Core',
    
    requires: [
        'Ext.ux.Deferred',
        'Ext.form.ViewManager'
    ],
    
    config : {       
         version : '1.0.0',
         status: null,
         context: null
    },
       
    constructor: function(config) {
        var self = this;        
        self.initConfig(config);
    
         // create odoo service and client
        self.service = new openerp.init();
        self.client = new this.service.web.WebClient();
        self.models = {};
    },
    
    /** Setup Barkeeper Core **/
    setup: function() {
        var self = this;
        var deferred = Ext.create('Ext.ux.Deferred');
            
        var user_obj = self.getModel('res.users');
        // query context
        user_obj.call('context_get').then(function(context) {
            self.setContext(context);
            // query user
            user_obj.call('whoami',[],{context:context}).then(function(status) {
                // query company
                user_obj.call("read", [status.uid, ["company_id"]], {context:context} ).then(function(res) {
                   status.company_id = res.company_id[0];
                   status.company = res.company_id[1];
                   self.setStatus(status);
                   deferred.resolve(status);
                }, function(err) {
                     deferred.reject(err);
                });                             
            }, function(err) {
                deferred.reject(err);  
            });            
        }, function(err) {
            deferred.reject(err);
        });
       
        return deferred.promise();
    },
    
    getModel: function(model) {
        return new this.service.web.Model(model);
    },
            
    restart: function() {      
        setTimeout(function() {
            window.location.reload();  
        }, 1000);        
    },
    
    call: function(model, method, args, kwargs) {
        var self = this;
        var deferred = Ext.create('Ext.ux.Deferred');
        
        var modelSvc = self.models[model];
        if ( !modelSvc ) {
            modelSvc = self.getModel(model);
            self.models[model] = modelSvc;
        }
        
        if ( !kwargs ) {
            kwargs = {context:self.getContext()};
        }
        
        modelSvc.call(method, args, kwargs).then(function(res) {
            deferred.resolve(res);
        }, function(err) {
            deferred.reject(err);
            self.models[model] = null;
        });
        
        return deferred.promise();
    }
   
});