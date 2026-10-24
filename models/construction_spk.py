from odoo import api, fields, models
from odoo.exceptions import UserError


class ConstructionSPK(models.Model):
    _name = 'construction.spk'
    _description = 'Surat Perintah Kerja'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Nomor SPK',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env._('Baru'),
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company, index=True,
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    project_id = fields.Many2one('project.project', string='Proyek', required=True, tracking=True)
    task_id = fields.Many2one(
        'project.task', string='Unit', required=True, tracking=True,
        domain="[('project_id', '=', project_id)]",
    )
    block = fields.Char(string='Blok')
    unit = fields.Char(string='Nomor Unit')
    unit_type = fields.Selection(
        [('a', 'Type A'), ('b', 'Type B'), ('c', 'Type C')],
        string='Tipe Unit',
    )
    discipline_id = fields.Many2one('construction.discipline', string='Jenis Pekerjaan', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Sub-Kontraktor', required=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', string='Telepon Sub-Kontraktor')
    user_id = fields.Many2one('res.users', string='PIC Internal', default=lambda self: self.env.user, tracking=True)
    date_issued = fields.Date(string='Tanggal Terbit', default=fields.Date.context_today)
    date_start = fields.Date(string='Mulai Rencana', required=True, tracking=True)
    date_end = fields.Date(string='Selesai Rencana', required=True, tracking=True)
    duration = fields.Integer(string='Durasi (Hari)', compute='_compute_duration')
    actual_start = fields.Date(string='Mulai Aktual')
    actual_end = fields.Date(string='Selesai Aktual')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Dikonfirmasi'),
            ('progress', 'Berjalan'),
            ('done', 'Selesai'),
            ('closed', 'Ditutup'),
        ],
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    progress = fields.Float(string='% Selesai', tracking=True)
    is_late = fields.Boolean(string='Lewat Jatuh Tempo', compute='_compute_is_late', search='_search_is_late')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Akun Analitik')
    line_ids = fields.One2many('construction.spk.line', 'spk_id', string='Lingkup Pekerjaan', copy=True)
    material_ids = fields.One2many('construction.spk.material', 'spk_id', string='Material', copy=True)
    timesheet_ids = fields.One2many('account.analytic.line', 'spk_id', string='Timesheet')
    total_work_value = fields.Monetary(string='Total Nilai Pekerjaan', compute='_compute_totals', store=True)
    total_material = fields.Monetary(string='Total Biaya Material', compute='_compute_totals', store=True)
    grand_total = fields.Monetary(string='Total Nilai SPK', compute='_compute_totals', store=True)

    _task_discipline_uniq = models.Constraint(
        'unique(task_id, discipline_id)',
        'Satu unit hanya boleh punya satu SPK untuk jenis pekerjaan yang sama.',
    )

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for spk in self:
            if spk.date_start and spk.date_end:
                spk.duration = (spk.date_end - spk.date_start).days
            else:
                spk.duration = 0

    @api.depends('date_end', 'state')
    def _compute_is_late(self):
        today = fields.Date.context_today(self)
        open_states = {'confirmed', 'progress'}
        for spk in self:
            spk.is_late = bool(
                spk.date_end and spk.date_end < today and spk.state in open_states
            )

    def _search_is_late(self, operator, value):
        # Odoo rewrites boolean "=" into "in" and then calls this method.
        # Only the positive "=" case is implemented; the framework inverts it.
        if operator != '=' or not value:
            return NotImplemented
        today = fields.Date.context_today(self)
        return [
            ('date_end', '<', today),
            ('state', 'in', ('confirmed', 'progress')),
        ]

    @api.depends('line_ids.subtotal', 'material_ids.total_cost')
    def _compute_totals(self):
        for spk in self:
            spk.total_work_value = sum(spk.line_ids.mapped('subtotal'))
            spk.total_material = sum(spk.material_ids.mapped('total_cost'))
            spk.grand_total = spk.total_work_value + spk.total_material

    def _values_from_task(self, task):
        if not task:
            return {}
        return {
            'project_id': task.project_id.id,
            'block': task.bpsp_block,
            'unit': task.bpsp_unit,
            'unit_type': task.bpsp_unit_type,
            'analytic_account_id': task.project_id.account_id.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        tasks = self.env['project.task'].browse([
            vals['task_id'] for vals in vals_list if vals.get('task_id')
        ])
        task_by_id = {task.id: task for task in tasks}
        for vals in vals_list:
            for field_name, value in self._values_from_task(task_by_id.get(vals.get('task_id'))).items():
                vals.setdefault(field_name, value)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('task_id') and not any(key in vals for key in ('block', 'unit', 'unit_type')):
            vals = dict(vals, **self._values_from_task(self.env['project.task'].browse(vals['task_id'])))
        return super().write(vals)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.task_id and self.task_id.project_id != self.project_id:
            self.task_id = False
        if self.project_id:
            self.analytic_account_id = self.project_id.account_id

    @api.onchange('task_id')
    def _onchange_task_id(self):
        task = self.task_id
        if not task:
            return
        self.project_id = task.project_id
        self.block = task.bpsp_block
        self.unit = task.bpsp_unit
        self.unit_type = task.bpsp_unit_type
        self.analytic_account_id = task.project_id.account_id

    @api.constrains('date_start', 'date_end', 'progress')
    def _check_dates_and_progress(self):
        for spk in self:
            if spk.date_start and spk.date_end and spk.date_end < spk.date_start:
                raise UserError(self.env._('Tanggal selesai rencana tidak boleh lebih awal dari tanggal mulai.'))
            if spk.progress < 0 or spk.progress > 100:
                raise UserError(self.env._('Persen selesai harus di antara 0 dan 100.'))

    def _assign_number(self):
        for spk in self.filtered(lambda record: not record.name or record.name == self.env._('Baru')):
            project_code = (spk.project_id.bpsp_code or 'PRJ').strip().upper()
            year = (spk.date_issued or fields.Date.context_today(spk)).year
            block = (spk.block or '').replace(' ', '')
            unit = (spk.unit or '').replace(' ', '')
            prefix = 'SPK/%s/%s/%s%s/' % (project_code, year, block, unit)
            last = self.search([('name', '=like', prefix + '%')], order='name desc', limit=1)
            sequence = 1
            if last and last.name.startswith(prefix):
                tail = last.name[len(prefix):]
                sequence = int(tail) + 1 if tail.isdigit() else self.search_count([('name', '=like', prefix + '%')]) + 1
            spk.name = '%s%03d' % (prefix, sequence)

    def action_confirm(self):
        for spk in self:
            if not spk.line_ids:
                raise UserError(self.env._('Isi lingkup pekerjaan sebelum mengonfirmasi SPK.'))
        self._assign_number()
        self.write({'state': 'confirmed'})

    def action_progress(self):
        today = fields.Date.context_today(self)
        for spk in self:
            spk.write({
                'state': 'progress',
                'actual_start': spk.actual_start or today,
            })

    def action_done(self):
        today = fields.Date.context_today(self)
        for spk in self:
            spk.write({
                'state': 'done',
                'actual_end': spk.actual_end or today,
                'progress': 100,
            })

    def action_close(self):
        self.write({'state': 'closed'})

    def action_draft(self):
        self.filtered(lambda spk: spk.state == 'confirmed').write({'state': 'draft'})

    def action_open_bom_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Muat Material dari BoM'),
            'res_model': 'spk.bom.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_spk_id': self.id},
        }
