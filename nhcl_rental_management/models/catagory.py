from odoo import api, fields, models
from datetime import date, timedelta
import calendar
from odoo.exceptions import UserError, ValidationError


class CategoryBill(models.Model):
    _name = 'catagory.bill'
    _rec_name = 'ten'

    category = fields.Char(string='Category', default='EB')
    ten = fields.Many2one('res.partner', string='Tenant',domain=lambda self: self._get_running_contract_tenants())
    date = fields.Date(string="Record Created Date", default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, readonly=True)
    months = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], string="Months")
    ct_line_ids = fields.One2many('category.line', 'ct_id', string='Ids')
    total = fields.Float(string='Total Consumption', compute='_compute_total', store=True)
    is_invoice_created = fields.Boolean(string='Is Invoice Created', default=False, store=True)
    meter_no = fields.Char(string='Meter No')
    tenancy_id = fields.Many2one('tenancy.details', string='Ten Name')

    def _set_latest_tenancy(self):
        """Find latest tenancy for tenant and update tenancy_id + meter_no."""
        for rec in self:
            if not rec.ten:
                rec.tenancy_id = False
                rec.meter_no = False
                continue
            print('calling')

            tenancy = self.env['tenancy.details'].search([
                ('tenancy_id', '=', rec.ten.id),
                ('contract_type', '=', 'running_contract'),
            ], order='id desc', limit=1)

            if tenancy:
                rec.tenancy_id = tenancy.id
                rec.meter_no = tenancy.unit_no
            else:
                rec.tenancy_id = False
                rec.meter_no = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        records._set_latest_tenancy()

        return records

    def write(self, vals):
        res = super().write(vals)

        # if 'ten' in vals:
        if 'category' in vals:
            self._set_latest_tenancy()

        return res

    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')
        return [('id', 'in', running_tenants)]

    @api.constrains('ten')
    def _check_tenant_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.ten:
                continue  # If empty, skip

            # 🔍 Check in tenancy.details if this tenant has an active contract
            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.ten.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.ten.name}' is not under an active tenancy contract."
                )

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')

    def action_sync_electric_data_to_lines(self):
        """Update existing category.line entries from electric.bill.line based on tenant and date."""

        for rec in self:
            if not rec.ten or not rec.months:
                raise UserError("Please select both a tenant and a month.")

            today = date.today()
            # Find electric.bill.line entries for this tenant
            electric_lines = self.env['electric.bill.line'].search([
                ('tenant_id', '=', rec.ten.id), ('bill_id.date', '=', today)
            ])
            # Create a map of electric lines by date
            electric_line_map = {
                line.bill_id.date: line for line in electric_lines
            }
            # Update ct_line entries if date matches electric line
            for ct_line in rec.ct_line_ids:
                elec_line = electric_line_map.get(ct_line.dt)
                if elec_line:
                    ct_line.open_unit = elec_line.open_unit
                    ct_line.close_unit = elec_line.close_unit
                    ct_line.reset_unit = elec_line.reset_date
                    ct_line.consumption = elec_line.consumption

    @api.depends('ct_line_ids.consumption')
    def _compute_total(self):
        for rec in self:
            rec.total = sum(line.consumption for line in rec.ct_line_ids)

    @api.model
    def create(self, vals):
        record = super(CategoryBill, self).create(vals)
        return record

    def _onchange_months(self):
        """Auto-populate category lines for selected month."""
        if self.months and not self.ct_line_ids:
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = month_map[self.months]
            year = date.today().year  # Or allow a user-defined year

            start_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])

            lines = []
            current_day = start_day
            while current_day <= last_day:
                lines.append((0, 0, {
                    'dt': current_day,
                    'open_unit': 0.0,
                    'close_unit': 0.0,
                    'consumption': 0.0
                }))
                current_day += timedelta(days=1)

            self.ct_line_ids = lines

