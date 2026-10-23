from datetime import datetime

from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError


class Mall(models.Model):
    _name = 'mall.main'

    name = fields.Char(string='Name', required=True, copy=False)


class MallDemo(models.Model):
    _name = 'mall.demo'

    mall_id = fields.Many2one('property.details')
    mall_master_id = fields.Many2one('mall.main', string="Retail Mix")
    mall_length = fields.Integer(string='Length(ft)')
    mall_width = fields.Integer(string='Width(ft)')
    mall_height = fields.Integer(string='Height(ft)')
    mall_no_of_unit = fields.Char(string='Floor')
    mall_carpet_area = fields.Float(string='Area(ft²)',digits=(10,2))


class TenantType(models.Model):
    _name = 'tenant.type'
    _description = 'Tenant Type'

    name = fields.Char(string='Name', required=True, copy=False)


class PreventingMaintenance(models.Model):
    _name = 'preventing.maintenance'
    _description = 'Preventing Maintenance'

    nhcl_start_date = fields.Date(string='Start Date')
    nhcl_schedule_date = fields.Date(string='Schedule Date')
    nhcl_end_date = fields.Date(string='End Date')
    nhcl_description = fields.Text(string='Description')
    nhcl_status = fields.Text(string='Status')
    nhcl_remarks = fields.Text(string='Remarks')
    maintenance_request_id = fields.Many2one(
        'maintenance.request', string='Maintenance Request'
    )


class SupportDocuments(models.Model):
    _name = 'support.documents'

    responsible = fields.Many2one('hr.employee')
    nhcl_description = fields.Char(string='Description')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='Expiry Date')
    attachments = fields.Binary(string='Attachments', attachment_name='attachment_name')
    attachment_name = fields.Char(string='File Name')
    amount = fields.Float(string='Amount',digits=(16, 2))
    support_id = fields.Many2one('tenancy.details')

    @api.constrains('attachments')
    def _check_mandatory_fields(self):
        for record in self:
            if record.attachments:
                if not record.nhcl_description:
                    raise ValidationError("Description must be provided when attachments are added.")
                if not record.start_date:
                    raise ValidationError("Start Date must be provided when attachments are added.")


# class ResPartner(models.Model):
#     _inherit = 'res.partner'
#
#     cam = fields.Char(string='Cam Email')
#     utility = fields.Char(string='Utility Email')
#     gas = fields.Char(string='Gas Email')
#     signage = fields.Char(string='Signage Email')
#
#     @api.constrains('vat')
#     def check_vat_validate(self):
#         for rec in self:
#             if rec.vat:
#                 if len(rec.vat) == 15:
#                     continue
#                 else:
#                     raise ValidationError(f"The GSTIN number {[rec.vat]} for partner {[rec.name]} does not seem to be valid \n.Note: the expected format is 12AAAAA1234AAZA")


