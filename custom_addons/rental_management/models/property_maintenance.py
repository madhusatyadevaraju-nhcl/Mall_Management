# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PropertyMaintenance(models.Model):
    _inherit = 'maintenance.request'

    property_id = fields.Many2one('property.details', string='Property')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    landlord_id = fields.Many2one('res.partner', string='Vendor Name',domain=[('user_type','=','vendor')],required=True)
    customer_new_id = fields.Many2one('res.partner', string='Customer Name',domain=[('user_type','=','customer')])
    maintenance_type_id = fields.Many2one('product.template', string='Type', domain=[('is_maintenance', '=', True)])
    price = fields.Float(related='maintenance_type_id.list_price', string='Price')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_state = fields.Boolean(string='State')


    # def action_crete_invoice(self):
    #     full_payment_record = {
    #         'product_id': self.maintenance_type_id.product_variant_id.id,
    #         'name': 'Maintenance',
    #         'quantity': 1,
    #         'price_unit': self.price
    #     }
    #     invoice_lines = [(0, 0, full_payment_record)]
    #     data = {
    #         'partner_id': self.landlord_id.id,
    #         'move_type': 'out_invoice',
    #         'invoice_date': fields.Date.today(),
    #         'invoice_line_ids': invoice_lines
    #     }
    #     invoice_id = self.env['account.move'].sudo().create(data)
    #     invoice_id.action_post()
    #     self.invoice_id = invoice_id.id
    #     self.invoice_state = True
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Invoice',
    #         'res_model': 'account.move',
    #         'res_id': invoice_id.id,
    #         'view_mode': 'form',
    #         'target': 'current'
    #     }

    def action_crete_invoice(self):
        full_payment_record = {
            'product_id': self.maintenance_type_id.product_variant_id.id,
            'name': 'Maintenance',
            'quantity': 1,
            'price_unit': self.price
        }
        invoice_lines = [(0, 0, full_payment_record)]
        data = {
            'partner_id': self.landlord_id.id,
            'move_type': 'in_invoice',#'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'nhcl_invoice_type': False
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        # ⚠️ Skip validation via context
        # invoice_id.with_context(skip_rent_validation=True).action_post()

        self.invoice_id = invoice_id.id
        self.invoice_state = True

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }


class MaintenanceProduct(models.Model):
    _inherit = 'product.template'

    is_maintenance = fields.Boolean(string='Maintenance')