class CategoryLine(models.Model):
    _name = 'category.line'

    ct_id = fields.Many2one('catagory.bill')
    dt = fields.Date(string='Date')
    open_unit = fields.Float(string='Initial Reading', digits=(4, 4))
    close_unit = fields.Float(string='Final reading', digits=(4, 4))
    reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('open_unit', 'close_unit', 'reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.close_unit > line.open_unit:
                line.consumption = (line.close_unit - line.open_unit) * (line.reset_unit)
            elif line.open_unit > line.close_unit:
                line.consumption = (line.close_unit * 1000) - line.open_unit
            else:
                line.consumption = 0.0


class DGReading(models.Model):
    _name = 'dg.reading'
    _description = 'DG Reading'
    _rec_name = 'tenant_id'

    category = fields.Char(string='Category', default='DG')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=lambda self: self._get_running_contract_tenants())

    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')

        return [('id', 'in', running_tenants)]
    month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], string="Month")
    dg_line_ids = fields.One2many('dg.reading.line', 'reading_id', string='Readings')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)
    date = fields.Date(string="Record Created Date", default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, readonly=True)

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')

    @api.depends('dg_line_ids.consumption')
    def _compute_total_consumption(self):
        for rec in self:
            rec.total_consumption = sum(line.consumption for line in rec.dg_line_ids)

    @api.constrains('tenant_id')
    def _check_tenant_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.tenant_id:
                continue  # If empty, skip

            # 🔍 Check in tenancy.details if this tenant has an active contract
            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.tenant_id.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.tenant_id.name}' is not under an active tenancy contract."
                )

    @api.model
    def create(self, vals):
        record = super(DGReading, self).create(vals)
        # if not record.dg_line_ids:
        #     record._onchange_month()
        return record

    # @api.onchange('month')
    def _onchange_month(self):
        """Auto-populate DG lines for selected month."""
        if self.month and not self.dg_line_ids:
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month_num = month_map[self.month]
            year = date.today().year

            start_day = date(year, month_num, 1)
            end_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            lines = []
            current = start_day
            while current <= end_day:
                lines.append((0, 0, {
                    'date': current,
                    'opening_unit': 0.0,
                    'closing_unit': 0.0,
                    'consumption': 0.0
                }))
                current += timedelta(days=1)

            self.dg_line_ids = lines

