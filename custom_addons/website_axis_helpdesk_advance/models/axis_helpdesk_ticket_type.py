# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class axisTicketType(models.Model):
    _name = "axis.helpdesk.ticket.type"
    _description = "Helpdesk Ticket Type"


    def _default_domain_member_ids(self):
        return [('groups_id', 'in', self.env.ref('website_axis_helpdesk_advance.group_helpdesk_ticket_users').id)]


    name = fields.Char(string="Name",required=1)
    type_based_on = fields.Selection([('helpdesk_team', 'Helpdesk Team'), ('users', 'Users')], string="Type Based On",
                                     default="helpdesk_team")
    team_ids = fields.Many2many("axis.helpdesk.ticket.team",string="Helpdesk Teams")
    user_ids = fields.Many2many('res.users', string="Users", domain=lambda self: self._default_domain_member_ids())
