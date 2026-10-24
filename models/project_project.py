from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    bpsp_code = fields.Char(
        string='Kode Proyek',
        help='Kode singkat untuk nomor SPK. Contoh: GI menghasilkan SPK/GI/2026/A01/001.',
    )