class DGReadingLine(models.Model):
    _name = 'dg.reading.line'
    _description = 'DG Reading Line'

    reading_id = fields.Many2one('dg.reading', string='DG Reading')
    date = fields.Date(string='Date')
    opening_unit = fields.Float(string='Initial Reading', digits=(16, 4))
    closing_unit = fields.Float(string='Final Reading', digits=(16, 4))
    reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('opening_unit', 'closing_unit','reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.reset_unit > 1:
                line.consumption = (line.closing_unit - line.opening_unit) * 1000
            elif line.closing_unit > line.opening_unit:
                line.consumption = (line.closing_unit - line.opening_unit)
            else:
                line.consumption = 0.0

class GasReading(models.Model):
    _name = 'gas.reading'
    _description = 'Gas Reading'
    _rec_name = 'tenant_id'

    category = fields.Char(string='Category', default='Gas')
    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        domain=lambda self: self._get_running_contract_tenants(),
    )
    month = fields.Selection([
        ('jan', 'January'), ('feb', 'February'), ('mar', 'March'),
        ('apr', 'April'), ('may', 'May'), ('jun', 'June'),
        ('jul', 'July'), ('aug', 'August'), ('sep', 'September'),
        ('oct', 'October'), ('nov', 'November'), ('dec', 'December')
    ], string="Month")
    date = fields.Date(string="Record Created Date", default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, readonly=True)
    gas_line_ids = fields.One2many('gas.reading.line', 'reading_id', string="Reading Lines")
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total', store=True)

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')

    @api.constrains('tenant_id')
    def _check_tenant_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.tenant_id:
                continue  # If empty, skip

            # 🔍 Check in tenancy.details if this tenant has an active contract
            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.tenant_id.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.tenant_id.name}' is not under an active tenancy contract."
                )

    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')

        return [('id', 'in', running_tenants)]

    @api.depends('gas_line_ids.consumption')
    def _compute_total(self):
        for rec in self:
            rec.total_consumption = sum(line.consumption for line in rec.gas_line_ids)

    # @api.onchange('month')
    def _onchange_month(self):
        if self.month:
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5,
                'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10,
                'nov': 11, 'dec': 12
            }
            month_num = month_map[self.month]
            year = date.today().year

            start_day = date(year, month_num, 1)
            end_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            lines = []
            current_day = start_day
            while current_day <= end_day:
                lines.append((0, 0, {
                    'date': current_day,
                    'opening_unit': 0.0,
                    'closing_unit': 0.0,
                    'consumption': 0.0
                }))
                current_day += timedelta(days=1)

            self.gas_line_ids = lines

    @api.model
    def create(self, vals):
        record = super(GasReading, self).create(vals)
        return record

    @api.model
    def cron_generate_gas_invoices(self):
        today = date.today()
        year = today.year
        month = today.month

        # Determine billing period
        if today.day == 26:
            period_month = month
            period_year = year
            start_date = date(period_year, period_month, 1)
            end_date = date(period_year, period_month, 15)
        elif today.day == 1:
            if month == 1:
                period_month = 12
                period_year = year - 1
            else:
                period_month = month - 1
                period_year = year
            start_date = date(period_year, period_month, 16)
            end_date = date(period_year, period_month, calendar.monthrange(period_year, period_month)[1])
        else:
            return  # Only run on 1st and 15th

        month_map = {
            1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'may', 6: 'jun',
            7: 'jul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
        }
        month_str = month_map[period_month]

        product = self.env['product.product'].search([('name', '=', 'gas')], limit=1)
        if not product:
            raise ValidationError("Product 'gas' not found.")

        readings = self.env['gas.reading'].search([
            ('month', '=', month_str),
            ('year', '=', period_year),
        ])

        for reading in readings:

            tenant = reading.tenant_id
            lines = reading.gas_line_ids.filtered(
                lambda l: start_date <= l.date <= end_date and not l.is_invoiced
            ).sorted(key=lambda l: l.date)

            if not lines:
                continue

            invoice_lines = []
            first_line = lines[0]

            last_line = lines[-1]

            reset_line = next((l for l in lines if l.reset_unit > 1), None)

            if reset_line:
                opening_1 = first_line.opening_unit
                closing_1 = reset_line.opening_unit
                consumption_1 = closing_1 - opening_1

                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f"Gas Usage (Before Reset)",
                    'quantity': 1,
                    'opening_reading': opening_1,
                    'closing_reading': closing_1,
                    'price_unit': consumption_1,
                    'multiplying_factor': 4.8020,
                    'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
                }))

                opening_2 = reset_line.opening_unit
                closing_2 = last_line.closing_unit
                consumption_2 = closing_2 - opening_2

                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f"Gas Usage (After Reset)",
                    'quantity': 1,
                    'opening_reading': opening_2,
                    'closing_reading': closing_2,
                    'price_unit': consumption_2,
                    'multiplying_factor': 4.8020,
                    'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
                }))
            else:
                opening = first_line.opening_unit
                closing = last_line.closing_unit
                consumption = closing - opening

                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f"Gas Usage ({start_date.strftime('%d %b')} – {end_date.strftime('%d %b')})",
                    'quantity': 1,
                    'opening_reading': opening,
                    'closing_reading': closing,
                    'price_unit': consumption,
                    'multiplying_factor': 4.8020,
                    'account_id': product.property_account_income_id.id or product.categ_id.property_account_income_categ_id.id,
                }))

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': tenant.id,
                'invoice_date': today,
                'invoice_line_ids': invoice_lines,
                'nhcl_invoice_type': 'gas',
            })

            for line in lines:
                line.is_invoiced = True


