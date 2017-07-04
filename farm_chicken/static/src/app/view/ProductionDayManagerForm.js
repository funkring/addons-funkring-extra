/*global Ext:false*/

Ext.define('ChickenFarm.view.ProductionDayManagerForm', {
    extend: 'Ext.form.FormPanel',    
    requires: [
        'Ext.form.FieldSet', 
        'Ext.field.Text',
        'Ext.field.Number',
        'Ext.field.Toggle'
    ],
    xtype: 'chf_production_day_manager_form',    
    config: {
        scrollable: true,
        saveable: true,
        items: [
            {
                xtype: 'fieldset',
                items: [
                    {
                        xtype: 'togglefield',
                        name: 'valid',
                        label: 'Validiert'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'loss',
                        label: 'Ausfall'
                    },
                    {
                        xtype: 'togglefield',
                        name: 'loss_fix',
                        label: 'Ausfallanpassung'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'loss_fix_amount',
                        label: 'Ausfall korrigiert'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_total',
                        label: 'Eier Gesamt'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_broken',
                        label: 'Bruch Eier'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_dirty',
                        label: 'Schmutz Eier'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_weight',
                        label: 'Gewicht Eier (g)'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'weight',
                        label: 'Gewicht Hühner (kg)'
                    },
                    {
                        xtype: 'textareafield',
                        label: 'Notiz',
                        name: 'note'
                    }   
                ]   
            }    
        ]       
    }
});