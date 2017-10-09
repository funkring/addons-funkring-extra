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

from openerp.osv import fields, osv

class res_partner(osv.Model):
  
  def _reg_active(self, cr, uid, ids, field_name, arg, context=None):
    res = dict.fromkeys(ids, False)
    
    sql_params = (tuple(ids),)
    
    # search active student
    cr.execute("SELECT p.id FROM academy_registration r "
               " INNER JOIN academy_student s ON s.id = r.student_id "
               " INNER JOIN res_partner p ON p.id = s.partner_id "
               " WHERE p.id IN %s AND r.state != 'cancel' ", sql_params)
    
    for row in cr.fetchall():
      res[row[0]] = True
          
    # search active parents
    cr.execute("SELECT p.id FROM academy_registration r "
               " INNER JOIN res_partner p ON p.id = r.student_parent_id "
               " WHERE p.id IN %s AND r.state != 'cancel' ", sql_params)
    
    for row in cr.fetchall():
      res[row[0]] = True
      
    # search active payers
    cr.execute("SELECT p.id FROM academy_registration r "
               " INNER JOIN res_partner p ON p.id = r.invoice_address_id "
               " WHERE p.id IN %s AND r.state != 'cancel' ", sql_params)
    
    for row in cr.fetchall():
      res[row[0]] = True
    
    return res
  
  def _relids_registration(self, cr, uid, ids, context=None):
    cr.execute("SELECT s.partner_id, r.student_parent_id, r.invoice_address_id "
               " FROM academy_registration r "
               " INNER JOIN academy_student s ON s.id = r.student_id "               
               " WHERE r.id IN %s ", (tuple(ids),))
    
    res = set()
    for partner_id, parent_id, invoice_partner_id in cr.fetchall():
      if partner_id:
        res.add(partner_id)
      if parent_id:
        res.add(parent_id)
      if invoice_partner_id:
        res.add(invoice_partner_id)
        
    return list(res) 
  
  _inherit = "res.partner"
  _columns = {
    "reg_active" : fields.function(_reg_active, string="Active Registration", type="boolean", readonly=True, store={
      "academy.registration" : (_relids_registration,["student_id","student_parent_id","invoice_address_id","state"], 10)
    })
  }