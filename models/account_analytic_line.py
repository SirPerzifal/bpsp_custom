from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    spk_id = fields.Many2one('construction.spk', string='SPK', index=True, ondelete='set null')

    @api.onchange('spk_id')
    def _onchange_spk_id(self):
        if not self.spk_id:
            return
        self.project_id = self.spk_id.project_id
        self.task_id = self.spk_id.task_id
        if not self.name:
            self.name = self.spk_id.name

    @api.model_create_multi
    def create(self, vals_list):
        spks = self.env['construction.spk'].browse([
            vals['spk_id'] for vals in vals_list if vals.get('spk_id')
        ])
        spk_by_id = {spk.id: spk for spk in spks}
        for vals in vals_list:
            spk = spk_by_id.get(vals.get('spk_id'))
            if not spk:
                continue
            vals.setdefault('project_id', spk.project_id.id)
            vals.setdefault('task_id', spk.task_id.id)
            vals.setdefault('name', spk.name or '/')
        return super().create(vals_list)
