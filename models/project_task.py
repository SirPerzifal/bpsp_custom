from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    bpsp_block = fields.Char(string='Blok')
    bpsp_unit = fields.Char(string='Nomor Unit')
    bpsp_unit_type = fields.Selection(
        [('a', 'Type A'), ('b', 'Type B'), ('c', 'Type C')],
        string='Tipe Unit',
    )
    spk_ids = fields.One2many('construction.spk', 'task_id', string='SPK')
    spk_count = fields.Integer(compute='_compute_spk_progress')
    spk_progress = fields.Float(string='% SPK', compute='_compute_spk_progress')

    @api.depends('spk_ids.progress', 'spk_ids.state')
    def _compute_spk_progress(self):
        for task in self:
            spks = task.spk_ids
            task.spk_count = len(spks)
            task.spk_progress = sum(spks.mapped('progress')) / len(spks) if spks else 0.0

    def action_view_spk(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('bpsp_custom.action_construction_spk')
        action['domain'] = [('task_id', '=', self.id)]
        action['context'] = {
            'default_task_id': self.id,
            'default_project_id': self.project_id.id,
            'default_block': self.bpsp_block,
            'default_unit': self.bpsp_unit,
            'default_unit_type': self.bpsp_unit_type,
        }
        if self.spk_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.spk_ids.id
            action['views'] = [(False, 'form')]
        return action
