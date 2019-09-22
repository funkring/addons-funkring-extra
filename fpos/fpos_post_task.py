# -*- coding: utf-8 -*-
#############################################################################
#
#    Copyright (c) 2007 Martin Reisenhofer <martin.reisenhofer@funkring.net>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _

class fpos_post_task(models.Model):
  _name = "fpos.post.task"
  _description = "Post Order Task"
  
  _inherits = {
    "automation.task": "task_id"
  }
  
 
  task_id = fields.Many2one("automation.task", "Task", required=True, index=True, ondelete="cascade")
  config_id = fields.Many2one("pos.config", "Point of Sale", readonly=True, states={'draft': [('readonly', False)]})
  
  def _run_options(self):
    self.ensure_one()
    return  {
      "stages": 1,
      "singleton": True
    }
  
  @api.multi
  def action_queue(self):
    return self.task_id.action_queue()
  
  @api.multi
  def action_cancel(self):
    return self.task_id.action_cancel()
  
  @api.multi
  def action_refresh(self):
    return self.task_id.action_refresh()
  
  @api.multi
  def action_reset(self):
    return self.task_id.action_reset()
  
  @api.model
  @api.returns("self", lambda self: self.id)
  def create(self, vals):
    res = super(fpos_post_task, self).create(vals)
    res.res_model = self._name
    res.res_id = res.id
    return res
  
  @api.multi
  def unlink(self):
    cr = self._cr
    ids = self.ids
    cr.execute("SELECT task_id FROM %s WHERE id IN %%s AND task_id IS NOT NULL" % self._table, (tuple(ids),))
    task_ids = [r[0] for r in cr.fetchall()]
    res = super(fpos_post_task, self).unlink()
    self.env["automation.task"].browse(task_ids).unlink()
    return res
  
  @api.onchange("config_id")
  def onchange_name(self):
    if self.config_id:
      self.name = _("Post %s") % self.config_id.name
    else:
      self.name = _("Post All")
  
  @api.one  
  def _run(self, taskc):
    # build config domain
    config_domain = []
    if self.config_id:
      config_domain = [("id", "=", self.config_id.id)]
    
    # search configs
    pos_configs = self.env["pos.config"].search(config_domain)
    if pos_configs:
      fpos_order_obj = self.env["fpos.order"]
      
      # post orders
      taskc.substage("Post", total = len(pos_configs))
      for pos_config in pos_configs:
        taskc.substage(pos_config.name)
        orders = fpos_order_obj.search([("fpos_user_id","=",pos_config.user_id.id), ("state","=","paid")], order="seq asc")
        orders._post()
        taskc.done()
        
      taskc.done()
      
    taskc.done()