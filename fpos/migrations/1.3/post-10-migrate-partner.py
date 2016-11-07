# -*- coding: utf-8 -*-
__name__ = "Correct available in pos of partner"

def migrate(cr,v):
    cr.execute("UPDATE res_partner SET available_in_pos=true WHERE id IN (SELECT o.partner_id FROM fpos_order o GROUP BY 1)")