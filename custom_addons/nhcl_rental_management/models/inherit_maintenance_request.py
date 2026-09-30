from datetime import datetime, timedelta
from odoo import fields, api, models, _


class Maintenance(models.Model):
    _inherit = 'maintenance.request'

    preventing_maintenance_ids = fields.One2many(
        'preventing.maintenance', 'maintenance_request_id',
        string='Preventing Maintenance'
    )
    maintenance_types = fields.Selection([
        ('monthly', 'Monthly'),
        ('quaterly', 'Quaterly'),
        ('halfyear', 'Half Yearly'),
        ('year', 'Year'),
    ],
        string='Maintenace Year Type',
    )
    nhcl_end_date = fields.Date(string='End Date')

    # maintenance email send based on preventing and corretive
    @api.model
    def maintenance_send_mail(self):
        template = self.env.ref('nhcl_rental_management.maintenance_notification_nail')
        for record in self.env['maintenance.request'].search([('maintenance_type', '=', 'preventive')]):
            for line in record.preventing_maintenance_ids:
                if line.nhcl_schedule_date:
                    if fields.Date.today() == line.nhcl_schedule_date + timedelta(days=-2):
                        template.send_mail(record.id, force_send=True)
        for record in self.env['maintenance.request'].search([('schedule_date', '!=', False)]):
            if record.schedule_date.date() == fields.Date.today():
                template.send_mail(record.id, force_send=True)

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    partner_id = fields.Many2one('res.partner', string='Vendor', check_company=True,domain=[('user_type', '=', 'vendor')])

