import calendar
import typing
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from email.policy import default
from odoo.exceptions import UserError, ValidationError
from odoo import fields, api, models, _
import base64
import math


class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(
        [('draft', 'Draft'), ('approve', 'Approve'), ('posted', 'Posted'), ('cancel', 'Cancelled')], default='draft')

    needs_approval = fields.Boolean(string="Needs Approval", default=False)
    nhcl_invoice_type = fields.Selection(
        [('rent', 'Rent'), ('cam', 'Cam'), ('regular', 'Regular'), ('advanced', 'Rent Security Deposit'),
         ('marketing', 'Marketing'),
         ('electric', 'Utility Charge'), ('gas', 'Gas'), ('signage', 'Signage'), ('mg', 'MG'), ('mg_or', 'MG or RS'),
         ('rs', 'RS'), ('adv_cam_fee', 'CAM Security Deposit'), ('slb', 'Slab Wise')], string="Invoice Type",
        copy=False,)
    invoice_month_range = fields.Char(string="Invoice Month Range", compute="_compute_invoice_month_range",
                                      store=True, )
    cam_fields = fields.Boolean(string="Check", compute='get_fields', default=False)
    amount_in_words = fields.Char(string='Amount in Words', compute='_compute_amount_in_words', store=True)
    amount_words_base = fields.Integer(
        string="Amount for Words",
        compute="_compute_amount_in_words",
        store=True
    )
    nhcl_total_amount = fields.Float('Total')
    for_ammount = fields.Integer(string='Amount change', compute='_get_amount', default=1)
    check_post = fields.Integer(string='Check post', default=0)
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
    date_year= fields.Date('Months & Year')
    date = fields.Date(string='Invoice Date', default=fields.Date.context_today)
    penality = fields.Float(string='Penality')
    comparision_yr_mnth = fields.Many2one('tenancy.relation.year', string='Comparison')
    billing_from = fields.Date(string='Billing Period From')#, default=lambda self: date.today().replace(day=1))
    billing_to = fields.Date(string='Billing Period To')#, default=lambda self: date.today().replace(day=1))
    billing_range_display = fields.Char(string='Billing Range', compute='_compute_billing_range')
    # marketing type invoice field
    po_number_category = fields.Char(string='Po Number')
    po_date = fields.Date(string='Po Date')
    site_location_num = fields.Char(string='Site Location Number')
    total_amount_show = fields.Float(string='Total Amount', compute='total_amount_count_discount')
    discount_amount_show = fields.Float(string='Discount Value', compute='total_amount_count_discount')
    rs_amount = fields.Float(string="RS Amount")
    mg_amount = fields.Float(string="MG Amount")
    slab_amount = fields.Float(string="Slab Amount")

    nhcl_invoice_type_label = fields.Char(
        string='Invoice Type Label',
        compute='_compute_invoice_type_label',
        store=False  # No need to store unless used in search/sort
    )

    def _compute_invoice_type_label(self):
        for rec in self:
            rec.nhcl_invoice_type_label = dict(self._fields['nhcl_invoice_type'].selection).get(rec.nhcl_invoice_type,
                                                                                                '')

    @api.depends('months')
    def _onchange_months(self):
        """When user selects a month, auto-set billing_from and billing_to"""
        if self.months: #and self.nhcl_invoice_type in ['rent', 'cam']:
            # Example: months = 'jan', 'feb', ...
            try:
                # Create a date for the 1st of that month in current year
                month_number = datetime.strptime(self.months.capitalize(), '%b').month
                year = date.today().year
                self.billing_from = date(year, month_number, 1)

                # Compute billing_to as last day of that month
                if month_number == 12:
                    self.billing_to = date(year, 12, 31)
                else:
                    next_month = date(year, month_number + 1, 1)
                    self.billing_to = next_month - timedelta(days=1)

            except Exception as e:
                # Optional: log or handle invalid month names
                _logger.warning(f"Invalid month name {self.months}: {e}")

    # def _custom_round(self, amount):
    #     """
    #     Custom rounding rule:
    #
    #     Decimal part < 0.51  -> Round DOWN
    #     Decimal part >= 0.51 -> Round UP
    #
    #     Examples:
    #         4814.40 -> 4814
    #         4814.50 -> 4814
    #         4814.51 -> 4815
    #         4814.59 -> 4815
    #         4814.99 -> 4815
    #
    #         866.40 -> 866
    #         866.50 -> 866
    #         866.51 -> 867
    #         866.59 -> 867
    #     """
    #
    #     if amount is None:
    #         return 0.0
    #
    #     decimal_part = amount - math.floor(amount)
    #
    #     if decimal_part >= 0.51:
    #         return math.ceil(amount)
    #
    #     return math.floor(amount)
    #
    #     # ============================================================
    #     # CUSTOM TAX TOTALS
    #     # ============================================================
    #
    # @api.depends(
    #     'invoice_line_ids',
    #     'invoice_line_ids.tax_ids',
    #     'invoice_line_ids.price_subtotal',
    #     'invoice_line_ids.price_total',
    # )
    # def _compute_tax_totals(self):
    #
    #     for move in self:
    #
    #         # ----------------------------------------------------
    #         # If not an invoice
    #         # ----------------------------------------------------
    #
    #         if not move.is_invoice(include_receipts=True):
    #             move.tax_totals = None
    #             continue
    #
    #         # ----------------------------------------------------
    #         # Get Odoo's original tax calculation
    #         # ----------------------------------------------------
    #
    #         base_lines, _tax_lines = (
    #             move._get_rounded_base_and_tax_lines()
    #         )
    #
    #         tax_totals = self.env['account.tax']._get_tax_totals_summary(
    #             base_lines=base_lines,
    #             currency=move.currency_id,
    #             company=move.company_id,
    #             cash_rounding=move.invoice_cash_rounding_id,
    #         )
    #
    #         # ====================================================
    #         # 1. ROUND UNTAXED / BASE AMOUNT
    #         # ====================================================
    #
    #         original_base_currency = tax_totals.get(
    #             'base_amount_currency',
    #             0.0
    #         )
    #
    #         rounded_base_currency = self._custom_round(
    #             original_base_currency
    #         )
    #
    #         tax_totals['base_amount_currency'] = (
    #             rounded_base_currency
    #         )
    #
    #         # ----------------------------------------------------
    #         # Company currency base amount
    #         # ----------------------------------------------------
    #
    #         original_base_company = tax_totals.get(
    #             'base_amount',
    #             0.0
    #         )
    #
    #         rounded_base_company = self._custom_round(
    #             original_base_company
    #         )
    #
    #         tax_totals['base_amount'] = (
    #             rounded_base_company
    #         )
    #
    #         # ====================================================
    #         # 2. ROUND GST / TAX
    #         # ====================================================
    #
    #         total_tax_currency = 0.0
    #         total_tax_company = 0.0
    #
    #         for subtotal in tax_totals.get('subtotals', []):
    #
    #             subtotal_tax_currency = 0.0
    #             subtotal_tax_company = 0.0
    #
    #             for group in subtotal.get('tax_groups', []):
    #                 # ------------------------------------------------
    #                 # Currency GST
    #                 # ------------------------------------------------
    #
    #                 original_tax_currency = group.get(
    #                     'tax_amount_currency',
    #                     0.0
    #                 )
    #
    #                 rounded_tax_currency = self._custom_round(
    #                     original_tax_currency
    #                 )
    #
    #                 group['tax_amount_currency'] = (
    #                     rounded_tax_currency
    #                 )
    #
    #                 # ------------------------------------------------
    #                 # Company currency GST
    #                 # ------------------------------------------------
    #
    #                 original_tax_company = group.get(
    #                     'tax_amount',
    #                     0.0
    #                 )
    #
    #                 rounded_tax_company = self._custom_round(
    #                     original_tax_company
    #                 )
    #
    #                 group['tax_amount'] = (
    #                     rounded_tax_company
    #                 )
    #
    #                 # ------------------------------------------------
    #                 # Add rounded GST
    #                 # ------------------------------------------------
    #
    #                 subtotal_tax_currency += (
    #                     rounded_tax_currency
    #                 )
    #
    #                 subtotal_tax_company += (
    #                     rounded_tax_company
    #                 )
    #
    #             # ----------------------------------------------------
    #             # Set subtotal GST
    #             # ----------------------------------------------------
    #
    #             subtotal['tax_amount_currency'] = (
    #                 subtotal_tax_currency
    #             )
    #
    #             subtotal['tax_amount'] = (
    #                 subtotal_tax_company
    #             )
    #
    #             # ----------------------------------------------------
    #             # Add to total GST
    #             # ----------------------------------------------------
    #
    #             total_tax_currency += (
    #                 subtotal_tax_currency
    #             )
    #
    #             total_tax_company += (
    #                 subtotal_tax_company
    #             )
    #
    #         # ====================================================
    #         # 3. SET TOTAL TAX
    #         # ====================================================
    #
    #         tax_totals['tax_amount_currency'] = (
    #             total_tax_currency
    #         )
    #
    #         tax_totals['tax_amount'] = (
    #             total_tax_company
    #         )
    #
    #         # ====================================================
    #         # 4. CALCULATE FINAL TOTAL
    #         # ====================================================
    #         #
    #         # Total = Rounded Untaxed + Rounded GST
    #         #
    #         # Example:
    #         #
    #         # Untaxed = 4814.41 -> 4814
    #         # GST     =  866.59 ->  867
    #         #
    #         # Total = 4814 + 867
    #         #       = 5681
    #         #
    #         # ====================================================
    #
    #         tax_totals['total_amount_currency'] = (
    #                 rounded_base_currency
    #                 + total_tax_currency
    #         )
    #
    #         tax_totals['total_amount'] = (
    #                 rounded_base_company
    #                 + total_tax_company
    #         )
    #
    #         # ====================================================
    #         # 5. ASSIGN TAX TOTALS
    #         # ====================================================
    #
    #         move.tax_totals = tax_totals
    #
    #         # ====================================================
    #         # 6. COMPANY CURRENCY DISPLAY
    #         # ====================================================
    #
    #         move.tax_totals['display_in_company_currency'] = (
    #                 move.company_id.display_invoice_tax_company_currency
    #                 and move.company_currency_id != move.currency_id
    #                 and move.tax_totals['has_tax_groups']
    #                 and move.is_sale_document(
    #             include_receipts=True
    #         )
    #         )
    #
    #         # ====================================================
    #         # DEBUG
    #         # ====================================================
    #
    #         print("\n")
    #         print("==========================================")
    #         print("         CUSTOM TAX ROUNDING")
    #         print("==========================================")
    #         print(
    #             "Original Untaxed :",
    #             original_base_currency
    #         )
    #         print(
    #             "Rounded Untaxed  :",
    #             rounded_base_currency
    #         )
    #         print(
    #             "Rounded GST      :",
    #             total_tax_currency
    #         )
    #         print(
    #             "Final Total      :",
    #             tax_totals['total_amount_currency']
    #         )
    #         print("==========================================")
    #         print("\n")

    # def _custom_tax_round(self, amount):
    #     decimal_part = amount - math.floor(amount)
    #     if decimal_part >= 0.51:
    #         return math.ceil(amount)
    #     return math.floor(amount)
    #
    # def _compute_tax_totals(self):
    #     for move in self:
    #         if not move.is_invoice(include_receipts=True):
    #             move.tax_totals = None
    #             continue
    #
    #         base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
    #         tax_totals = self.env['account.tax']._get_tax_totals_summary(
    #             base_lines=base_lines,
    #             currency=move.currency_id,
    #             company=move.company_id,
    #             cash_rounding=move.invoice_cash_rounding_id,
    #         )
    #
    #         total_tax = 0.0
    #
    #         for subtotal in tax_totals.get('subtotals', []):
    #             subtotal_tax = 0.0
    #
    #             for group in subtotal.get('tax_groups', []):
    #                 rounded_tax = self._custom_tax_round(group['tax_amount_currency'])
    #
    #                 group['tax_amount_currency'] = rounded_tax
    #                 group['tax_amount'] = rounded_tax
    #
    #                 subtotal_tax += rounded_tax
    #             subtotal['tax_amount_currency'] = subtotal_tax
    #             subtotal['tax_amount'] = subtotal_tax
    #             total_tax += subtotal_tax
    #         # 🔹 FINAL totals derived from rounded groups
    #         tax_totals['tax_amount_currency'] = total_tax
    #         tax_totals['tax_amount'] = total_tax
    #         tax_totals['total_amount_currency'] = (
    #                 tax_totals['base_amount_currency'] + total_tax
    #         )
    #         tax_totals['total_amount'] = (
    #                 tax_totals['base_amount'] + total_tax
    #         )
    #         move.tax_totals = tax_totals
    #         print(tax_totals,"///////////////////////////////////")
    #         move.tax_totals['display_in_company_currency'] = (
    #                 move.company_id.display_invoice_tax_company_currency
    #                 and move.company_currency_id != move.currency_id
    #                 and move.tax_totals['has_tax_groups']
    #                 and move.is_sale_document(include_receipts=True)
    #         )

    @api.depends('invoice_line_ids')
    def total_amount_count_discount(self):
        for rec in self:
            if rec.invoice_line_ids:
                line = rec.invoice_line_ids[0]
                rec.total_amount_show = line.price_unit
                rec.discount_amount_show = line.price_unit * (line.discount / 100)
            else:
                rec.total_amount_show = 0
                rec.discount_amount_show = 0

    @api.constrains('billing_from', 'billing_to')
    def _check_billing_period_same_month(self):
        for rec in self:
            # print(rec.tenancy_id.payment_term,".......................")
            if rec.billing_from and rec.billing_to and rec.tenancy_id.payment_term != 'quarterly':
                print(rec.tenancy_id.payment_term != 'quarterly')
                if (rec.billing_from.month != rec.billing_to.month or
                        rec.billing_from.year != rec.billing_to.year):
                    raise ValidationError(
                        "Billing Period From and Billing Period To must be in the same month and year.")

    @api.constrains('billing_from', 'billing_to', 'invoice_line_ids')
    def _compute_billing_range(self):
        for record in self:

            if record.billing_from and record.billing_to and record.invoice_line_ids:

                if not record.date_year:
                    record.date_year = record.billing_from.strftime("%Y-%m-%d")

                # record.invoice_line_ids[0].description2 = ""

                # %d gives leading zero: 01, 02, 03, etc.
                from_str = record.billing_from.strftime("%d %B %Y")
                to_str = record.billing_to.strftime("%d %B %Y")

                record.billing_range_display = f"{from_str} to {to_str}"

                if record.invoice_line_ids and record.nhcl_invoice_type == 'rent':
                    desc = 'Rental Invoice for the period of '
                    record.invoice_line_ids[0].description2 = (
                            desc + f"{from_str} to {to_str}"
                    )

                elif record.invoice_line_ids and record.nhcl_invoice_type == 'cam':
                    desc = 'CAM Invoice for the period of '
                    record.invoice_line_ids[0].description2 = (
                            desc + f"{from_str} to {to_str}"
                    )
                elif record.invoice_line_ids and record.nhcl_invoice_type == 'signage':
                    desc = ' '
                    record.invoice_line_ids[0].description2 = (
                            desc + f"{from_str} to {to_str}"
                    )


            else:
                record.billing_range_display = ""
                # continue


    @api.onchange('date_year')
    def change_billing(self):
        for rec in self:
            if not rec.date_year:
                rec.billing_from = False
                rec.billing_to = False
                continue

            first_day = rec.date_year.replace(day=1)
            last_day = first_day + relativedelta(months=1, days=-1)

            rec.update({
                'billing_from': first_day,
                'billing_to': last_day,
            })

    def generate_lines_compute_billing_range_price_total(self):
        # if self.invoice_line_ids:
            for record in self:
                matched_cam = None
                from_date = record.billing_from
                to_date = record.billing_to
                billed_days = (to_date - from_date).days + 1
                month_days = monthrange(from_date.year, from_date.month)[1]
                matched_renewal = None
                if record.tenancy_id.renewal_type and True and record.tenancy_id.payment_term != 'quarterly':
                    if record.billing_from and record.billing_to and record.tenancy_id and record.invoice_line_ids and record.nhcl_invoice_type == 'rent':

                        for renewal in record.tenancy_id.year_ids:
                            start = renewal.start_year
                            end = renewal.end_date
                            if isinstance(start, date) and isinstance(end, date):
                                if start <= from_date <= end:
                                    matched_renewal = renewal
                                    # print("matched_renewal", matched_renewal)
                                    break

                        if matched_renewal:
                            rent_amount = matched_renewal.amount
                            price_unit = round((rent_amount / month_days) * billed_days, 2)

                        else:
                            # Fallback: use total rent directly (not prorated)
                            price_unit = record.tenancy_id.total_rent


                            # ✅ Apply the computed price_unit to all invoice lines (or selectively)

                        for line in record.invoice_line_ids:
                            line.price_unit = price_unit

                    elif record.billing_from and record.billing_to and record.tenancy_id and record.invoice_line_ids and record.nhcl_invoice_type == 'cam':
                        for cam in record.tenancy_id.cam_year_ids:
                            start = cam.cam_start_year
                            end = cam.cam_end_date
                            # print(cam.cam_amount,'cam  belongs to',start,end)
                            if isinstance(start, date) and isinstance(end, date):
                                if start <= from_date <= (end):  # or start # in case end is None
                                    matched_cam = cam
                                    break

                        if matched_cam:
                            cam_amount = matched_cam.cam_amount

                            price_unit = round((cam_amount / month_days) * billed_days, 2)
                        else:

                            price_unit = 0.0  # fallback
                        for line in record.invoice_line_ids:
                            line.price_unit = price_unit
                    else:
                        continue
                elif record.tenancy_id.payment_term == 'quarterly':

                    if record.nhcl_invoice_type == 'rent':
                        record.invoice_line_ids.price_unit = round(record.tenancy_id.total_rent)
                    elif record.nhcl_invoice_type == 'cam':
                        if record.tenancy_id.cam_type == 'cam_sft':
                            record.invoice_line_ids.price_unit = record.tenancy_id.cam_chargeable if record.tenancy_id.use_chargeable else record.tenancy_id.cam_carpet
                        else:
                            record.invoice_line_ids.price_unit = record.cam_fixed

                else:
                    if record.nhcl_invoice_type == 'rent':
                        record.invoice_line_ids.price_unit = round(
                            (record.tenancy_id.total_rent / month_days) * billed_days, 2)
                        # print(round((record.tenancy_id.total_rent / month_days) * billed_days, 2))
                    elif record.nhcl_invoice_type == 'cam':
                        if record.tenancy_id.use_carpet:
                            # print("cam carpet area value", record.tenancy_id.cam_carpet)
                            record.invoice_line_ids.price_unit = round(
                                (record.tenancy_id.cam_carpet / month_days) * billed_days, 2)
                        elif record.tenancy_id.use_chargeable:
                            # print("cam charge area value", record.tenancy_id.cam_chargeable)
                            record.invoice_line_ids.price_unit = round(
                                (record.tenancy_id.cam_chargeable / month_days) * billed_days, 2)
                        else:
                            record.invoice_line_ids.price_unit = round(
                                (record.tenancy_id.cam_fixed / month_days) * billed_days, 2)

                            # print("getting chargeable area ", record.tenancy_id.cam_chargeable)

                    else:
                        continue
                if record.nhcl_invoice_type == 'gas':
                    record._generate_gas_lines()


    # @api.constrains('billing_from', 'billing_to', 'invoice_line_ids.price_unit')
    # def _compute_billing_range_price_total(self):
    #     if self.invoice_line_ids:
    #         for record in self:
    #             matched_cam = None
    #             from_date = record.billing_from
    #             to_date = record.billing_to
    #             billed_days = (to_date - from_date).days + 1
    #             month_days = monthrange(from_date.year, from_date.month)[1]
    #             matched_renewal = None
    #             if record.tenancy_id.renewal_type and True and record.tenancy_id.payment_term != 'quarterly':
    #                 #print('quaterly not found............', record.id)
    #                 if record.billing_from and record.billing_to and record.tenancy_id and record.invoice_line_ids and record.nhcl_invoice_type == 'rent':
    #                     # print("hii")
    #
    #                     for renewal in record.tenancy_id.year_ids:
    #                         start = renewal.start_year
    #                         end = renewal.end_date
    #
    #                         if isinstance(start, date) and isinstance(end, date):
    #                             if start <= from_date <= end:
    #                                 matched_renewal = renewal
    #                                 # print("matched_renewal", matched_renewal)
    #                                 break
    #
    #                     if matched_renewal:
    #                         rent_amount = matched_renewal.amount
    #                         price_unit = round((rent_amount / month_days) * billed_days, 2)
    #                         # print("price_unit", price_unit)
    #                         # print("rent_amount", rent_amount)
    #                     else:
    #                         # Fallback: use total rent directly (not prorated)
    #                         price_unit = record.tenancy_id.total_rent
    #                         # print("done")
    #
    #                         # ✅ Apply the computed price_unit to all invoice lines (or selectively)
    #
    #                     for line in record.invoice_line_ids:
    #                         line.price_unit = price_unit
    #                         # print("line.price_unit", line.price_unit)
    #                 elif record.billing_from and record.billing_to and record.tenancy_id and record.invoice_line_ids and record.nhcl_invoice_type == 'cam':
    #                     print('calling.............', record.name)
    #                     for cam in record.tenancy_id.cam_year_ids:
    #                         start = cam.cam_start_year
    #                         end = cam.cam_end_date
    #                         # print(cam.cam_amount,'cam  belongs to',start,end)
    #                         if isinstance(start, date) and isinstance(end, date):
    #                             if start <= from_date <= (end):  # or start # in case end is None
    #
    #                                 # print('matched data')
    #                                 matched_cam = cam
    #                                 # print(matched_cam, "//////////", matched_cam.cam_yid.tenancy_seq,
    #                                 #       matched_cam.cam_start_year, matched_cam.cam_amount)
    #                                 break
    #
    #                     if matched_cam:
    #                         cam_amount = matched_cam.cam_amount
    #                        # print(cam_amount, month_days, billed_days)
    #                         price_unit = round((cam_amount / month_days) * billed_days, 2)
    #                     else:
    #                         #print('dada////')
    #                         price_unit = 0.0  # fallback
    #                     for line in record.invoice_line_ids:
    #                         line.price_unit = price_unit
    #                 else:
    #                     continue
    #             elif record.tenancy_id.payment_term == 'quarterly':
    #                 #print('quaterly found....', record.id)
    #                 if record.nhcl_invoice_type == 'rent':
    #                     record.invoice_line_ids.price_unit = round(record.tenancy_id.total_rent)
    #                 elif record.nhcl_invoice_type == 'cam':
    #                     if record.tenancy_id.cam_type == 'cam_sft':
    #                         record.invoice_line_ids.price_unit = record.tenancy_id.cam_chargeable if record.tenancy_id.use_chargeable else record.tenancy_id.cam_carpet
    #                     else:
    #                         record.invoice_line_ids.price_unit = record.cam_fixed
    #
    #             else:
    #                 if record.nhcl_invoice_type == 'rent':
    #                     record.invoice_line_ids.price_unit = round(
    #                         (record.tenancy_id.total_rent / month_days) * billed_days, 2)
    #                     # print(round((record.tenancy_id.total_rent / month_days) * billed_days, 2))
    #                 elif record.nhcl_invoice_type == 'cam':
    #                     if record.tenancy_id.use_carpet:
    #                         # print("cam carpet area value", record.tenancy_id.cam_carpet)
    #                         record.invoice_line_ids.price_unit = round(
    #                             (record.tenancy_id.cam_carpet / month_days) * billed_days, 2)
    #                     elif record.tenancy_id.use_chargeable:
    #                         # print("cam charge area value", record.tenancy_id.cam_chargeable)
    #                         record.invoice_line_ids.price_unit = round(
    #                             (record.tenancy_id.cam_chargeable / month_days) * billed_days, 2)
    #                     else:
    #                         record.invoice_line_ids.price_unit = round(
    #                             (record.tenancy_id.cam_fixed / month_days) * billed_days, 2)
    #
    #                         # print("getting chargeable area ", record.tenancy_id.cam_chargeable)
    #
    #                 else:
    #                     continue
    # this is for the amount convert to words
    def convert_to_indian_words(self, amount):
        # Ensure amount is a float
        amount = float(amount)
        integer_part = int(amount)  # Get the integer part
        decimal_part = round((amount - integer_part) * 100)  # Get the decimal part as paise (always two digits)

        # Define components for conversion
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen",
                 "Nineteen"]
        thousands = ["", "Thousand", "Lakh", "Crore"]

        def convert_chunk(num):
            """Convert a three-digit chunk into words."""
            if num == 0:
                return ""
            elif num < 10:
                return units[num]
            elif num < 20:
                return teens[num - 10]
            elif num < 100:
                return tens[num // 10] + (" " + units[num % 10] if num % 10 != 0 else "")
            else:
                return units[num // 100] + " Hundred" + (" " + convert_chunk(num % 100) if num % 100 != 0 else "")

        # Convert the integer part
        words = []
        chunk_idx = 0

        while integer_part > 0:
            chunk = integer_part % 1000
            if chunk > 0:
                chunk_in_words = convert_chunk(chunk) + " " + thousands[chunk_idx]
                words.insert(0, chunk_in_words.strip())
            integer_part //= 1000
            chunk_idx += 1

        # Handle the case where the amount is exactly zero
        if not words:
            words.append("Zero")

        rupee_words = " ".join(words).strip() + " Rupees"

        # Add the decimal part (paise) if it exists
        if decimal_part > 0:
            paise_words = convert_chunk(decimal_part) + " Paise"
            return f"{rupee_words} and {paise_words}"

        return rupee_words

    @api.depends('amount_total','billing_from')
    def _compute_amount_in_words(self):
        for record in self:

            # Retrieve the total amount from the invoice (absolute value in case of negative amounts)
            # amount_total = round(record.amount_total)
            total = sum(record.invoice_line_ids.mapped('price_total'))
            subtotal = sum(record.invoice_line_ids.mapped('price_subtotal'))

            v1 = round((total - subtotal) / 2)
            v2 = round((total - subtotal) / 2)

            print(v1, v2,'finerlfnld')

            v3 = int(v1 + v2) + record.total_amount_show
            record.amount_words_base=v3
            # v4 = int(record.amount_tax) + record.total_amount_show

            # Use the custom method to convert the amount to words
            # record.amount_in_words = self.convert_to_indian_words(amount_total)
            # record.amount_in_words = self.convert_to_indian_words(v3)
            #print(record.tax_totals,"uhkaskcl")
            record.nhcl_total_amount = record.tax_totals['total_amount'] if record.tax_totals else 0
            record.amount_in_words = self.convert_to_indian_words(record.nhcl_total_amount)


    @api.depends('needed_terms', 'invoice_date', 'invoice_date_due')
    def _compute_invoice_date_due(self):
        # First run Odoo's logic
        super()._compute_invoice_date_due()

        for move in self:
            # If no payment term is set, override the due date
            if not move.invoice_payment_term_id:
                base_date = move.invoice_date or fields.Date.context_today(move)
                if move.nhcl_invoice_type in ['rent', 'cam', 'electric','rs']:
                    move.invoice_date_due = base_date + timedelta(days=6)
                elif move.nhcl_invoice_type == 'gas':
                    move.invoice_date_due = base_date + timedelta(days=2)
                # elif move.nhcl_invoice_type == 'signage':
                #     move.invoice_date_due = base_date + timedelta(days=2)
                else:
                    move.invoice_date_due = base_date

    @api.onchange('nhcl_invoice_type', 'invoice_line_ids')
    def get_fields(self):
        invoice = self.env.context.get('default_move_type') == 'out_invoice'
        credit_note = self.env.context.get('default_move_type') == 'out_refund' and self.env.context.get(
            'display_account_trust', False)
        for rec in self:

            if (invoice and rec.nhcl_invoice_type == 'electric') or (
                    credit_note and rec.nhcl_invoice_type == 'electric'):
                rec.cam_fields = True
            else:
                rec.cam_fields = False

            # multiplying_factor logic
            for line in rec.invoice_line_ids:
                if rec.nhcl_invoice_type == 'gas':
                    line.multiplying_factor = 4.8020
                # else:
                #     line.multiplying_factor = 0.0

    # this is for the invoice date for report

    def _generate_electric_lines(self):
        for move in self:
            if move.nhcl_invoice_type != 'electric' or not move.partner_id:
                return
            comparison_month = move.comparision_yr_mnth.name
            if not  comparison_month:
                continue
            year=comparison_month[-1:-5:-1]
            # print(comparison_month)
            # print(year[::-1],year)

            d = move.months
            meter = move.tenancy_id.unit_no

            bill = self.env['catagory.bill'].search([
                ('ten', '=', move.partner_id.id),
                ('months', '=', d), ('is_invoice_created', '=', False), ('year', '=', year[::-1])
            ], limit=1)
            if not bill or not bill.ct_line_ids:
                raise ValidationError('Already created one Eb bill or does not present')
            lines = bill.ct_line_ids.sorted(key=lambda l: l.dt)
            first_line = lines[0]
            last_line = lines[-1]
            reset_line = next((l for l in lines if l.open_unit < 1), None)
            prev_line = None
            for i, line in enumerate(lines):
                if line.open_unit < 1:
                    if i > 0:
                        prev_line = lines[i - 1]
                        break

            product = self.env['product.product'].search([('name', '=', 'Units from APEPDCL Charges for')], limit=1)
            if not product:
                raise ValidationError("Product 'Units from APEPDCL Charges for' not found.")

            invoice_lines = []

            if not reset_line:
                # Case 1
                opening = first_line.open_unit
                closing = last_line.close_unit
                consumption = (closing - opening)  # * 1000
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f'EB- {meter}',
                    'opening_reading': opening,
                    'closing_reading': closing,
                    'consumption': consumption,
                    'description2':f'EB- {meter}',
                }))
            else:
                # Case 2
                opening_1 = first_line.open_unit  # 50
                closing_1 = prev_line.close_unit  # open_unit#20
                consumption_1 = (closing_1 - opening_1) * 1000  # 20*1000-50
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f'EB- {meter}',
                    'opening_reading': opening_1,
                    'closing_reading': closing_1,
                    'consumption': consumption_1,
                    'description2': f'EB- {meter}',
                }))
                opening_2 = reset_line.open_unit  # open_unit
                closing_2 = last_line.close_unit
                consumption_2 = closing_2 - opening_2
                invoice_lines.append((0, 0, {
                    'product_id': product.id,
                    'name': f'EB- {meter}',
                    'opening_reading': opening_2,
                    'closing_reading': closing_2,
                    'consumption': consumption_2,
                    'description2':f'EB- {meter}',
                }))
            hvac = self.env['hvac.reading'].search([
                ('tenant_id', '=', move.partner_id.id),
                ('month', '=', d), ('year', '=', year[::-1])
            ], limit=1)
            # this is for the hvac screen value line creation
            if hvac and hvac.hvac_line_ids:
                hvac_lines = hvac.hvac_line_ids.sorted(key=lambda l: l.date)
                first_line = hvac_lines[0]
                last_line = hvac_lines[-1]
                reset_line = next((l for l in hvac_lines if l.opening_unit < 1), None)
                prev_line = None
                for i, line in enumerate(hvac_lines):
                    if line.opening_unit < 1:
                        if i > 0:
                            prev_line = hvac_lines[i - 1]
                            break
                product_hvac = self.env['product.product'].search(
                    [('name', '=', 'Air Conditional APEPDCL Charges for')], limit=1)
                if not product_hvac:
                    raise ValidationError("Product 'Air Conditional APEPDCL Charges for' not found.")

                if not reset_line:
                    # print('caling if ')
                    # Case 1: No reset
                    opening = first_line.opening_unit
                    closing = last_line.closing_unit
                    consumption = closing - opening

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac.id,
                        'name': f'AC- {meter}',
                        'opening_reading': opening,
                        'closing_reading': closing,
                        'consumption': consumption,
                        'description2': f'AC- {meter}',
                    }))
                else:
                    # print('calling else')
                    # Case 2: Reset occurred
                    opening_1 = first_line.opening_unit
                    closing_1 = prev_line.closing_unit
                    consumption_1 = (closing_1 - opening_1) * 1000

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac.id,
                        'name': f'AC- {meter}',
                        'opening_reading': opening_1,
                        'closing_reading': closing_1,
                        'consumption': consumption_1,
                        'description2': f'AC- {meter}',
                    }))

                    opening_2 = reset_line.opening_unit
                    closing_2 = last_line.closing_unit
                    consumption_2 = closing_2 - opening_2

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac.id,
                        'name': f'AC- {meter}',
                        'opening_reading': opening_2,
                        'closing_reading': closing_2,
                        'consumption': consumption_2,
                        'description2': f'AC- {meter}',
                    }))


            dg = self.env['dg.reading'].search([
                ('tenant_id', '=', move.partner_id.id),
                ('month', '=', d), ('year', '=', year[::-1])
            ], limit=1)
            # this is for the DG  screen value line creation
            if dg and dg.dg_line_ids:
                dg_lines = dg.dg_line_ids.sorted(key=lambda l: l.date)
                first_line = dg_lines[0]
                last_line = dg_lines[-1]
                reset_line = next((l for l in dg_lines if l.opening_unit < 1), None)
                prev_line = None
                for i, line in enumerate(dg_lines):
                    if line.opening_unit < 1:
                        if i > 0:
                            prev_line = dg_lines[i - 1]
                            break
                product_hvac = self.env['product.product'].search(
                    [('name', '=', 'Units Generated Charges for')], limit=1)
                if not product_hvac:
                    raise ValidationError("Product 'Units Generated Charges for' not found.")

                if not reset_line:
                    # print('caling if ')
                    # Case 1: No reset
                    opening = first_line.opening_unit
                    closing = last_line.closing_unit
                    consumption = closing - opening
                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac.id,
                        'name': f'DG- {meter}',
                        'opening_reading': opening,
                        'closing_reading': closing,
                        'consumption': consumption,
                        'description2':f'DG- {meter}',
                    }))
                else:
                    # print('calling else')
                    # Case 2: Reset occurred
                    opening_1 = first_line.opening_unit
                    closing_1 = prev_line.closing_unit
                    consumption_1 = (closing_1 - opening_1) * 1000

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac.id,
                         'name': f'DG- {meter}',
                        'opening_reading': opening_1,
                        'closing_reading': closing_1,
                        'consumption': consumption_1,
                        'description2': f'DG- {meter}',
                    }))
                    opening_2 = reset_line.opening_unit
                    closing_2 = last_line.closing_unit
                    consumption_2 = closing_2 - opening_2

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac.id,
                         'name': f'DG- {meter}',
                        'opening_reading': opening_2,
                        'closing_reading': closing_2,
                        'consumption': consumption_2,
                        'description2': f'DG- {meter}',
                    }))
            # cool water line created
            hot_water = self.env['hot.water.reading'].search([
                ('tenant_id', '=', move.partner_id.id),
                ('month', '=', d), ('year', '=', year[::-1])
            ], limit=1)

            if hot_water and hot_water.hot_water_line_ids:
                hw_lines = hot_water.hot_water_line_ids.sorted(key=lambda l: l.date)
                first_line = hw_lines[0]
                last_line = hw_lines[-1]
                reset_line = next((l for l in hw_lines if l.opening_unit < 1), None)
                prev_line = None
                for i, line in enumerate(hw_lines):
                    if line.opening_unit < 1:
                        if i > 0:
                            prev_line = hw_lines[i - 1]
                            break
                product_hw = self.env['product.product'].search([('name', '=', 'Cooling Tower Water Charges for')], limit=1)
                if not product_hw:
                    raise ValidationError("Cooling Tower Water Charges for.")

                if not reset_line:
                    # No reset case
                    opening = first_line.opening_unit
                    closing = last_line.closing_unit
                    consumption = closing - opening
                    invoice_lines.append((0, 0, {
                        'product_id': product_hw.id,
                        'name': f'CTWC- {meter}',
                        'opening_reading': opening,
                        'closing_reading': closing,
                        'consumption': consumption,
                        'description2': f'CTWC- {meter}',
                    }))
                else:
                    # Reset occurred
                    opening_1 = first_line.opening_unit
                    closing_1 = prev_line.closing_unit
                    consumption_1 = (closing_1 - opening_1) *1000

                    invoice_lines.append((0, 0, {
                        'product_id': product_hw.id,
                        'name': f'CTWC- {meter}',
                        'opening_reading': opening_1,
                        'closing_reading': closing_1,
                        'consumption': consumption_1,
                        'description2': f'CTWC- {meter}',
                    }))
                    opening_2 = reset_line.opening_unit
                    closing_2 = last_line.closing_unit
                    consumption_2 = closing_2 - opening_2
                    invoice_lines.append((0, 0, {
                        'product_id': product_hw.id,
                        'name': f'CTWC- {meter}',
                        'opening_reading': opening_2,
                        'closing_reading': closing_2,
                        'consumption': consumption_2,
                        'description2': f'CTWC- {meter}',
                    }))
            # Get Water Reading for the partner and month
            water = self.env['water.reading'].search([
                ('tenant_id', '=', move.partner_id.id),
                ('month', '=', d), ('year', '=', year[::-1])
            ], limit=1)

            if water and water.water_line_ids:
                water_lines = water.water_line_ids.sorted(key=lambda l: l.date)
                first_line = water_lines[0]
                last_line = water_lines[-1]
                reset_line = next((l for l in water_lines if l.opening_unit < 1), None)
                prev_line = None
                for i, line in enumerate(water_lines):
                    if line.opening_unit < 1:
                        if i > 0:
                            prev_line = water_lines[i - 1]
                            break

                # Get Product for Water Billing
                product_water = self.env['product.product'].search([
                    ('name', '=', 'Water Used in KL Charges for')
                ], limit=1)

                if not product_water:
                    raise ValidationError("Product 'Water Used in KL Charges for' not found.")

                if not reset_line:
                    # Case 1: No Reset
                    opening = first_line.opening_unit
                    closing = last_line.closing_unit
                    consumption = max(closing - opening, 0.0)

                    invoice_lines.append((0, 0, {
                        'product_id': product_water.id,
                        'name': f'wat- {meter}',
                        'opening_reading': opening,
                        'closing_reading': closing,
                        'consumption': consumption,
                        'description2':  f'wat- {meter}',
                    }))
                else:
                    # Case 2: Reset Occurred

                    # Before Reset
                    opening_1 = first_line.opening_unit
                    closing_1 = prev_line.closing_unit
                    consumption_1 = max(closing_1 - opening_1, 0.0) * 1000

                    invoice_lines.append((0, 0, {
                        'product_id': product_water.id,
                        'name': f'wat- {meter}',
                        'opening_reading': opening_1,
                        'closing_reading': closing_1,
                        'consumption': consumption_1,
                        'description2': f'wat- {meter}',
                    }))

                    # After Reset
                    opening_2 = reset_line.opening_unit
                    closing_2 = last_line.closing_unit
                    consumption_2 = max(closing_2 - opening_2, 0.0)

                    invoice_lines.append((0, 0, {
                        'product_id': product_water.id,
                        'name': f'wat- {meter}',
                        'opening_reading': opening_2,
                        'closing_reading': closing_2,
                        'consumption': consumption_2,
                        'description2': f'wat- {meter}',
                    }))
            # ============================================================
            # HVAC DG Reading
            # ============================================================

            hvac_dc = self.env['hvac.dc.reading'].search([
                ('tenant_id', '=', move.partner_id.id),
                ('month', '=', d),
                ('year', '=', year[::-1])
            ], limit=1)

            if hvac_dc and hvac_dc.hvac_dc_line_ids:

                hvac_dc_lines = hvac_dc.hvac_dc_line_ids.sorted(
                    key=lambda l: l.date
                )

                first_line = hvac_dc_lines[0]
                last_line = hvac_dc_lines[-1]

                # Find reset reading
                reset_line = next(
                    (l for l in hvac_dc_lines if l.opening_unit < 1),
                    None
                )

                # Find reading immediately before reset
                prev_line = None

                for i, line in enumerate(hvac_dc_lines):
                    if line.opening_unit < 1:
                        if i > 0:
                            prev_line = hvac_dc_lines[i - 1]
                        break

                # Get HVAC DC product
                product_hvac_dc = self.env['product.product'].search([
                    ('name', '=', 'Air Conditional Generated Charges for')
                ], limit=1)

                if not product_hvac_dc:
                    raise ValidationError(
                        "Product 'Air Conditional Generated Charges for' not found."
                    )

                # --------------------------------------------------------
                # CASE 1: No Reset
                # --------------------------------------------------------
                if not reset_line:

                    opening = first_line.opening_unit
                    closing = last_line.closing_unit

                    consumption = closing - opening

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac_dc.id,
                        'name': f'AC-DG- {meter}',
                        'opening_reading': opening,
                        'closing_reading': closing,
                        'consumption': consumption,
                        'description2': f'AC-DG- {meter}',
                    }))

                # --------------------------------------------------------
                # CASE 2: Reset Occurred
                # --------------------------------------------------------
                else:

                    # ----------------------------------------------------
                    # Before Reset
                    # ----------------------------------------------------
                    if prev_line:
                        opening_1 = first_line.opening_unit
                        closing_1 = prev_line.closing_unit

                        consumption_1 = (
                                                closing_1 - opening_1
                                        ) * 1000

                        invoice_lines.append((0, 0, {
                            'product_id': product_hvac_dc.id,
                            'name': f'AC-DG- {meter}',
                            'opening_reading': opening_1,
                            'closing_reading': closing_1,
                            'consumption': consumption_1,
                            'description2': f'AC-DG- {meter}',
                        }))

                    # ----------------------------------------------------
                    # After Reset
                    # ----------------------------------------------------
                    opening_2 = reset_line.opening_unit
                    closing_2 = last_line.closing_unit

                    consumption_2 = closing_2 - opening_2

                    invoice_lines.append((0, 0, {
                        'product_id': product_hvac_dc.id,
                        'name': f'AC-DG- {meter}',
                        'opening_reading': opening_2,
                        'closing_reading': closing_2,
                        'consumption': consumption_2,
                        'description2': f'AC-DG- {meter}',
                    }))
            move.invoice_line_ids = [(5, 0, 0)] + invoice_lines

    def get_previous_month(self, current_month):
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul',
                  'aug', 'sep', 'oct', 'nov', 'dec']
        index = months.index(current_month)
        return months[index - 1] if index > 0 else months[-1]

    def _generate_gas_lines(self):
        print('calling.....')
        # self.ensure_one()

        comparison_month = self.comparision_yr_mnth.name

        if not comparison_month:
            return []

        year = comparison_month[-1:-5:-1]
        d = self.months
        meter = self.tenancy_id.unit_no

        gas_reading = self.env['gas.reading'].search([
            ('tenant_id', '=', self.partner_id.id),
            ('month', '=', d),
            ('year', '=', year[::-1])
        ], limit=1)

        # print("GAS READING:", gas_reading)

        if not gas_reading:
            return []

        if not gas_reading.gas_line_ids:
            return []

        # =====================================================
        # GET GAS LINES ONLY FOR BILLING PERIOD
        # =====================================================

        gas_lines = gas_reading.gas_line_ids.filtered(
            lambda line: (
                    self.billing_from
                    and self.billing_to
                    and self.billing_from <= line.date <= self.billing_to
            )
        ).sorted(key=lambda line: line.date)

        if not gas_lines:
            return []

        first_line = gas_lines[0]
        last_line = gas_lines[-1]

        # =====================================================
        # FIND RESET LINE
        # =====================================================

        reset_line = next(
            (line for line in gas_lines if line.reset_unit > 1),
            None
        )

        # =====================================================
        # FIND LINE BEFORE RESET
        # =====================================================

        prev_line = None

        if reset_line:
            previous_lines = gas_lines.filtered(
                lambda line: line.date < reset_line.date
            )

            if previous_lines:
                prev_line = previous_lines[-1]

        # =====================================================
        # FIND GAS PRODUCT
        # =====================================================

        product_gas = self.env['product.product'].search([
            ('name', '=', 'Units from Gas Consumption')
        ], limit=1)

        if not product_gas:
            raise ValidationError("Product 'Units from Gas Consumption' not found.")

        invoice_lines = []

        # =====================================================
        # NO RESET
        # =====================================================

        if not reset_line:

            opening = first_line.opening_unit
            closing = last_line.closing_unit
            consumption = closing - opening

            invoice_lines.append((0, 0, {
                'product_id': product_gas.id,
                'name': f'Gas- {meter}',
                'description2': f'Gas- {meter}',
                'opening_reading': opening,
                'closing_reading': closing,
                'consumption': consumption,
            }))

        # =====================================================
        # RESET
        # =====================================================

        else:

            # =================================================
            # BEFORE RESET
            # =================================================

            opening_1 = first_line.opening_unit

            if prev_line:
                closing_1 = prev_line.closing_unit
            else:
                closing_1 = reset_line.opening_unit

            consumption_1 = closing_1 - opening_1

            invoice_lines.append((0, 0, {
                'product_id': product_gas.id,
                'name': f'Gas- {meter}',
                'description2': f'Gas- {meter}',
                'opening_reading': opening_1,
                'closing_reading': closing_1,
                'consumption': consumption_1,
            }))

            # =================================================
            # AFTER RESET
            # =================================================

            opening_2 = reset_line.opening_unit
            closing_2 = last_line.closing_unit
            consumption_2 = closing_2 - opening_2

            invoice_lines.append((0, 0, {
                'product_id': product_gas.id,
                'name': f'Gas- {meter}',
                'description2': f'Gas- {meter}',
                'opening_reading': opening_2,
                'closing_reading': closing_2,
                'consumption': consumption_2,
            }))

        return invoice_lines

    @api.model
    def create(self, vals):
        if vals.get('billing_from') and vals.get('nhcl_invoice_type') in ['rent','cam']:
            # print('getting data')
            billing_from = fields.Date.from_string(vals['billing_from'])
            vals['months'] = billing_from.strftime('%b').lower()

        move = super().create(vals)
        # Step 3: Generate electric lines if applicable
        if move.nhcl_invoice_type == 'electric':
            move._generate_electric_lines()
        if move.nhcl_invoice_type == 'gas':
            invoice_lines = move._generate_gas_lines() or []

            move.invoice_line_ids = [(5, 0, 0)] + invoice_lines
        return move



    # @api.constrains('partner_id')
    # def get_tenancy_record(self):
    #     for rec in self:
             #if self.move_type in ['out_invoice', 'out_refund']:
        #         if not rec.tenancy_id:
        #             raise UserError('This Customer not present in the Tenancy')

    def action_print_out(self):
        self.ensure_one()

        if self.nhcl_invoice_type in ['utility']:
            return self.env.ref(
                'nhcl_rental_management.electric_report_print'
            ).report_action(self)
        elif self.nhcl_invoice_type in ['gas']:
            return self.env.ref(
                'nhcl_rental_management.gas_report_print'
            ).report_action(self)

        return self.env.ref(
            'nhcl_rental_management.tenancy_account_invoice_customise'
        ).report_action(self)

    @api.onchange('billing_from')
    def _onchange_billing_from(self):
        if not self.billing_from:
            return
        if self.billing_from:# and self.nhcl_invoice_type in ['rent', 'cam']:
            month_str = self.billing_from.strftime('%b').lower()
            self.months = month_str

        # Format as "Jul-2025"
        formatted_name = self.billing_from.strftime('%b-%Y')  # e.g., "Jul-2025"

        # Search if it already exists
        year_rec = self.env['tenancy.relation.year'].search([('name', '=', formatted_name)], limit=1)

        # If not found, create
        if not year_rec:
            year_rec = self.env['tenancy.relation.year'].create({'name': formatted_name})

    @api.depends('billing_from','billing_to')
    def _compute_invoice_month_range(self):
        for record in self:
            if record.invoice_date and record.billing_from:
                # Parse the invoice_date into a date object
                invoice_date1 = fields.Date.from_string(record.billing_from)
                invoice_date2 = fields.Date.from_string(record.billing_to)
                formatted_range = f"{invoice_date1.strftime('%d/%b/%Y')} to {invoice_date2.strftime('%d/%b/%Y')}"
                record.invoice_month_range = formatted_range
            else:
                record.invoice_month_range = "No Invoice Date"

    # this is for the tenancy 2 days before alert message
    @api.model
    def send_message_invoice(self):
        # Get the email template
        template = self.env.ref('nhcl_rental_management.maintenance_invoice_message')
        channel = self.env['discuss.channel'].search([('name', '=', 'Invoice Alert')])
        # Create the channel if it does not exist
        if not channel:
            user_ids = self.env['res.users'].search([]).ids
            channel = self.env['discuss.channel'].create({
                'name': 'Invoice Alert',
                'channel_type': 'group',
                'channel_partner_ids': [(4, user.partner_id.id) for user in self.env['res.users'].browse(user_ids)],
            })
        for record in self.env['account.move'].search(
                [('move_type', '=', 'out_invoice'), ('invoice_date', '!=', False), ('state', '=', 'draft')]):
            notification_date = record.invoice_date + timedelta(days=-2)
            if fields.Date.today() == notification_date:
                template.send_mail(record.id, force_send=True)
                channel.message_post(
                    body=f"email sent to tenant: {record.partner_id.name} for aleart",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )

    def send_invoice_email_post(self):
        # Reference the email template you want to use
        template = self.env.ref('nhcl_rental_management.invoice_message_post')

        # Search for all posted invoices (out_invoice type) with a valid invoice date
        account_post = self.env['account.move'].search(
            [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('invoice_date', '!=', False)]
        )

        for post in account_post:
            if post.invoice_date == fields.Date.today():
                template = self.env.ref('nhcl_rental_management.invoice_message_post')

                account_post = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('invoice_date', '!=', False)])
                for post in account_post:
                    if post.invoice_date == fields.Date.today():
                        # print("working successfully")
                        template.send_mail(post.id, force_send=True)

    # it's for the getting record of the areunit in the invoice screen from same customer previous record
    def getrecord_areaunit(self):
        # Search for all moves where tenancy_id is set
        rec = self.env['account.move'].search([('tenancy_id', '!=', False)])
        for data in rec:
            if data.partner_id.id == self.partner_id.id:
                for line in data.line_ids:
                    if line.nhcl_area_units:
                        for myline in self.line_ids:
                            update_record = myline.write({'nhcl_area_units': line.nhcl_area_units})
                return " "


    def send_email_invoice(self):
        template = self.env.ref('nhcl_rental_management.invoice_message_post')
        template2 = self.env.ref('nhcl_rental_management.invoice_cam_post')
        template3 = self.env.ref('nhcl_rental_management.invoice_utility_post')
        template4 = self.env.ref('nhcl_rental_management.invoice_gas_post')
        template5 = self.env.ref('nhcl_rental_management.invoice_signage_post')
        template6 = self.env.ref('nhcl_rental_management.invoice_rs_post')

        # Send appropriate email
        if self.nhcl_invoice_type == 'cam':
            # print("Invoice type is CAM. Sending CAM email...")
            template2.send_mail(self.id, force_send=True)
            self.getrecord_areaunit()
            # print("CAM email sent and area unit recorded.")
        elif self.nhcl_invoice_type == 'gas':
            # print("Invoice type is GAS. Sending GAS email...")
            template4.send_mail(self.id, force_send=True)
        elif self.nhcl_invoice_type == 'rs':
            # print("Invoice type is RS. Sending Rs email...")
            template6.send_mail(self.id, force_send=True)
        elif self.nhcl_invoice_type == 'electric':
            # print("Invoice type is ELECTRIC. Sending Electric email...")
            template3.send_mail(self.id, force_send=True)
        elif self.nhcl_invoice_type == 'signage':
            # print("Invoice type is Signage. Sending Signage email...")
            template5.send_mail(self.id, force_send=True)
        else:
            # print("Default email being sent.")
            template.send_mail(self.id, force_send=True)

    # def action_post(self):
    #     if self.move_type == 'out_invoice':
    #         expiry=self.env['tenancy.details'].search([('tenancy_id','=',self.partner_id.id),('contract_type','=','expire_contract')],order='id DESC',limit=1)
    #         print('found///////////////////////',expiry)
    #         if expiry:
    #             raise ValidationError("You can't Confirm because Already Tenancy is expired")
    #         if self.nhcl_invoice_type == 'rs' and not self.comparision_yr_mnth:
    #             raise ValidationError('You need to add the Comparison month')
    #
    #         # res = super(AccountMove, self).action_post()
    #
    #         for invoice in self:
    #             # Electric-specific logic
    #             if invoice.nhcl_invoice_type == 'electric' and invoice.invoice_date:
    #                 # print("Processing electric invoice for:", invoice.name)
    #                 prev_month = invoice.months
    #                 category_bills = self.env['catagory.bill'].search([
    #                     ('ten', '=', invoice.partner_id.id),
    #                     ('months', '=', prev_month),
    #                     ('is_invoice_created', '=', False)
    #                 ])
    #                 # print(f"Found {len(category_bills)} category bills to update.")
    #
    #                 for bill in category_bills:
    #                     bill.is_invoice_created = True
    #                     # print(f"Marked bill {bill.id} as invoiced.")
    #
    #             # ❗ Skip validation if context flag is set
    #             if self.env.context.get('skip_rent_validation'):
    #                 # print("Skipping rent/RS/MG/SLB validation due to context.")
    #                 continue
    #
    #             # Validation logic for rent vs RS/MG/SLB
    #             if invoice.move_type == 'out_invoice' and invoice.tenancy_id:
    #                 # print("Validating RS/MG vs Rent comparison...")
    #                 rent_invoices = self.env['account.move'].search([
    #                     ('tenancy_id', '=', invoice.tenancy_id.id),
    #                     ('nhcl_invoice_type', '=', 'rent'),
    #                     ('move_type', '=', 'out_invoice'),
    #                     ('state', '!=', 'cancel'),
    #                     ('comparision_yr_mnth', '=', invoice.comparision_yr_mnth.id),
    #                 ])
    #                 rs_invoice = self.env['account.move'].search([
    #                     ('tenancy_id', '=', invoice.tenancy_id.id),
    #                     ('nhcl_invoice_type', '=', 'rs'),
    #                     ('move_type', '=', 'out_invoice'),
    #                     ('state', '!=', 'cancel'),
    #                 ], limit=1)
    #                 sb_invoice = self.env['account.move'].search([
    #                     ('tenancy_id', '=', invoice.tenancy_id.id),
    #                     ('nhcl_invoice_type', '=', 'slb'),
    #                     ('move_type', '=', 'out_invoice'),
    #                     ('state', '!=', 'cancel'),
    #                 ], limit=1)
    #                 mg_invoice = self.env['account.move'].search([
    #                     ('tenancy_id', '=', invoice.tenancy_id.id),
    #                     ('nhcl_invoice_type', '=', 'mg'),
    #                     ('move_type', '=', 'out_invoice'),
    #                     ('state', '!=', 'cancel'),
    #                 ], limit=1)
    #
    #                 # print("Invoices fetched: Rent =", len(rent_invoices),
    #                 #       ", RS =", bool(rs_invoice),
    #                 #       ", SB =", bool(sb_invoice),
    #                 #       ", MG =", bool(mg_invoice))
    #
    #                 rent_price = sum(rent_invoices.mapped('invoice_line_ids').mapped('price_unit'))
    #                 rs_price = sum(rs_invoice.invoice_line_ids.mapped('price_unit')) if rs_invoice else 0
    #                 sb_price = sum(sb_invoice.invoice_line_ids.mapped('price_unit')) if sb_invoice else 0
    #                 mg_price = sum(mg_invoice.invoice_line_ids.mapped('price_unit')) if mg_invoice else 0
    #                 # print(f"Rent Price: {rent_price}, RS Price: {rs_price}, SB Price: {sb_price}, MG Price: {mg_price}")
    #                 msg = ""
    #                 if invoice.nhcl_invoice_type == 'rent':
    #                     invoice_type = invoice.tenancy_id.invoice_type
    #                     # print("Invoice type from tenancy:", invoice_type)
    #                     if invoice_type == 'rs':
    #                         if invoice.rs_amount == 0:
    #                             msg = "RS Amount is not given"
    #                     elif invoice_type == 'mg':
    #                         if invoice.mg_amount == 0:
    #                             msg = "MG Amount is not given"
    #                     elif invoice_type == 'slb':
    #                         if invoice.slab_amount == 0:
    #                             msg = "Slab Amount is not given"
    #                     elif invoice_type == 'rs_or_mg':
    #                         if invoice.rs_amount == 0:
    #                             msg = "RS Amount is not given"
    #                         elif invoice.mg_amount == 0:
    #                             msg = "MG Amount is not given"
    #                     if msg:
    #                         # print("Validation failed:", msg)
    #                         raise UserError(_(msg))
    #
    #                     # Compare rent price with RS/SB/MG
    #                     if rent_price < rs_price:
    #                         raise UserError(_(f"Rent amount ({rent_price}) is less than RS amount ({rs_price})"))
    #                     if rent_price < sb_price:
    #                         raise UserError(_(f"Rent amount ({rent_price}) is less than SB amount ({sb_price})"))
    #                     if rent_price < mg_price:
    #                         raise UserError(_(f"Rent amount ({rent_price}) is less than MG amount ({mg_price})"))
    #
    #                 # ✅ 🔒 ADDITIONAL VALIDATION for RS month & comparison match
    #                 elif invoice.nhcl_invoice_type == 'rs':
    #                     # print("ntered")
    #                     related_rent_invoice = self.env['account.move'].search([
    #                         ('tenancy_id', '=', invoice.tenancy_id.id),
    #                         ('nhcl_invoice_type', '=', 'rent'),
    #                         ('comparision_yr_mnth', '=', invoice.comparision_yr_mnth.id),
    #                         ('move_type', '=', 'out_invoice'),
    #                         ('state', '!=', 'cancel'),
    #                     ], limit=1)
    #                     # print("related",related_rent_invoice)
    #
    #                     if related_rent_invoice:
    #                         # print("related")
    #                         rent_month = related_rent_invoice.comparision_yr_mnth
    #                         rs_month = invoice.comparision_yr_mnth
    #                         # print(rs_month.name,"rs_month")
    #                         # print(rent_month.name,"invoice.months")
    #                         if rent_month != rs_month:
    #                             raise UserError(_(
    #                                 f"The RS invoice month '{rs_month}' does not match the Rent invoice month '{rent_month}' "
    #                                 f"for comparison period {invoice.comparision_yr_mnth.name}."
    #                             ))
    #                     else:
    #                         raise ValidationError('please change the  comparison month')
    #
    #                     if rs_price < rent_price:
    #                         raise UserError(_(f"RS amount ({rs_price}) is less than Rent amount ({rent_price})"))
    #
    #                 elif invoice.nhcl_invoice_type == 'mg' and mg_price < rent_price:
    #                     raise UserError(_(f"MG amount ({mg_price}) is less than Rent amount ({rent_price})"))
    #                 elif invoice.nhcl_invoice_type == 'slb' and sb_price < rent_price:
    #                     raise UserError(_(f"SB amount ({sb_price}) is less than Rent amount ({rent_price})"))
    #
    #                 # print("All validations passed.")
    #
    #         for invoice in self:
    #             if invoice.name in [False, '/']:
    #
    #                 # invoice_date = date.today()
    #                 #
    #                 # if invoice_date.month < 4:
    #                 #     fy_start = invoice_date.year - 1
    #                 # else:
    #                 #     fy_start = invoice_date.year
    #                 #
    #                 # fy_code = f"{str(fy_start)[-2:]}{str(fy_start + 1)[-2:]}"  # e.g., '2526'
    #                 # type_inv = invoice.nhcl_invoice_type
    #                 # invoice_number = invoice._generate_invoice_number(type_inv, fy_code)
    #                 # invoice.name = invoice_number
    #                 # invoice.payment_reference = invoice_number
    #                 # Map selection keys to month numbers for comparison
    #                 month_order = {
    #                     'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    #                     'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
    #                     'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    #                 }
    #
    #                 for invoice in self:
    #                     existing_invoice = self.env['account.move'].search([
    #                         ('id', '!=', invoice.id),
    #                         ('partner_id', '=', invoice.partner_id.id),
    #                         ('nhcl_invoice_type', '=', invoice.nhcl_invoice_type),
    #                         ('move_type', '=', 'out_invoice'),
    #                         ('state', '=', 'posted'),
    #                         ('billing_from', '=', invoice.billing_from),
    #                     ], limit=1)
    #
    #                     if existing_invoice:
    #                         raise ValidationError(
    #                             "An invoice is already posted for this customer for the selected Billing From period."
    #                         )
    #                     # print('satisfied')
    #                     if invoice.months and invoice.move_type == 'out_invoice':
    #                         # print('comming inside ///')
    #                         inv_month_num = month_order[invoice.months]
    #
    #                         # Search all draft invoices for same tenant + type + company
    #                         draft_invoices = self.env['account.move'].search([
    #                             ('id', '!=', invoice.id),
    #                             ('partner_id', '=', invoice.partner_id.id),
    #                             ('nhcl_invoice_type', '=', invoice.nhcl_invoice_type),
    #                             ('move_type', '=', 'out_invoice'),
    #                             ('state', '=', 'draft'),
    #                         ], order="create_date desc", limit=1)
    #                         # print(draft_invoices)
    #
    #                         for draft in draft_invoices:
    #                             # print('comming draft ///')
    #                             if draft.months and draft.nhcl_invoice_type not in ['rs', 'rent']:
    #                                 draft_month_num = month_order[draft.months]
    #                                 # print(draft_month_num, "////", inv_month_num)
    #                                 if draft_month_num < inv_month_num:
    #                                     # print(draft.name)
    #                                     raise UserError(_(
    #                                         f"You cannot post this invoice because another draft entry "
    #                                         f" exists for {dict(draft._fields['months'].selection).get(draft.months)} "
    #                                         f"which is after {dict(invoice._fields['months'].selection).get(invoice.months)} "
    #                                         f"for customer {invoice.partner_id.display_name}."
    #                                     ))
    #                 invoice_date = date.today()
    #
    #                 if invoice_date.month < 4:
    #                     fy_start = invoice_date.year - 1
    #                 else:
    #                     fy_start = invoice_date.year
    #
    #                 fy_code = f"{str(fy_start)[-2:]}{str(fy_start + 1)[-2:]}"  # e.g., '2526'
    #                 type_inv = invoice.nhcl_invoice_type
    #                 invoice_number = invoice._generate_invoice_number(type_inv, fy_code)
    #                 invoice.name = invoice_number
    #                 invoice.payment_reference = invoice_number
    #
    #         res = super(AccountMove, self).action_post()
    #
    #         # print("action_post finished for:", self.name)
    #         return res

    def rounding_total(self):
        for rec in self:
            if rec.amount_total:
                decimal_part = round(rec.amount_total % 1, 2)

                if decimal_part >= 0.51:
                    rounding = self.env['account.cash.rounding'].search(
                        [('name', '=', 'Half Up')], limit=1
                    )
                else:
                    rounding = self.env['account.cash.rounding'].search(
                        [('name', '=', 'DOWN')], limit=1
                    )

                rec.invoice_cash_rounding_id = rounding.id if rounding else False
    def action_post(self):
        for invoice in self:
                if invoice.move_type != 'out_invoice':
                    continue
                # Get latest tenancy for this tenant
                tenancy = invoice.env['tenancy.details'].search(
                    [('tenancy_id', '=', invoice.partner_id.id)],
                    order='id desc',
                    limit=1
                )
                if not tenancy:
                    raise ValidationError(_("No tenancy found for this tenant."))

                if tenancy.contract_type == 'expire_contract':
                    raise ValidationError(_("You can't confirm because the tenancy has expired."))

                if not tenancy.active_contract_state:
                    raise ValidationError(_("You can't confirm because the tenancy is not active."))

                if invoice.nhcl_invoice_type == 'rs' and not invoice.comparision_yr_mnth:
                    raise ValidationError(_("You need to add the Comparison month."))

                # Electric-specific logic
                if invoice.nhcl_invoice_type == 'electric' and invoice.invoice_date:
                    category_bills = self.env['catagory.bill'].search([
                        ('ten', '=', invoice.partner_id.id),
                        ('months', '=', invoice.months),
                        ('is_invoice_created', '=', False),
                    ])

                    category_bills.write({'is_invoice_created': True})

                # Skip rent validation if context flag is set
                if self.env.context.get('skip_rent_validation'):
                    continue

                # Validation logic for rent vs RS/MG/SLB
                if invoice.move_type == 'out_invoice' and invoice.tenancy_id:
                    # print("Validating RS/MG vs Rent comparison...")
                    rent_invoices = self.env['account.move'].search([
                        ('tenancy_id', '=', invoice.tenancy_id.id),
                        ('nhcl_invoice_type', '=', 'rent'),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '!=', 'cancel'),
                        ('comparision_yr_mnth', '=', invoice.comparision_yr_mnth.id),
                    ])
                    rs_invoice = self.env['account.move'].search([
                        ('tenancy_id', '=', invoice.tenancy_id.id),
                        ('nhcl_invoice_type', '=', 'rs'),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '!=', 'cancel'),
                    ], limit=1)
                    sb_invoice = self.env['account.move'].search([
                        ('tenancy_id', '=', invoice.tenancy_id.id),
                        ('nhcl_invoice_type', '=', 'slb'),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '!=', 'cancel'),
                    ], limit=1)
                    mg_invoice = self.env['account.move'].search([
                        ('tenancy_id', '=', invoice.tenancy_id.id),
                        ('nhcl_invoice_type', '=', 'mg'),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '!=', 'cancel'),
                    ], limit=1)
                    rent_price = sum(rent_invoices.mapped('invoice_line_ids').mapped('price_unit'))
                    rs_price = sum(rs_invoice.invoice_line_ids.mapped('price_unit')) if rs_invoice else 0
                    sb_price = sum(sb_invoice.invoice_line_ids.mapped('price_unit')) if sb_invoice else 0
                    mg_price = sum(mg_invoice.invoice_line_ids.mapped('price_unit')) if mg_invoice else 0
                    msg = ""
                    if invoice.nhcl_invoice_type == 'rent':
                        invoice_type = False
                        commercial_term = self.env['commerce.term.term'].search([
                            ('tenacy_id', '=', invoice.tenancy_id.id),
                            ('start_date', '<=', invoice.invoice_date),
                            ('end_date', '>=', invoice.invoice_date),
                        ], limit=1)
                        if commercial_term:
                            invoice_type = commercial_term.rent_type
                        if invoice_type == 'rs':
                            if invoice.rs_amount == 0:
                                msg = "RS Amount is not given"
                        elif invoice_type == 'mg':
                            if invoice.mg_amount == 0:
                                msg = "MG Amount is not given"
                        elif invoice_type == 'slb':
                            if invoice.slab_amount == 0:
                                msg = "Slab Amount is not given"
                        elif invoice_type == 'rs_or_mg':
                            if invoice.rs_amount == 0:
                                msg = "RS Amount is not given"
                            elif invoice.mg_amount == 0:
                                msg = "MG Amount is not given"
                        if msg:
                            # print("Validation failed:", msg)
                            raise UserError(_(msg))

                        # Compare rent price with RS/SB/MG
                        if rent_price < rs_price:
                            raise UserError(_(f"Rent amount ({rent_price}) is less than RS amount ({rs_price})"))
                        if rent_price < sb_price:
                            raise UserError(_(f"Rent amount ({rent_price}) is less than SB amount ({sb_price})"))
                        if rent_price < mg_price:
                            raise UserError(_(f"Rent amount ({rent_price}) is less than MG amount ({mg_price})"))
                    # ✅ 🔒 ADDITIONAL VALIDATION for RS month & comparison match
                    elif invoice.nhcl_invoice_type == 'rs':
                        # print("ntered")
                        related_rent_invoice = self.env['account.move'].search([
                            ('tenancy_id', '=', invoice.tenancy_id.id),
                            ('nhcl_invoice_type', '=', 'rent'),
                            ('comparision_yr_mnth', '=', invoice.comparision_yr_mnth.id),
                            ('move_type', '=', 'out_invoice'),
                            ('state', '!=', 'cancel'),
                        ], limit=1)
                        # print("related",related_rent_invoice)

                        if related_rent_invoice:
                            # print("related")
                            rent_month = related_rent_invoice.comparision_yr_mnth
                            rs_month = invoice.comparision_yr_mnth
                            # print(rs_month.name,"rs_month")
                            # print(rent_month.name,"invoice.months")
                            if rent_month != rs_month:
                                raise UserError(_(
                                    f"The RS invoice month '{rs_month}' does not match the Rent invoice month '{rent_month}' "
                                    f"for comparison period {invoice.comparision_yr_mnth.name}."
                                ))
                        else:
                            raise ValidationError('please change the  comparison month')

                        if rs_price < rent_price:
                            raise UserError(_(f"RS amount ({rs_price}) is less than Rent amount ({rent_price})"))
                    elif invoice.nhcl_invoice_type == 'mg' and mg_price < rent_price:
                        raise UserError(_(f"MG amount ({mg_price}) is less than Rent amount ({rent_price})"))
                    elif invoice.nhcl_invoice_type == 'slb' and sb_price < rent_price:
                        raise UserError(_(f"SB amount ({sb_price}) is less than Rent amount ({rent_price})"))
                    if invoice.name in [False, '/']:
                        month_order = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        existing_invoice = self.env['account.move'].search([
                            ('id', '!=', invoice.id),
                            ('partner_id', '=', invoice.partner_id.id),
                            ('nhcl_invoice_type', '=', invoice.nhcl_invoice_type),
                            ('move_type', '=', 'out_invoice'),
                            ('state', '=', 'posted'),
                            ('billing_from', '=', invoice.billing_from),
                        ], limit=1)
                        if existing_invoice:
                            raise ValidationError(
                                _("An invoice is already posted for this customer for the selected Billing From period.")
                            )
                        if invoice.months and invoice.move_type == 'out_invoice':
                            inv_month_num = month_order[invoice.months]
                            draft_invoices = self.env['account.move'].search([
                                ('id', '!=', invoice.id),
                                ('partner_id', '=', invoice.partner_id.id),
                                ('nhcl_invoice_type', '=', invoice.nhcl_invoice_type),
                                ('move_type', '=', 'out_invoice'),
                                ('state', '=', 'draft'),
                            ], order="create_date desc", limit=1)
                            for draft in draft_invoices:
                                if draft.months and draft.nhcl_invoice_type not in ['rs', 'rent']:
                                    draft_month_num = month_order[draft.months]

                                    if draft_month_num < inv_month_num:
                                        raise UserError(_(
                                            f"You cannot post this invoice because another draft entry "
                                            f"exists for {dict(draft._fields['months'].selection).get(draft.months)} "
                                            f"which is after {dict(invoice._fields['months'].selection).get(invoice.months)} "
                                            f"for customer {invoice.partner_id.display_name}."
                                        ))
                        invoice_date = date.today()
                        if invoice_date.month < 4:
                            fy_start = invoice_date.year - 1
                        else:
                            fy_start = invoice_date.year
                        fy_code = f"{str(fy_start)[-2:]}{str(fy_start + 1)[-2:]}"
                        type_inv = invoice.nhcl_invoice_type
                        invoice_number = invoice._generate_invoice_number(type_inv, fy_code)
                        invoice.name = invoice_number
                        invoice.payment_reference = invoice_number
        # res = super(AccountMove, self).action_post()
        invoice.rounding_total()
        res = super().action_post()
            # print("action_post finished for:", self.name)
        return res
    # @api.constrains('billing_to', 'invoice_date', 'partner_id')
    # def _check_billing_period_with_tenancy(self):
    #     for rec in self:
    #         if not rec.partner_id:
    #             continue
    #         # 🔍 Get tenancy
    #         tenancy = self.env['tenancy.details'].search([
    #             ('tenancy_id', '=', rec.partner_id.id)
    #         ], limit=1)
    #         if not tenancy or not tenancy.end_date:
    #             continue
    #         # ✅ Priority logic
    #         if rec.billing_to:
    #             check_date = rec.billing_to
    #         elif rec.invoice_date:
    #             check_date = rec.invoice_date
    #         else:
    #             continue  # nothing to validate
    #         # 🚫 Validation
    #         if check_date > tenancy.end_date:
    #             raise ValidationError(
    #                 "Selected date (%s) exceeds Tenant End Date (%s)"
    #                 % (check_date, tenancy.end_date)
    #             )

    @api.constrains('billing_from', 'billing_to', 'invoice_date', 'partner_id')
    def _check_billing_period_with_tenancy(self):
        errors = []
        for rec in self:
            if not rec.partner_id:
                continue
            # 🔍 Get tenancy
            tenancy = self.env['tenancy.details'].search([
                ('tenancy_id', '=', rec.partner_id.id)
            ], order="id DESC", limit=1)
            if not tenancy or not tenancy.start_date or not tenancy.end_date:
                continue
            tenant_name = rec.partner_id.name
            # ✅ For billing-based invoice types
            if rec.nhcl_invoice_type in ['rent', 'cam', 'soh', 'mpc', 'water', 'Hvac', 'slb', 'mg_or']:
                billing_from = rec.billing_from
                billing_to = rec.billing_to
                if not billing_from or not billing_to:
                    continue
                # 🚫 Billing From < Tenancy Start Date
                if billing_from < tenancy.start_date:
                    errors.append(
                        "Tenant: %s \nBilling From (%s) is before Tenancy Start Date (%s)"
                        % (tenant_name, billing_from, tenancy.start_date)
                    )
                # 🚫 Billing To > Tenancy End Date
                if billing_to > tenancy.end_date:
                    errors.append(
                        "Tenant: %s \nBilling To (%s) exceeds Tenancy End Date (%s)"
                        % (tenant_name, billing_to, tenancy.end_date)
                    )
            # ✅ For other invoice types (invoice_date validation)
            else:
                check_date = rec.invoice_date
                if not check_date:
                    continue
                if check_date < tenancy.start_date or check_date > tenancy.end_date:
                    errors.append(
                        "Tenant: %s \nSelected Date (%s) is outside Tenancy Period (%s to %s)"
                        % (tenant_name, check_date, tenancy.start_date, tenancy.end_date)
                    )

        # 🚨 Raise all errors at once
        if errors:
            raise ValidationError("\n\n".join(errors))



    """
    def write(self, vals):
        # Prevent recursive write calls if name or payment_reference are being updated
        for demo in self:
            billing_from = fields.Date.from_string(vals.get('billing_from', demo.billing_from))
            nhcl_invoice_type = vals.get('nhcl_invoice_type', demo.nhcl_invoice_type)
            if billing_from and nhcl_invoice_type in ['rent', 'cam']:
                vals['months'] = billing_from.strftime('%b').lower()
        # if 'name' not in vals and 'payment_reference' not in vals:
        #     # Call the parent write method
            res = super(AccountMove, self).write(vals)
            # invoice_date = fields.Date.from_string(vals.get('date')) if vals.get('date') else date.today()
            #
            # # Calculate financial year: 2025 → 2526
            # if invoice_date.month < 4:
            #     fy_start = invoice_date.year - 1
            # else:
            #     fy_start = invoice_date.year
            #
            # fy_code = f"{str(fy_start)[-2:]}{str(fy_start + 1)[-2:]}"  # e.g., '2526'
            # print(fy_code)
            # for record in self:
                # if not record.name or record.name == '/':
                #     type_inv = record.nhcl_invoice_type
                #     invoice_number = record._generate_invoice_number(type_inv, fy_code)
                #
                #     # Assign generated invoice number
                #     record.name = invoice_number
                #     record.payment_reference = invoice_number
            if vals.get('nhcl_invoice_type') == 'electric' or 'partner_id' in vals:
                    demo._generate_electric_lines()

            return res

        # Fall back to default write if `name` or `payment_reference` is explicitly being set
        return super(AccountMove, self).write(vals)
    """

    def _generate_invoice_number(self, invoice_type, fy_code):
        year = fields.Date.today().year  # Current year
        sequence_code = None
        if invoice_type in ['rent','rs']:
            sequence = self.env['ir.sequence'].with_context(fy=fy_code).next_by_code('invoice.rent.sequence')
            # sequence_code = 'invoice.rent.sequence'
            return sequence
        elif invoice_type == 'cam':
            # sequence_code = 'invoice.cam.sequence'
            sequence = self.env['ir.sequence'].with_context(fy=fy_code).next_by_code('invoice.cam.sequence')
            return sequence
        elif invoice_type == 'electric':
            # sequence_code = 'electric.invoice.sequence'
            sequence = self.env['ir.sequence'].with_context(fy=fy_code).next_by_code('electric.invoice.sequence')
            return sequence
        elif invoice_type == 'gas':
            # sequence_code = 'gas.invoice.sequence'
            sequence = self.env['ir.sequence'].with_context(fy=fy_code).next_by_code('gas.invoice.sequence')
            return sequence
        elif invoice_type == 'marketing':
            sequence_code = 'marketing.invoice.sequence'
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            return sequence
        elif invoice_type == 'advanced':
            sequence_code = 'advanced.invoice.sequence'
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            return sequence
        elif invoice_type == 'regular':
            sequence_code = 'account.invoice.sequence'
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            return sequence
        elif invoice_type == 'signage':
            sequence = self.env['ir.sequence'].with_context(fy=fy_code).next_by_code('Signage.invoice.sequence')
            return sequence
        # elif invoice_type == 'rs':
        #     sequence_code = 'rs.invoice.sequence'
        #     sequence = self.env['ir.sequence'].next_by_code(sequence_code)
        #     return sequence
        elif invoice_type == 'mg_or':
            sequence_code = 'mg.rs.invoice.sequence'
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            return sequence
        elif invoice_type == 'adv_cam_fee':
            sequence_code = 'invoice.add.cam.sequence'
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            return sequence
            # print(sequence_code)
        elif invoice_type == 'slb':
            sequence_code = 'sb.invoice.sequence'
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            return sequence

        sequence = self.env['ir.sequence'].next_by_code(sequence_code) or '00001'
        # print(sequence)
        return f"{sequence}"

    def get_and_update_invoice_data(self):
        today = fields.Date.today()
        ten_rec = self.env['tenancy.details'].search(
            [('contract_type', '=', 'running_contract'), ('is_partial_month', '=', True)],
            order='tenancy_seq ASC')
        # print(ten_rec, "did not find any record ........")

        for rec in ten_rec:

            print(rec.tenancy_seq)
            c = 0
            for val in rec.year_ids:
                print('val.is_invoice_generated',val.is_invoice_generated,'val.end_year == today',val.end_year , today)

                if val.end_year == today and not val.is_invoice_generated:
                    print('llll')

                    # 🔽 First invoice
                    invoice_vals_1 = {
                        'partner_id': rec.tenancy_id.id,
                        'move_type': 'out_invoice',
                        'invoice_date': today,
                        'nhcl_invoice_type': 'rent',
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.env.ref('rental_management.property_product_1').id,
                            'name': 'Property Value ',
                            'quantity': 1,
                            'price_unit': 0,
                            'nhcl_area_units': rec.carpet_area if rec.carpet_value_take else rec.chargeable_area
                        })],
                    }
                    # print(invoice_vals_1)
                    invoice_1 = self.env['account.move'].sudo().create(invoice_vals_1)
                    invoice_1.tenancy_id = rec.id
                    invoice_1.tenancy_id = rec.id

                    # 🔽 Second invoice
                    invoice_vals_2 = {
                        'partner_id': rec.tenancy_id.id,
                        'move_type': 'out_invoice',
                        'invoice_date': today,
                        'nhcl_invoice_type': 'rent',
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.env.ref('rental_management.property_product_1').id,
                            'name': 'Property Value ',
                            'quantity': 1,
                            'price_unit': 0,
                            'nhcl_area_units': rec.carpet_area if rec.carpet_value_take else rec.chargeable_area
                        })],
                    }

                    invoice_2 = self.env['account.move'].sudo().create(invoice_vals_2)
                    invoice_2.tenancy_id = rec.id
                    # ✅ Prevent reprocessing
                    val.is_invoice_generated = True
                c += 1
        self.get_and_update_cam_invoice_data()

        return True

    def get_and_update_cam_invoice_data(self):
        # print('calling cam creation ???????????????')
        today = fields.Date.today()
        # Step 1: Find tenancy records with CAM Year lines ending today
        ten_cam = self.env['tenancy.details'].search([
            ('contract_type', '=', 'running_contract'),
            ('is_partial_month', '=', True),
            ('cam_year_ids.cam_end_year', '=', today)
        ])
        # print(ten_cam)

        for rec in ten_cam:
            # print('getting data')
            for cam_line in rec.cam_year_ids:
                nhcl_area_units = None
                if rec.use_carpet:
                    nhcl_area_units = rec.cam_carpet_area
                elif rec.use_chargeable:
                    nhcl_area_units = rec.cam_chargeable_area
                else:
                    nhcl_area_units = '-'
                if cam_line.cam_end_year == today:
                    # Optional: Skip if invoice already generated
                    if getattr(cam_line, 'is_invoice_generated', False):
                        continue

                    # Step 2: Prepare invoice line for CAM
                    cam_invoice_vals = {
                        'partner_id': rec.tenancy_id.id,
                        'move_type': 'out_invoice',
                        'invoice_date': today,
                        'nhcl_invoice_type': 'cam',
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.env['product.product'].search([('name', '=', 'Cam Maintenance')],
                                                                             limit=1).id,
                            # Replace with actual external ID
                            'name': f'CAM Charges Renewal on {today}',
                            'quantity': 1,
                            'price_unit': cam_line.cam_amount or 0.0,
                            'nhcl_area_units': nhcl_area_units#rec.chargeable_area
                        })],
                    }

                    cam_invoice = self.env['account.move'].sudo().create(cam_invoice_vals)
                    cam_invoice.tenancy_id = rec.id
                    # print('created sucessfull created')

                    # this is for the secound invoice creation
                    sec_invoice_vals = {
                        'partner_id': rec.tenancy_id.id,
                        'move_type': 'out_invoice',
                        'invoice_date': today,
                        'nhcl_invoice_type': 'cam',
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.env['product.product'].search([('name', '=', 'Cam Maintenance')],
                                                                             limit=1).id,
                            'name': f'CAM Charges Renewal on {today}',
                            'quantity': 1,
                            'price_unit': cam_line.cam_amount or 0.0,
                            'nhcl_area_units': nhcl_area_units
                        })],
                    }
                    sec_invoice = self.env['account.move'].sudo().create(sec_invoice_vals)
                    sec_invoice.tenancy_id = rec.id

                    # Step 3: Mark invoice generated
                    cam_line.is_invoice_generated = True
        return True

    @api.onchange('nhcl_invoice_type', 'billing_from')
    def _onchange_nhcl_invoice_type(self):
        journal_map = {
            'rent': 'Customer Invoices',
            'mg_or': 'Customer Invoices',
            'prs': 'Customer Invoices',
            'water': 'WB-Receipt',
            'electric': 'EB',
            'cam': 'CAM Invoices',
            'Hvac': 'HVAC',
            'soh': 'SOH',
            'mpc': 'Mall Promotion',
            'gas': 'GAS' ,
            'signage': 'Signage',
        }

        for rec in self:
            if rec.nhcl_invoice_type:
                journal_name = journal_map.get(rec.nhcl_invoice_type)

                if journal_name:
                    journal = self.env['account.journal'].search(
                        [('name', '=', journal_name)],
                        limit=1
                    )
                    rec.journal_id = journal.id if journal else False

    # @api.model
    # def _apply_delta_recurring_entries(self, date, date_origin, period):
    #     """
    #     Calculates the next recurring date based on the given period.
    #     Adds one month by default to the result from the super method.
    #     """
    #     next_date = super(self)._apply_delta_recurring_entries(date, date_origin, period)
    #     # print("Original next_date from parent:", next_date)
    #
    #     # Optional adjustment
    #     # next_date = next_date + relativedelta(months=1)
    #     return next_date

    def _copy_recurring_entries(self):

        for record in self:

            record.auto_post_origin_id = (
                    record.auto_post_origin_id or record
            )

            # Use Odoo's original recurring-date calculation
            next_date = record._apply_delta_recurring_entries(
                record.date,
                record.auto_post_origin_id.date,
                record.auto_post,
            )

            print("Current Date:", record.date)
            print("Next Date:", next_date)

            # Stop if beyond auto-post limit
            if record.auto_post_until and next_date > record.auto_post_until:
                continue

            # -----------------------------------------
            # Check renewal month
            # -----------------------------------------
            renewal_in_same_month = any(
                renewal.end_year
                and renewal.end_year.month == next_date.month
                and renewal.end_year.year == next_date.year
                for renewal in record.tenancy_id.year_ids
            )

            print("Renewal Month:", renewal_in_same_month)

            # -----------------------------------------
            # Skip invoice creation in renewal month
            # -----------------------------------------
            if (
                    record.tenancy_id.is_partial_month
                    and record.nhcl_invoice_type == 'rent'
                    and renewal_in_same_month
            ):
                print(
                    "Skipping invoice because this is renewal month:",
                    next_date.strftime("%B %Y")
                )
                continue

            # -----------------------------------------
            # Next billing period
            # -----------------------------------------
            new_billing_from = (
                    record.billing_from + relativedelta(months=1, day=1)
            )

            new_billing_to = (
                    new_billing_from + relativedelta(day=31)
            )

            # -----------------------------------------
            # Create recurring invoice
            # -----------------------------------------
            record.copy(
                default=record._get_fields_to_copy_recurring_entries({
                    'date': next_date,
                    'nhcl_invoice_type': record.nhcl_invoice_type,
                    'rs_amount': 0.00,
                    'comparision_yr_mnth': '',
                    'billing_from': new_billing_from,
                    'billing_to': new_billing_to,
                })
            )

    # def _copy_recurring_entries(self):
    #     """
    #     Custom recurring entry logic:
    #     - Skips auto-posting in the renewal month.
    #     - Resumes posting in following months.
    #     """
    #     for record in self:
    #         # print(record.tenancy_id.year_ids)
    #
    #         record.auto_post_origin_id = record.auto_post_origin_id or record
    #
    #         # Calculate the next posting date
    #         next_date = self._apply_delta_recurring_entries(
    #             record.date, record.auto_post_origin_id.date, record.auto_post
    #         )
    #         for data in record.tenancy_id.year_ids:
    #             if data.end_year.month == next_date.month and data.end_year.year == next_date.year:
    #                 print('Doneeeeeeeeeeeeeeeeeeee')
    #
    #         # Stop if beyond the auto-post limit
    #         if record.auto_post_until and next_date > record.auto_post_until:
    #             continue
    #
    #         # Skip posting if renewal starts this month
    #         renewal_in_same_month = any(
    #             renewal.end_year.month == (next_date.month - 1) and
    #             renewal.end_year.year == next_date.year
    #             for renewal in record.tenancy_id.year_ids
    #         )
    #         new_billing_from = record.billing_from + relativedelta(months=1, day=1)
    #         new_billing_to = new_billing_from + relativedelta(day=31)
    #         # print("///////", renewal_in_same_month)
    #         if record.tenancy_id.is_partial_month and record.nhcl_invoice_type == 'rent':
    #             if renewal_in_same_month:
    #                 # print(f"Skipping auto-posting for {record.name} in renewal month: {next_date.strftime('%B %Y')}")
    #                 continue  # Skip this month's posting
    #
    #         # Otherwise, copy with updated date
    #         # record.copy(default=record._get_fields_to_copy_recurring_entries({'date': next_date}))
    #         record.copy(default=record._get_fields_to_copy_recurring_entries({
    #             'date': next_date,
    #             'nhcl_invoice_type': record.nhcl_invoice_type,
    #             'rs_amount':0.00,
    #             'comparision_yr_mnth':'',
    #             'billing_from': new_billing_from,
    #             'billing_to': new_billing_to,
    #         }))
    #         # print(f"Processed recurring entry for {record.name} with new date {next_date}")

    @api.model
    def default_get(self, fields_list):
        # res = super(AccountMove, self).default_get(fields_list)
        res = super().default_get(fields_list)
        try:
            # Replace this with the actual external ID for Andhra Pradesh
            default_state = self.env.ref('base.state_in_ap')  # Andhra Pradesh
            if default_state:
                res['l10n_in_state_id'] = default_state.id
        except ValueError:
            pass  # In case the external ID is missing or not installed
        return res

    def action_update_commercial_terms(self):
        for move in self:
            if not move.tenancy_id:
                raise UserError(_("No Tenancy found on this invoice."))

            if not move.billing_from or not move.billing_to:
                raise UserError(_("Billing From and Billing To must be filled."))

            term = self.env['commerce.term.term'].search([
                ('tenacy_id', '=', move.tenancy_id.id),
                ('start_date', '<=', move.billing_from),
                ('end_date', '>=', move.billing_to),
                ('rent_type', '=', move.nhcl_invoice_type),
            ], limit=1)

            if not term:
                raise UserError(_("No Commercial Term found for this billing period."))

            if move.nhcl_invoice_type == 'rs':
                vals = {
                    'percentage': term.revenue,
                    'net_rent': term.min_guarantee_rate,
                }
            else:
                vals = {
                    'product_id': self.env.ref('rental_management.property_product_rs').id,
                    'mg_percentage': term.revenue,
                    'mg_carpet': term.min_guarantee_rate,
                }

            move.invoice_line_ids.write(vals)
            move.invoice_line_ids[0]._onchange_price_unit()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    opening_reading = fields.Float(string='Opening Reading', digits=(16, 4))
    closing_reading = fields.Float(string='Closing Reading', digits=(16, 4))
    consumption = fields.Float(string="Consumption", store=True,default=0)
    consumed_units = fields.Float(string='Consumed Units', digits=(16, 4), compute='consumption_unit', store=True)
    nhcl_area_units = fields.Char(string='Area Units',default="-")
    rate = fields.Float(string='Rate', digits=(0, 4))
    multiplying_factor = fields.Float(string='Multiplying Factor', digits=(0, 4), store=True)
    description2 = fields.Char(string='Product',default='')
    net_rent = fields.Float(string='Net Sales', digits=(0, 4))
    percentage = fields.Float(string='RS Percentage')
    mg_carpet = fields.Integer(string='Mg Carpet')
    mg_percentage = fields.Integer(string='Mg Percentage')

    price_unit = fields.Float(compute='_compute_price_unit', store=True)
    net_slab = fields.Float(string='Slab Rent')
    percentage_slab = fields.Float(string='Slab Percentage')
    tax_cal=fields.Float(string='Tax Cal',compute='_compute_price_unit_test', store=True)

    # @api.depends('price_unit','price_total')
    # def _compute_price_unit_test(self):
    #     for rec in self:
    #         print('calling......dsfahfyheruyhety')
    #         if rec.tax_ids[0].amount_type == 'group':
    #             print('pass')

    # @api.depends('price_unit', 'price_total', 'tax_ids')
    # def _compute_price_unit_test(self):
    #     for rec in self:
    #         if rec.tax_ids:
    #             if rec.tax_ids[0].amount_type == 'group':
    #                 tax_amount = rec.price_total - rec.price_subtotal
    #                 print(tax_amount,'llllllllllllllll')
    #
    #                 print('amount_residual',rec.amount_residual)
    #                 print('price_subtotal',rec.price_subtotal)
    #                 # rec.tax_cal=rec.amount_residual-rec.price_subtotal
    #                 rec.tax_cal = round(rec.price_total - rec.price_subtotal, 2)
    #
    #                 print(rec.tax_cal,round(rec.tax_cal,2))
    @api.depends('price_unit', 'price_total', 'price_subtotal', 'tax_ids')
    def _compute_price_unit_test(self):
        for rec in self:
            rec.tax_cal = 0.0

            if not rec.tax_ids:
                continue
            if rec.tax_ids[0].amount_type == 'group':
                if  'GST S'  in rec.tax_ids[0].name:
                    s = rec.tax_ids[0].name
                    k = s.find('%')
                    # print(s.find('%'))
                    # print(s[0:k])

                    total_tax = rec.price_subtotal * int(s[0:k])/100

                    # Divide into CGST + SGST
                    half_tax = total_tax / 2
                    # Custom rounding rule
                    decimal_part = round(half_tax - int(half_tax), 2)
                    if decimal_part >= 0.51:
                        rec.tax_cal = int(half_tax) + 1
                    else:
                        rec.tax_cal = int(half_tax)

                elif  'gst S'  in rec.tax_ids[0].name:
                        print('kkkkk')
                        s = rec.tax_ids[0].name
                        k = s.find('%')
                        # print(s.find('%'))
                        # print(s[0:k])

                        total_tax = rec.price_subtotal * int(s[0:k])/100

                        # Divide into CGST + SGST
                        half_tax = total_tax / 2
                        # Custom rounding rule
                        decimal_part = round(half_tax - int(half_tax), 2)
                        if decimal_part >= 0.51:
                            rec.tax_cal = int(half_tax) + 1
                        else:
                            rec.tax_cal = int(half_tax)
            else:
                        s = rec.tax_ids[0].name  # e.g., "18%"
                        k = s.find('%')

                        if k == -1:
                            raise ValueError(f"Invalid tax format: {s}")

                        # Extract numeric part of tax
                        try:
                            tax_rate = int(s[:k])
                        except ValueError:
                            raise ValueError(f"Cannot parse tax rate from: {s}")

                        # Calculate total tax
                        total_tax = rec.price_subtotal * tax_rate / 100

                        # Round based on decimal part
                        decimal_part = total_tax - int(total_tax)
                        if decimal_part >= 0.51:
                            rec.tax_cal = int(total_tax) + 1
                        else:
                            rec.tax_cal = int(total_tax)



    @api.depends('consumption', 'multiplying_factor')
    def consumption_unit(self):
        for rec in self:
            rec.consumed_units = rec.consumption * rec.multiplying_factor

    @api.depends('consumed_units', 'rate', 'move_id.nhcl_invoice_type', 'net_rent', 'percentage', 'net_slab',
                 'percentage_slab', 'mg_percentage', 'mg_carpet')
    def _compute_price_unit(self):
        for rec in self:
            # print('calling')
            if rec.move_id.nhcl_invoice_type in ['electric', 'gas']:
                rec.price_unit = rec.consumed_units * rec.rate
            elif rec.move_id.nhcl_invoice_type in ['rs']:
                rec.price_unit = (rec.net_rent * (rec.percentage or 0.0) / 100.0)
            elif rec.move_id.nhcl_invoice_type == 'mg':
                rec.price_unit = rec.mg_carpet + (rec.mg_carpet * rec.mg_percentage / 100)
            elif rec.move_id.nhcl_invoice_type in ['slb']:
                rec.price_unit = (rec.net_slab * (rec.percentage_slab or 0.0) / 100.0)#rec.net_slab +
            else:
                rec.price_unit = 0.0

    # @api.depends('opening_reading', 'closing_reading')
    # def _compute_consumption(self):
    #     for line in self:
    #         if line.closing_reading > line.opening_reading:
    #             line.consumption = (line.closing_reading - line.opening_reading)
    #         elif line.opening_reading >= line.closing_reading:
    #             # line.consumption = (line.closing_reading * 1000) - line.opening_reading
    #             line.closing_reading = (line.closing_reading * 1000)
    #             line.consumption = (line.closing_reading) - line.opening_reading
    #             print(line.consumption,'??????????????????????????jjjjjjjjjj')
    #         else:
    #             line.consumption = 0.0

    # @api.onchange('price_unit')
    # def _onchange_price_unit(self):
    #     print('price chnage happen')
    #     for line in self:
    #         move = line.move_id
    #         if move.tenancy_id:
    #             rent_invoice = self.env['account.move'].search([
    #                 ('nhcl_invoice_type', '=', 'rent'),
    #                 ('tenancy_id', '=', move.tenancy_id.id),
    #                 ('state', '!=', 'cancel'),
    #             ], limit=1)
    #             print(rent_invoice,rent_invoice.name)
    #
    #             # if rent_invoice:
    #             #     if move.nhcl_invoice_type == 'rs':
    #             #         rent_invoice.rs_amount = line.price_unit
    #             #     elif move.nhcl_invoice_type == 'mg':
    #             #         rent_invoice.mg_amount = line.price_unit
    #             #     elif move.nhcl_invoice_type == 'slb':
    #             #         rent_invoice.slab_amount = line.price_unit
    #
    #             if rent_invoice:
    #                 if move.nhcl_invoice_type == 'rs':
    #                     rent_invoice.rs_amount = line.price_unit
    #                 elif move.nhcl_invoice_type == 'mg':
    #                     rent_invoice.mg_amount = line.price_unit
    #                 elif move.nhcl_invoice_type == 'slb':
    #                     rent_invoice.slab_amount = line.price_unit
    # @api.depends('opening_reading', 'closing_reading')
    # def _compute_consumption(self):
    #     for line in self:
    #         if line.closing_reading > line.opening_reading and line.opening_reading > 0:
    #             line.consumption = (line.closing_reading - line.opening_reading) * 1000
    #         # elif line.opening_reading > line.closing_reading:
    #         #     # line.consumption = (line.closing_reading * 1000) - line.opening_reading
    #         #     line.closing_reading = (line.closing_reading * 1000)
    #         #     line.consumption = (line.closing_reading) - line.opening_reading
    #         else:
    #             line.consumption = (line.closing_reading) - line.opening_reading

    # @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id')
    # def _compute_totals(self):
    #     # Call the original method from the parent class
    #     super()._compute_totals()
    #
    #     # Apply rounding to price_subtotal
    #     for line in self:
    #         if line.display_type in ('product', 'cogs') and line.price_subtotal:
    #             line.price_subtotal = round(line.price_subtotal)
    #             line.price_unit = round(line.price_unit)




    @api.onchange('price_unit','move_id.months')
    def _onchange_price_unit(self):
        for line in self:
            move = line.move_id
            if move.tenancy_id:
                rent_invoices = self.env['account.move'].search([
                    ('nhcl_invoice_type', '=', 'rent'),
                    ('partner_id', '=', move.partner_id.id),
                    ('comparision_yr_mnth', '=', move.comparision_yr_mnth.id),
                    ('state', '!=', 'cancel'),
                ], order='id DESC') #it will reflect to the lastes rent invoice slab and rs amount
                # print("Found Rent Invoices:", rent_invoices.mapped('name'),rent_invoices.name)
                print(rent_invoices,"rent invoice id......")
                for rent_invoice in rent_invoices:
                    print(rent_invoice.id,rent_invoice.months,rent_invoice.name)
                    # if move.nhcl_invoice_type == 'rent':
                    #     print("self.months",move.months)
                    #     print("rent_invoice",rent_invoice.months)
                    #     move.months = rent_invoice.months

                    if move.nhcl_invoice_type == 'rs': #move.move_type == 'out_invoice' and move.comparision_yr_mnth

                        rent_invoice.rs_amount = line.price_unit
                        print( rent_invoice.months,rent_invoice.name)
                        move.months = rent_invoice.months
                        print("rent_invoice.rs_amount ", rent_invoice.rs_amount)
                    elif move.nhcl_invoice_type == 'mg':
                        rent_invoice.mg_amount = line.price_unit
                    elif move.nhcl_invoice_type == 'slb':
                        rent_invoice.slab_amount = line.price_unit
                        print(rent_invoice)
                        print(rent_invoice.slab_amount)

    @api.onchange('net_slab')
    def _onchange_net_slab(self):
        if not self.net_slab or not self.move_id.partner_id:
            return

        partner = self.move_id.partner_id

        # Get slab.master for the partner
        slab = self.env['slab.master'].search([('customer_id', '=', partner.id)], limit=1)
        if not slab:
            self.percentage_slab = 0.0
            raise ValidationError("No slab master defined for this customer.")

        # Find the matching slab line
        matching_line = slab.slab_line_ids.filtered(
            lambda line: line.from_slab <= self.net_slab <= line.to_slab
        )

        if matching_line:
            self.percentage_slab = matching_line[0].percentage
        else:
            self.percentage_slab = 0.0
            raise ValidationError("Net Slab does not fall under any defined slab range.")







# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Laxicon Solution (<http://www.laxicon.in>).
#
#    For Module Support : info@laxicon.in
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
import datetime
import json
import requests
import re
import logging
import pytz
from io import BytesIO
import qrcode
import base64

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    irn_no = fields.Char("IRN No.", readonly=True, copy=False)
    ack_no = fields.Char("Ack No.", readonly=True, copy=False)
    ack_date = fields.Datetime(string="Ack Dt", readonly=True, copy=False)
    signed_invoice = fields.Text("SignedInvoice", readonly=True, copy=False)

    ewb_no = fields.Char("EWB No.", readonly=True, copy=False)
    ewb_date = fields.Datetime("EWB Dt", readonly=True, copy=False)
    ewb_valid_till = fields.Datetime("EWB Valid Till", readonly=True, copy=False)

    cancel_reason = fields.Selection(
        [('1', 'Buyer cancels the order'), ('2', 'There are mistakes in the e-invoice'), ('3', 'Incorrect entries'),
         ('4', 'Duplicate entries')], string="Cancel IRN Reason", copy=False)
    cancel_remark = fields.Char(string="Cancel IRN Remark", copy=False)
    cancel_date = fields.Datetime(string="Cancel Date Time", copy=False)

    distance = fields.Integer(string="Distance")
    transportation_mode = fields.Selection([('1', 'Road'), ('2', 'Rail'), ('3', 'Air'), ('4', 'Ship')],
                                           string='Transportation Mode')
    transportation_id = fields.Many2one('res.partner', string="Transportor Name")
    transportation_gst = fields.Char(related="transportation_id.vat", string="Transportor GST")
    document_date = fields.Date(string="Transportation Document Date")
    document_no = fields.Char(string="Transportation Document No")
    vehical_no = fields.Char(string="Vehicle No")
    vehical_type = fields.Selection([('O', 'ODC'), ('R', 'Regular')], string='Vehicle Type')

    ship_b_no = fields.Char(string="Ship Bill Number")
    ship_b_dt = fields.Date(string="Ship Bill Date")
    ref_claim = fields.Selection([('Y', 'Yes'), ('N', 'No')], string="Refund Claim", default='N')
    is_indian_company = fields.Boolean(compute='_compute_is_indian_company',
                                       help="True if the company's country is India")
    qr_code = fields.Binary(string="QR Code", readonly=True, copy=False)

    @api.model
    def generate_qr_code(self, text):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_image = base64.b64encode(buffer.getvalue())

        return qr_code_image

    def _compute_is_indian_company(self):
        india_id = self.env.ref('base.in').id
        for move in self:
            move.is_indian_company = (
                move.company_id.country_id.id == india_id if move.company_id.country_id else False)

    def _save_e_invoice_request_json(self, operation, data):
        """Save the exact outbound JSON body on the current invoice."""
        self.ensure_one()
        json_content = data if isinstance(data, str) else json.dumps(data)
        invoice_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', self.name or str(self.id))
        timestamp = fields.Datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return self.env['ir.attachment'].create({
            'name': '%s_%s_request_%s.json' % (
                invoice_name,
                operation,
                timestamp,
            ),
            'type': 'binary',
            'datas': base64.b64encode(json_content.encode('utf-8')),
            'mimetype': 'application/json',
            'res_model': self._name,
            'res_id': self.id,
        })

    def _get_supply_type(self):
        supply_type = "B2B"
        if self.l10n_in_gst_treatment in ("overseas",
                                          "special_economic_zone") and self.partner_id.state_id != self.company_id.state_id:
            supply_type = self.l10n_in_gst_treatment == "overseas" and "EXPWP" or "SEZWP"
        elif self.l10n_in_gst_treatment in ("overseas", "special_economic_zone"):
            supply_type = self.l10n_in_gst_treatment == "overseas" and "EXPWOP" or "SEZWOP"
        elif self.l10n_in_gst_treatment == "deemed_export":
            supply_type = "DEXP"
        return supply_type

    def generate_json_data(self):
        final_data_dict = {
            "Version": "1.1",
            "TranDtls": self.TranDtls(),
            "DocDtls": self.DocDtls(),
            "SellerDtls": self.SellerDtls(),
            "BuyerDtls": self.BuyerDtls(),
            'DispDtls': self.DispDtls(),
            'ShipDtls': self.ShipDtls(),  # It's mandatory only when ShipDtls address is different from buyer details.
            "ItemList": self.ItemList(),
            "ValDtls": self.ValDtls(),
        }
        if self.partner_id.country_id != self.company_id.country_id:
            final_data_dict.update({'ExpDtls': self.ExpDtls})
        return final_data_dict

    def ExpDtls(self):
        return {
            "ShipBNo": self.ship_b_no or "",
            "ShipBDt": self.ship_b_dt.strftime("%d/%m/%Y") if self.ship_b_dt else "",
            "Port": self.port_id.port_code if self.port_id.port_code else "",
            "RefClm": self.ref_claim or "N",
            "ForCur": self.currency_id.name if self.currency_id else "",
            "CntCode": self.partner_id.country_id.code if self.partner_id.country_id else "",
        }




    def ewaybill_by_irn(self):
        company_id = self.company_id

        auth_url = (
                company_id.e_inv_api_url
                + '/einvoice/type/GENERATE_EWAYBILL/version/V1_03'
        )

        if not company_id.register_email:
            raise UserError(
                "Please set Register Email for %s" % company_id.name
            )

        auth_url += "?email=%s" % company_id.register_email

        headers = company_id.sudo().get_e_invoice_header()
        headers.update({
            "auth-token": company_id.sudo().get_e_inv_token()
        })

        data = self.generate_ewaybill_data()
        data = json.dumps(data)

        self._save_e_invoice_request_json(
            'ewaybill_by_irn',
            data
        )

        _logger.info(
            "E-Way Bill request data >>>>>>>>> %s",
            data
        )

        try:
            response = requests.post(
                url=auth_url,
                headers=headers,
                data=data,
                timeout=60
            )
        except requests.exceptions.RequestException as e:
            _logger.exception(
                "E-Way Bill API request failed"
            )
            raise UserError(
                "Unable to connect to E-Way Bill API.\n\n%s" % str(e)
            )

        _logger.info(
            "E-Way Bill HTTP status >>>>>>>>> %s",
            response.status_code
        )

        _logger.info(
            "E-Way Bill raw response >>>>>>>>> %s",
            response.text
        )

        try:
            json_data = response.json()
        except ValueError:
            raise UserError(
                "E-Way Bill API returned an invalid response.\n\n%s"
                % response.text[:2000]
            )

        _logger.info(
            "E-Way Bill JSON response >>>>>>>>> %s",
            json.dumps(json_data, indent=2, default=str)
        )

        msg = ""
        title = ""
        tz = pytz.timezone("Asia/Kolkata")

        # ==========================================================
        # SUCCESS
        # ==========================================================

        if str(json_data.get('status_cd')) == "1":

            title = json_data.get(
                'status_desc',
                'E-Way Bill Generated'
            )

            final_result = json_data.get('data') or {}

            if not isinstance(final_result, dict):
                raise UserError(
                    "Invalid E-Way Bill success response.\n\n%s"
                    % str(final_result)
                )

            EwbNo = (
                    final_result.get('EwbNo')
                    or final_result.get('ewb_no')
            )

            EwbDate = (
                    final_result.get('EwbDt')
                    or final_result.get('ewb_date')
            )

            EwbValidTill = (
                    final_result.get('EwbValidTill')
                    or final_result.get('ewb_valid_till')
            )

            if not EwbNo:
                raise UserError(
                    "E-Way Bill generated but EWB Number was not received.\n\n%s"
                    % json.dumps(final_result, indent=2, default=str)
                )

            ewb_date_data = {
                'ewb_no': EwbNo,
            }

            # ------------------------------------------------------
            # EWB DATE
            # ------------------------------------------------------

            if EwbDate:
                try:
                    dt_obj = False
                    for fmt in ('%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %I:%M:%S %p',
                                '%Y-%m-%d %H:%M:%S.%f'):
                        try:
                            dt_obj = datetime.strptime(str(EwbDate), fmt)
                            break
                        except ValueError:
                            continue

                    if not dt_obj:
                        dt_obj = fields.Datetime.to_datetime(EwbDate)

                    if dt_obj:
                        local_time = tz.localize(dt_obj)
                        utc_time = local_time.astimezone(pytz.utc)
                        ewb_date_data['ewb_date'] = fields.Datetime.to_string(utc_time)

                except Exception as e:
                    _logger.warning(
                        "Unable to convert EWB date %s: %s",
                        EwbDate,
                        e
                    )

            # ------------------------------------------------------
            # EWB VALID TILL
            # ------------------------------------------------------

            if EwbValidTill:
                try:
                    dt_obj_valid = False
                    for fmt in ('%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%d/%m/%Y %I:%M:%S %p',
                                '%Y-%m-%d %H:%M:%S.%f'):
                        try:
                            dt_obj_valid = datetime.strptime(str(EwbValidTill), fmt)
                            break
                        except ValueError:
                            continue

                    if not dt_obj_valid:
                        dt_obj_valid = fields.Datetime.to_datetime(EwbValidTill)

                    if dt_obj_valid:
                        local_time_valid = tz.localize(dt_obj_valid)
                        utc_time_valid = local_time_valid.astimezone(pytz.utc)
                        ewb_date_data['ewb_valid_till'] = fields.Datetime.to_string(utc_time_valid)

                except Exception as e:
                    _logger.warning(
                        "Unable to convert EWB valid till %s: %s",
                        EwbValidTill,
                        e
                    )

            self.write(ewb_date_data)

            msg = "Your EWB Number => %s" % EwbNo

        # ==========================================================
        # ERROR
        # ==========================================================

        elif str(json_data.get('status_cd')) == "0":

            title = "Error"

            status_desc = json_data.get('status_desc')

            _logger.error(
                "E-Way Bill API returned error: %s",
                status_desc
            )

            if isinstance(status_desc, str):
                try:
                    errors = json.loads(status_desc)
                except (ValueError, TypeError):
                    errors = status_desc
            else:
                errors = status_desc

            if isinstance(errors, list):

                error_messages = []

                for err in errors:

                    if isinstance(err, dict):

                        error_code = (
                                err.get('ErrorCode')
                                or err.get('error_code')
                                or err.get('errorCode')
                                or err.get('code')
                                or err.get('Code')
                        )

                        error_message = (
                                err.get('ErrorMessage')
                                or err.get('error_message')
                                or err.get('errorMessage')
                                or err.get('message')
                                or err.get('Message')
                                or err.get('error')
                                or err.get('Error')
                        )

                        if not error_message:
                            error_message = str(err)

                        if error_code:
                            error_messages.append(
                                "%s: %s" % (
                                    error_code,
                                    error_message
                                )
                            )
                        else:
                            error_messages.append(
                                str(error_message)
                            )

                    else:
                        error_messages.append(
                            str(err)
                        )

                msg = "\n".join(error_messages)

            elif isinstance(errors, dict):

                error_code = (
                        errors.get('ErrorCode')
                        or errors.get('error_code')
                        or errors.get('errorCode')
                        or errors.get('code')
                        or errors.get('Code')
                )

                error_message = (
                        errors.get('ErrorMessage')
                        or errors.get('error_message')
                        or errors.get('errorMessage')
                        or errors.get('message')
                        or errors.get('Message')
                        or errors.get('error')
                        or errors.get('Error')
                )

                if not error_message:
                    error_message = str(errors)

                if error_code:
                    msg = "%s: %s" % (
                        error_code,
                        error_message
                    )
                else:
                    msg = str(error_message)

            else:

                msg = str(
                    errors
                    or "Unknown E-Way Bill error"
                )

            if not msg.strip():
                msg = (
                        json_data.get('message')
                        or json_data.get('Message')
                        or "Unknown E-Way Bill error"
                )

        # ==========================================================
        # UNKNOWN STATUS
        # ==========================================================

        else:

            title = "Error"

            msg = (
                    json_data.get('status_desc')
                    or json_data.get('message')
                    or json_data.get('Message')
                    or "Unknown response received from E-Way Bill API."
            )

            if not isinstance(msg, str):
                msg = json.dumps(
                    msg,
                    indent=2,
                    default=str
                )

            _logger.error(
                "Unknown E-Way Bill API response: %s",
                json_data
            )

        # ==========================================================
        # SHOW MESSAGE WIZARD
        # ==========================================================

        _logger.info(
            "E-Way Bill final message >>>>>>>>> %s",
            msg
        )

        view = self.env.ref(
            'l10n_in_e_invoice_lax.message_wizard'
        )

        context = dict(self._context or {})
        context['message'] = msg

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard.einv',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    # def ewaybill_by_irn(self):
    #     company_id = self.company_id
    #
    #     auth_url = (
    #             company_id.e_inv_api_url
    #             + '/einvoice/type/GENERATE_EWAYBILL/version/V1_03'
    #     )
    #
    #     if not company_id.register_email:
    #         raise UserError(
    #             "Please set Register Email for %s" % company_id.name
    #         )
    #
    #     auth_url += "?email=%s" % company_id.register_email
    #
    #     headers = company_id.sudo().get_e_invoice_header()
    #     headers.update({
    #         "auth-token": company_id.sudo().get_e_inv_token()
    #     })
    #
    #     data = self.generate_ewaybill_data()
    #     data = json.dumps(data)
    #
    #     self._save_e_invoice_request_json(
    #         'ewaybill_by_irn',
    #         data
    #     )
    #
    #     _logger.info(
    #         "E-Way Bill request data >>>>>>>>> %s",
    #         data
    #     )
    #
    #     try:
    #         response = requests.post(
    #             url=auth_url,
    #             headers=headers,
    #             data=data,
    #             timeout=60
    #         )
    #     except requests.exceptions.RequestException as e:
    #         _logger.exception(
    #             "E-Way Bill API request failed"
    #         )
    #
    #         raise UserError(
    #             "Unable to connect to E-Way Bill API.\n\n%s" % str(e)
    #         )
    #
    #     _logger.info(
    #         "E-Way Bill HTTP status >>>>>>>>> %s",
    #         response.status_code
    #     )
    #
    #     _logger.info(
    #         "E-Way Bill raw response >>>>>>>>> %s",
    #         response.text
    #     )
    #
    #     try:
    #         json_data = response.json()
    #     except ValueError:
    #         raise UserError(
    #             "E-Way Bill API returned an invalid response.\n\n%s"
    #             % response.text[:2000]
    #         )
    #
    #     _logger.info(
    #         "E-Way Bill JSON response >>>>>>>>> %s",
    #         json.dumps(json_data, indent=2, default=str)
    #     )
    #
    #     msg = ""
    #     title = ""
    #
    #     # ==========================================================
    #     # SUCCESS
    #     # ==========================================================
    #
    #     if str(json_data.get('status_cd')) == "1":
    #
    #         title = json_data.get(
    #             'status_desc',
    #             'E-Way Bill Generated'
    #         )
    #
    #         final_result = json_data.get('data') or {}
    #
    #         if not isinstance(final_result, dict):
    #             raise UserError(
    #                 "Invalid E-Way Bill success response.\n\n%s"
    #                 % str(final_result)
    #             )
    #
    #         EwbNo = (
    #                 final_result.get('EwbNo')
    #                 or final_result.get('ewb_no')
    #         )
    #
    #         EwbDate = (
    #                 final_result.get('EwbDt')
    #                 or final_result.get('ewb_date')
    #         )
    #
    #         EwbValidTill = (
    #                 final_result.get('EwbValidTill')
    #                 or final_result.get('ewb_valid_till')
    #         )
    #
    #         if not EwbNo:
    #             raise UserError(
    #                 "E-Way Bill generated but EWB Number was not received.\n\n%s"
    #                 % json.dumps(final_result, indent=2, default=str)
    #             )
    #
    #         ewb_date_data = {
    #             'ewb_no': EwbNo,
    #         }
    #
    #         # ------------------------------------------------------
    #         # EWB DATE
    #         # ------------------------------------------------------
    #
    #         if EwbDate:
    #             try:
    #                 local_time = tz.localize(
    #                     fields.Datetime.to_datetime(EwbDate)
    #                 )
    #
    #                 utc_time = local_time.astimezone(pytz.utc)
    #
    #                 ewb_date_data['ewb_date'] = (
    #                     fields.Datetime.to_string(utc_time)
    #                 )
    #
    #             except Exception as e:
    #                 _logger.warning(
    #                     "Unable to convert EWB date %s: %s",
    #                     EwbDate,
    #                     e
    #                 )
    #
    #         # ------------------------------------------------------
    #         # EWB VALID TILL
    #         # ------------------------------------------------------
    #
    #         if EwbValidTill:
    #             try:
    #                 local_time_valid = tz.localize(
    #                     fields.Datetime.to_datetime(EwbValidTill)
    #                 )
    #
    #                 utc_time_valid = local_time_valid.astimezone(
    #                     pytz.utc
    #                 )
    #
    #                 ewb_date_data['ewb_valid_till'] = (
    #                     fields.Datetime.to_string(utc_time_valid)
    #                 )
    #
    #             except Exception as e:
    #                 _logger.warning(
    #                     "Unable to convert EWB valid till %s: %s",
    #                     EwbValidTill,
    #                     e
    #                 )
    #
    #         self.write(ewb_date_data)
    #
    #         msg = "Your EWB Number => %s" % EwbNo
    #
    #     # ==========================================================
    #     # ERROR
    #     # ==========================================================
    #
    #     elif str(json_data.get('status_cd')) == "0":
    #
    #         title = "Error"
    #
    #         status_desc = json_data.get('status_desc')
    #
    #         _logger.error(
    #             "E-Way Bill API returned error: %s",
    #             status_desc
    #         )
    #
    #         # ------------------------------------------------------
    #         # Try to decode status_desc if it is JSON string
    #         # ------------------------------------------------------
    #
    #         if isinstance(status_desc, str):
    #
    #             try:
    #                 errors = json.loads(status_desc)
    #             except (ValueError, TypeError):
    #                 errors = status_desc
    #
    #         else:
    #             errors = status_desc
    #
    #         # ------------------------------------------------------
    #         # ERROR IS LIST
    #         # ------------------------------------------------------
    #
    #         if isinstance(errors, list):
    #
    #             error_messages = []
    #
    #             for err in errors:
    #
    #                 if isinstance(err, dict):
    #
    #                     error_code = (
    #                             err.get('ErrorCode')
    #                             or err.get('error_code')
    #                             or err.get('errorCode')
    #                             or err.get('code')
    #                             or err.get('Code')
    #                     )
    #
    #                     error_message = (
    #                             err.get('ErrorMessage')
    #                             or err.get('error_message')
    #                             or err.get('errorMessage')
    #                             or err.get('message')
    #                             or err.get('Message')
    #                             or err.get('error')
    #                             or err.get('Error')
    #                     )
    #
    #                     # ------------------------------------------
    #                     # If no known message key exists
    #                     # ------------------------------------------
    #
    #                     if not error_message:
    #                         error_message = str(err)
    #
    #                     if error_code:
    #                         error_messages.append(
    #                             "%s: %s" % (
    #                                 error_code,
    #                                 error_message
    #                             )
    #                         )
    #                     else:
    #                         error_messages.append(
    #                             str(error_message)
    #                         )
    #
    #                 else:
    #                     error_messages.append(
    #                         str(err)
    #                     )
    #
    #             msg = "\n".join(error_messages)
    #
    #         # ------------------------------------------------------
    #         # ERROR IS DICT
    #         # ------------------------------------------------------
    #
    #         elif isinstance(errors, dict):
    #
    #             error_code = (
    #                     errors.get('ErrorCode')
    #                     or errors.get('error_code')
    #                     or errors.get('errorCode')
    #                     or errors.get('code')
    #                     or errors.get('Code')
    #             )
    #
    #             error_message = (
    #                     errors.get('ErrorMessage')
    #                     or errors.get('error_message')
    #                     or errors.get('errorMessage')
    #                     or errors.get('message')
    #                     or errors.get('Message')
    #                     or errors.get('error')
    #                     or errors.get('Error')
    #             )
    #
    #             if not error_message:
    #                 error_message = str(errors)
    #
    #             if error_code:
    #                 msg = "%s: %s" % (
    #                     error_code,
    #                     error_message
    #                 )
    #             else:
    #                 msg = str(error_message)
    #
    #         # ------------------------------------------------------
    #         # ERROR IS STRING / OTHER
    #         # ------------------------------------------------------
    #
    #         else:
    #
    #             msg = str(
    #                 errors
    #                 or "Unknown E-Way Bill error"
    #             )
    #
    #         # ------------------------------------------------------
    #         # Final fallback
    #         # ------------------------------------------------------
    #
    #         if not msg.strip():
    #             msg = (
    #                     json_data.get('message')
    #                     or json_data.get('Message')
    #                     or "Unknown E-Way Bill error"
    #             )
    #
    #     # ==========================================================
    #     # UNKNOWN STATUS
    #     # ==========================================================
    #
    #     else:
    #
    #         title = "Error"
    #
    #         msg = (
    #                 json_data.get('status_desc')
    #                 or json_data.get('message')
    #                 or json_data.get('Message')
    #                 or "Unknown response received from E-Way Bill API."
    #         )
    #
    #         if not isinstance(msg, str):
    #             msg = json.dumps(
    #                 msg,
    #                 indent=2,
    #                 default=str
    #             )
    #
    #         _logger.error(
    #             "Unknown E-Way Bill API response: %s",
    #             json_data
    #         )
    #
    #     # ==========================================================
    #     # SHOW MESSAGE WIZARD
    #     # ==========================================================
    #
    #     _logger.info(
    #         "E-Way Bill final message >>>>>>>>> %s",
    #         msg
    #     )
    #
    #     view = self.env.ref(
    #         'l10n_in_e_invoice_lax.message_wizard'
    #     )
    #
    #     context = dict(self._context or {})
    #     context['message'] = msg
    #
    #     return {
    #         'name': title,
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'message.wizard.einv',
    #         'views': [(view.id, 'form')],
    #         'view_id': view.id,
    #         'target': 'new',
    #         'context': context,
    #     }

    def generate_ewaybill_data(self):
        if not self.irn_no:
            raise UserError("IRN not generated yet. Please generate IRN first.")
        if not self.distance:
            raise UserError(_("Distance is required"))
        if not self.transportation_mode:
            raise UserError(_("Transportation Mode is required"))
        if not self.transportation_gst:
            raise UserError(_("Transportation GST is required"))
        if not self.transportation_id:
            raise UserError(_("Transportation ID is required"))
        if not self.document_date:
            raise UserError(_("Document Date is required"))
        if not self.document_no:
            raise UserError(_("Document No is required"))
        if not self.vehical_no:
            raise UserError(_("Vehicle No is required"))
        if not self.vehical_type:
            raise UserError(_("Vehicle Type is required"))
        data_dict = {
            "Irn": self.irn_no,
            "Distance": self.distance,
            "TransMode": self.transportation_mode,
            "TransId": self.transportation_gst,
            "TransName": self.transportation_id.name,
            "TransDocDt": self.document_date.strftime("%d/%m/%Y"),
            "TransDocNo": self.document_no,
            "VehNo": self.vehical_no,
            "VehType": self.vehical_type,
            "ExpShipDtls": self.ExpShipDtls(),
            "DispDtls": self.DispDtls(),
        }

        _logger.info(f"data_dict>>>>>>>>>>>>>>>{data_dict}")

        return data_dict

    def EwbDtls(self):
        if not self.distance:
            raise UserError(_("Distance is required"))
        if not self.transportation_mode:
            raise UserError(_("Transportation Mode is required"))
        if not self.transportation_gst:
            raise UserError(_("Transportation GST is required"))
        if not self.transportation_id:
            raise UserError(_("Transportation ID is required"))
        if not self.document_date:
            raise UserError(_("Document Date is required"))
        if not self.document_no:
            raise UserError(_("Document No is required"))
        if not self.vehical_no:
            raise UserError(_("Vehicle No is required"))
        if not self.vehical_type:
            raise UserError(_("Vehicle Type is required"))
        data_dict = {
            "Distance": self.distance,
            "TransMode": self.transportation_mode,
            "TransId": self.transportation_gst,
            "TransName": self.transportation_id.name,
            "TransDocDt": self.document_date.strftime("%d/%m/%Y"),
            "TransDocNo": self.document_no,
            "VehNo": self.vehical_no,
            "VehType": self.vehical_type,
        }
        return data_dict

    def generate_irn_and_ewaybill(self):
        self.ensure_one()

        company_id = self.company_id

        auth_url = (
                company_id.e_inv_api_url
                + '/einvoice/type/GENERATE/version/V1_03'
        )

        if not company_id.register_email:
            raise UserError(
                "Please set Register Email for %s" % company_id.name
            )

        auth_url += "?email=%s" % company_id.register_email

        headers = company_id.sudo().get_e_invoice_header()

        # Get authentication token
        auth_token = company_id.sudo().get_e_inv_token()

        if not auth_token:
            raise UserError(
                "E-Invoice authentication failed. "
                "Auth token was not generated."
            )

        headers.update({
            "auth-token": str(auth_token)
        })

        data = self.generate_json_data()
        data.update({
            'EwbDtls': self.EwbDtls()
        })

        data = json.dumps(data)

        self._save_e_invoice_request_json(
            'generate_irn_and_ewaybill',
            data
        )

        _logger.info(
            "E-Invoice Generate Request: %s",
            data
        )

        try:
            response = requests.post(
                url=auth_url,
                headers=headers,
                data=data,
                timeout=60
            )

            _logger.info(
                "E-Invoice Generate HTTP Status: %s",
                response.status_code
            )

            _logger.info(
                "E-Invoice Generate Response: %s",
                response.text
            )

            json_data = response.json()

        except requests.exceptions.RequestException as e:
            _logger.exception(
                "E-Invoice Generate API Error"
            )
            raise UserError(
                "E-Invoice API error: %s" % str(e)
            )

        except ValueError:
            _logger.exception(
                "Invalid JSON response from E-Invoice API"
            )
            raise UserError(
                "Invalid response received from E-Invoice API."
            )

        title, msg = self.get_result_from_response(response)

        view = self.env.ref(
            'l10n_in_e_invoice_lax.message_wizard'
        )

        context = dict(self._context or {})
        context['message'] = msg

        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard.einv',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def get_irn_detail(self):
        company_id = self.company_id
        auth_url = company_id.e_inv_api_url + '/einvoice/type/GETIRNBYDOCDETAILS/version/V1_03'
        if not company_id.register_email:
            raise UserError("Please set Register Email for %s" % company_id.name)
        auth_url += "?email=%s" % company_id.register_email
        doc_type = "INV"
        if self.move_type == "out_refund":
            doc_type = "CRN"
        elif self.move_type == "in_refund":
            doc_type = "DBN"
        auth_url += "&param1=%s" % doc_type
        print("auth_url:::::::::::::::", auth_url)
        headers = company_id.sudo().get_e_invoice_header()
        headers.update({"docnum": self.name, "docdate": self.invoice_date.strftime("%d/%m/%Y")})
        headers.update({"auth-token": company_id.sudo().get_e_inv_token()})
        print(":::::::::::::::::HEADERS:::UPDATEE::::::::::::", headers)
        data = {}
        self._save_e_invoice_request_json('get_irn_detail', data)
        response = requests.get(url=auth_url, headers=headers, data=data)
        title, msg = self.get_result_from_response(response)
        view = self.env.ref('l10n_in_e_invoice_lax.message_wizard')
        context = dict(self._context or {})
        context['message'] = msg
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard.einv',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def generate_irn(self):
        company_id = self.company_id
        auth_url = company_id.e_inv_api_url + '/einvoice/type/GENERATE/version/V1_03'
        if not company_id.register_email:
            raise UserError("Please set Register Email for %s" % company_id.name)
        auth_url += "?email=%s" % company_id.register_email
        headers = company_id.sudo().get_e_invoice_header()
        headers.update({"auth-token": company_id.sudo().get_e_inv_token()})
        data = self.generate_json_data()
        data = json.dumps(data)
        self._save_e_invoice_request_json('generate_irn', data)
        _logger.info(f"sent data>>>>>>>>>>>>>>>{data}")
        response = requests.post(url=auth_url, headers=headers, data=data)
        json_data = response.json()
        _logger.info(f"response data>>>>>>>>>>>>>>>{json_data}")
        title, msg = self.get_result_from_response(response)
        view = self.env.ref('l10n_in_e_invoice_lax.message_wizard')
        context = dict(self._context or {})
        context['message'] = msg
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'message.wizard.einv',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def get_result_from_response(self, response):
        json_data = response.json()
        msg = ""
        title = ""
        tz = pytz.timezone("Asia/Kolkata")
        if json_data.get('status_cd') == "1":
            title = json_data.get('status_desc')
            final_result = json_data.get('data')
            Irn = final_result.get('Irn')
            AckDate = final_result.get('AckDt')
            local_time = tz.localize(fields.Datetime.to_datetime(AckDate))
            utc_time = local_time.astimezone(pytz.utc)
            irn_data = {
                'irn_no': Irn,
                'ack_no': final_result.get('AckNo'),
                'ack_date': fields.Datetime.to_string(utc_time),
                'signed_invoice': final_result.get('SignedInvoice')
            }
            self.qr_code = self.generate_qr_code(final_result.get('SignedQRCode'))
            msg = "Your IRN Number => %s" % Irn
            EwbNo = final_result.get('EwbNo')
            if EwbNo:
                EwbDate = final_result.get('EwbDt')
                EwbValidTill = final_result.get('EwbValidTill')
                local_time = tz.localize(fields.Datetime.to_datetime(EwbDate))
                utc_time = local_time.astimezone(pytz.utc)
                local_time_valid = tz.localize(fields.Datetime.to_datetime(EwbValidTill))
                utc_time_valid = local_time_valid.astimezone(pytz.utc)
                irn_data.update({
                    'ewb_no': EwbNo,
                    'ewb_date': fields.Datetime.to_string(utc_time),
                    'ewb_valid_till': fields.Datetime.to_string(utc_time_valid),
                })
                msg += "\n"
                msg += "Your E-way Bill Number => %s" % EwbNo
            self.write(irn_data)
        elif json_data.get('status_cd') == "0":
            title = "Error"
            msg += json_data.get('status_desc')
            msg += '\n'
            # for err in json.loads(json_data.get('status_desc')):
            #     msg += str(err['ErrorMessage'])
            #     msg += '\n'
        return title, msg

    def cancel_irn(self):
        if self.irn_no and self.ewb_no:
            raise UserError("You can not cancel E-way Bill and E-Invoice.")
        if not self.irn_no:
            raise UserError("Please Generate IRN number")

        wiz_id = self.env['cancel.irn.wizard'].create({'invoice_id': self.id})
        return {
            'name': _('Cancel IRN'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'cancel.irn.wizard',
            'views': [(self.env.ref('l10n_in_e_invoice_lax.cancel_irn_wizard').id, 'form')],
            'view_id': self.env.ref('l10n_in_e_invoice_lax.cancel_irn_wizard').id,
            'target': 'new',
            'res_id': wiz_id.id,
        }

    # def button_draft(self):
    #     if self.irn_no and self.cancel_remark:
    #         raise UserError("IRN already cancelled and you can not reset to draft this invoice.")
    #     if self.irn_no:
    #         raise UserError("Please Cancel E-invoice IRN")
    #     super(AccountMove, self).button_draft()

    def TranDtls(self):
        return {
            "TaxSch": "GST",
            "SupTyp": self._get_supply_type() or 'B2B',
            "RegRev": "N",
            # "EcmGstin": '29AABCT1332L000', not reqired in B2B transcation
            "IgstOnIntra": "N"
        }

    def DocDtls(self):
        type = "INV"
        if self.move_type == 'out_refund':
            type = 'CRN'
        elif self.move_type == 'in_refund':
            type = 'DBN'
        return {
            'Typ': type,
            'No': self.name,
            'Dt': self.invoice_date.strftime("%d/%m/%Y")
        }

    def SellerDtls(self):
        company_id = self.company_id
        if not company_id.vat and company_id.e_inv_environment == 'production':
            raise UserError("please Set GSTIN Number for %s " % company_id.name)
        if not self.company_id.phone:
            raise UserError("Please Add Phone Number for %s" % company_id.name)
        if not company_id.email:
            raise UserError("Please Add Email for %s" % company_id.name)
        if not company_id.zip:
            raise UserError("Please Add Zip for %s" % company_id.name)
        if not company_id.city:
            raise UserError("Please Add City for %s" % company_id.name)
        if not company_id.street or len(company_id.street) <= 3:
            raise UserError("Please Add Proper Addess street for %s" % company_id.name)
        if not company_id.street2 or len(company_id.street2) <= 3:
            raise UserError("Please Add Proper Addess street2 for %s" % company_id.name)
        if not company_id.state_id:
            raise UserError("Please Add State for %s" % company_id.name)

        data = {
            "Gstin": company_id.vat and company_id.vat or '',
            "LglNm": company_id.name,
            "Addr1": company_id.street and company_id.street or '',
            "Addr2": company_id.street2 and company_id.street2 or company_id.street,
            "Loc": company_id.city,
            "Pin": company_id.zip,
            "Stcd": company_id.state_id.l10n_in_tin,
            "Ph": company_id.phone.replace(" ", "").replace("+", "").strip(),
            "Em": company_id.email
        }
        # if company_id.e_inv_environment == 'sandbox':
        #     data.update({"Gstin": "29AABCT1332L000"})
        return data

    def BuyerDtls(self):
        if not self.partner_id.phone:
            raise UserError("Please Add Phone Number for %s" % self.partner_id.name)
        if not self.partner_id.email:
            raise UserError("Please Add Email for %s" % self.partner_id.name)
        if not self.partner_id.zip:
            raise UserError("Please Add Zip for %s" % self.partner_id.name)
        if not self.partner_id.city:
            raise UserError("Please Add City for %s" % self.partner_id.name)
        if not self.partner_id.street or len(self.partner_id.street) <= 3:
            raise UserError("Please Add Proper Addess street for %s" % self.partner_id.name)
        if not self.partner_id.street2 or len(self.partner_id.street2) <= 3:
            raise UserError("Please Add Proper Addess street2 for %s" % self.partner_id.name)
        if not self.partner_id.state_id:
            raise UserError("Please Add State for %s" % self.partner_id.name)

        data = {
            "Gstin": self.partner_id.vat and self.partner_id.vat or False,
            "LglNm": self.partner_id.name,
            "Pos": self.partner_id.state_id.l10n_in_tin,
            "Addr1": self.partner_id.street,
            "Addr2": self.partner_id.street2,
            "Loc": self.partner_id.city,
            "Pin": self.partner_id.zip,
            "Stcd": self.partner_id.state_id.l10n_in_tin,
            "Ph": self.partner_id.phone.replace(" ", "").replace("+", "").strip(),
            "Em": self.partner_id.email,
        }
        return data

    def DispDtls(self):
        return {
            "Nm": self.partner_id.name,
            "Addr1": self.partner_id.street,
            "Addr2": self.partner_id.street2,
            "Loc": self.partner_id.city,
            "Pin": self.partner_id.zip,
            "Stcd": self.partner_id.state_id.l10n_in_tin
        }

    def ExpShipDtls(self):
        return {
            "Addr1": self.partner_id.street,
            "Addr2": self.partner_id.street2,
            "Loc": self.partner_id.city,
            "Pin": self.partner_id.zip,
            "Stcd": self.partner_id.state_id.l10n_in_tin
        }

    # non mandatory
    def ShipDtls(self):
        return {
            "Gstin": self.partner_id.vat and self.partner_id.vat or False,
            "LglNm": self.partner_id.name,
            "TrdNm": self.partner_id.name,
            "Addr1": self.partner_id.street,
            "Addr2": self.partner_id.street2,
            "Loc": self.partner_id.city,
            "Pin": self.partner_id.zip,
            "Stcd": self.partner_id.state_id.l10n_in_tin
        }

    # get all item list in detail
    def ItemList(self):
        ItemList = []
        company_id = self.company_id
        cnt = 0
        for item in self.invoice_line_ids:
            cnt += 1
            gst_rate = 0.0
            for tax in item.tax_ids:
                if tax.tax_group_id.name in ["GST", "IGST", "CGST", "SGST"]:  # Filter GST taxes
                    gst_rate += float(tax.amount)  # Sum up the tax percentage
            tax_detail = item._gsts_for_json_file()
            IsServc = "N"
            if item.product_id.type == 'service':
                IsServc = 'Y'
            item_dict = {
                "SlNo": str(cnt),
                "IsServc": IsServc,
                "HsnCd": str(item.product_id.l10n_in_hsn_code),
                "UnitPrice": item.price_unit,
                "TotAmt": item.price_subtotal,
                "AssAmt": item.price_subtotal,
                "GstRt": gst_rate,
                "TotItemVal": item.price_total,
                "PrdDesc": item.product_id.display_name,
                # "Barcde": item.product_id.barcode and item.product_id.barcode or '',
                "Qty": item.quantity,
                "Unit": item.product_id.uom_id.l10n_in_code and item.product_id.uom_id.l10n_in_code[:3] or "UNT",
                "UnitPrice": item.price_unit,
                "Discount": item.discount,
                "PreTaxVal": item.price_subtotal,
                "IgstAmt": round(tax_detail.get('iamt', 0.0), 2),
                "CgstAmt": round(tax_detail.get('samt', 0.0), 2),
                "SgstAmt": round(tax_detail.get('camt', 0.0), 2),
                "CesRt": round(tax_detail.get('cess', 0.0), 2),
                "OthChrg": 0.0,
            }
            ItemList.append(item_dict)
        return ItemList

    def ValDtls(self):
        amts = {'samt': 0.0, 'camt': 0.0, 'iamt': 0.0, 'cess': 0.0}

        for amt in self.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            print("::::::::::", amt.get('tax_group_name'), amt.get('tax_group_amount'))
            if amt.get('tax_group_name') == 'SGST':
                amts['samt'] = amt.get('tax_group_amount')
            elif amt.get('tax_group_name') == 'CGST':
                amts['camt'] = amt.get('tax_group_amount')
            elif amt.get('tax_group_name') == 'IGST':
                amts['iamt'] = amt.get('tax_group_amount')
            elif amt.get('tax_group_name') == 'CESS':
                amts['cess'] = amt.get('tax_group_amount')

        # for amt in self.amount_by_group:
        #     if 'SGST' in amt[0]:
        #         amts['samt'] = amt[1]
        #     elif 'CGST' in amt[0]:
        #         amts['camt'] = amt[1]
        #     elif 'IGST' in amt[0]:
        #         amts['iamt'] = amt[1]
        #     elif 'CESS' in amt[0]:
        #         amts['cess'] = amt[1]

        data = {
            'AssVal': round(self.amount_untaxed, 2),
            'CgstVal': round(amts.get('camt', 0.0), 2),
            "SgstVal": round(amts.get('samt', 0.0), 2),
            "IgstVal": round(amts.get('iamt', 0.0), 2),
            "CesVal": round(amts.get('cess', 0.0), 2),
            "RndOffAmt": 0.0,
            "TotInvVal": round(self.amount_total, 2),
        }

        return data


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _gsts_for_json_file(self):
        taxes = self.tax_ids.json_friendly_compute_all(self.price_unit, self.currency_id.id, self.quantity,
                                                       self.product_id.id, self.partner_id.id)
        amts = {'samt': 0.0, 'camt': 0.0, 'iamt': 0.0, 'cess': 0.0}
        for tax in taxes.get('taxes', []):
            if 'SGST' in tax['name']:
                amts['samt'] += tax['amount']
            elif 'CGST' in tax['name']:
                amts['camt'] += tax['amount']
            elif 'IGST' in tax['name']:
                amts['iamt'] += tax['amount']
            elif 'CESS' in tax['name']:
                amts['cess'] += tax['amount']
        return amts




































