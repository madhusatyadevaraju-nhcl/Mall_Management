from datetime import datetime

from odoo.addons.test_convert.tests.test_env import record
from odoo import api, fields, models


class RentInvoice(models.Model):
    _inherit = 'rent.invoice'

    rent_depo_date = fields.Date(string='Caution Deposit Money Handover Date')


class DateRangeWizardRent(models.TransientModel):
    _name = 'date.range.wizard'
    _description = 'Date Range Wizard'

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer")

    def action_print_report_rent(self):
        #     """Fetch records from rent.invoice and pass to the report"""
        domain = [
            ('invoice_date', '>=', self.from_date),
            ('invoice_date', '<=', self.to_date),
            ('state', '=', 'posted'),
            ('nhcl_invoice_type', '=', 'rent'),
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        invoices = self.env['account.move'].search(domain, order='name ASC')
        res = []
        for data in invoices:
            type_data = data.nhcl_invoice_type
            if data.invoice_line_ids:
                tax = ", ".join(tax.name for tax in data.invoice_line_ids[0].tax_ids)
            else:
                tax = ''

            if data.invoice_line_ids:
                tax_amount = round(data.invoice_line_ids[0].price_total - data.invoice_line_ids[0].price_subtotal, 4)
            else:
                tax_amount = 0.0
            if data.invoice_line_ids:
                total_tax_amount = data.amount_total
            else:
                total_tax_amount = 0.0
            status = dict(data.tenancy_id._fields['contract_type'].selection).get(data.tenancy_id.contract_type, " ")

            if data.nhcl_invoice_type == 'rent':
                res += [{data.id: 'id', 'invoice': data.name, 'brand': data.partner_id.name,
                         'Brand': data.tenancy_id.brand_name, 'amount': data.invoice_line_ids[0].price_unit, 'tax': tax,
                         'tax_amount': data.amount_tax, 'total_tax_amount': total_tax_amount, 'status': status}]
        from_date = self.from_date
        to_date = self.to_date
        month_name = datetime.strptime(str(from_date), "%Y-%m-%d").strftime("%B")
        month_name_to = datetime.strptime(str(to_date), "%Y-%m-%d").strftime("%B")

        return self.env.ref('nhcl_rental_management.action_report_rent_invoice').report_action(self,
                                                                                               {"from_date": from_date,
                                                                                                'to_date': to_date,
                                                                                                'res': res,
                                                                                                'month_name': month_name,
                                                                                                'month_name_to': month_name_to})


class DateRangeWizardCam(models.TransientModel):
    _name = 'cam.date.range.wizard'
    _description = 'CAM Date Range Wizard'

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer")

    def action_print_report_cam(self):
        """Fetch records from rent.invoice and pass to the report"""

        domain = [
            ('invoice_date', '>=', self.from_date),
            ('invoice_date', '<=', self.to_date),
             ('state', '=', 'posted'),
            ('nhcl_invoice_type', '=', 'cam'),
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        invoices = self.env['account.move'].search(domain, order='name ASC')
        res = []
        for data in invoices:

            tax = data.invoice_line_ids[0].product_id.taxes_id[0].name if data.invoice_line_ids and \
                                                                          data.invoice_line_ids[
                                                                              0].product_id.taxes_id else 0

            if data.invoice_line_ids:
                tax_amount = data.invoice_line_ids[0].price_total - data.invoice_line_ids[0].price_subtotal
                tax_amount = round(tax_amount, 2)
            else:
                tax_amount = 0.0
            # total_tax_amount = data.invoice_line_ids.price_total
            if data.invoice_line_ids:
                # total_tax_amount = data.invoice_line_ids[0].price_total - data.invoice_line_ids[0].price_subtotal
                total_tax_amount = data.amount_total
            else:
                total_tax_amount = 0.0
            status = dict(data.tenancy_id._fields['contract_type'].selection).get(data.tenancy_id.contract_type, " ")
            if data.nhcl_invoice_type == 'cam':
                res += [{data.id: 'id', 'invoice': data.name, 'brand': data.partner_id.name,
                         'Brand': data.tenancy_id.brand_name, 'amount': data.invoice_line_ids[0].price_unit, 'tax': tax,
                         'tax_amount': data.amount_tax, 'total_tax_amount': total_tax_amount, 'status': status}]
        from_date = self.from_date
        to_date = self.to_date
        month_name = datetime.strptime(str(from_date), "%Y-%m-%d").strftime("%B")
        month_name_to = datetime.strptime(str(to_date), "%Y-%m-%d").strftime("%B")
        return self.env.ref('nhcl_rental_management.action_report_cam_invoice').report_action(self,
                                                                                              {"from_date": from_date,
                                                                                               'to_date': to_date,
                                                                                               'res': res,
                                                                                               'month_name_to': month_name_to,
                                                                                               'month_name': month_name})


class UcGroup(models.TransientModel):
    _name = 'uc.group'
    _description = 'uc group electric'

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer")

    def uc_group_record(self):
        from_date = self.from_date
        to_date = self.to_date
        month_name = datetime.strptime(str(from_date), "%Y-%m-%d").strftime("%B")
        month_name_to = datetime.strptime(str(to_date), "%Y-%m-%d").strftime("%B")
        res = []
        if self.partner_id:
            tenants = self.env['tenancy.details'].search([('tenancy_id', '=', self.partner_id.id)])
        else:
            tenants = self.env['tenancy.details'].search([])
        partner_ids = tenants.mapped('tenancy_id').ids
        invoices = self.env['account.move'].search(
            [('partner_id', 'in', partner_ids), ('nhcl_invoice_type', '=', 'electric'),
             ('invoice_date', '>=', self.from_date),
             ('invoice_date', '<=', self.to_date)], order='name ASC')
        for invoice in invoices:
            if invoice.invoice_line_ids[0].product_id.taxes_id:
                tax = invoice.invoice_line_ids[0].product_id.taxes_id[0].name
            else:
                tax = ''
            tax_amount = round(invoice.invoice_line_ids[0].price_total - invoice.invoice_line_ids[
                0].price_subtotal, 2)
            # total_tax_amount = invoice.invoice_line_ids[0].price_total
            total_tax_amount = invoice.amount_total
            brand = self.env['tenancy.details'].search([('tenancy_id', '=', invoice.partner_id.id)], limit=1)
            res += [{'invoice_no': invoice.name, 'company': invoice.partner_id.name, 'brand': brand.brand_name,
                     'amount': invoice.amount_untaxed_signed, 'tax': tax, 'tax_amount': invoice.amount_tax,
                     'total_tax_amount': total_tax_amount}]
        return self.env.ref('nhcl_rental_management.action_report_uc_group').report_action(self,
                                                                                           {
                                                                                               "from_date": from_date,
                                                                                               'to_date': to_date,
                                                                                               'res': res,
                                                                                               'month_name_to': month_name_to,
                                                                                               'month_name': month_name})


class Gas(models.TransientModel):
    _name = 'gas.report.data'
    _description = 'Gas report Data'

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer")


    def gas_report_data(self):
        from_date = self.from_date
        to_date = self.to_date
        month_name = datetime.strptime(str(from_date), "%Y-%m-%d").strftime("%B")
        month_name_to = datetime.strptime(str(to_date), "%Y-%m-%d").strftime("%B")
        res = []
        if self.partner_id:
            tenants = self.env['tenancy.details'].search([('tenancy_id', '=', self.partner_id.id)])
        else:
            tenants = self.env['tenancy.details'].search([])
        partner_ids = tenants.mapped('tenancy_id').ids
        invoices = self.env['account.move'].search(
            [('partner_id', 'in', partner_ids), ('nhcl_invoice_type', '=', 'gas'),
             ('invoice_date', '>=', self.from_date),
             ('invoice_date', '<=', self.to_date)], order='name ASC')
        for invoice in invoices:
            if invoice.invoice_line_ids:
                tax = ", ".join(tax.name for tax in invoice.invoice_line_ids[0].tax_ids)
            else:
                tax = ''
            tax_amount = round(invoice.invoice_line_ids[0].price_total - invoice.invoice_line_ids[
                0].price_subtotal, 2)
            total_tax_amount = invoice.invoice_line_ids[0].price_total
            brand = self.env['tenancy.details'].search([('tenancy_id', '=', invoice.partner_id.id)], limit=1)
            res += [{'invoice_no': invoice.name, 'company': invoice.partner_id.name, 'brand': brand.brand_name,
                     'amount': invoice.invoice_line_ids[0].price_subtotal, 'tax': tax, 'tax_amount': invoice.amount_tax,
                     'total_tax_amount': total_tax_amount}]
        return self.env.ref('nhcl_rental_management.action_report_gas_group').report_action(self,
                                                                                            {
                                                                                                "from_date": from_date,
                                                                                                'to_date': to_date,
                                                                                                'res': res,
                                                                                                'month_name_to': month_name_to,
                                                                                                'month_name': month_name})