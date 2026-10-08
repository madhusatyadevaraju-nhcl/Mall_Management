from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseBlankets(models.Model):
    _inherit = "purchase.requisition"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approval_one', 'First Approval'),  # New state before 'ongoing'
        ('approval_two', 'Second Approval'),  # New state before 'ongoing'
        ('confirmed', 'Confirmed'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft')
    is_price_changed = fields.Boolean(string="Price Changed", default=False)


    def nhcl_action_first_approve(self):
        for record in self:
            if record.state == 'approval_one':  # Check if current state is 'draft'
                record.state = 'approval_two'  # Set the state to 'pre_ongoing'
            else:
                raise UserError("You can only move to 'Pre-Ongoing' from 'Draft' state.")

    def nhcl_action_second_approval(self):
        for record in self:
            if record.state == 'approval_two':  # Check if current state is 'draft'
                record.state = 'confirmed'  # Set the state to 'pre_ongoing'
            else:
                raise UserError("You can only move to 'Pre-Ongoing' from 'Draft' state.")

    @api.onchange('line_ids')
    def _check_price_change(self):
        channel = self.env['discuss.channel'].search([('name', '=', 'Blanked Alert')])
        # Check if any line has price changed
        for record in self:
            if any(line.is_price_changed_in_line for line in record.line_ids):
                if not channel:
                    user_ids = self.env['res.users'].search([]).ids
                    channel = self.env['discuss.channel'].create({
                        'name': 'Blanked Alert',
                        'channel_type': 'group',
                        'channel_partner_ids': [(4, user.partner_id.id) for user in
                                                self.env['res.users'].browse(user_ids)],
                    })
                channel.message_post(
                    body=f"The Order Line Value Changed: {record.name} for aleart",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
                # If any line's price is changed, move the state to 'pre_ongoing'
                if record.state == 'confirmed':
                    record.state = 'approval_one'
                elif record.state == 'approval_two':
                    record.state = 'approval_one'
                    # Reset price change flags
                    for line in record.line_ids:
                        line.is_price_changed_in_line = False


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    is_price_changed_in_line = fields.Boolean(string="Price Changed", default=False)

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        for record in self:
            # Only trigger the price change logic if the parent is in "ongoing" state
            if record.requisition_id.state == 'confirmed' and record.price_unit:
                # Set the 'is_price_changed_in_line' to True when the price is changed
                record.is_price_changed_in_line = True
                # Change the state of the parent to 'pre_ongoing'