# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TenancyDetails(models.Model):
    _name = 'tenancy.details'
    _description = 'Information Related To customer Tenancy while Creating Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'tenancy_seq'

    tenancy_seq = fields.Char(string='Sequence', required=True,readonly=True, copy=False, default=lambda self: ('New'))
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    close_contract_state = fields.Boolean(string='Contract State')
    active_contract_state = fields.Boolean(string='Active State')
    is_extended = fields.Boolean(string='Extended')
    contract_type = fields.Selection([('new_contract', 'Draft'),
                                      ('running_contract', 'Running'),
                                      ('cancel_contract', 'Cancel'),
                                      ('close_contract', 'Close'),
                                      ('expire_contract', 'Expire')],
                                     string='Contract Type')

    # Tenancy Information
    tenancy_id = fields.Many2one('res.partner', string='Tenant', domain=[('user_type', '=', 'customer')])
    is_any_broker = fields.Boolean(string='Any Broker')
    broker_id = fields.Many2one('res.partner', string='Broker', domain=[('user_type', '=', 'broker')])
    commission = fields.Monetary(string='Commission ', compute='_compute_broker_commission', store=True)
    last_invoice_payment_date = fields.Date(string='Last Invoice Payment Date')
    broker_invoice_state = fields.Boolean(string='Broker  invoice State')
    broker_invoice_id = fields.Many2one('account.move', string='Bill')
    term_condition = fields.Html(string='Term and Condition')
    is_any_deposit = fields.Boolean(string="Deposit")
    deposit_amount = fields.Monetary(string="Security Deposit")

    # Property Information
    property_id = fields.Many2one('property.details', string='Property', domain=[('stage', '=', 'available')])
    is_extra_service = fields.Boolean(related="property_id.is_extra_service", string="Any Extra Services")
    property_landlord_id = fields.Many2one(related='property_id.landlord_id', string='Landlord', store=True)
    property_type = fields.Selection(related='property_id.type', string='Type')
    total_rent = fields.Monetary(string='Rental Amount')
    extra_services_ids = fields.One2many('tenancy.service.line', 'tenancy_id', string="Services")

    # Time Period
    payment_term = fields.Selection([('monthly', 'Monthly'),
                                     ('full_payment', 'Full Payment'), ('quarterly', 'Quarterly')],
                                    string='Payment Term')
    # duration_id = fields.Many2one('contract.duration', string='Duration')
    duration_id = fields.Many2one('contract.duration', string='Duration', compute='_compute_duration', store=True)
    contract_agreement = fields.Binary(string='Contract Agreement')
    file_name = fields.Char(string='File Name')
    month = fields.Integer(related='duration_id.month', string='Month')
    start_date = fields.Date(string='Start Date', default=fields.Date.today(),required=True)
    # end_date = fields.Date(string='End Date', compute='_compute_end_date')
    end_date = fields.Date(string='End Date', required=True)

    rent_type = fields.Selection([('once', 'One Month'), ('e_rent', 'All Month')], string='Brokerage Type')
    commission_type = fields.Selection([('f', 'Fix'), ('p', 'Percentage')], string="Commission Type")
    broker_commission = fields.Monetary(string='Commission')
    broker_commission_percentage = fields.Float(string='Percentage')

    # floor number
    # floor_no = fields.Integer(string='Floor No',default=1)
    floor_no = fields.Selection(
        [('-4', 'Basement'), ('-3', 'Lower Cellar'), ('-2', 'Cellar'), ('-1', 'Parking'), ('0', 'Ground Floor'),
         ('1', 'Floor 1'), ('2', 'Floor 2'), ('3', 'Floor 3'), ('4', 'Floor 4'),
         ('5', 'Terrace'), ('6', 'Atrium'), ('7', 'Mall Outside'), ('8', 'Mall Entrance')],
        string='Floor Number',required=True)
    # Related Field
    rent_invoice_ids = fields.One2many('rent.invoice', 'tenancy_id', string='Invoices')


    # for duration calculation based on start and end Date
    # @api.depends('start_date', 'end_date')
    # def _compute_duration(self):
    #     """Compute the duration based on the start_date and end_date, and create a record if not found."""
    #     for rec in self:
    #         if rec.start_date and rec.end_date:
    #             # Ensure start_date is before or equal to end_date
    #             if rec.end_date < rec.start_date:
    #                 raise ValidationError("End Date must be greater than or equal to Start Date.")
    #             # Calculate the difference in months and days
    #             delta = relativedelta(rec.end_date, rec.start_date)
    #             months = delta.years * 12 + delta.months  # Convert years to months
    #             days = delta.days
    #             # Search for the corresponding duration
    #             duration = self.env['contract.duration'].search([
    #                 ('month', '=', months),
    #                 ('day', '=', days)
    #             ], limit=1)
    #             # If no matching duration is found, create a new one
    #             if not duration:
    #                 description = f"{months} Months, {days} Days" if months > 0 else f"{days} Days"
    #                 duration = self.env['contract.duration'].create({'duration': description,'month': months,'day': days})
    #
    #             # Assign the duration to the record
    #             rec.duration_id = duration
    #             print(rec.duration_id)  # Debugging output
    #         else:
    #             rec.duration_id = False

    # Sequence Create
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """Compute the duration based on the start_date and end_date, and create a record if not found."""
        for rec in self:
            if rec.start_date and rec.end_date:
                # Ensure start_date is before or equal to end_date
                if rec.end_date < rec.start_date:
                    raise ValidationError("End Date must be greater than or equal to Start Date.")

                # Calculate difference using relativedelta
                delta = relativedelta(rec.end_date + datetime.timedelta(days=1), rec.start_date)
                years = delta.years
                months = delta.months
                days = delta.days

                months_total = years * 12 + months

                # Build human-readable description
                parts = []
                if years:
                    parts.append(f"{years} Year{'s' if years > 1 else ''}")
                if months:
                    parts.append(f"{months} Month{'s' if months > 1 else ''}")
                if days:
                    parts.append(f"{days} Day{'s' if days > 1 else ''}")

                description = ", ".join(parts) or "0 Days"

                # Search for matching duration
                duration = self.env['contract.duration'].search([
                    ('month', '=', months_total),
                    ('day', '=', days)
                ], limit=1)

                # Create duration if not found
                if not duration:
                    duration = self.env['contract.duration'].create({
                        'duration': description,
                        'month': months_total,
                        'day': days
                    })

                # Assign the duration
                rec.duration_id = duration
                print(duration)
            else:
                rec.duration_id = False

    # @api.model
    # def create(self, vals):
    #     # if vals.get('tenancy_seq', ('New')) == ('New'):
    #     #     vals['tenancy_seq'] = self.env['ir.sequence'].next_by_code(
    #     #         'tenancy.details') or ('New')
    #     # if vals.get('tenancy_id'):
    #     #     # existing = self.search([('tenancy_id', '=', vals['tenancy_id'])], limit=1)
    #     #     # seq = self.search([('tenancy_seq', '=', vals['tenancy_seq'])], limit=1)
    #     #     existing = self.search([('tenancy_id', '=', vals['tenancy_id']),
    #     #                             ('contract_type', 'in', ['new_contract', 'running_contract', False])], limit=1)
    #     #     seq = self.search([('tenancy_seq', '=', vals['tenancy_seq']),
    #     #                        ('contract_type', 'in', ['new_contract', 'running_contract', False])], limit=1)
    #     #     if existing or seq:
    #     #         raise ValidationError("You can't Create same Tenant It's already Existed. And the number also.")
    #
    #     res = super(TenancyDetails, self).create(vals)
    #     return res

    @api.depends('start_date', 'month')
    def _compute_end_date(self):
        end_date = fields.date.today()
        for rec in self:
            end_date = rec.start_date + relativedelta(months=rec.month)
            rec.end_date = end_date

    @api.depends('is_any_broker', 'month')
    def _compute_broker_commission(self):
        for rec in self:
            if rec.is_any_broker:
                if rec.rent_type == 'once':
                    if rec.commission_type == 'f':
                        rec.commission = rec.broker_commission
                    else:
                        rec.commission = rec.broker_commission_percentage * rec.total_rent / 100
                else:
                    if rec.commission_type == 'f':
                        rec.commission = rec.broker_commission * rec.month
                    else:
                        rec.commission = rec.broker_commission_percentage * rec.total_rent * rec.month / 100
            else:
                rec.commission = 0

    # Smart Button
    invoice_count = fields.Integer(string='Invoice Count', compute="_compute_invoice_count")

    @api.depends('rent_invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            count = self.env['rent.invoice'].search_count([('tenancy_id', '=', rec.id)])
            rec.invoice_count = count

    def action_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'rent.invoice',
            'domain': [('tenancy_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current'
        }

    # Button
    def action_close_contract(self):
        self.close_contract_state = True
        self.property_id.write({'stage': 'available'})
        self.contract_type = 'close_contract'
        return True

    def action_active_contract(self):
        if self.end_date < fields.Date.today():
            raise ValidationError("You can't Active Tenant It's already EXPIRY")
        invoice_lines = []
        if self.is_any_broker:
            self.action_broker_invoice()
        self.contract_type = 'running_contract'
        self.active_contract_state = True
        # custom_name_rs = self.env['ir.sequence'].next_by_code('rs.invoice.sequence')  # You must define this sequence
        # custom_name_mg = self.env['ir.sequence'].next_by_code('mg.invoice.sequence')  # You must define this sequence
        #custom_name_sb = self.env['ir.sequence'].next_by_code('sb.invoice.sequence')  # You must define this sequence
        # custom_name = f"MG/{fields.Date.today().year}/{sequence}"
        # if self.invoice_type == 'rs':
        #     demo = {
        #         'product_id': self.env.ref('rental_management.property_product_rs').id,
        #         'name': 'Revenue Invoice of ' + self.property_id.name,
        #         'quantity': 1,
        #         'percentage': self.rs_percentage,
        #     }
        #     # invoice_lines.append((0, 0, record))
        #     blank_invoice = self.env['account.move'].sudo().create({
        #         'partner_id': self.tenancy_id.id,
        #         'move_type': 'out_invoice',
        #         'invoice_date': fields.Date.today(),
        #         'invoice_line_ids':  [(0, 0, demo)],
        #         'nhcl_invoice_type': 'rs',
        #
        #         # 'invoice_type_custom': 'rs',
        #         # 'name': custom_name_rs,
        #
        #     })
        #     blank_invoice.tenancy_id = self.id
        #
        #     self.env['rent.invoice'].create({
        #         'tenancy_id': self.id,
        #         'type': 'rent',
        #         'invoice_date': fields.Date.today(),
        #         'description': 'RS Invoice',
        #         'rent_invoice_id': blank_invoice.id,
        #         'amount': 0.0,
        #         'rent_amount': 0.0,
        #     })
        #
        # elif self.invoice_type == 'mg':
        #     blank_invoice = self.env['account.move'].sudo().create({
        #         'partner_id': self.tenancy_id.id,
        #         'move_type': 'out_invoice',
        #         'invoice_date': fields.Date.today(),
        #         'invoice_line_ids': [],
        #         'nhcl_invoice_type': 'mg',
        #         # 'invoice_type_custom': 'mg',
        #         # 'name': custom_name_mg,
        #     })
        #     blank_invoice.tenancy_id = self.id
        #
        #     self.env['rent.invoice'].create({
        #         'tenancy_id': self.id,
        #         'type': 'rent',
        #         'invoice_date': fields.Date.today(),
        #         'description': 'MG Invoice',
        #         'rent_invoice_id': blank_invoice.id,
        #         'amount': 0.0,
        #         'rent_amount': 0.0,
        #     })

        if self.sft_fixed == 'sft':
            if self.payment_term == 'monthly':
                record = {
                    'product_id': self.env.ref('rental_management.property_product_1').id,
                    'name': 'First Invoice of ' + self.property_id.name,
                    'quantity': 1,
                    'price_unit': self.total_rent,#self.chargeable_area * self.rate,
                    'nhcl_area_units': self.carpet_area if self.carpet_value_take else self.chargeable_area
                }
                invoice_lines.append((0, 0, record))
                if self.is_any_deposit:
                    deposit_record = {
                        'product_id': self.env.ref('rental_management.property_product_1').id,
                        'name': 'Deposit of ' + self.property_id.name,
                        'quantity': 1,
                        'price_unit': self.deposit_amount
                    }
                    invoice_lines.append((0, 0, deposit_record))
                for rec in self:
                    desc = ""
                    if rec.is_extra_service:
                        for line in rec.extra_services_ids:
                            if line.service_type == "once":
                                desc = "Once"
                            if line.service_type == "monthly":
                                desc = "Monthly"
                            service_invoice_record = {
                                'product_id': line.service_id.id,
                                'name': desc,
                                'quantity': 1,
                                'price_unit': line.price
                            }
                            invoice_lines.append((0, 0, service_invoice_record))
                data = {
                    'partner_id': self.tenancy_id.id,
                    'move_type': 'out_invoice',
                    'invoice_date': fields.Date.today(),
                    'invoice_line_ids': invoice_lines,
                    'nhcl_invoice_type': 'rent'
                }
                invoice_id = self.env['account.move'].sudo().create(data)
                invoice_id.tenancy_id = self.id
                # invoice_id.action_post()
                self.last_invoice_payment_date = invoice_id.invoice_date
                self.action_send_active_contract()
                amount_total = invoice_id.amount_total
                rent_invoice = {
                    'tenancy_id': self.id,
                    'type': 'rent',
                    'invoice_date': fields.Date.today(),
                    'description': 'First Rent',
                    'rent_invoice_id': invoice_id.id,
                    'amount': self.total_rent,
                    'rent_amount': self.chargeable_area * self.rate
                }
                if self.is_any_deposit:
                    rent_invoice['description'] = 'First Rent + Deposit'
                else:
                    rent_invoice['description'] = 'First Rent'
                self.env['rent.invoice'].create(rent_invoice)
            elif self.payment_term == 'quarterly':
                record = {
                    'product_id': self.env.ref('rental_management.property_product_1').id,
                    'name': 'First Quarter Invoice of ' + self.property_id.name,
                    'quantity': 1,
                    'price_unit': self.total_rent ,#* 3,
                    'nhcl_area_units': self.carpet_area if self.carpet_value_take else self.chargeable_area
                }
                invoice_lines.append((0, 0, record))
                if self.is_any_deposit:
                    deposit_record = {
                        'product_id': self.env.ref('rental_management.property_product_1').id,
                        'name': 'Deposit of ' + self.property_id.name,
                        'quantity': 1,
                        'price_unit': self.deposit_amount
                    }
                    invoice_lines.append((0, 0, deposit_record))
                for rec in self:
                    desc = ""
                    if rec.is_extra_service:
                        for line in rec.extra_services_ids:
                            if line.service_type == "once":
                                desc = "Once"
                            if line.service_type == "monthly":
                                desc = "Monthly"
                            service_invoice_record = {
                                'product_id': line.service_id.id,
                                'name': desc,
                                'quantity': 1,
                                'price_unit': line.price
                            }
                            invoice_lines.append((0, 0, service_invoice_record))
                data = {
                    'partner_id': self.tenancy_id.id,
                    'move_type': 'out_invoice',
                    'invoice_date': fields.Date.today(),
                    'invoice_line_ids': invoice_lines,
                    'nhcl_invoice_type': 'rent',
                }
                invoice_id = self.env['account.move'].sudo().create(data)
                invoice_id.tenancy_id = self.id
                # invoice_id.action_post()
                self.last_invoice_payment_date = invoice_id.invoice_date
                self.action_send_active_contract()
                amount_total = invoice_id.amount_total
                rent_invoice = {
                    'tenancy_id': self.id,
                    'type': 'rent',
                    'invoice_date': fields.Date.today(),
                    'description': 'First Quarter Rent',
                    'rent_invoice_id': invoice_id.id,
                    'amount': self.total_rent,
                    'rent_amount': self.total_rent * 3
                }
                if self.is_any_deposit:
                    rent_invoice['description'] = 'First Quarter Rent + Deposit'
                else:
                    rent_invoice['description'] = 'First Quarter Rent'
                self.env['rent.invoice'].create(rent_invoice)
            # fully payment
            # elif self.payment_term == 'full_payment':
            else:
                record = {
                    'product_id': self.env.ref('rental_management.property_product_1').id,
                    'name': 'Full payment Invoice of ' + self.property_id.name,
                    'quantity': 1,
                    'price_unit': self.total_rent,
                    'nhcl_area_units': self.carpet_area if self.carpet_value_take else self.chargeable_area,
                }
                invoice_lines.append((0, 0, record))
                if self.is_any_deposit:
                    deposit_record = {
                        'product_id': self.env.ref('rental_management.property_product_1').id,
                        'name': 'Deposit of ' + self.property_id.name,
                        'quantity': 1,
                        'price_unit': self.deposit_amount
                    }
                    invoice_lines.append((0, 0, deposit_record))
                for rec in self:
                    desc = ""
                    if rec.is_extra_service:
                        for line in rec.extra_services_ids:
                            if line.service_type == "once":
                                desc = "Once"
                            if line.service_type == "monthly":
                                desc = "Monthly"
                            service_invoice_record = {
                                'product_id': line.service_id.id,
                                'name': desc,
                                'quantity': 1,
                                'price_unit': line.price
                            }
                            invoice_lines.append((0, 0, service_invoice_record))
                data = {
                    'partner_id': self.tenancy_id.id,
                    'move_type': 'out_invoice',
                    'invoice_date': fields.Date.today(),
                    'invoice_line_ids': invoice_lines,
                    'nhcl_invoice_type': 'rent'
                }
                invoice_id = self.env['account.move'].sudo().create(data)
                invoice_id.tenancy_id = self.id
                # invoice_id.action_post()
                self.last_invoice_payment_date = invoice_id.invoice_date
                self.action_send_active_contract()
                amount_total = invoice_id.amount_total
                rent_invoice = {
                    'tenancy_id': self.id,
                    'type': 'rent',
                    'invoice_date': fields.Date.today(),
                    'description': 'Full payment Rent',
                    'rent_invoice_id': invoice_id.id,
                    'amount':self.total_rent,
                    'rent_amount': self.total_rent
                }
                if self.is_any_deposit:
                    rent_invoice['description'] = 'Full payment Rent + Deposit'
                else:
                    rent_invoice['description'] = 'Full payment Rent'
                self.env['rent.invoice'].create(rent_invoice)

        # this is the part of payment_term blank record invoice create
        # else:
        #     record = {
        #         'product_id': self.env.ref('rental_management.property_product_1').id,
        #         'name': 'Payment Invoice of ' + self.property_id.name,
        #         'quantity': 1,
        #         'price_unit': self.lum_sum,
        #         'nhcl_area_units': self.chargeable_area,
        #     }
        #     invoice_lines.append((0, 0, record))
        #     if self.is_any_deposit:
        #         deposit_record = {
        #             'product_id': self.env.ref('rental_management.property_product_1').id,
        #             'name': 'Deposit of ' + self.property_id.name,
        #             'quantity': 1,
        #             'price_unit': self.deposit_amount
        #         }
        #         invoice_lines.append((0, 0, deposit_record))
        #     for rec in self:
        #         desc = ""
        #         if rec.is_extra_service:
        #             for line in rec.extra_services_ids:
        #                 if line.service_type == "once":
        #                     desc = "Once"
        #                 if line.service_type == "monthly":
        #                     desc = "Monthly"
        #                 service_invoice_record = {
        #                     'product_id': line.service_id.id,
        #                     'name': desc,
        #                     'quantity': 1,
        #                     'price_unit': line.price
        #                 }
        #                 invoice_lines.append((0, 0, service_invoice_record))
        #     data = {
        #         'partner_id': self.tenancy_id.id,
        #         'move_type': 'out_invoice',
        #         'invoice_date': fields.Date.today(),
        #         'invoice_line_ids': invoice_lines
        #     }
        #     invoice_id = self.env['account.move'].sudo().create(data)
        #     invoice_id.tenancy_id = self.id
        #     #invoice_id.action_post()
        #     self.last_invoice_payment_date = invoice_id.invoice_date
        #     self.action_send_active_contract()
        #     amount_total = invoice_id.amount_total
        #     rent_invoice = {
        #         'tenancy_id': self.id,
        #         'type': 'rent',
        #         'invoice_date': fields.Date.today(),
        #         'description': 'Payment Rent',
        #         'rent_invoice_id': invoice_id.id,
        #         'amount': amount_total,
        #         'rent_amount': self.lum_sum,
        #     }
        #     if self.is_any_deposit:
        #         rent_invoice['description'] = 'Full payment Rent + Deposit'
        #     else:
        #         rent_invoice['description'] = 'Full payment Rent'
        #     self.env['rent.invoice'].create(rent_invoice)
        elif self.sft_fixed == 'Fixed':
            record = {
                'product_id': self.env.ref('rental_management.property_product_1').id,
                'name': 'Payment Invoice of ' + self.property_id.name,
                'quantity': 1,
                'price_unit': 0,
                'nhcl_area_units': "-"
            }
            invoice_lines.append((0, 0, record))
            if self.is_any_deposit:
                deposit_record = {
                    'product_id': self.env.ref('rental_management.property_product_1').id,
                    'name': 'Deposit of ' + self.property_id.name,
                    'quantity': 1,
                    'price_unit': self.deposit_amount
                }
                invoice_lines.append((0, 0, deposit_record))
            for rec in self:
                desc = ""
                if rec.is_extra_service:
                    for line in rec.extra_services_ids:
                        if line.service_type == "once":
                            desc = "Once"
                        if line.service_type == "monthly":
                            desc = "Monthly"
                        service_invoice_record = {
                            'product_id': line.service_id.id,
                            'name': desc,
                            'quantity': 1,
                            'price_unit': line.price
                        }
                        invoice_lines.append((0, 0, service_invoice_record))
            data = {
                'partner_id': self.tenancy_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'nhcl_invoice_type': 'rent'
            }
            invoice_id = self.env['account.move'].sudo().create(data)
            invoice_id.tenancy_id = self.id
            # invoice_id.action_post()
            self.last_invoice_payment_date = invoice_id.invoice_date
            self.action_send_active_contract()
            amount_total = invoice_id.amount_total
            rent_invoice = {
                'tenancy_id': self.id,
                'type': 'rent',
                'invoice_date': fields.Date.today(),
                'description': 'Payment Rent',
                'rent_invoice_id': invoice_id.id,
                'amount': self.total_rent,
                'rent_amount': self.lum_sum,
            }
            if self.is_any_deposit:
                rent_invoice['description'] = 'Full payment Rent + Deposit'
            else:
                rent_invoice['description'] = 'Full payment Rent'
            self.env['rent.invoice'].create(rent_invoice)
        commercial_term = self.env['commerce.term.term'].search([
            ('tenacy_id', '=', self.id)
        ], order='start_date asc', limit=1)

        if not commercial_term:
            return

        if commercial_term.rent_type == 'rs':

            demo = {
                'product_id': self.env.ref('rental_management.property_product_1').id,
                'name': 'Payment Invoice of ' + self.property_id.name,
                'quantity': 1,
                'percentage': commercial_term.revenue,  # or self.rs_percentage if required
            }

            blank_invoice = self.env['account.move'].sudo().create({
                'partner_id': self.tenancy_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, demo)],
                'nhcl_invoice_type': 'rs',
            })

            blank_invoice.tenancy_id = self.id

            self.env['rent.invoice'].create({
                'tenancy_id': self.id,
                'type': 'rent',
                'invoice_date': fields.Date.today(),
                'description': 'RS Invoice',
                'rent_invoice_id': blank_invoice.id,
                'amount': 0.0,
                'rent_amount': 0.0,
            })

        elif commercial_term.rent_type == 'mg':

            blank_invoice = self.env['account.move'].sudo().create({
                'partner_id': self.tenancy_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [],
                'nhcl_invoice_type': 'mg',
            })

            blank_invoice.tenancy_id = self.id

            self.env['rent.invoice'].create({
                'tenancy_id': self.id,
                'type': 'rent',
                'invoice_date': fields.Date.today(),
                'description': 'MG Invoice',
                'rent_invoice_id': blank_invoice.id,
                'amount': 0.0,
                'rent_amount': 0.0,
            })

        elif self.invoice_type == 'rs_or_mg':
            # Create two invoices, one for RS and one for MG
            blank_invoice_rs = self.env['account.move'].sudo().create({
                'partner_id': self.tenancy_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [],
                'nhcl_invoice_type': 'rs',
                # 'invoice_type_custom': 'rs',
                # 'name': custom_name_rs,
            })
            blank_invoice_rs.tenancy_id = self.id

            self.env['rent.invoice'].create({
                'tenancy_id': self.id,
                'type': 'rent',
                'invoice_date': fields.Date.today(),
                'description': 'RS Invoice',
                'rent_invoice_id': blank_invoice_rs.id,
                'amount': 0.0,
                'rent_amount': 0.0,
            })

            blank_invoice_mg = self.env['account.move'].sudo().create({
                'partner_id': self.tenancy_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [],
                'nhcl_invoice_type': 'mg',
                # 'invoice_type_custom': 'mg',
                # 'name': custom_name_mg,
            })
            blank_invoice_mg.tenancy_id = self.id

            self.env['rent.invoice'].create({
                'tenancy_id': self.id,
                'type': 'rent',
                'invoice_date': fields.Date.today(),
                'description': 'MG Invoice',
                'rent_invoice_id': blank_invoice_mg.id,
                'amount': 0.0,
                'rent_amount': 0.0,
            })


        elif self.invoice_type == 'slb':
            blank_invoice = self.env['account.move'].sudo().create({
                'partner_id': self.tenancy_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [],
                'nhcl_invoice_type': 'slb',
                # 'invoice_type_custom': self.invoice_type,
                # 'name': custom_name_sb,
            })
            blank_invoice.tenancy_id = self.id

            self.env['rent.invoice'].create({
                'tenancy_id': self.id,
                'type': 'rent',
                'invoice_date': fields.Date.today(),
                'description': 'SB Invoice',
                'rent_invoice_id': blank_invoice.id,
                'amount': 0.0,
                'rent_amount': 0.0,
            })


    def action_cancel_contract(self):
        self.close_contract_state = True
        self.property_id.write({'stage': 'available'})
        self.contract_type = 'cancel_contract'
    def action_change_draft(self):
        self.contract_type = 'new_contract'

    def action_broker_invoice(self):
        record = {
            'product_id': self.env.ref('rental_management.property_product_1').id,
            'name': 'Brokerage of ' + self.property_id.name,
            'quantity': 1,
            'price_unit': self.commission
        }
        invoice_lines = [(0, 0, record)]
        data = {
            'partner_id': self.broker_id.id,
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        invoice_id.tenancy_id = self.id
        invoice_id.action_post()
        self.broker_invoice_state = True
        self.broker_invoice_id = invoice_id.id
        return True

    @api.model
    def tenancy_recurring_invoice(self):
        today_date = fields.Date.today()
        reminder_days = self.env['ir.config_parameter'].sudo().get_param('rental_management.reminder_days')
        tenancy_contracts = self.env['tenancy.details'].sudo().search(
            [('contract_type', '=', 'running_contract'), ('payment_term', '=', 'monthly')])
        for rec in tenancy_contracts:
            if rec.contract_type == 'running_contract' and rec.payment_term == 'monthly':
                if today_date < rec.end_date:
                    invoice_date = rec.last_invoice_payment_date + relativedelta(months=1)
                    next_invoice_date = rec.last_invoice_payment_date + relativedelta(months=1) - relativedelta(
                        days=int(reminder_days))
                    if today_date == next_invoice_date:
                        record = {
                            'product_id': self.env.ref('rental_management.property_product_1').id,
                            'name': 'Installment of ' + rec.property_id.name,
                            'quantity': 1,
                            'price_unit': rec.total_rent
                        }
                        invoice_lines = [(0, 0, record)]
                        if rec.is_extra_service:
                            for line in rec.extra_services_ids:
                                if line.service_type == "monthly":
                                    desc = "Monthly"
                                    service_invoice_record = {
                                        'product_id': line.service_id.id,
                                        'name': desc,
                                        'quantity': 1,
                                        'price_unit': line.price
                                    }
                                    invoice_lines.append((0, 0, service_invoice_record))
                        data = {
                            'partner_id': rec.tenancy_id.id,
                            'move_type': 'out_invoice',
                            'invoice_date': invoice_date,
                            'invoice_line_ids': invoice_lines
                        }
                        invoice_id = self.env['account.move'].sudo().create(data)
                        invoice_id.tenancy_id = rec.id
                        invoice_id.action_post()
                        rec.last_invoice_payment_date = invoice_id.invoice_date
                        rent_invoice = {
                            'tenancy_id': rec.id,
                            'type': 'rent',
                            'invoice_date': invoice_date,
                            'description': 'Installment of ' + rec.property_id.name,
                            'rent_invoice_id': invoice_id.id,
                            'amount': invoice_id.amount_total,
                            'rent_amount': self.total_rent
                        }
                        self.env['rent.invoice'].create(rent_invoice)
                        rec.action_send_tenancy_reminder()

            #         else:
            #             print('Not 30 Days')
            #     else:
            #         print('Contract is Over')
            # else:
            #     print('Not running or Monthly contract')
        return True

    @api.model
    def tenancy_expire(self):
        today_date = fields.Date.today()
        tenancy_contracts = self.env['tenancy.details'].sudo().search(
            [('contract_type', '=', 'running_contract'), '|', ('payment_term', '=', 'monthly'),
             ('payment_term', '=', 'quarterly')])
        for rec in tenancy_contracts:
            if rec.contract_type == 'running_contract':
                if today_date > rec.end_date:
                    rec.contract_type = 'expire_contract'
            elif today_date > rec.end_date:
                rec.contract_type = 'expire_contract'

            #     else:
            #         print('Not expire')
            # else:
            #     print('Not in Running')
        return True

    def action_send_active_contract(self):
        mail_template = self.env.ref('rental_management.active_contract_mail_template')
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)

    def action_send_tenancy_reminder(self):
        mail_template = self.env.ref('rental_management.tenancy_reminder_mail_template')
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)

    @api.model
    def tenancy_recurring_quarterly_invoice(self):
        today_date = fields.Date.today()
        # today_date = datetime.date(2023, 6, 28)
        reminder_days = self.env['ir.config_parameter'].sudo().get_param('rental_management.reminder_days')
        tenancy_contracts = self.env['tenancy.details'].sudo().search(
            [('contract_type', '=', 'running_contract'), ('payment_term', '=', 'quarterly')])
        for rec in tenancy_contracts:
            if rec.contract_type == 'running_contract' and rec.payment_term == 'quarterly':
                if today_date < rec.end_date:
                    invoice_date = rec.last_invoice_payment_date + relativedelta(months=3)
                    next_next_invoice_date = invoice_date + relativedelta(months=3)
                    next_invoice_date = rec.last_invoice_payment_date + relativedelta(months=3) - relativedelta(
                        days=int(reminder_days))
                    if rec.end_date < next_next_invoice_date:
                        delta = relativedelta(next_next_invoice_date, rec.end_date)
                        diff = delta.months
                    else:
                        diff = 0
                    if today_date == next_invoice_date:
                        record = {
                            'product_id': self.env.ref('rental_management.property_product_1').id,
                            'name': 'Quarterly Installment of ' + rec.property_id.name,
                            'quantity': 1,
                            'price_unit': rec.total_rent * (3 - diff)
                        }
                        invoice_lines = [(0, 0, record)]
                        if rec.is_extra_service:
                            for line in rec.extra_services_ids:
                                if line.service_type == "monthly":
                                    desc = "Quarterly Service"
                                    service_invoice_record = {
                                        'product_id': line.service_id.id,
                                        'name': desc,
                                        'quantity': 1,
                                        'price_unit': line.price * (3 - diff)
                                    }
                                    invoice_lines.append((0, 0, service_invoice_record))
                        data = {
                            'partner_id': rec.tenancy_id.id,
                            'move_type': 'out_invoice',
                            'invoice_date': invoice_date,
                            'invoice_line_ids': invoice_lines
                        }
                        invoice_id = self.env['account.move'].sudo().create(data)
                        invoice_id.tenancy_id = rec.id
                        invoice_id.action_post()
                        rec.last_invoice_payment_date = invoice_id.invoice_date
                        rent_invoice = {
                            'tenancy_id': rec.id,
                            'type': 'rent',
                            'invoice_date': invoice_date,
                            'description': 'Quarterly Installment of ' + rec.property_id.name,
                            'rent_invoice_id': invoice_id.id,
                            'amount': invoice_id.amount_total,
                            'rent_amount': self.total_rent * (3 - diff)
                        }
                        self.env['rent.invoice'].create(rent_invoice)
                        rec.action_send_tenancy_reminder()