class YearAddInTenancy(models.Model):
    _name = 'year.add'

    start_year = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    end_year = fields.Date(string='Renewal Date')
    yid = fields.Many2one('tenancy.details')

    rupees = fields.Float(string='Rupee')
    fixed_amount = fields.Float(string='Fixed')
    percentage = fields.Integer(string='Percentage')
    amount = fields.Float(string='Amount', compute='_amount_change', store=True,readonly=False)
    extra_rate = fields.Integer('Extra amount')

    is_invoice_generated = fields.Boolean(string="Invoice Created", default=False)
    is_first_line = fields.Boolean("Is First Line", compute="_compute_is_first_line", store=True)
    is_last_line=fields.Boolean('Last Line',compute='_compute_is_last_line', store=True)

    # add for the percentage calculator
    increase_type = fields.Selection([
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('rupees', 'Rupees'),
    ], string="Calculation Type", default='percent')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('increase_type') == 'rupees':
                vals.update({
                    'percentage': 0.0,
                    'fixed_amount': 0.0,
                })
            elif vals.get('increase_type') == 'percent':
                vals.update({
                    'rupees': 0.0,
                    'fixed_amount': 0.0,
                })
            elif vals.get('increase_type') == 'fixed':
                vals.update({
                    'percentage': 0.0,
                    'rupees': 0.0,
                })

        return super().create(vals_list)

    def write(self, vals):
        vals = vals.copy()

        if vals.get('increase_type') == 'rupees':
            vals.update({
                'percentage': 0.0,
                'fixed_amount': 0.0,
            })
        elif vals.get('increase_type') == 'percent':
            vals.update({
                'rupees': 0.0,
                'fixed_amount': 0.0,
            })
        elif vals.get('increase_type') == 'fixed':
            vals.update({
                'percentage': 0.0,
                'rupees': 0.0,
            })

        return super().write(vals)

    @api.depends('yid')
    def _compute_is_first_line(self):
        for record in self:
            record.is_first_line = False  # default
            if record.yid:
                first_line = self.env['year.add'].search(
                    [('yid', '=', record.yid.id)],
                    order='id',
                    limit=1
                )
                record.is_first_line = (record.id == first_line.id)


    @api.depends('yid')
    def _compute_is_last_line(self):
        for record in self:
            record.is_last_line = False  # default

            if record.yid:
                last_line = self.env['year.add'].search(
                    [('yid', '=', record.yid.id)],
                    order='id desc',
                    limit=1
                )
                record.is_last_line = (record.id == last_line.id)

    # @api.depends('percentage', 'yid')
    # def _amount_change(self):
    #     tenancies = self.mapped('yid')
    #     for tenancy in tenancies:
    #         related_lines = self.env['year.add'].search(
    #             [('yid', '=', tenancy.id)],
    #             order='id'
    #         )
    #
    #         for i, line in enumerate(related_lines):
    #             if i == 0:
    #                 # First line: total rent only
    #                 line.amount = tenancy.total_rent
    #             else:
    #                 prev_line = related_lines[i - 1]
    #                 base = prev_line.amount
    #                 percentage = line.percentage
    #                 line.amount = base + (base * percentage / 100)

    @api.depends(
        'increase_type',
        'percentage',
        'fixed_amount',
        'rupees',
        'yid.total_rent','yid.carpet_area',
        'yid.year_ids.increase_type',
        'yid.year_ids.percentage',
        'yid.year_ids.fixed_amount',
        'yid.year_ids.rupees',
    )
    def _amount_change(self):
        for record in self:
            if not record.yid:
                record.amount = 0
                continue

            lines = self.env['year.add'].search(
                [('yid', '=', record.yid.id)],
                order='start_year, id'
            )
            # lines = record.yid.year_ids.sorted(key=lambda l: (l.start_year or datetime.date.min, l.id))

            for index, line in enumerate(lines):
                # ✅ First line = base rent
                if index == 0:
                    line.amount = line.yid.total_rent or 0
                    continue

                prev_amount = lines[index - 1].amount

                if line.increase_type == 'percent':
                    line.amount = prev_amount + (prev_amount * line.percentage / 100)


                elif line.increase_type == 'fixed':
                    line.amount = prev_amount + line.fixed_amount

                elif line.increase_type == 'rupees':

                    # Fixed rent -> manual entry, keep what the user typed
                    if line.yid.sft_fixed == 'fixed':
                        line.amount = prev_amount
                        continue

                    if line.yid.sft_fixed == 'sft':
                        # get previous extra
                        prev_extra = lines[index - 1].extra_rate or 0.0
                        # cumulative extra
                        current_extra = prev_extra + (line.rupees or 0.0)

                        # store cumulative value
                        line.extra_rate = current_extra

                        if line.yid.carpet_value_take:
                            line.amount = line.yid.carpet_area * (
                                    line.yid.rate + current_extra
                            )
                        else:
                            line.amount = line.yid.chargeable_area * (
                                    line.yid.rate + current_extra
                            )
                else:
                    line.amount = prev_amount

    # @api.depends(
    #     'increase_type', 'percentage', 'fixed_amount', 'rupees',
    #     'yid.total_rent', 'yid.carpet_area', 'yid.chargeable_area',
    #     'yid.rate', 'yid.sft_fixed', 'yid.carpet_value_take',
    #     'yid.year_ids.increase_type',
    #     'yid.year_ids.percentage',
    #     'yid.year_ids.fixed_amount',
    #     'yid.year_ids.rupees',
    # )
    # def _amount_change(self):
    #     # lines with no parent
    #     for record in self.filtered(lambda r: not r.yid):
    #         record.amount = 0
    #
    #     for yid in self.mapped('yid'):
    #         # "| self" guarantees the edited lines are always in the loop
    #         lines = (yid.year_ids | self.filtered(lambda r: r.yid == yid)).sorted(
    #             key=lambda l: (l.start_year or datetime.date.max, l._origin.id or 0)
    #         )
    #         prev_amount = 0.0
    #         cumulative_extra = 0.0
    #         area = yid.carpet_area if yid.carpet_value_take else yid.chargeable_area
    #
    #         for index, line in enumerate(lines):
    #             if index == 0:
    #                 line.amount = yid.total_rent or 0.0
    #                 cumulative_extra = 0.0
    #
    #             elif line.increase_type == 'percent':
    #                 line.amount = prev_amount + (prev_amount * (line.percentage or 0.0) / 100)
    #                 cumulative_extra = 0.0
    #
    #             elif line.increase_type == 'fixed':
    #                 line.amount = prev_amount + (line.fixed_amount or 0.0)
    #                 cumulative_extra = 0.0
    #
    #             elif line.increase_type == 'rupees':
    #                 if yid.sft_fixed == 'sft':
    #                     cumulative_extra += (line.rupees or 0.0)
    #                     line.amount = area * (yid.rate + cumulative_extra)
    #                 else:
    #                     # Fixed rent: previous amount + rupees
    #                     line.amount = prev_amount + (line.rupees or 0.0)
    #                     cumulative_extra = 0.0
    #             else:
    #                 line.amount = prev_amount
    #                 cumulative_extra = 0.0
    #
    #             if 'extra_rate' in line._fields:
    #                 line.extra_rate = cumulative_extra
    #
    #             prev_amount = line.amount

    @api.onchange('increase_type')
    def _onchange_increase_type(self):
        if self.increase_type == 'percent':
            self.fixed_amount = 0
            self.rupees = 0
            self.extra_rate = 0

        elif self.increase_type == 'fixed':
            self.percentage = 0
            self.rupees = 0
            self.extra_rate = 0

        elif self.increase_type == 'rupees':
            self.percentage = 0
            self.fixed_amount = 0

        else:
            self.percentage = 0
            self.fixed_amount = 0
            self.rupees = 0
            self.extra_rate = 0

