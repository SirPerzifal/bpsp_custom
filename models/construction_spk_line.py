from odoo import api, fields, models


class ConstructionSPKLine(models.Model):
    _name = 'construction.spk.line'
    _description = 'Lingkup Pekerjaan SPK'
    _order = 'sequence, id'

    spk_id = fields.Many2one('construction.spk', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Text(string='Uraian Pekerjaan', required=True)
    uom_id = fields.Many2one('uom.uom', string='Satuan')
    qty = fields.Float(string='Volume', digits='Product Unit')
    unit_price = fields.Monetary(string='Harga Satuan')
    subtotal = fields.Monetary(string='Jumlah', compute='_compute_subtotal', store=True)
    notes = fields.Text(string='Keterangan')
    currency_id = fields.Many2one(related='spk_id.currency_id')
    company_id = fields.Many2one(related='spk_id.company_id', store=True)

    @api.depends('qty', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_price
