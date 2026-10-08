from email.policy import default

from odoo import models, fields, api
from datetime import date, timedelta
import calendar

from odoo.exceptions import UserError, ValidationError


# Electric Bill Screen
class ElectricBill(models.Model):
    _name = 'electric.bill'
    _rec_name = 'date'

    category = fields.Char(string='Category', default='EB')
    date = fields.Date(string='Bill Month', default=fields.Date.context_today)
    is_pushed = fields.Boolean(string="Lines Pushed to Category", default=False)

    line_ids = fields.One2many('electric.bill.line', 'bill_id', string='Tenant Consumption Lines')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)

    @api.depends('line_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(line.consumption for line in bill.line_ids)

    @api.model
    def create(self, vals):
        # Prevent duplicate bill for the same date
        if vals.get('date'):
            existing = self.search([('date', '=', vals['date'])], limit=1)
            if existing:
                raise ValidationError("An electric bill for this date already exists.")

        record = super().create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'), ('start_date', '<=', record.date),
                ('end_date', '>=', record.date)])
            yesterday = record.date - timedelta(days=1)

            lines = []
            for i, tenant in enumerate(tenants):
                # Fetch yesterday's line (from electric.bill.line) for this tenant
                previous_line = self.env['electric.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday)
                ], limit=1, order='id DESC')

                opening_unit = previous_line.close_unit if previous_line else 0.0

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False
                }))

            record.line_ids = lines

        return record

    def action_push_lines_to_category(self):
        """Push each electric.bill.line to the correct catagory.bill.ct_line_ids based on date and tenant"""
        if not self.date:
            raise UserError("Please set the date on the Electric Bill.")
        if self.is_pushed:
            raise UserError("Lines have already been pushed to the Category Bill.")

        bill_month = self.date.strftime('%b').lower()[:3]  # e.g. 'jun'
        bill_year = self.date.strftime('%Y')

        for line in self.line_ids:
            # 1. Find matching Category Bill by tenant and month
            category_bill = self.env['catagory.bill'].search([
                ('ten', '=', line.tenant_id.id),
                ('months', '=', bill_month),
                ('year', '=', bill_year),
                ('is_invoice_created', '=', False)
            ], limit=1)

            if not category_bill:
                continue
                # raise ValidationError(f"No Record {line.tenant_id.name} Are Present In this month In the Electric main")

            # 2. Always create a new category.line even for same date
            new_line_vals = {
                'dt': self.date,
                'open_unit': line.open_unit,
                'close_unit': line.close_unit,
                'reset_unit': line.reset_date,
                # If your model has tenant_id in ct_line_ids, include this:
                # 'tenant_id': line.tenant_id.id,
            }

            category_bill.write({
                'ct_line_ids': [(0, 0, new_line_vals)]
            })
        self.is_pushed = True

class ElectricBillLine(models.Model):
    _name = 'electric.bill.line'

    bill_id = fields.Many2one('electric.bill', string='Electric Bill')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    reset_date = fields.Float(string='reset', default=1)
    editable_line = fields.Boolean(string="Allow Editing", default=False)
    open_unit = fields.Float(string='Opening Unit', digits=(0, 4))
    close_unit = fields.Float(string='Closing Unit', digits=(0, 4))
    # reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)
    is_locked = fields.Boolean(string="Is Locked", compute="_compute_is_locked", store=True)

    @api.constrains('tenant_id', 'bill_id.date', 'open_unit', 'close_unit')
    def _compute_is_locked(self):
        for line in self:
            if line.tenant_id and line.bill_id.date:
                month_key = line.bill_id.date.strftime('%b').lower()
                bill = self.env['catagory.bill'].search([
                    ('ten', '=', line.tenant_id.id),
                    ('months', '=', month_key),
                    ('is_invoice_created', '=', True)
                ], limit=1)
                line.is_locked = bool(bill)

                if bill:
                    raise ValidationError("can't chnage the value")
            else:
                line.is_locked = False

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:
            if line.reset_date > 1:
                line.consumption = (line.close_unit - line.open_unit) * 1000
            elif line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit)
            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        """Save current line and enable the next line in the same bill.
        If last line, loop back to the first one."""
        lines = self.bill_id.line_ids.sorted(key=lambda l: l.id)
        found = False
        next_found = False

        for index, line in enumerate(lines):
            if line.id == self.id:
                # Disable current line
                line.editable_line = False
                found = True
                # Try to enable next line if it exists
                if index + 1 < len(lines):
                    lines[index + 1].editable_line = True
                    next_found = True
                break

        if found and not next_found and lines:
            # We were at the last line, so enable the first one again
            lines[0].editable_line = True