class ContractDuration(models.Model):
    _name = 'contract.duration'
    _description = 'Contract Duration and Month'
    _rec_name = 'duration'

    # duration = fields.Char(string='Duration', required=True)
    # month = fields.Integer(string='Month')
    duration = fields.Char(string='Duration', required=True,
                           help="Duration description (e.g., 'Three Months, Four Days')")
    month = fields.Integer(string='Months', default=0, help="Number of months in the duration")
    day = fields.Integer(string='Days', default=0, help="Number of days in the duration")

    @api.constrains('month', 'day')
    def _check_valid_duration(self):
        """Ensure months and days are valid."""
        for rec in self:
            if rec.month < 0 or rec.day < 0:
                raise ValidationError("Month and Day must be non-negative values.")


class TenancyExtraServiceLine(models.Model):
    _name = "tenancy.service.line"
    _description = "Tenancy Service Line"

    service_id = fields.Many2one('product.product', string="Service", domain=[('is_extra_service_product', '=', True)])
    price = fields.Float(related="service_id.lst_price", string="Cost")
    service_type = fields.Selection([('once', 'Once'), ('monthly', 'Monthly')], string="Type", default="once")
    tenancy_id = fields.Many2one('tenancy.details', string="Tenancies")
    from_contract = fields.Boolean()

    def action_create_service_invoice(self):
        self.from_contract = True
        record = {
            'product_id': self.service_id.id,
            'name': "Extra Added Service",
            'quantity': 1,
            'price_unit': self.service_id.lst_price
        }
        invoice_lines = [(0, 0, record)]
        data = {
            'partner_id': self.tenancy_id.tenancy_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        invoice_id.tenancy_id = self.tenancy_id.id
        invoice_id.action_post()
        rent_invoice = {
            'tenancy_id': self.tenancy_id.id,
            'type': 'maintenance',
            'amount': self.service_id.lst_price,
            'invoice_date': fields.Date.today(),
            'description': 'New Service',
            'rent_invoice_id': invoice_id.id
        }
        self.env['rent.invoice'].create(rent_invoice)
