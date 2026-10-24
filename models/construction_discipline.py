from odoo import fields, models


class ConstructionDiscipline(models.Model):
    _name = 'construction.discipline'
    _description = 'Jenis Pekerjaan SPK'
    _order = 'sequence, code'

    name = fields.Char(string='Jenis Pekerjaan', required=True, translate=True)
    code = fields.Char(string='Kode', required=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one('product.category', string='Kategori Material')
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        'unique(code)',
        'Kode jenis pekerjaan harus unik.',
    )