# Gas Screen model
class GasScreen(models.Model):
    _name = 'gas.bill'
    _rec_name = 'date'

    category = fields.Char(string='Category', default='Gas')
    date = fields.Date(string='Bill Month', default=fields.Date.context_today)
    is_pushed = fields.Boolean(string="Lines Pushed to Gas Reading", default=False)

    line_ids = fields.One2many('gas.bill.line', 'bill_id', string='Tenant Consumption Lines')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)

    @api.depends('line_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(line.consumption for line in bill.line_ids)

    @api.model
    def create(self, vals):
        # Prevent duplicate bill for the same date
        if vals.get('date'):
            existing = self.search([('date', '=', vals['date'])], limit=1)
            if existing:
                raise ValidationError("An gas bill for this date already exists.")

        record = super().create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'), ('start_date', '<=', record.date),
                ('end_date', '>=', record.date)])
            yesterday = record.date - timedelta(days=1)

            lines = []
            for i, tenant in enumerate(tenants):
                # Fetch yesterday's line (from electric.bill.line) for this tenant
                previous_line = self.env['gas.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday)
                ], limit=1, order='id DESC')

                opening_unit = previous_line.close_unit if previous_line else 0.0

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False
                }))

            record.line_ids = lines

        return record

    def action_push_lines_to_gas_bill(self):
        """Push each gas.bill.line to the correct gas.reading.gas_line_ids based on date and tenant"""

        # Step 1: Prevent double execution
        if self.is_pushed:
            raise UserError("Lines have already been pushed to the Gas Reading.")

        if not self.date:
            raise UserError("Please set the date on the Gas Bill.")

        if not self.line_ids:
            raise ValidationError("No Gas Bill lines are present.")

        bill_month = self.date.strftime('%b').lower()[:3]

        for line in self.line_ids:
            if not line.tenant_id:
                continue

            # Step 2: Find the matching gas reading record
            category_bill = self.env['gas.reading'].search([
                ('tenant_id', '=', line.tenant_id.id),
                ('month', '=', bill_month),
            ], limit=1)

            if not category_bill:
                continue

            # Step 3: Always create a new line (even if one exists for the same date)
            category_bill.write({
                'gas_line_ids': [(0, 0, {
                    'date': self.date,
                    'opening_unit': line.open_unit,
                    'closing_unit': line.close_unit,
                    'reset_unit': line.reset_date,
                })]
            })

        # Step 4: Mark as pushed
        self.is_pushed = True

class GasScreenLine(models.Model):
    _name = 'gas.bill.line'

    bill_id = fields.Many2one('gas.bill', string='GAS Bill')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    reset_date = fields.Float(string='reset',default=1)
    editable_line = fields.Boolean(string="Allow Editing", default=False)
    open_unit = fields.Float(string='Opening Unit', digits=(0, 4))
    close_unit = fields.Float(string='Closing Unit', digits=(0, 4))
    # reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:
            if line.reset_date > 1:
                line.consumption = (line.close_unit - line.open_unit) * 1000
            elif line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit)
            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        """Save current line and enable the next line in the same bill.
        If last line, loop back to the first one."""
        lines = self.bill_id.line_ids.sorted(key=lambda l: l.id)
        found = False
        next_found = False

        for index, line in enumerate(lines):
            if line.id == self.id:
                # Disable current line
                line.editable_line = False
                found = True
                # Try to enable next line if it exists
                if index + 1 < len(lines):
                    lines[index + 1].editable_line = True
                    next_found = True
                break

        if found and not next_found and lines:
            # We were at the last line, so enable the first one again
            lines[0].editable_line = True


# DG Screen Model

