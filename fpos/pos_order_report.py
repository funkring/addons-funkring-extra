# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
from openerp.osv import fields,osv

class pos_order_report(osv.osv):
    _inherit = "report.pos.order"
    _columns = {
        "config_id": fields.many2one('pos.config', "Point of Sale", readonly=True),
        "fpos_ga": fields.boolean("Group Order"),
        "weekday": fields.selection([(0,"Sunday"),
                                      (1,"Monday"),
                                      (2,"Tuesday"),
                                      (3,"Wednesday"),
                                      (4,"Thursday"),
                                      (5,"Friday"),
                                      (6,"Saturday")],
                                     string="Weekday"),
                
        "pos_categ_id": fields.many2one("pos.category","POS Category", readonly=True)
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_pos_order')
        cr.execute("""
            create or replace view report_pos_order as (
                select
                    min(l.id) as id,
                    count(*) as nbr,
                    s.date_order as date,
                    sum(l.qty * u.factor) as product_qty,
                    sum(l.qty * l.price_unit) as price_total,
                    sum((l.qty * l.price_unit) * (l.discount / 100)) as total_discount,
                    (sum(l.qty*l.price_unit)/sum(l.qty * u.factor))::decimal as average_price,
                    sum(cast(to_char(date_trunc('day',s.date_order) - date_trunc('day',s.create_date),'DD') as int)) as delay_validation,
                    s.partner_id as partner_id,
                    s.state as state,
                    s.user_id as user_id,
                    s.location_id as location_id,
                    se.config_id as config_id,
                    s.company_id as company_id,
                    s.sale_journal as journal_id,
                    l.product_id as product_id,
                    pt.categ_id as product_categ_id,
                    fo.ga as fpos_ga,
                    EXTRACT(DOW FROM fo.date) AS weekday,
                    pt.pos_categ_id
                from pos_order_line as l
                    left join pos_order s on (s.id=l.order_id)
                    left join fpos_order fo on (fo.id=s.fpos_order_id) 
                    left join product_product p on (p.id=l.product_id)
                    left join product_template pt on (pt.id=p.product_tmpl_id)
                    left join product_uom u on (u.id=pt.uom_id)
                    left join pos_session se on (se.id=s.session_id)
                group by
                    s.date_order, s.partner_id,s.state, pt.categ_id,
                    s.user_id,s.location_id,se.config_id,s.company_id,
                    s.sale_journal,l.product_id,s.create_date, fo.ga,
                    EXTRACT(DOW FROM fo.date),
                    pt.pos_categ_id
                having
                    sum(l.qty * u.factor) != 0)""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
