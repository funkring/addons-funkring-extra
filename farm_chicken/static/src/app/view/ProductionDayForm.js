/*global Ext:false*/

Ext.define('ChickenFarm.view.ProductionDayForm', {
    extend: 'Ext.form.FormPanel',    
    requires: [
        'Ext.form.FieldSet', 
        'Ext.field.Text',
        'Ext.field.Number'
    ],
    xtype: 'chf_production_day_form',    
    config: {
        scrollable: true,
        saveable: true,
        items: [
            {
                xtype: 'fieldset',
                title: 'Tagesdaten',
                items: [
                    {
                        xtype: 'numberfield',
                        name: 'loss',
                        label: 'Ausfall'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_total',
                        label: 'Eier Gesamt'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_broken',
                        label: 'Bruch'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_dirty',
                        label: 'Schmutz'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'eggs_weight',
                        label: 'Ei-KG'
                    },
                    {
                        xtype: 'numberfield',
                        name: 'weight',
                        label: 'Hü-KG'
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