class GasReadingLine(models.Model):
    _name = 'gas.reading.line'
    _description = 'Gas Reading Line'

    reading_id = fields.Many2one('gas.reading')
    date = fields.Date(string='Date')
    opening_unit = fields.Float(string='Initial Reading', digits=(16, 4))
    closing_unit = fields.Float(string='Final Reading', digits=(16, 4))
    reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)
    is_invoiced = fields.Boolean(string='Invoiced', default=False)

    @api.depends('opening_unit', 'closing_unit', 'reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.reset_unit > 1:
                line.consumption = (line.closing_unit - line.opening_unit) * 1000
            elif line.closing_unit > line.opening_unit:
                line.consumption = (line.closing_unit - line.opening_unit)
            else:
                line.consumption = 0.0

class WaterReading(models.Model):
    _name = 'water.reading'
    _description = 'Tenant Water Reading'
    _rec_name = 'tenant_id'

    category = fields.Char(string='Category', default='Water')
    tenant_id = fields.Many2one('res.partner', string='Tenant',domain=lambda self: self._get_running_contract_tenants())
    month = fields.Selection([
        ('jan', 'January'), ('feb', 'February'), ('mar', 'March'),
        ('apr', 'April'), ('may', 'May'), ('jun', 'June'),
        ('jul', 'July'), ('aug', 'August'), ('sep', 'September'),
        ('oct', 'October'), ('nov', 'November'), ('dec', 'December')
    ], string="Month")
    water_line_ids = fields.One2many('water.reading.line', 'reading_id', string="Reading Lines")
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total', store=True)
    date = fields.Date(string="Record Created Date", required=True)  # default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, )

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')
    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')

        return [('id', 'in', running_tenants)]

    @api.constrains('tenant_id')
    def _check_tenant_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.tenant_id:
                continue  # If empty, skip

            # 🔍 Check in tenancy.details if this tenant has an active contract
            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.tenant_id.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.tenant_id.name}' is not under an active tenancy contract."
                )

    @api.depends('water_line_ids.consumption')
    def _compute_total(self):
        for rec in self:
            rec.total_consumption = sum(line.consumption for line in rec.water_line_ids)

    # @api.onchange('month')
    def _onchange_month(self):
        if self.month:
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5,
                'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10,
                'nov': 11, 'dec': 12
            }
            month_num = month_map[self.month]
            year = date.today().year

            start_day = date(year, month_num, 1)
            end_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            lines = []
            current_day = start_day
            while current_day <= end_day:
                lines.append((0, 0, {
                    'date': current_day,
                    'opening_unit': 0.0,
                    'closing_unit': 0.0,
                    'consumption': 0.0
                }))
                current_day += timedelta(days=1)

            self.water_line_ids = lines

class WaterReadingLine(models.Model):
    _name = 'water.reading.line'
    _description = 'Water Reading Line'

    reading_id = fields.Many2one('water.reading')
    date = fields.Date(string='Date')
    opening_unit = fields.Float(string='Start')
    closing_unit = fields.Float(string='Close')
    reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('opening_unit', 'closing_unit', 'reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.reset_unit > 1:
                line.consumption = (line.closing_unit - line.opening_unit) * 1000
            elif line.closing_unit > line.opening_unit:
                line.consumption = (line.closing_unit - line.opening_unit)
            else:
                line.consumption = 0.0

# it's for the HVAC new screen
class HVACReading(models.Model):
    _name = 'hvac.reading'
    _description = 'HVAC Reading'
    _rec_name = 'tenant_id'

    category = fields.Char(string='Category', default='HVAC')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=lambda self: self._get_running_contract_tenants())

    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')

        return [('id', 'in', running_tenants)]
    month = fields.Selection([
        ('jan', 'January'), ('feb', 'February'), ('mar', 'March'),
        ('apr', 'April'), ('may', 'May'), ('jun', 'June'),
        ('jul', 'July'), ('aug', 'August'), ('sep', 'September'),
        ('oct', 'October'), ('nov', 'November'), ('dec', 'December')
    ], string="Month")
    hvac_line_ids = fields.One2many('hvac.reading.line', 'reading_id', string='Readings')
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total_consumption', store=True)
    date = fields.Date(string="Record Created Date", required=True)  # default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, )

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')
    @api.constrains('tenant_id')
    def _check_tenant_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.tenant_id:
                continue  # If empty, skip

            # 🔍 Check in tenancy.details if this tenant has an active contract
            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.tenant_id.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.tenant_id.name}' is not under an active tenancy contract."
                )

    @api.depends('hvac_line_ids.consumption')
    def _compute_total_consumption(self):
        for rec in self:
            rec.total_consumption = sum(line.consumption for line in rec.hvac_line_ids)

    @api.model
    def create(self, vals):
        record = super(HVACReading, self).create(vals)
        # if not record.hvac_line_ids:
        #     record._onchange_month()
        return record

    def _onchange_month(self):
        if self.month and not self.hvac_line_ids:
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month_num = month_map[self.month]
            year = date.today().year

            start_day = date(year, month_num, 1)
            end_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            lines = []
            current = start_day
            while current <= end_day:
                lines.append((0, 0, {
                    'date': current,
                    'opening_unit': 0.0,
                    'closing_unit': 0.0,
                    'consumption': 0.0
                }))
                current += timedelta(days=1)

            self.hvac_line_ids = lines

