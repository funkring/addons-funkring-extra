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
from openerp.exceptions import Warning
from openerp.addons.at_base import util
from openerp.addons.at_base import format
from datetime import datetime
from babel.dates import format_date
from openerp import tools


class chicken_logbook(models.Model):
    
    @api.one
    def action_start(self):
        if self._get_active(self.house_id.id):
            raise Warning(_("Only one active logbook per house allowed!"))
        return self.write({"state":"active"})
    
    @api.multi
    def action_draft(self):
        log_obj = self.env["farm.chicken.log"]
        logs = log_obj.search([("logbook_id","in",self.ids)])
        logs.write({"state":"valid"})        
        return self.write({"state":"draft"})
    
    @api.multi
    def action_done(self):
        log_obj = self.env["farm.chicken.log"]
        logs = log_obj.search([("logbook_id","in",self.ids),("state","!=","valid")])
        if logs:
            raise Warning(_("There are unvalided logbook entries"))
        
        for log in self:
            self._cr.execute("SELECT MAX(l.day) FROM farm_chicken_log l WHERE l.logbook_id = %s", (log.id,))
            row = self._cr.fetchone()
            if row and row[0]:
                log.write({"date_end":row[0]})
        
        logs = log_obj.search([("logbook_id","in",self.ids),("state","=","valid")])
        logs.write({"state":"done"})
        return self.write({"state":"done"})
    
    @api.multi
    def action_validate(self):
        log_obj = self.env["farm.chicken.log"]
        for logbook in self:
            if logbook.state == "active":
                logs = log_obj.search([("logbook_id","=",logbook.id)], order="day asc")
                logs._calc_beyond()
        return True
    
    @api.multi
    def action_inactive(self):
        return self.write({"state":"inactive"})
    
    @api.multi
    def name_get(self):
        result = []
        for book in self:
            result.append((book.id, "%s / %s" % (book.house_id.name,book.name)))
        return result
    
    @api.model
    def _default_name(self):
        return self.env["ir.sequence"].get("farm.chicken.logbook") or "/"
    
    @api.model
    def _get_active(self, house_id):
        res = self.search([("house_id","=",house_id),("state","=","active")],limit=1)
        return res and res[0] or None
    
    @api.model
    def import_logs(self, house_id, data):
        logbook = self._get_active(house_id)
        if not logbook:
            raise Warning(_("No active logbook for house %s") % house_id)
        
        log_obj = self.env["farm.chicken.log"]
        for day, values in data.iteritems():
            if day < logbook.date_start or (logbook.date_end and logbook.date_end < day):
                continue
            
            log = log_obj.search([("logbook_id","=",logbook.id),("day","=",day)],limit=1)
            log = log and log[0] or None
            
            if not log:
                values["day"]=day
                values["logbook_id"]=logbook.id
                log = log_obj.create(values)
            elif log.state == "draft":
                if log.feed_manual:
                    values.pop("feed")
                log.write(values)
        return True
     
    @api.one
    def logbook_weeks(self):
        weeks = []
        
        f = format.LangFormat(self._cr, self._uid, self._context)
        week_start = util.getFirstOfWeek(self.date_start)
        date_end = self.date_end or util.getPrevDayDate(util.getFirstOfNextWeek(util.currentDate()))
        
        while week_start <= date_end:
            week_str = datetime.strftime(util.strToDate(week_start), _("CW %W"))
            week_first = week_start
            week_start = util.getFirstOfNextWeek(week_start)
            week_end = util.getPrevDayDate(week_start)
            
            weeks.append({
                "name": week_str,
                "date_start": week_first,
                "group": week_first[:7],
                "start": f.formatLang(week_first, date=True),
                "end": f.formatLang(week_end,  date=True)
            })                          
            
        weeks.sort(key=lambda v: v["date_start"], reverse=True)
        return weeks
     
    @api.one
    def update_day(self, values, next_state=None):
        log_obj = self.env["farm.chicken.log"]
        logs = log_obj.search([("logbook_id","=",self.id),("day","=",values["day"])])
        values["logbook_id"] = self.id
        if not logs:            
            log = log_obj.create(values)
        else:
            log = logs[0]
            if log.state != "draft" and next_state != "draft":
                raise Warning(_("Unable to change logentry which is already validated"))
            log.write(values)
            
        if log.state == "done":
            raise Warning(_("Done log could not be changed!"))
            
        if next_state:           
            if log.state != next_state:
                if next_state == "draft":
                    log.action_draft()
                elif next_state == "valid":
                    log.action_validate()
        return log.id
    
    @api.one
    def logbook_week(self, date_start=None):
        if not date_start:
            date_start = util.currentDate()
        
        f = format.LangFormat(self._cr, self._uid, self._context)
                
        week_start = util.getFirstOfWeek(date_start)
        week_next = util.getFirstOfNextWeek(date_start)
        week_str = datetime.strftime(util.strToDate(week_start), _("CW %W"))
        
        week_day = week_start
        week_end = week_day
        
        days = []
        log_obj = self.env["farm.chicken.log"]
        
        sum_loss = 0
        
        first_weight = 0.0
        
        valid_count = 0
        fill_count = 0
        day_count = 0
        
        chicken_count = 0
        
        avg_data = {}
        
        def getAvg(name, calc=True):
            data = avg_data.get(name, None)
            if data is None:
                data = {
                    "val": [],
                    "avg": 0.0
                }
                avg_data[name] = data
                
            if calc:
                val = data["val"][:7]
                val_len = len(val)
                if val_len:
                    data["avg"] = sum(val) / val_len
                
            return data
        
        def addAvg(name, val):
            if val:
                data = getAvg(name, calc=False)                
                data["val"].insert(0,val)
            return val
        
        # get 14 logs for average calc
        logByDay = {}        
        logs = log_obj.search([("logbook_id","=",self.id),("day","<",week_next)], limit=14, order="day desc")
        if logs:
            # set new start
            week_day_avg = logs[-1].day
            if week_day_avg < week_day:
                week_day = week_day_avg
            # assign log  
            for log in logs:
                logByDay[log.day] = log
                
        chicken_age_weeks = 0
        
        while week_day < week_next:
            week_end = week_day
            
            loss = 0
            loss_fix = False
            loss_fix_amount = 0
            loss_amount = 0            
            eggs_performance = 0.0
            weight = 0
            
            eggs_total = 0
            eggs_broken = 0
            eggs_dirty = 0
            eggs_weight = 0
            eggs_machine = 0
            chicken_age = 0
            
            feed = 0
            water = 0
            
            valid = False
            filled = False
            note = ""
            
            log = logByDay.get(week_day)
            if log:
                loss = log.loss
                loss_amount = log.loss_amount or 0
                loss_fix = log.loss_fix
                loss_fix_amount = log.loss_fix_amount
                
                eggs_total = addAvg("eggs_total", log.eggs_total)                
                eggs_broken = addAvg("eggs_broken", log.eggs_broken)
                eggs_dirty = addAvg("eggs_dirty", log.eggs_dirty)
                eggs_weight = addAvg("eggs_weight", log.eggs_weight)
                eggs_machine = addAvg("eggs_machine", log.eggs_machine)
                eggs_performance = addAvg("eggs_performance", log.eggs_performance)
                
                feed = addAvg("feed", log.feed)
                water = addAvg("water", log.water)
                
                weight = log.weight
                if weight and not first_weight:
                    first_weight = weight
                
                chicken_count = log.chicken_count
                
                note = log.note or note
                chicken_age_weeks = log.chicken_age_weeks
                chicken_age = log.chicken_age
                valid = log.state != "draft"
                filled = True
            
            if filled:
                day_count += 1            
                sum_loss += loss_amount
            
            # add day only if within week
            if week_day >= week_start:
                if filled:
                    fill_count += 1
                if valid:
                    valid_count += 1
                
                days.append({
                    "name" : format_date(util.strToDate(week_day), "E d.M.y", locale=self._context.get("lang") or tools.config.defaultLang),
                    "day": week_day,
                    "loss": loss,
                    "loss_fix": loss_fix,
                    "loss_fix_amount": loss_fix_amount,
                    "eggs_total": eggs_total,
                    "eggs_broken": eggs_broken,
                    "eggs_dirty": eggs_dirty,
                    "eggs_weight": eggs_weight,
                    "eggs_machine" : eggs_machine,
                    "weight": weight,
                    "note": note,
                    "valid": valid,
                    "filled": filled,
                    "chicken_age_weeks": chicken_age_weeks,
                    "overview" :  [               
                        {
                            "name": _("Eggs Total"),
                            "value": "%s" % eggs_total                  
                        },
                        {
                            "name": _("Eggs Machine"),
                            "value": "%s" % eggs_machine
                        },  
                        {
                            "name": _("Broken Eggs"),
                            "value": "%s" % eggs_broken
                        },
                        {
                            "name" : _("Dirty Eggs"),
                            "value": "%s" % eggs_dirty
                        },
                        {
                            "name": _("Eggs Weight"),
                            "value": "%s g" % f.formatLang(eggs_weight) 
                        },
                        {
                            "name": _("Egg Performance"),
                            "value" : "%s %%" % f.formatLang(eggs_performance)
                        },
                        {
                            "name": _("Loss"),
                            "value": "%s" % loss_amount                    
                        },
                        {
                            "name": _("Chicken Count"),
                            "value": "%s" % chicken_count
                        },                        
                        {
                            "name": _("Chicken Weight"),
                            "value": "%s kg" % f.formatLang(weight) 
                        },
                        {
                            "name": _("Day Age"),
                            "value": "%s" % chicken_age
                        },
                        {
                            "name": _("Feed"),
                            "value": "%s kg" % f.formatLang(feed, digits=0) 
                        },
                        {
                            "name": _("Water"),
                            "value" : "%s l" % f.formatLang(water)
                        }                        
                    ] 
                })
            
            week_day = util.getNextDayDate(week_day)
            
       
        days_len = len(days)
        return {
            "name": "%s %s" % (self.name, week_str),
            "week" : week_str,
            "date" : week_start,
            "start" : f.formatLang(week_start, date=True),
            "end" : f.formatLang(week_end, date=True),
            "filled": days_len == fill_count,
            "validated": days_len == valid_count,
            "days": days,
            "overview" : [               
                {
                    "name" : _("Eggs"),
                    "value": "%s" % f.formatLang(getAvg("eggs_total")["avg"])                  
                },
                {
                    "name" : _("Eggs Machine"),
                    "value": "%s" % f.formatLang(getAvg("eggs_machine")["avg"])
                },  
                {
                    "name" : _("Broken Eggs"),
                    "value": "%s" % f.formatLang(getAvg("eggs_broken")["avg"])
                },
                {
                    "name" : _("Dirty Eggs"),
                    "value": "%s" % f.formatLang(getAvg("eggs_dirty")["avg"])
                },
                {
                    "name" : _("Eggs Weight"),
                    "value": "%s g" % f.formatLang(getAvg("eggs_weight")["avg"]) 
                },
                {
                    "name": _("Egg Performance"),
                    "value" : "%s %%" % f.formatLang(getAvg("eggs_performance")["avg"])
                },
                {
                    "name" : _("Loss"),
                    "value": "%s" % sum_loss,                    
                },
                {
                    "name" : _("Chicken Count"),
                    "value": "%s" % chicken_count 
                },                
                
                {
                    "name" : _("Chicken Weight"),
                    "value": "%s kg" % f.formatLang(first_weight) 
                },
                {
                    "name": _("Week Age"),
                    "value": "%s" % chicken_age_weeks
                },                
                {
                    "name": _("Feed"),
                    "value": "%s kg" % f.formatLang(getAvg("feed")["avg"], digits=0) 
                },
                {
                    "name": _("Water"),
                    "value" : "%s l" % f.formatLang(getAvg("water")["avg"])
                }       
            ]            
        }
            
    
    @api.one
    @api.depends("chicken_age")
    def _compute_chicken_age_weeks(self):
        self.chicken_age_weeks = self.chicken_age / 7.0 
                             
    
    _name = "farm.chicken.logbook"
    _description = "Logbook"
    _inherit = ["mail.thread"]
    _order = "date_start desc"
    
    name = fields.Char("Name", required=True, default=_default_name)
    date_start = fields.Date("Start", required=True, index=True, readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date("End", index=True, readonly=True)
    house_id = fields.Many2one("farm.house", string="House", index=True, required=True, readonly=True, states={'draft': [('readonly', False)]})
    chicken_count = fields.Integer("Chicken Count", readonly=True, states={'draft': [('readonly', False)]})
    chicken_age = fields.Integer("Chicken Age [Days]", help="Chicken age in days", readonly=True, states={'draft': [('readonly', False)]})
    chicken_age_weeks = fields.Integer("Chicken Age [Weeks]", help="chicken age in weeks", readonly=True, compute="_compute_chicken_age_weeks")
    log_ids = fields.One2many("farm.chicken.log", "logbook_id", "Logs")
    state = fields.Selection([("draft","Draft"),
                              ("active","Active"),
                              ("inactive","Inactive"),
                              ("done","Done")],string="State", index=True, default="draft")
        
               
class chicken_log(models.Model):

    @api.one
    def _parent_log(self):
        parent_house = self.logbook_id.house_id.parent_id
        if parent_house:
            parent_logs = self.search([("logbook_id.house_id","=",parent_house.id),("day","=",self.day)])
            return parent_logs and parent_logs[0] or None
            
    
    @api.multi
    def action_draft(self):
        return self.write({"state":"draft"})
        
    @api.one
    def _validate_inv(self):
        # get childs
        parent = self.parent_id
        if not parent:
            parent = self
        logs = [parent]
        logs.extend(parent.child_ids)
        
        # get invoice logs
        inv_logs = []
        non_inv_logs = []
        inv_parent = False
        delivered = False
        for log in logs:
            if log.delivered:
                delivered = True
            if log.inv_exists:
                inv_logs.append(log)
                if log.id == parent.id:
                    inv_parent = True
            else:
                non_inv_logs.append(log)
        
        # check if invoice exist
        if inv_logs:
            for inv_log in inv_logs:
                inv_log.inv_hierarchy = True
                
            # check if parent has no invoice
            if not inv_parent:
                # sumup invoice fields
                inv_fields = {}
                for inv_field in self._inv_fields:
                    val = inv_logs[0][inv_field]
                    for inv_log in inv_logs[1:]:
                        val+=inv_log[inv_field]                    
                    inv_fields[inv_field] = val
                
                # set it to parent
                for inv_field,val in inv_fields.iteritems():
                    parent[inv_field] = val
                    
                if delivered:
                    parent.delivered=delivered 

        else:
            for log in logs:
                log.inv_hierarchy = False
        
        return True
            
    @api.multi
    def action_validate(self):
        for log in self:
            log._validate_inv()
            logs_after = log.search([("logbook_id","=",self.logbook_id.id),("day",">",self.day)], order="day desc")
            logs_after._validate_inv()
        return self.write({"state":"valid"})
    
    @api.one
    @api.depends("loss","loss_fix","loss_fix_amount")
    def _compute_loss_total(self):
        # add loss without fix
        self._cr.execute("SELECT SUM(COALESCE(loss,0)) FROM farm_chicken_log l "
                         " WHERE l.logbook_id = %s AND l.day <= %s AND NOT COALESCE(l.loss_fix,False) ", (self.logbook_id.id, self.day) )
        res = self._cr.fetchone()
        loss_total = res and res[0] or 0
        
        # add loss with fix
        self._cr.execute("SELECT SUM(COALESCE(loss_fix_amount,0)) FROM farm_chicken_log l "
                         " WHERE l.logbook_id = %s AND l.day <= %s AND l.loss_fix ", (self.logbook_id.id, self.day) )
        res = self._cr.fetchone()
        loss_total += res and res[0] or 0
        
        self.loss_total = loss_total
                
        self.loss_amount = self.loss
        if self.loss_fix:
            self.loss_amount = self.loss_fix_amount
        
    @api.one
    @api.depends("loss")
    def _compute_loss_total_real(self):
        self._cr.execute("SELECT SUM(COALESCE(loss,0)) FROM farm_chicken_log l "
                         " WHERE l.logbook_id = %s AND l.day <= %s ", (self.logbook_id.id, self.day) )
        res = self._cr.fetchone()
        loss_total = res and res[0] or 0
        
        self.loss_total_real = loss_total
        
    @api.one
    @api.depends("loss_total_real","loss")
    def _compute_chicken_count(self):
        self.chicken_count = self.logbook_id.chicken_count-self.loss_total_real
        
    @api.one
    @api.depends("eggs_total","eggs_removed")
    def _compute_eggs_count(self):        
        self._cr.execute("SELECT SUM(COALESCE(eggs_total,0))-SUM(COALESCE(eggs_removed,0))-(SUM(COALESCE(delivered_eggs_mixed,0))+SUM(COALESCE(delivered_eggs_industry,0))) FROM farm_chicken_log l "
                         " WHERE l.logbook_id = %s AND l.day <= %s ",
                         (self.logbook_id.id, self.day) )
        res = self._cr.fetchone()
        self.eggs_count = res and res[0] or None
          
    @api.one
    @api.depends("delivered_eggs_mixed",
                 "delivered_eggs_industry",
                 "inv_eggs_xl",
                 "inv_eggs_m",
                 "inv_eggs_l",
                 "inv_eggs_s",
                 "inv_eggs_s45g",
                 "inv_eggs_industry",
                 "inv_eggs_presorted")
    def _compute_delivery(self):
        self.delivered_eggs = self.delivered_eggs_mixed + self.delivered_eggs_industry
        self.inv_eggs = self.inv_eggs_xl + self.inv_eggs_l + self.inv_eggs_m + self.inv_eggs_s + self.inv_eggs_s45g + self.inv_eggs_industry + self.inv_eggs_presorted
        self.inv_diff_eggs = self.inv_eggs - self.delivered_eggs
        self.inv_diff_presorted = self.inv_eggs_presorted - self.delivered_eggs_industry
                
    @api.one
    @api.depends("logbook_id.date_start","logbook_id.chicken_age")
    def _compute_chicken_age(self):
        logbook = self.logbook_id
        dt_start = util.strToDate(logbook.date_start)
        dt_cur = util.strToDate(self.day)
        diff = dt_cur - dt_start
        self.chicken_age = logbook.chicken_age + diff.days
        self.chicken_age_weeks = self.chicken_age / 7.0 
    
    @api.one
    @api.depends("eggs_total","chicken_count")    
    def _compute_eggs_performance(self):
        if self.chicken_count:
            self.eggs_performance = 100.0 / self.chicken_count * self.eggs_total
        else:
            self.eggs_performance = 0.0
    
    @api.model
    def _default_logbook_id(self):        
        logbooks = self.env["farm.chicken.logbook"].search([("state","=","active")])
        default_day = util.currentDate()
        for logbook in logbooks:
            logs = self.search([("logbook_id","=",logbook.id),("day","=",default_day)])
            if not logs:                
                return logbook.id            
        return None
    
    @api.one
    @api.depends("day",
                 "logbook_id",
                 "logbook_id.house_id",
                 "logbook_id.house_id.parent_id")
    def _compute_parent_id(self):
        if self.state != "done":
            parent_log = None
            parent_house = self.logbook_id.house_id.parent_id
            
            if parent_house:
                # assign parent log
                parent_log = self.search([("day","=",self.day),
                                   ("logbook_id.state","=","active"),
                                   ("logbook_id.house_id","=",parent_house.id)])
                # create parent if not exist
                if parent_log:
                    parent_log = parent_log[0]
                    
            self.parent_id = parent_log
        
     
    @api.one
    def _validate(self, values=None):
        if self.state != "done":
            parent = self.parent_id
            
            # validate parent
            parent_house = self.logbook_id.house_id.parent_id
            if not parent and parent_house:
                logbook_obj = self.env["farm.chicken.logbook"]
                parent_logbook = logbook_obj._get_active(parent_house.id)
                if parent_logbook:                
                    self.parent_id = self.create({
                            "logbook_id" : parent_logbook.id,
                            "day" : self.day
                          })
                    parent = self.parent_id
            
            # check if parent exists
            # and validate
            if parent:
                # check for validate
                if values:
                    validate_fields = []            
                    for field in self._forward_fields:
                        if field in values:
                            validate_fields.append(field)
                else:
                    validate_fields = self._forward_fields
    
                # validate fields                
                if validate_fields:
                    childs = parent.child_ids
                    if childs:
                        values = self.read(validate_fields)[0]
                        for key in validate_fields:
                            val = values[key]
                            for child in childs:
                                if child.id == self.id:
                                    continue
                                val += child[key]
                            values[key]=val
                        parent.write(values)
     
    @api.multi                  
    def _calc_beyond(self):
        for field in ("chicken_count",
                      "chicken_age",
                      "chicken_age_weeks",
                      "eggs_performance"):
            self._fields[field]._compute_value(self)
                    
    def _create(self, cr, uid, vals, context=None):        
        res = super(chicken_log,self)._create(cr, uid, vals, context=context)
        # validate
        log = self.browse(cr, uid, res, context=context)
        log._validate(vals)
        # validate beyond
        log._calc_beyond()
        return res
                
    def _write(self, cr, uid, ids, vals, context=None):
        # check invalid
        invalid_ids = []
        if "loss" in vals:
            for stored_vals in self.search_read(cr, uid, [("id","in",ids)], ["loss"], order="day asc", context=context):
                if vals.get("loss",0) != stored_vals["loss"]:
                    invalid_ids.append(stored_vals["id"]) 
        
        # write
        res = super(chicken_log,self)._write(cr, uid, ids, vals, context=context)
        
        # validate        
        self.browse(cr, uid, ids, context=context)._validate(vals)
        # validate beyond
        if invalid_ids:
            cr.execute("SELECT l.logbook_id, MIN(l.day) FROM farm_chicken_log l WHERE l.id IN %s GROUP BY 1", (tuple(invalid_ids),))
            for logbook_id, day in cr.fetchall():
                log_ids = self.search(cr, uid, [("logbook_id","=",logbook_id),("day",">",day)], order="day asc")
                self.browse(cr, uid, log_ids, context=context)._calc_beyond()
            
        return res
    
    _name = "farm.chicken.log"
    _description = "Log"
    _inherit = ["mail.thread"]
    _order = "day desc, logbook_id"
    _rec_name = "day"
    
    _forward_fields = [
        "feed",
        "water",
        "eggs_machine"         
    ]
    _inv_fields = [
         "delivered_eggs_mixed",
         "delivered_eggs_industry",
         "inv_eggs_xl",
         "inv_eggs_m",
         "inv_eggs_l",
         "inv_eggs_s",
         "inv_eggs_s45g",
         "inv_eggs_industry",
         "inv_eggs_presorted"     
    ]
    _calc_fields = [
        "loss",
        "eggs_total"
    ]
    
    _sql_constraints = [
        ("date_uniq", "unique(logbook_id, day)",
            "Only one log entry per day allowed!")
    ]
    
    logbook_id = fields.Many2one("farm.chicken.logbook","Logbook",required=True, index=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_logbook_id, ondelete="restrict")
    
    day = fields.Date("Day", required=True, readonly=True, index=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: util.currentDate())
    
    loss = fields.Integer("Loss", readonly=True, states={'draft': [('readonly', False)]})
    loss_fix = fields.Boolean("Loss Fix", readonly=True, states={'draft': [('readonly', False)]})
    loss_fix_amount = fields.Integer("Loss Fix Amount", readonly=True, states={'draft': [('readonly', False)]})
    loss_total = fields.Integer("Loss Total", readonly=True, compute="_compute_loss_total")
    loss_total_real = fields.Integer("Real Loss", readonly=True, compute="_compute_loss_total_real")
    loss_amount = fields.Integer("Loss Amount", readonly=True, compute="_compute_loss_total")
    
    weight = fields.Float("Weight [kg]", readonly=True, states={'draft': [('readonly', False)]})
    feed_manual = fields.Boolean("Manual Feed Input", readonly=True, states={'draft': [('readonly', False)]})
    feed = fields.Float("Feet [kg]", readonly=True, states={'draft': [('readonly', False)]})
    water = fields.Float("Water [l]", readonly=True, states={'draft': [('readonly', False)]})
    co2 = fields.Float("Co2", readonly=True, states={'draft': [('readonly', False)]})
    temp = fields.Float("Temperature [°C]", readonly=True, states={'draft': [('readonly', False)]})
    humidity = fields.Float("Humidity [%]", readonly=True, states={'draft': [('readonly', False)]})
    eggs_total = fields.Integer("Eggs Total", readonly=True, states={'draft': [('readonly', False)]})
    eggs_machine = fields.Integer("Eggs Machine", readonly=True, states={'draft': [('readonly', False)]})
    
    eggs_nest = fields.Integer("Nest Eggs", readonly=True, states={'draft': [('readonly', False)]})
    eggs_top = fields.Integer("Eggs moved above", readonly=True, states={'draft': [('readonly', False)]})
    eggs_buttom = fields.Integer("Eggs laid down", readonly=True, states={'draft': [('readonly', False)]})    
    eggs_weight = fields.Float("Eggs Weight [g]", readonly=True, states={'draft': [('readonly', False)]})
    eggs_dirty = fields.Integer("Dirty Eggs", readonly=True, states={'draft': [('readonly', False)]})
    eggs_broken = fields.Integer("Broken Eggs", readonly=True, states={'draft': [('readonly', False)]})
    
    eggs_color = fields.Selection([(1,"01"),
                                   (2,"02"),
                                   (3,"03"),
                                   (4,"04"),
                                   (5,"05"),
                                   (6,"06"),
                                   (7,"07"),
                                   (8,"08"),
                                   (9,"09"),
                                   (10,"10"),
                                   (11,"11"),
                                   (12,"12"),
                                   (13,"13"),
                                   (14,"14"),
                                   (15,"15"),
                                  ]
                                  , string="Eggs Color", help="Color aligned to the DSM Yolk Color Fan" 
                                  , readonly=True, states={'draft': [('readonly', False)]})
    
    
    eggs_color_dote = fields.Selection([(1,"01"),
                                       (2,"02"),
                                       (3,"03"),
                                       (4,"04"),
                                       (5,"05")
                                      ]
                                      , string="Eggs Dote Color", help="Color aligned to the DSM Yolk Color Fan"
                                      , readonly=True, states={'draft': [('readonly', False)]}) 
    
    eggs_thickness = fields.Float("Eggs Thickness [kg]", readonly=True, states={'draft': [('readonly', False)]})
    
    state = fields.Selection([("draft","Draft"),
                              ("valid","Valid"),
                              ("done","Done")],
                              string="State", default="draft")
    
    eggs_removed = fields.Integer("Eggs Removed", readonly=True, states={'draft': [('readonly', False)]}) 
    
    chicken_age = fields.Integer("Chicken Age [Days]", readonly=True, compute="_compute_chicken_age", store=True)
    chicken_age_weeks = fields.Integer("Chicken Age [Weeks]", readonly=True, compute="_compute_chicken_age", store=True)
    chicken_count = fields.Integer("Chicken Count", readonly=True, compute="_compute_chicken_count", store=True)
    
    eggs_count = fields.Integer("Eggs Stock", readonly=True, compute="_compute_eggs_count")
    eggs_performance = fields.Float("Eggs Performance", readonly=True, compute="_compute_eggs_performance", store=True)
    
    delivered = fields.Boolean("Delivery", readonly=True, states={'draft': [('readonly', False)]})    
    delivered_eggs_mixed = fields.Integer("Delivered Eggs", readonly=True, states={'draft': [('readonly', False)]})
    delivered_eggs_industry = fields.Integer("Delivered Eggs Industry", readonly=True, states={'draft': [('readonly', False)]})
    delivered_eggs = fields.Integer("Delivered Eggs Total", readonly=True, compute="_compute_delivery", store=True)
    
    inv_exists = fields.Boolean("Invoice Exists", help="Standalone invoice for the delivery exists", states={'draft': [('readonly', False)]})
    inv_hierarchy = fields.Boolean("Invoice in Hierarchy Exists")
    inv_eggs_xl = fields.Integer("Invoiced Eggs XL", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs_l = fields.Integer("Invoiced Eggs L", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs_m = fields.Integer("Invoiced Eggs M", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs_s = fields.Integer("Invoiced Eggs S", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs_s45g = fields.Integer("Invoiced Eggs < 45g", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs_industry = fields.Integer("Invoiced Eggs Industry", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs_presorted = fields.Integer("Invoiced Eggs Industry (presorted)", readonly=True, states={'draft': [('readonly', False)]})
    inv_eggs = fields.Integer("Invoiced Eggs Total", readonly=True, compute="_compute_delivery", store=True)
    
    inv_diff_eggs = fields.Integer("Eggs Difference", readonly=True, compute="_compute_delivery", store=True)
    inv_diff_presorted = fields.Integer("Eggs Difference (presorted)", readonly=True, compute="_compute_delivery", store=True)
    
    child_ids = fields.One2many("farm.chicken.log", "parent_id", string="Child Logs", readonly=True)
    parent_id = fields.Many2one("farm.chicken.log", string="Parent Log", compute="_compute_parent_id", readonly=True, store=True)
    
    note = fields.Text("Note")