class DGScreen(models.Model):
    _name = 'dg.bill'
    _rec_name = 'date'

    category = fields.Char(string='Category', default='DG')
    date = fields.Date(string='Bill Month', default=fields.Date.context_today)
    is_pushed = fields.Boolean(string="Lines Pushed to DG Reading", default=False)

    line_ids = fields.One2many('dg.bill.line', 'bill_id', string='Tenant Consumption Lines')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)

    @api.depends('line_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(line.consumption for line in bill.line_ids)

    @api.model
    def create(self, vals):
        # Prevent duplicate bill for the same date
        if vals.get('date'):
            existing = self.search([('date', '=', vals['date'])], limit=1)
            if existing:
                raise ValidationError("An DG bill for this date already exists.")

        record = super(DGScreen, self).create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'), ('start_date', '<=', record.date),
                ('end_date', '>=', record.date)])
            yesterday = record.date - timedelta(days=1)

            lines = []
            for i, tenant in enumerate(tenants):
                # Fetch yesterday's line (from electric.bill.line) for this tenant
                previous_line = self.env['dg.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday)
                ], limit=1, order='id DESC')

                opening_unit = previous_line.close_unit if previous_line else 0.0

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False
                }))

            record.line_ids = lines

        return record

    def action_push_lines_to_dg_bill(self):
        """Push each DG.bill.line to the correct dg.reading.dg_line_ids based on date and tenant"""

        if self.is_pushed:
            raise UserError("Lines have already been pushed to the DG Reading.")

        if not self.date:
            raise UserError("Please set the date on the DG Bill.")

        if not self.line_ids:
            raise ValidationError("No DG Bill lines are present.")

        bill_month = self.date.strftime('%b').lower()[:3]
        bill_year = self.date.strftime('%Y')

        for line in self.line_ids:
            if not line.tenant_id:
                continue

            # Step 1: Find matching dg.reading record
            category_bill = self.env['dg.reading'].search([
                ('tenant_id', '=', line.tenant_id.id),
                ('month', '=', bill_month), ('year', '=', bill_year),
            ], limit=1)

            if not category_bill:
                continue

            # Step 2: Always create new dg.line entry
            category_bill.write({
                'dg_line_ids': [(0, 0, {
                    'date': self.date,
                    'opening_unit': line.open_unit,
                    'closing_unit': line.close_unit,
                    'reset_unit': line.reset_date,
                })]
            })

        # Step 3: Mark the bill as pushed
        self.is_pushed = True


class DGScreenLine(models.Model):
    _name = 'dg.bill.line'

    bill_id = fields.Many2one('dg.bill', string='DG Bill')
    editable_line = fields.Boolean(string="Allow Editing", default=False)
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    reset_date = fields.Float(string='reset',default=1)
    open_unit = fields.Float(string='Opening Unit', digits=(0, 4))
    close_unit = fields.Float(string='Closing Unit', digits=(0, 4))
    # reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:
            if line.reset_date > 1:
                line.consumption = (line.close_unit - line.open_unit) * 1000
            elif line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit)
            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        """Save current line and enable the next line in the same bill.
        If last line, loop back to the first one."""
        lines = self.bill_id.line_ids.sorted(key=lambda l: l.id)
        found = False
        next_found = False

        for index, line in enumerate(lines):
            if line.id == self.id:
                # Disable current line
                line.editable_line = False
                found = True
                # Try to enable next line if it exists
                if index + 1 < len(lines):
                    lines[index + 1].editable_line = True
                    next_found = True
                break

        if found and not next_found and lines:
            # We were at the last line, so enable the first one again
            lines[0].editable_line = True


# this is for the new HVAC Screen
class HVACBill(models.Model):
    _name = 'hvac.bill'
    _rec_name = 'date'
    _description = 'HVAC Monthly Bill'

    category = fields.Char(string='Category', default='HVAC')
    date = fields.Date(string='Bill Month', default=fields.Date.context_today)
    is_pushed = fields.Boolean(string="Lines Pushed to HVAC Reading", default=False)

    hvac_ids = fields.One2many('hvac.bill.line', 'bill_id', string='Tenant HVAC Lines')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)

    @api.depends('hvac_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(line.consumption for line in bill.hvac_ids)

    @api.model
    def create(self, vals):
        # Prevent duplicate bill for the same date
        if vals.get('date'):
            existing = self.search([('date', '=', vals['date'])], limit=1)
            if existing:
                raise ValidationError("An HVAC bill for this date already exists.")

        record = super(HVACBill, self).create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'), ('start_date', '<=', record.date),
                ('end_date', '>=', record.date)])
            yesterday = record.date - timedelta(days=1)

            lines = []
            for i, tenant in enumerate(tenants):
                # Fetch yesterday's line (from electric.bill.line) for this tenant
                previous_line = self.env['hvac.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday)
                ], limit=1, order='id DESC')

                opening_unit = previous_line.close_unit if previous_line else 0.0

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False
                }))

            record.hvac_ids = lines

        return record

    def action_push_lines_to_hvac_reading(self):
        """Push each HVAC line to the correct hvac.reading.hvac_line_ids based on date and tenant."""

        # Prevent multiple pushes
        if self.is_pushed:
            raise UserError("Lines have already been pushed to the HVAC Reading.")

        if not self.date:
            raise UserError("Please set the bill date.")

        if not self.hvac_ids:
            raise ValidationError("No HVAC lines found.")

        month = self.date.strftime('%b').lower()[:3]

        for line in self.hvac_ids:
            if not line.tenant_id:
                continue

            # Find matching HVAC reading for the tenant
            hvac_reading = self.env['hvac.reading'].search([
                ('tenant_id', '=', line.tenant_id.id),
                ('month', '=', month),
            ], limit=1)

            if not hvac_reading:
                continue

            # Always create new line even if one already exists
            hvac_reading.write({
                'hvac_line_ids': [(0, 0, {
                    'date': self.date,
                    'opening_unit': line.open_unit,
                    'closing_unit': line.close_unit,
                    'reset_unit': line.reset_date
                })]
            })

        # Mark as pushed
        self.is_pushed = True