class HVACReadingLine(models.Model):
    _name = 'hvac.reading.line'
    _description = 'HVAC Reading Line'

    reading_id = fields.Many2one('hvac.reading', string='HVAC Reading')
    date = fields.Date(string='Date')
    opening_unit = fields.Float(string='Initial Reading', digits=(16, 4))
    closing_unit = fields.Float(string='Final Reading', digits=(16, 4))
    reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('closing_unit', 'opening_unit', 'reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.reset_unit > 1:
                line.consumption = (line.closing_unit - line.opening_unit) * 1000
            elif line.closing_unit > line.opening_unit:
                line.consumption = (line.closing_unit - line.opening_unit)
            else:
                line.consumption = 0.0

class HotWaterReading(models.Model):
    _name = 'hot.water.reading'
    _description = 'Tenant Hot Water Reading'
    _rec_name = 'tenant_id'

    category = fields.Char(string='Category', default='Cool Water')
    tenant_id = fields.Many2one('res.partner', string='Tenant', domain=lambda self: self._get_running_contract_tenants())

    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')

        return [('id', 'in', running_tenants)]
    month = fields.Selection([
        ('jan', 'January'), ('feb', 'February'), ('mar', 'March'),
        ('apr', 'April'), ('may', 'May'), ('jun', 'June'),
        ('jul', 'July'), ('aug', 'August'), ('sep', 'September'),
        ('oct', 'October'), ('nov', 'November'), ('dec', 'December')
    ], string="Month")

    hot_water_line_ids = fields.One2many('hot.water.reading.line', 'reading_id', string="Reading Lines")
    total_consumption = fields.Float(string='Total Consumption', compute='_compute_total', store=True)
    date = fields.Date(string="Record Created Date", required=True)  # default=fields.Date.context_today)
    year = fields.Char(string="Year", compute='_compute_year', store=True, )

    @api.depends('date')
    def _compute_year(self):
        for rec in self:
            if rec.date:
                rec.year = rec.date.strftime('%Y')
    @api.constrains('tenant_id')
    def _check_tenant_is_active(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.tenant_id:
                continue  # If empty, skip

            # 🔍 Check in tenancy.details if this tenant has an active contract
            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.tenant_id.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.tenant_id.name}' is not under an active tenancy contract."
                )

    @api.depends('hot_water_line_ids.consumption')
    def _compute_total(self):
        for rec in self:
            rec.total_consumption = sum(line.consumption for line in rec.hot_water_line_ids)

    # @api.onchange('month')
    def _onchange_month(self):
        if self.month:
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5,
                'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10,
                'nov': 11, 'dec': 12
            }
            month_num = month_map[self.month]
            year = date.today().year

            start_day = date(year, month_num, 1)
            end_day = date(year, month_num, calendar.monthrange(year, month_num)[1])

            lines = []
            current_day = start_day
            while current_day <= end_day:
                lines.append((0, 0, {
                    'date': current_day,
                    'opening_unit': 0.0,
                    'closing_unit': 0.0,
                    'consumption': 0.0
                }))
                current_day += timedelta(days=1)

            self.hot_water_line_ids = lines

