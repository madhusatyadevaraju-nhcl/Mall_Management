from odoo import fields, models, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class PropertyDetails(models.Model):
    _inherit = 'property.details'

    mall_matrix_ids = fields.One2many('mall.demo', 'mall_id')
    mall_mix_total = fields.Integer(string='Total Square feet', compute='_compute_mall_mix_total', store=True)

    @api.depends('mall_matrix_ids')
    def _compute_mall_mix_total(self):
        total = 0
        for rec in self:
            if rec.mall_matrix_ids:
                for data in rec.mall_matrix_ids:
                    total = total + data.mall_carpet_area
                    rec.mall_mix_total = total
            else:
                rec.mall_mix_total = 0

    def safety_certificate(self):
        channel = self.env['discuss.channel'].search([('name', '=', 'Safety Certificate Expiry')])
        if not channel:
            user_ids = self.env['res.users'].search([]).ids
            channel = self.env['discuss.channel'].create({
                'name': 'Safety Certificate Expiry',
                'channel_type': 'group',
                'channel_partner_ids': [(4, user.partner_id.id) for user in
                                        self.env['res.users'].browse(user_ids)],
            })

        property_data = self.env['property.details'].search([('stage', '=', 'available')])
        today_date = fields.Date.today()

        for rec in property_data:
            for sp in rec.certificate_ids:
                if not sp.expiry_date:
                    continue  # Skip if expiry_date is not set
                past_date = sp.expiry_date - relativedelta(months=1)
                if past_date == today_date:
                    channel.message_post(
                        body=f"The certificate '{sp.attachment_name}' is expiring on {sp.expiry_date}. Please review it.",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )


class FloorPlan(models.Model):
    _inherit = 'floor.plan'  # This is incorrect. _inherits must be a dictionary.
    floor_no = fields.Selection(
        [('-4', 'Basement'), ('-3', 'Lower Cellar'), ('-2', 'Cellar'), ('-1', 'Parking'), ('0', 'Ground Floor '),
         ('1', 'Floor 1'), ('2', 'Floor 2'), ('3', 'Floor 3'), ('4', 'Floor 4'),
         ('5', 'Terrace'), ('6', 'Atrium'), ('7', 'Mall Outside'), ('8', 'Mall Entrance')],
        string='Floor Number')

    total_sft = fields.Float(string='Total ft²')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string='Status')
    tenancy = fields.Many2one('tenancy.details', string='Tenancy ID')

    @api.onchange('total_sft')
    def check_value_total(self):
        v = 0
        rec = self.env['property.commercial.measurement'].search([
            ('commercial_measurement_id.name', '=', self.property_id.name)
        ])

        for r in rec:
            if int(self.floor_no) == r.no_of_unit:

                data = self.env['floor.plan'].search([
                    ('floor_no', '=', str(r.no_of_unit))
                ])

                for value in data:
                    if rec.commercial_measurement_id.name == value.property_id.name:
                        v += value.total_sft
                        print(v, "inside")
                v = v + self.total_sft
                if (self.total_sft <= r.carpet_area) and (int(self.floor_no) == r.no_of_unit) and (v <= r.carpet_area):
                    pass
                else:
                    raise UserError('Total Square Feet cannot be greater than Area.')


class PropertyCertificate(models.Model):
    _inherit = 'property.certificate'

    start_date = fields.Date(string='Start Date')
    attachments = fields.Binary(string='Attachments', attachment_name='attachment_name')
    attachment_name = fields.Char(string='File Name')
