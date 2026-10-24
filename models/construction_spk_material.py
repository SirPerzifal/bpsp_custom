from odoo import api, fields, models


class ConstructionSPKMaterial(models.Model):
    _name = 'construction.spk.material'
    _description = 'Kebutuhan Material SPK'
    _order = 'id'

    spk_id = fields.Many2one('construction.spk', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Material', required=True)
    uom_id = fields.Many2one('uom.uom', string='Satuan')
    planned_qty = fields.Float(string='Qty Rencana', digits='Product Unit')
    actual_qty = fields.Float(string='Qty Terpakai', digits='Product Unit')
    unit_cost = fields.Monetary(string='Harga Satuan')
    total_cost = fields.Monetary(string='Total', compute='_compute_total', store=True)
    move_id = fields.Many2one('stock.move', string='Stock Move')
    currency_id = fields.Many2one(related='spk_id.currency_id')
    company_id = fields.Many2one(related='spk_id.company_id', store=True)

    @api.depends('actual_qty', 'planned_qty', 'unit_cost')
    def _compute_total(self):
        for line in self:
            qty = line.actual_qty or line.planned_qty
            line.total_cost = qty * line.unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.unit_cost = self.product_id.standard_price
