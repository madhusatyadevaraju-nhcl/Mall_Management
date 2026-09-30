from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseIndent(models.Model):
    _name = 'purchase.indent'
    _description = 'Purchase Indent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Indent Reference', required=True, copy=False, readonly=True, default='New')
    req_customer_id=fields.Many2one('res.users',string='Request Owner',required=True,Tracking=True)
    vendor_id=fields.Many2one('res.partner',string='Vendor',required=True, domain=[('user_type', '=', 'vendor')])
    category=fields.Char(string='Category',readonly=True,default='Purchase Indent')
    to_date = fields.Date(string='To Date')
    fm_date = fields.Date(string='From Date', default=fields.Date.today)
    street = fields.Char(string="Address", related='vendor_id.street', tracking=True, copy=False)
    street2 = fields.Char(related='vendor_id.street2', tracking=True, copy=False)
    zip = fields.Char(change_default=True, related='vendor_id.zip', tracking=True, copy=False)
    city = fields.Char(related='vendor_id.city', tracking=True, copy=False)
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]", related='vendor_id.state_id',
                               tracking=True, copy=False)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', related='vendor_id.country_id',
                                 tracking=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting for Manager Approval '),
        ('manager_approved', 'Manager Approved'),
        ('final_approved', 'Final Approved'),
        ('rfq_created', 'RFQ Created'),('refused', 'Refused'),
    ], string='Status', default='draft', tracking=True)
    purchase_order_id = fields.Many2one('purchase.order', string='RFQ')

    approval_line_ids = fields.One2many(
        'purchase.indent.approval.line',
        'indent_id',
        string="Approval History"
    )

    line_ids = fields.One2many('purchase.indent.line', 'indent_id', string='Indent Lines')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.indent') or 'New'
        return super(PurchaseIndent, self).create(vals)

    def action_submit(self):
        print(self.line_ids)
        if self.line_ids:
            self.state = 'submitted'

            # Create approval lines for managers
            manager_group = self.env.ref('purchase_indent.purchase_manager_approval')  # Replace with your actual group
            manager_users = manager_group.users

            for user in manager_users:
                self.env['purchase.indent.approval.line'].create({
                    'indent_id': self.id,
                    'approver_id': user.id,
                    'approval_stage': 'manager',
                    'status': 'pending',
                })
            manager_group = self.env.ref('purchase_indent.purchase_indent_final_approve')  # Replace with your actual group
            final_manager_users = manager_group.users

            for user in final_manager_users:
                self.env['purchase.indent.approval.line'].create({
                    'indent_id': self.id,
                    'approver_id': user.id,
                    'approval_stage': 'final',
                    'status': 'pending',
                })
        else:
            raise ValidationError('Hey You Forgot to add the product')

    @api.constrains('fm_date', 'to_date')
    def _check_date_order(self):
        for rec in self:
            if rec.fm_date and rec.to_date and rec.fm_date > rec.to_date:
                raise ValidationError("From Date must be earlier than or equal to To Date.")

    def open_indent_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Purchase Indent',
            'res_model': 'purchase.indent',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_vendor_id': self.vendor_id.id or False,
            }
        }

    def action_manager_approve(self):
        self.state = 'manager_approved'

        approval_line = self.approval_line_ids.filtered(
            lambda l: l.approver_id == self.env.user and l.approval_stage == 'manager'
        )
        if approval_line:
            approval_line.write({
                'status': 'approved',
                'approved_date': fields.Datetime.now()
            })

    def action_manager_refuse(self):
        self.state = 'refused'

        approval_line = self.approval_line_ids.filtered(
            lambda l: l.approver_id == self.env.user and l.approval_stage == 'manager'
        )
        if approval_line:
            approval_line.write({
                'status': 'refuse',
                'approved_date': fields.Datetime.now()
            })

    def action_final_approve(self):
        self.state = 'final_approved'
        approval_line = self.approval_line_ids.filtered(
            lambda l: l.approver_id == self.env.user and l.approval_stage == 'final'
        )
        if approval_line:
            approval_line.write({
                'status': 'approved',
                'approved_date': fields.Datetime.now()
            })

    def action_create_rfq(self):
        PurchaseOrder = self.env['purchase.order']
        for indent in self:
            order_lines = []
            for line in indent.line_ids:
                order_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                    'price_unit': line.price,
                    'date_planned': fields.Date.today(),
                    'name': line.product_id.name,
                    'product_uom':line.uom.id
                }))
            rfq = PurchaseOrder.create({
                'partner_id': indent.vendor_id.id,
                'order_line': order_lines,
            })

            indent.purchase_order_id = rfq
            indent.state = 'rfq_created'

            return {
                'name': 'Request for Quotation',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': rfq.id,
                'target': 'current',
            }


class PurchaseIndentLine(models.Model):
    _name = 'purchase.indent.line'
    _description = 'Purchase Indent Line'

    indent_id = fields.Many2one('purchase.indent', string='Indent')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', required=False,default=1)
    product_des=fields.Char(string='Product Description')
    # uom=fields.Integer(string='UOM')
    uom = fields.Many2one('uom.uom', string='Unit of Measure',)# domain="[('category_id', '=', product_uom_category_id)]")
    hsn_code = fields.Char(string='HSN Code', related='product_id.l10n_in_hsn_code', store=True, readonly=False)
    price=fields.Float(string='Price')
    # tax_id=fields.Many2many('account.tax',string='Tax')
    # taxes_id = fields.Many2many('account.tax', string='Taxes')
    amount=fields.Float(string='Total',compute='_compute_amount',store=True)

    @api.depends('product_qty', 'price')
    def _compute_amount(self):
        for line in self:
            subtotal = line.product_qty * line.price
            # tax_total = 0.0
            line.amount = subtotal #+ tax_total


class PurchaseIndentApprovalLine(models.Model):
    _name = 'purchase.indent.approval.line'
    _description = 'Purchase Indent Approval Line'

    indent_id = fields.Many2one('purchase.indent', string="Indent Reference", ondelete='cascade')
    approver_id = fields.Many2one('res.users', string="Approver", required=True)
    approval_stage = fields.Selection([
        ('manager', 'Manager Approval'),
        ('final', 'Final Approval'),
    ], string='Stage', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),('refuse', 'Refuse'),
    ], string='Status', default='pending')
    approved_date = fields.Datetime(string="Approved On")

