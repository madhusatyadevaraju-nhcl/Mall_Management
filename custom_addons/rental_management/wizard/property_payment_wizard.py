# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PropertyPayment(models.TransientModel):
    _name = 'property.payment.wizard'
    _description = 'Create Invoice For Rent'

    tenancy_id = fields.Many2one('tenancy.details', string='Tenancy No.')
    customer_id = fields.Many2one(related='tenancy_id.tenancy_id', string='Customer')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    type = fields.Selection([
        ('deposit', 'Deposit'), ('rent', 'Rent'),
        ('maintenance', 'Maintenance'),
        ('penalty', 'Penalty')],
        string='Payment', default='rent')
    description = fields.Char(string='Description')
    invoice_date = fields.Date(string='Date')
    rent_amount = fields.Monetary(string='Rent Amount', related='tenancy_id.total_rent')
    amount = fields.Monetary(string='Amount')
    rent_invoice_id = fields.Many2one('account.move', string='Invoice')

    def property_payment_action(self):
        if self.type == 'rent':
            amount = self.rent_amount
        else:
            amount = self.amount
        record = {
            'product_id': self.env.ref('rental_management.property_product_1').id,
            'name': self.description,
            'quantity': 1,
            'price_unit': amount
        }
        invoice_lines = [(0, 0, record)]
        data = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': self.invoice_date,
            'invoice_line_ids': invoice_lines
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        invoice_id.tenancy_id = self.tenancy_id.id
        invoice_id.action_post()
        self.rent_invoice_id = invoice_id.id

        rent_invoice = {
            'tenancy_id': self.tenancy_id.id,
            'type': self.type,
            'invoice_date': self.invoice_date,
            'rent_amount': self.rent_amount,
            'amount': self.amount,
            'description': self.description,
            'rent_invoice_id': self.rent_invoice_id.id
        }
        self.env['rent.invoice'].create(rent_invoice)

        return True