class HVACBillLine(models.Model):
    _name = 'hvac.bill.line'
    _description = 'HVAC Bill Line'

    bill_id = fields.Many2one('hvac.bill', string='HVAC Bill')
    editable_line = fields.Boolean(string="Allow Editing", default=False)
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    reset_date = fields.Integer(string='Reset', default=1)
    open_unit = fields.Float(string='Opening Unit', digits=(16, 4))
    close_unit = fields.Float(string='Closing Unit', digits=(16, 4))
    # reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:
            # if line.open_unit is not None and line.close_unit is not None:
            #     line.consumption = (line.close_unit - line.open_unit) * line.reset_date
            if line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit) * (line.reset_date)
            elif line.open_unit > line.close_unit:
                line.consumption = (line.close_unit * 1000) - line.open_unit
            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        lines = self.bill_id.hvac_ids.sorted(key=lambda l: l.id)
        current_index = lines.ids.index(self.id)
        self.editable_line = False
        next_index = (current_index + 1) % len(lines)
        lines[next_index].editable_line = True


# it's for the new screen GHMC water
class WaterBill(models.Model):
    _name = 'water.bill'
    _rec_name = 'date'

    category = fields.Char(string='Category', default='Water')
    date = fields.Date(string='Bill Date', default=fields.Date.context_today)
    is_pushed = fields.Boolean(string="Lines Pushed to Water Reading", default=False)

    line_ids = fields.One2many('water.bill.line', 'bill_id', string='Tenant Water Consumption Lines')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)

    @api.depends('line_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(line.consumption for line in bill.line_ids)

    @api.model
    def create(self, vals):
        if vals.get('date'):
            existing = self.search([('date', '=', vals['date'])], limit=1)
            if existing:
                raise ValidationError("A water bill for this date already exists.")

        record = super().create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'), ('start_date', '<=', record.date),
                ('end_date', '>=', record.date)])
            yesterday = record.date - timedelta(days=1)

            lines = []
            for i, tenant in enumerate(tenants):
                previous_line = self.env['water.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday)
                ], limit=1, order='id DESC')

                opening_unit = previous_line.close_unit if previous_line else 0.0

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False
                }))

            record.line_ids = lines

        return record

    def action_push_lines_to_water_reading(self):
        """Push each line to the water.reading model by matching tenant, month, and date."""

        if self.is_pushed:
            raise UserError("Lines have already been pushed to the Water Reading.")

        if not self.date:
            raise UserError("Please set the bill date.")

        if not self.line_ids:
            raise ValidationError("No Water Bill lines are present.")

        month = self.date.strftime('%b').lower()[:3]

        for line in self.line_ids:
            if not line.tenant_id:
                continue

            # Find matching water reading record
            water_reading = self.env['water.reading'].search([
                ('tenant_id', '=', line.tenant_id.id),
                ('month', '=', month),
            ], limit=1)

            if not water_reading:
                continue  # Skip if not found

            # Always create a new line for this date
            water_reading.write({
                'water_line_ids': [(0, 0, {
                    'date': self.date,
                    'opening_unit': line.open_unit,
                    'closing_unit': line.close_unit,
                    'reset_unit': line.reset_date,
                })]
            })

        # Mark as pushed
        self.is_pushed = True


