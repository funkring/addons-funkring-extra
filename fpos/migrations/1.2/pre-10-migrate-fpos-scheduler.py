# -*- coding: utf-8 -*-
__name__ = "Correct Fpos scheduler"

def migrate(cr,v):
    cr.execute("UPDATE ir_model_data SET noupdate=false WHERE name='cron_fpos_post' and module='fpos'")
