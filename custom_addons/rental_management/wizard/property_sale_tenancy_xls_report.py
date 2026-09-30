# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
import xlwt
import base64
from io import BytesIO


class PropertyXlsReport(models.TransientModel):
    _name = 'property.report.wizard'
    _description = 'Create Property Report'
    _rec_name = 'type'

    type = fields.Selection([('tenancy', 'Tenancy'), ('sold', 'Property Sold')], string="Report For")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")

    def action_property_xls_report(self):
        if self.type == "tenancy":
            workbook = xlwt.Workbook(encoding='utf-8')
            sheet1 = workbook.add_sheet('Tenancy Details', cell_overwrite_ok=True)
            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'mm/dd/yyyy'
            sheet1.col(0).width = 7000
            sheet1.write(0, 0, 'Tenancy No.')
            sheet1.write(0, 1, 'Tenant')
            sheet1.write(0, 2, 'Property')
            sheet1.write(0, 3, 'Landlord')
            sheet1.write(0, 4, 'Total Invoiced')
            c = 1

            for group in self.env['account.move'].read_group(
                    [('tenancy_id', '!=', False), ('payment_state', '=', 'paid'),
                     ('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date)],
                    ['tenancy_id', 'amount_total'],
                    ['tenancy_id'], orderby="amount_total DESC"):
                if group['tenancy_id']:
                    active_id = self.env['tenancy.details'].sudo().browse(int(group['tenancy_id'][0]))
                    sheet1.col(c).width = 7000
                    sheet1.write(c, 0, active_id.tenancy_seq)
                    sheet1.write(c, 1, active_id.tenancy_id.name)
                    sheet1.write(c, 2, active_id.property_id.name)
                    sheet1.write(c, 3, active_id.property_landlord_id.name)
                    sheet1.write(c, 4, group['amount_total'])
                    c += 1

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env['ir.attachment'].sudo()
            filename = 'Tenancy Details' + ".xlsx"
            attachment_id = attachment.create(
                {'name': filename,
                 'type': 'binary',
                 'public': False,
                 'datas': out})
            if attachment_id:
                report = {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/%s?download=true' % (attachment_id.id),
                    'target': 'self',
                    'nodestroy': False,
                }
                return report

        elif self.type == "sold":
            workbook = xlwt.Workbook(encoding='utf-8')
            sheet1 = workbook.add_sheet('Property Sold Information', cell_overwrite_ok=True)
            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'mm/dd/yyyy'
            sheet1.col(0).width = 7000
            sheet1.write(0, 0, 'Sequence')
            sheet1.write(0, 1, 'Customer')
            sheet1.write(0, 2, 'Property')
            sheet1.write(0, 3, 'Landlord')
            sheet1.write(0, 4, 'Total Invoiced')
            c = 1

            for group in self.env['account.move'].read_group(
                    [('sold_id', '!=', False), ('payment_state', '=', 'paid'),
                     ('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date)],
                    ['sold_id', 'amount_total'],
                    ['sold_id'], orderby="amount_total DESC"):
                if group['sold_id']:
                    active_id = self.env['property.vendor'].sudo().browse(int(group['sold_id'][0]))
                    sheet1.col(c).width = 7000
                    sheet1.write(c, 0, active_id.sold_seq)
                    sheet1.write(c, 1, active_id.customer_id.name)
                    sheet1.write(c, 2, active_id.property_id.name)
                    sheet1.write(c, 3, active_id.property_id.landlord_id.name)
                    sheet1.write(c, 4, group['amount_total'])
                    c += 1

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env['ir.attachment'].sudo()
            filename = 'Sold Information' + ".xlsx"
            attachment_id = attachment.create(
                {'name': filename,
                 'type': 'binary',
                 'public': False,
                 'datas': out})
            if attachment_id:
                report = {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/%s?download=true' % (attachment_id.id),
                    'target': 'self',
                    'nodestroy': False,
                }
                return report