class HotWaterReadingLine(models.Model):
    _name = 'hot.water.reading.line'
    _description = 'Hot Water Reading Line'

    reading_id = fields.Many2one('hot.water.reading')
    date = fields.Date(string='Date')
    opening_unit = fields.Float(string='Start')
    closing_unit = fields.Float(string='Close')
    reset_unit = fields.Integer(string='Reset', default=1)
    consumption = fields.Float(string='Consumption', compute='_compute_consumption', store=True)

    @api.depends('opening_unit', 'closing_unit', 'reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.reset_unit > 1:
                line.consumption = (line.closing_unit - line.opening_unit) * 1000
            elif line.closing_unit > line.opening_unit:
                line.consumption = (line.closing_unit - line.opening_unit)
            else:
                line.consumption = 0.0


class  HVACDCReading(models.Model):
    _name = 'hvac.dc.reading'
    _description = 'HVAC DC Reading'
    _rec_name = 'tenant_id'

    category = fields.Char(string='Category', default='HVAC DC')
    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        domain=lambda self: self._get_running_contract_tenants()
    )

    @api.model
    def _get_running_contract_tenants(self):
        running_tenants = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract')
        ]).mapped('tenancy_id.id')

        return [('id', 'in', running_tenants)]

    month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], string="Month")

    hvac_dc_line_ids = fields.One2many(
        'hvac.dc.reading.line',
        'reading_id',
        string='Readings'
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

    @api.constrains('tenant_id')
    def _check_tenant_is_active(self):
        today = fields.Date.today()

        for rec in self:
            if not rec.tenant_id:
                continue

            active = self.env['tenancy.details'].search_count([
                ('tenancy_id', '=', rec.tenant_id.id),
                ('start_date', '<=', today),
                ('end_date', '>=', today),
            ])

            if not active:
                raise ValidationError(
                    f"Tenant '{rec.tenant_id.name}' is not under an active tenancy contract."
                )

    @api.depends('hvac_dc_line_ids.consumption')
    def _compute_total_consumption(self):
        for rec in self:
            rec.total_consumption = sum(
                line.consumption
                for line in rec.hvac_dc_line_ids
            )

    @api.model
    def create(self, vals):
        record = super(HVACDCReading, self).create(vals)
        # if not record.hvac_dc_line_ids:
        #     record._onchange_month()
        return record

    def _onchange_month(self):
        if self.month and not self.hvac_dc_line_ids:
            month_map = {
                'jan': 1,
                'feb': 2,
                'mar': 3,
                'apr': 4,
                'may': 5,
                'jun': 6,
                'jul': 7,
                'aug': 8,
                'sep': 9,
                'oct': 10,
                'nov': 11,
                'dec': 12
            }

            month_num = month_map[self.month]
            year = date.today().year

            start_day = date(year, month_num, 1)
            end_day = date(
                year,
                month_num,
                calendar.monthrange(year, month_num)[1]
            )

            lines = []
            current = start_day

            while current <= end_day:
                lines.append((0, 0, {
                    'date': current,
                    'opening_unit': 0.0,
                    'closing_unit': 0.0,
                    'consumption': 0.0
                }))

                current += timedelta(days=1)

            self.hvac_dc_line_ids = lines


class HVACDCReadingLine(models.Model):
    _name = 'hvac.dc.reading.line'
    _description = 'HVAC DC Reading Line'

    reading_id = fields.Many2one(
        'hvac.dc.reading',
        string='HVAC DC Reading'
    )

    date = fields.Date(
        string='Date'
    )

    opening_unit = fields.Float(
        string='Initial Reading',
        digits=(16, 4)
    )

    closing_unit = fields.Float(
        string='Final Reading',
        digits=(16, 4)
    )

    reset_unit = fields.Integer(
        string='Reset',
        default=1
    )

    consumption = fields.Float(
        string='Consumption',
        compute='_compute_consumption',
        store=True
    )

    @api.depends('closing_unit', 'opening_unit', 'reset_unit')
    def _compute_consumption(self):
        for line in self:
            if line.reset_unit > 1:
                line.consumption = (
                    line.closing_unit - line.opening_unit
                ) * 1000

            elif line.closing_unit > line.opening_unit:
                line.consumption = (
                    line.closing_unit - line.opening_unit
                )

            else:
                line.consumption = 0.0