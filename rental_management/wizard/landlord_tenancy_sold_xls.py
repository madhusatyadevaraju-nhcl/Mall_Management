from odoo import fields, api, models
import xlwt
import base64
from io import BytesIO


class LandlordSaleTenancy(models.TransientModel):
    _name = 'landlord.sale.tenancy'
    _description = "Landlord Tenancy And sale Report"
    _rec_name = "landlord_id"

    landlord_id = fields.Many2one('res.partner', domain="[('user_type','=','landlord')]")
    report_for = fields.Selection([('tenancy', 'Tenancy'), ('sold', 'Property Sold')], string="Report For")

    def action_tenancy_sold_xls_report(self):
        if self.report_for == "tenancy":
            name = "Tenancy Information - " + self.landlord_id.name
            sheet2_name = "Tenancy Information - " + self.landlord_id.name + " : PAID"
            sheet3_name = "Tenancy Information - " + self.landlord_id.name + " : NOT PAID"
            sheet4_name = "Tenancy Information - " + self.landlord_id.name + " : PARTIAL PAID"
            workbook = xlwt.Workbook(encoding='utf-8')

            # Font Color
            red = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index red")
            green = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index green")
            magenta_ega = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index magenta_ega")
            gold = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index gold")
            violet = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index violet")
            blue_gray = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index blue_gray")
            # Style
            sheet_style = xlwt.easyxf("align: vert centre, horiz centre")
            sheet_style_amount = xlwt.easyxf("align: vert centre, horiz right")
            heading = xlwt.easyxf("align: vert centre, horiz centre;font: bold on,height 200")
            main_heading = xlwt.easyxf("align: vert centre, horiz centre;font: bold on,height 320")

            # Sheet
            xlwt.add_palette_colour("warning", 0x21)
            workbook.set_colour_RGB(0x21, 75, 211, 152)
            sheet1 = workbook.add_sheet('Landlord wise Tenancies', cell_overwrite_ok=True)
            sheet2 = workbook.add_sheet('Paid Tenancies', cell_overwrite_ok=True)
            sheet3 = workbook.add_sheet('Not Paid Tenancy', cell_overwrite_ok=True)
            sheet4 = workbook.add_sheet('Partial Paid Tenancies', cell_overwrite_ok=True)
            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'mm/dd/yyyy'

            # SHEET1
            sheet1.write_merge(0, 1, 0, 8, name, main_heading)
            sheet1.col(0).width = 2800
            sheet1.col(1).width = 3500
            sheet1.col(2).width = 7000
            sheet1.col(3).width = 7000
            sheet1.col(4).width = 6000
            sheet1.col(5).width = 5500
            sheet1.col(6).width = 3000
            sheet1.col(7).width = 5500
            sheet1.col(8).width = 5500
            sheet1.row(2).height = 500
            sheet1.write(2, 0, 'Date', heading)
            sheet1.write(2, 1, 'Tenancy No.', heading)
            sheet1.write(2, 2, 'Tenant', heading)
            sheet1.write(2, 3, 'Property', heading)
            sheet1.write(2, 4, 'Invoice Ref.', heading)
            sheet1.write(2, 5, 'Payment Term', heading)
            sheet1.write(2, 6, 'Amount', heading)
            sheet1.write(2, 7, 'Payment Status', heading)
            sheet1.write(2, 8, 'Tenancy Status', heading)
            c = 3
            rent_invoice = self.env['rent.invoice'].search([('landlord_id', '=', self.landlord_id.id)])
            for data in rent_invoice:
                amount = str(data.rent_invoice_id.amount_total) + " " + str(data.currency_id.symbol)
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold

                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"
                if data.tenancy_id.payment_term == "monthly":
                    payment_term = "Monthly"
                elif data.tenancy_id.payment_term == "full_payment":
                    payment_term = "Full Payment"
                else:
                    payment_term = "Quarterly"
                sheet1.write(c, 0, data.invoice_date, date_format)
                sheet1.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet1.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet1.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet1.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet1.write(c, 5, payment_term, sheet_style)
                sheet1.write(c, 6, amount, sheet_style_amount)
                sheet1.write(c, 7, status, style0)
                sheet1.write(c, 8, stage, sheet_style)
                c += 1

            # Sheet 2
            sheet2.write_merge(0, 1, 0, 7, sheet2_name, main_heading)
            sheet2.col(0).width = 2800
            sheet2.col(1).width = 3500
            sheet2.col(2).width = 7000
            sheet2.col(3).width = 7000
            sheet2.col(4).width = 6000
            sheet2.col(5).width = 3000
            sheet2.col(6).width = 5500
            sheet2.col(7).width = 5500
            sheet2.row(2).height = 500
            sheet2.write(2, 0, 'Date', heading)
            sheet2.write(2, 1, 'Tenancy No.', heading)
            sheet2.write(2, 2, 'Tenant', heading)
            sheet2.write(2, 3, 'Property', heading)
            sheet2.write(2, 4, 'Invoice Ref.', heading)
            sheet2.write(2, 5, 'Amount', heading)
            sheet2.write(2, 6, 'Payment Status', heading)
            sheet2.write(2, 7, 'Tenancy Status', heading)
            c = 3
            rent_invoice = self.env['rent.invoice'].search(
                [('landlord_id', '=', self.landlord_id.id), ('payment_state', '=', 'paid')])
            for data in rent_invoice:
                amount = str(data.rent_invoice_id.amount_total) + " " + str(data.currency_id.symbol)
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold
                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"

                sheet2.write(c, 0, data.invoice_date, date_format)
                sheet2.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet2.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet2.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet2.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet2.write(c, 5, amount, sheet_style_amount)
                sheet2.write(c, 6, status, style0)
                sheet2.write(c, 7, stage, sheet_style)
                c += 1

            # Sheet 3
            sheet3.write_merge(0, 1, 0, 7, sheet3_name, main_heading)
            sheet3.col(0).width = 2800
            sheet3.col(1).width = 3500
            sheet3.col(2).width = 7000
            sheet3.col(3).width = 7000
            sheet3.col(4).width = 6000
            sheet3.col(5).width = 3000
            sheet3.col(6).width = 5500
            sheet3.col(7).width = 5500
            sheet3.row(2).height = 500
            sheet3.write(2, 0, 'Date', heading)
            sheet3.write(2, 1, 'Tenancy No.', heading)
            sheet3.write(2, 2, 'Tenant', heading)
            sheet3.write(2, 3, 'Property', heading)
            sheet3.write(2, 4, 'Invoice Ref.', heading)
            sheet3.write(2, 5, 'Amount', heading)
            sheet3.write(2, 6, 'Payment Status', heading)
            sheet3.write(2, 7, 'Tenancy Status', heading)
            c = 3
            rent_invoice = self.env['rent.invoice'].search(
                [('landlord_id', '=', self.landlord_id.id), ('payment_state', '=', 'not_paid')])
            for data in rent_invoice:
                amount = str(data.rent_invoice_id.amount_total) + " " + str(data.currency_id.symbol)
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold
                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"

                sheet3.write(c, 0, data.invoice_date, date_format)
                sheet3.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet3.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet3.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet3.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet3.write(c, 5, amount, sheet_style_amount)
                sheet3.write(c, 6, status, style0)
                sheet3.write(c, 7, stage, sheet_style)
                c += 1

            # Sheet 4
            sheet4.write_merge(0, 1, 0, 7, sheet4_name, main_heading)
            sheet4.col(0).width = 2800
            sheet4.col(1).width = 3500
            sheet4.col(2).width = 7000
            sheet4.col(3).width = 7000
            sheet4.col(4).width = 6000
            sheet4.col(5).width = 3000
            sheet4.col(6).width = 5500
            sheet4.col(7).width = 5500
            sheet4.row(2).height = 500
            sheet4.write(2, 0, 'Date', heading)
            sheet4.write(2, 1, 'Tenancy No.', heading)
            sheet4.write(2, 2, 'Tenant', heading)
            sheet4.write(2, 3, 'Property', heading)
            sheet4.write(2, 4, 'Invoice Ref.', heading)
            sheet4.write(2, 5, 'Amount', heading)
            sheet4.write(2, 6, 'Payment Status', heading)
            sheet4.write(2, 7, 'Tenancy Status', heading)
            c = 3
            rent_invoice = self.env['rent.invoice'].search(
                [('landlord_id', '=', self.landlord_id.id), ('payment_state', '=', 'partial')])
            for data in rent_invoice:
                amount = str(data.rent_invoice_id.amount_total) + " " + str(data.currency_id.symbol)
                status = ""
                stage = ""
                if data.payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold
                if data.tenancy_id.contract_type == "new_contract":
                    stage = "Draft"
                elif data.tenancy_id.contract_type == "running_contract":
                    stage = "Running"
                elif data.tenancy_id.contract_type == "cancel_contract":
                    stage = "Cancel"
                elif data.tenancy_id.contract_type == "close_contract":
                    stage = "Close"
                else:
                    stage = "Expire"

                sheet4.write(c, 0, data.invoice_date, date_format)
                sheet4.write(c, 1, data.tenancy_id.tenancy_seq, sheet_style)
                sheet4.write(c, 2, data.tenancy_id.tenancy_id.name, sheet_style)
                sheet4.write(c, 3, data.tenancy_id.property_id.name, sheet_style)
                sheet4.write(c, 4, data.rent_invoice_id.name, sheet_style)
                sheet4.write(c, 5, amount, sheet_style_amount)
                sheet4.write(c, 6, status, style0)
                sheet4.write(c, 7, stage, sheet_style)
                c += 1

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env['ir.attachment'].sudo()
            filename = self.landlord_id.name + ".xlsx"
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
        elif self.report_for == "sold":
            name = "Sold Information - " + self.landlord_id.name
            workbook = xlwt.Workbook(encoding='utf-8')
            # Font Color
            red = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index red")
            green = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index green")
            magenta_ega = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index magenta_ega")
            gold = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index gold")
            violet = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index violet")
            blue_gray = xlwt.easyxf("align: vert centre, horiz centre;font: bold on, color-index blue_gray")
            sheet_style = xlwt.easyxf("align: vert centre, horiz centre")
            heading = xlwt.easyxf("align: vert centre, horiz centre;font: bold on,height 200")
            main_heading = xlwt.easyxf("align: vert centre, horiz centre;font: bold on,height 320")
            sheet_style_amount = xlwt.easyxf("align: vert centre, horiz right")
            sheet1 = workbook.add_sheet('Landlord wise Sold Information', cell_overwrite_ok=True)
            date_format = xlwt.XFStyle()
            date_format.num_format_str = 'mm/dd/yyyy'
            sheet1.write_merge(0, 1, 0, 7, name, main_heading)
            sheet1.col(0).width = 2800
            sheet1.col(1).width = 3000
            sheet1.col(2).width = 7000
            sheet1.col(3).width = 7000
            sheet1.col(4).width = 3000
            sheet1.col(5).width = 5500
            sheet1.col(6).width = 5500
            sheet1.col(7).width = 3000
            sheet1.row(2).height = 500
            sheet1.write(2, 0, 'Date', heading)
            sheet1.write(2, 1, 'Sequence', heading)
            sheet1.write(2, 2, 'Customer', heading)
            sheet1.write(2, 3, 'Property', heading)
            sheet1.write(2, 4, 'Sale Price', heading)
            sheet1.write(2, 5, 'Invoice Reference', heading)
            sheet1.write(2, 6, 'Payment Status', heading)
            sheet1.write(2, 7, 'Sold Status', heading)
            c = 3
            property_sold = self.env['property.vendor'].search([('landlord_id', '=', self.landlord_id.id)])
            for data in property_sold:
                status = ""
                stage = ""
                amount = str(data.sale_price) + " " + str(data.currency_id.symbol)
                if data.sold_invoice_payment_state == "paid":
                    status = "Paid"
                    style0 = green
                elif data.sold_invoice_payment_state == "not_paid":
                    status = "Not Paid"
                    style0 = red
                elif data.sold_invoice_payment_state == "reversed":
                    status = "Reversed"
                    style0 = magenta_ega
                elif data.sold_invoice_payment_state == "partial":
                    status = "Partial Paid"
                    style0 = blue_gray
                elif data.sold_invoice_payment_state == "in_payment":
                    status = "In Payment"
                    style0 = violet
                else:
                    status = "Invoicing App Legacy"
                    style0 = gold

                if data.stage == "booked":
                    stage = "Booked"
                elif data.stage == "refund":
                    stage = "Refund"
                else:
                    stage = "Sold"

                sheet1.col(c).width = 7000
                sheet1.write(c, 0, data.date, date_format)
                sheet1.write(c, 1, data.sold_seq, sheet_style)
                sheet1.write(c, 2, data.customer_id.name, sheet_style)
                sheet1.write(c, 3, data.property_id.name, sheet_style)
                sheet1.write(c, 4, amount, sheet_style_amount)
                sheet1.write(c, 5, data.sold_invoice_id.name, sheet_style)
                sheet1.write(c, 6, status, style0)
                sheet1.write(c, 7, stage, sheet_style)
                c += 1

            stream = BytesIO()
            workbook.save(stream)
            out = base64.encodebytes(stream.getvalue())

            attachment = self.env['ir.attachment'].sudo()
            filename = self.landlord_id.name + ".xlsx"
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