class YearAddInTenancy_cam(models.Model):
    _name = 'cam.year'

    cam_start_year = fields.Date(string='Start Date')
    cam_end_year = fields.Date(string='Renewal Date')
    cam_end_date = fields.Date(string='End Date')
    cam_yid = fields.Many2one('tenancy.details')
    is_invoice_generated = fields.Boolean(string="Invoice Created", default=False)
    cam_percentage = fields.Integer(string='Percentage')
    cam_amount = fields.Float(string='Amount', compute='cam_amount_chnage',inverse='_inverse_cam_amount',store=True)
    amount_type = fields.Selection(
        [
            ('auto', 'Auto Calculate'),
            ('manual', 'Manual'),
        ],
        string="Amount Type",
        default='auto',
        required=True
    )
    is_first_line_cam = fields.Boolean("Is First Line", compute="_compute_is_first_line", store=True, default=False)

    @api.depends('cam_yid')
    def _compute_is_first_line(self):
        for record in self:
            record.is_first_line_cam = False  # default
            if record.cam_yid:
                first_line = self.env['cam.year'].search(
                    [('cam_yid', '=', record.cam_yid.id)],
                    order='id',
                    limit=1
                )
                record.is_first_line_cam = (record.id == first_line.id)

    # @api.onchange('cam_percentage')
    # def cam_amount_chnage(self):
    #     related_lines = self.env['cam.year'].search([('cam_yid.tenancy_seq', '=', self.cam_yid.tenancy_seq)],
    #                                                 order='id')
    #     for rec in self:
    #         if rec.cam_percentage and related_lines:
    #             rec.cam_amount = 0
    #             c = 0
    #             if related_lines:
    #                 for record in self:
    #                     tenancy = record.cam_yid
    #                     print(tenancy.tenancy_id.name, record.cam_percentage, record.id, record.cam_amount)
    #                     if record.cam_percentage and tenancy:
    #                         print('satisfied')
    #                         if tenancy.use_carpet:
    #                             if c == 0:
    #                                 record.cam_amount = tenancy.cam_carpet
    #                                 print('updated')
    #                             else:
    #                                 record.cam_amount = related_lines.cam_yid.cam_year_ids[c - 1].cam_amount + (
    #                                         related_lines.cam_yid.cam_year_ids[
    #                                             c - 1].cam_amount * record.cam_percentage / 100)
    #                         else:
    #                             if c == 0:
    #                                 record.cam_amount = tenancy.cam_chargeable
    #                             else:
    #                                 record.cam_amount = related_lines.cam_yid.cam_year_ids[c - 1].cam_amount + (
    #                                         related_lines.cam_yid.cam_year_ids[
    #                                             c - 1].cam_amount * record.cam_percentage / 100)
    #                     else:
    #                         record.cam_amount = 0
    #                     c += 1
    #         else:
    #             rec.cam_amount = 0
    @api.depends(
        'cam_percentage',
        'cam_yid.cam_year_ids.cam_percentage',
        'cam_yid.cam_year_ids.cam_amount',
        'amount_type'
    )
    def cam_amount_chnage(self):

        for rec in self:

            if rec.amount_type == 'manual':
                continue

            tenancy = rec.cam_yid
            if not tenancy:
                continue

            # ❌ NO SORTING
            lines = tenancy.cam_year_ids

            for index, line in enumerate(lines):

                if line.amount_type == 'manual':
                    continue

                # FIRST LINE
                if index == 0:
                    if tenancy.cam_type == 'cam_sft':
                        if tenancy.use_carpet:
                            line.cam_amount = tenancy.cam_carpet
                        else:
                            line.cam_amount = tenancy.cam_chargeable
                    else:
                        line.cam_amount = tenancy.cam_fixed

                # NEXT LINES
                else:
                    prev_line = lines[index - 1]
                    base = prev_line.cam_amount or 0
                    percentage = line.cam_percentage or 0

                    line.cam_amount = base + (base * percentage / 100)

    def _inverse_cam_amount(self):
        # Needed to allow manual editing when using compute + store
        for rec in self:
            pass


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    class MaintenanceRequest(models.Model):
        _inherit = 'maintenance.request'

        def change_button_next(self):
            for rec in self:
                current_stage = rec.stage_id.name.lower()
                next_stage_name = None

                if current_stage == 'new request':
                    next_stage_name = 'In Progress'
                elif current_stage == 'in progress':
                    next_stage_name = 'Repaired'
                elif current_stage == 'repaired':
                    next_stage_name = 'Scrap'

                if next_stage_name:
                    next_stage = self.env['maintenance.stage'].search(
                        [('name', '=', next_stage_name)],
                        limit=1
                    )
                    if next_stage:
                        rec.stage_id = next_stage

        def change_button_back(self):
            for rec in self:
                current_stage = rec.stage_id.name.lower()

                # BLOCK condition: Prevent going back if in 'Repaired' and corrective
                if current_stage == 'repaired' and rec.maintenance_type == 'corrective':
                    raise UserError(
                        "You cannot change the stage of a corrective maintenance request once it's in 'Repaired'.")

                previous_stage_name = None

                if current_stage == 'repaired':
                    previous_stage_name = 'In Progress'
                elif current_stage == 'in progress':
                    previous_stage_name = 'New Request'
                elif current_stage == 'scrap' and rec.maintenance_type != 'corrective':
                    previous_stage_name = 'Repaired'

                if previous_stage_name:
                    previous_stage = self.env['maintenance.stage'].search([
                        ('name', '=', previous_stage_name)
                    ], limit=1)

                    if previous_stage:
                        rec.stage_id = previous_stage


class RelationYear(models.Model):
    _name = 'tenancy.relation.year'

    name=fields.Char(string='Name')

class CommertialTerm(models.Model):
    _name = 'commerce.term.term'

    name_term=fields.Selection([('term1','Term 1'),('term2','Term 2'),('term3','Term 3'),('term4','Term 4'),('term5','Term 5'),('term6','Term 6'),('term7','Term 7'),('term8','Term 8'),],string='Term Name')
    start_date=fields.Date(string='Start Date')
    end_date=fields.Date(string='End Date')
    rent_type=fields.Selection([('mg','MG'),('rs','Rs')],string='Rent Type')
    min_guarantee_rate=fields.Integer(string='Minimum guarantee rate')
    revenue = fields.Float(string='Revenue Share %')
    charge_type=fields.Selection([('a','A'),('b','B')],string='Charge Type')
    rate=fields.Selection([('month','Monthly'),('quat','Quarterly'),('half','Half Yearly'),('year','Yearly')],string='Rate Based On')
    tenacy_id = fields.Many2one("tenancy.details")