class WaterBillLine(models.Model):
    _name = 'water.bill.line'

    bill_id = fields.Many2one('water.bill', string='Water Bill')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    reset_date = fields.Float(string='Reset',default=1)
    editable_line = fields.Boolean(string="Allow Editing", default=False)
    open_unit = fields.Float(string='Opening Unit', digits=(0, 4))
    close_unit = fields.Float(string='Closing Unit', digits=(0, 4))
    # reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:
            if line.reset_date > 1:
                line.consumption = (line.close_unit - line.open_unit) * 1000
            elif line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit)
            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        lines = self.bill_id.line_ids.sorted(key=lambda l: l.id)
        found = False
        next_found = False

        for index, line in enumerate(lines):
            if line.id == self.id:
                line.editable_line = False
                found = True
                if index + 1 < len(lines):
                    lines[index + 1].editable_line = True
                    next_found = True
                break

        if found and not next_found and lines:
            lines[0].editable_line = True


class HotWaterBill(models.Model):
    _name = 'hot.water.bill'
    _rec_name = 'date'

    category = fields.Char(string='Category', default='Cool Water')
    date = fields.Date(string='Bill Date', default=fields.Date.context_today)
    is_pushed = fields.Boolean(string="Lines Pushed to Hot Water Reading", default=False)

    line_ids = fields.One2many('hot.water.bill.line', 'bill_id', string='Tenant Hot Water Lines')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)

    @api.depends('line_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(line.consumption for line in bill.line_ids)

    @api.model
    def create(self, vals):
        if vals.get('date'):
            existing = self.search([('date', '=', vals['date'])], limit=1)
            if existing:
                raise ValidationError("A Cool water bill for this date already exists.")

        record = super().create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'), ('start_date', '<=', record.date),
                ('end_date', '>=', record.date)])
            yesterday = record.date - timedelta(days=1)

            lines = []
            for i, tenant in enumerate(tenants):
                previous_line = self.env['hot.water.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday)
                ], limit=1, order='id DESC')

                opening_unit = previous_line.close_unit if previous_line else 0.0

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False
                }))

            record.line_ids = lines

        return record

    def action_push_lines_to_hot_water_reading(self):
        """Push each line to hot.water.reading based on tenant, month, and date."""

        if self.is_pushed:
            raise UserError("Lines have already been pushed to the Hot Water Reading.")

        if not self.date:
            raise UserError("Please set the bill date.")

        if not self.line_ids:
            raise ValidationError("No Hot Water Bill lines are present.")

        month = self.date.strftime('%b').lower()[:3]

        for line in self.line_ids:
            if not line.tenant_id:
                continue

            hot_water_reading = self.env['hot.water.reading'].search([
                ('tenant_id', '=', line.tenant_id.id),
                ('month', '=', month),
            ], limit=1)

            if not hot_water_reading:
                continue

            # ✅ Always create new reading line regardless of date match
            hot_water_reading.write({
                'hot_water_line_ids': [(0, 0, {
                    'date': self.date,
                    'opening_unit': line.open_unit,
                    'closing_unit': line.close_unit,
                    'reset_unit': line.reset_date,
                })]
            })

        # Mark the bill as pushed
        self.is_pushed = True

class HotWaterBillLine(models.Model):
    _name = 'hot.water.bill.line'

    bill_id = fields.Many2one('hot.water.bill', string='Hot Water Bill')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    reset_date = fields.Float(string='Reset',default=1)
    editable_line = fields.Boolean(string="Allow Editing", default=False)
    open_unit = fields.Float(string='Opening Unit', digits=(0, 4))
    close_unit = fields.Float(string='Closing Unit', digits=(0, 4))
    # reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:

            if line.reset_date > 1:
                line.consumption = (line.close_unit - line.open_unit) * 1000
            elif line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit)
            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        lines = self.bill_id.line_ids.sorted(key=lambda l: l.id)
        found = False
        next_found = False

        for index, line in enumerate(lines):
            if line.id == self.id:
                line.editable_line = False
                found = True
                if index + 1 < len(lines):
                    lines[index + 1].editable_line = True
                    next_found = True
                break

        if found and not next_found and lines:
            lines[0].editable_line = True

