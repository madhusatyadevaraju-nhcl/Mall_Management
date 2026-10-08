from odoo import models, fields, api, _

class SlabMaster(models.Model):
    _name = "slab.master"
    _rec_name = "customer_id"

    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Tenant",
        domain="[('user_type', '=', 'customer')]",
        help="Only partners with user_type = 'customer' will be shown here."
    )

    slab_line_ids = fields.One2many(
        comodel_name="slab.master.line",
        inverse_name="slab_id",
        string="Slab Lines"
    )

class SlabMasterLine(models.Model):
    _name = "slab.master.line"
    _description = "Slab Master Line"

    slab_id = fields.Many2one("slab.master", string="Slab Master", ondelete="cascade")
    from_slab = fields.Float(string="From Slab", digits=(16, 4))
    to_slab = fields.Float(string="To Slab", digits=(16, 4))
    percentage = fields.Float(string="Percentage")

    # amount = fields.Float(string="Amount",digits=(16, 4))

    @api.onchange('from_slab', 'to_slab')
    def _onchange_slab_range(self):
        if not self.slab_id:
            return

        # ❌ Block negative from_slab
        if self.from_slab is not None and self.from_slab < 0:
            raise ValidationError("From Slab must be greater than 0.")

        # ✅ Filter only active lines excluding deleted ones and self
        active_lines = self.slab_id.slab_line_ids.filtered(
            lambda l: not l._origin or l in self.slab_id.slab_line_ids
        )
        other_lines = active_lines.filtered(lambda l: l != self and l.to_slab is not None)

        # ✅ Sort by to_slab to find the last one
        if not self.from_slab and other_lines:
            last_line = max(other_lines, key=lambda l: l.to_slab)
            self.from_slab = last_line.to_slab + 1

        # 💥 Validate overlaps
        for line in other_lines:
            if self.from_slab and self.from_slab <= line.to_slab:
                raise ValidationError("From Slab must be greater than the previous line's To Slab.")

        if self.from_slab and self.to_slab:
            if self.to_slab <= self.from_slab:
                raise ValidationError("To Slab must be greater than From Slab.")
