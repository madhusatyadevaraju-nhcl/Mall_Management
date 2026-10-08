from odoo import models, fields, api


class RentalConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    reminder_days = fields.Integer(string='Days', default=5,
                                   config_parameter='rental_management.reminder_days')