# HVAC DG Bill
class HVACDCBill(models.Model):
    _name = 'hvac.dc.bill'
    _rec_name = 'date'
    _description = 'HVAC DC Monthly Bill'

    category = fields.Char(string='Category', default='HVAC DC')
    date = fields.Date(
        string='Bill Month',
        default=fields.Date.context_today
    )
    is_pushed = fields.Boolean(
        string="Lines Pushed to HVAC DC Reading",
        default=False
    )

    hvac_dc_ids = fields.One2many(
        'hvac.dc.bill.line',
        'bill_id',
        string='Tenant HVAC DC Lines'
    )

    total_consumption = fields.Float(
        string='Total Consumption',
        compute='_compute_total_consumption',
        store=True
    )
    date = fields.Date(string="Record Created Date", required=True)  # default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, )

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')

    @api.depends('hvac_dc_ids.consumption')
    def _compute_total_consumption(self):
        for bill in self:
            bill.total_consumption = sum(
                line.consumption for line in bill.hvac_dc_ids
            )

    @api.model
    def create(self, vals):
        # Prevent duplicate bill for the same date
        if vals.get('date'):
            existing = self.search([
                ('date', '=', vals['date'])
            ], limit=1)

            if existing:
                raise ValidationError(
                    "An HVAC DC bill for this date already exists."
                )

        record = super(HVACDCBill, self).create(vals)

        if record.date:
            tenants = self.env['tenancy.details'].search([
                ('contract_type', '=', 'running_contract'),
                ('start_date', '<=', record.date),
                ('end_date', '>=', record.date),
            ])

            yesterday = record.date - timedelta(days=1)

            lines = []

            for i, tenant in enumerate(tenants):

                # Fetch yesterday's HVAC DC bill line
                previous_line = self.env['hvac.dc.bill.line'].search([
                    ('tenant_id', '=', tenant.tenancy_id.id),
                    ('bill_id.date', '=', yesterday),
                ], limit=1, order='id DESC')

                opening_unit = (
                    previous_line.close_unit
                    if previous_line
                    else 0.0
                )

                lines.append((0, 0, {
                    'tenant_id': tenant.tenancy_id.id,
                    'reset_date': 1,
                    'open_unit': opening_unit,
                    'close_unit': 0.0,
                    'consumption': 0.0,
                    'editable_line': True if i == 0 else False,
                }))

            record.hvac_dc_ids = lines

        return record

    def action_push_lines_to_hvac_dc_reading(self):
        """
        Push each HVAC DC bill line to the corresponding
        hvac.dc.reading record.
        """

        # Prevent multiple pushes
        if self.is_pushed:
            raise UserError(
                "Lines have already been pushed to the HVAC DC Reading."
            )

        if not self.date:
            raise UserError("Please set the bill date.")

        if not self.hvac_dc_ids:
            raise ValidationError("No HVAC DC lines found.")

        month = self.date.strftime('%b').lower()[:3]

        for line in self.hvac_dc_ids:

            if not line.tenant_id:
                continue

            # Find matching HVAC DC reading
            hvac_dc_reading = self.env['hvac.dc.reading'].search([
                ('tenant_id', '=', line.tenant_id.id),
                ('month', '=', month),
            ], limit=1)

            if not hvac_dc_reading:
                continue

            # Create new reading line
            hvac_dc_reading.write({
                'hvac_dc_line_ids': [(0, 0, {
                    'date': self.date,
                    'opening_unit': line.open_unit,
                    'closing_unit': line.close_unit,
                    'reset_unit': line.reset_date,
                })]
            })

        # Mark as pushed
        self.is_pushed = True


class HVACDCBillLine(models.Model):
    _name = 'hvac.dc.bill.line'
    _description = 'HVAC DC Bill Line'

    bill_id = fields.Many2one(
        'hvac.dc.bill',
        string='HVAC DC Bill'
    )

    editable_line = fields.Boolean(
        string="Allow Editing",
        default=False
    )

    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        domain=[('user_type', '=', 'customer')]
    )

    reset_date = fields.Integer(
        string='Reset',
        default=1
    )

    open_unit = fields.Float(
        string='Opening Unit',
        digits=(16, 4)
    )

    close_unit = fields.Float(
        string='Closing Unit',
        digits=(16, 4)
    )

    consumption = fields.Float(
        string='Consumption',
        compute='_compute_consumption',
        store=True
    )

    @api.depends('open_unit', 'close_unit', 'reset_date')
    def _compute_consumption(self):
        for line in self:

            if line.close_unit > line.open_unit:
                line.consumption = (
                    line.close_unit - line.open_unit
                ) * line.reset_date

            elif line.open_unit > line.close_unit:
                line.consumption = (
                    line.close_unit * 1000
                ) - line.open_unit

            else:
                line.consumption = 0.0

    def action_save_and_next(self):
        lines = self.bill_id.hvac_dc_ids.sorted(
            key=lambda l: l.id
        )

        current_index = lines.ids.index(self.id)

        self.editable_line = False

        next_index = (current_index + 1) % len(lines)

        lines[next_index].editable_line = True
