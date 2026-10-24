from odoo import fields, models
from odoo.exceptions import UserError


class SPKFromBOMWizard(models.TransientModel):
    _name = 'spk.bom.wizard'
    _description = 'Muat Material SPK dari BoM'

    spk_id = fields.Many2one('construction.spk', required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True)
    quantity = fields.Float(string='Jumlah Unit', default=1.0, required=True)

    def action_load_materials(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError(self.env._('Jumlah unit harus lebih dari 0.'))
        material_model = self.env['construction.spk.material']
        for line in self.bom_id.bom_line_ids:
            planned_qty = line.product_qty * self.quantity
            existing = self.spk_id.material_ids.filtered(lambda material: material.product_id == line.product_id)[:1]
            if existing:
                existing.planned_qty += planned_qty
                continue
            material_model.create({
                'spk_id': self.spk_id.id,
                'product_id': line.product_id.id,
                'uom_id': line.product_uom_id.id,
                'planned_qty': planned_qty,
                'unit_cost': line.product_id.standard_price,
            })
        return {'type': 'ir.actions.act_window_close'}
