"""Load the client workbook into BPSP_CUSTOM.

Real values come from BPSP_Client_Data_Request.xlsx (25 Oct 2026).
Rows the client left empty are created as dummy data and tagged so they
can be removed at go-live. Run from the Odoo shell:

    ./odoo-bin shell -c ./debian/odoo-2.conf -d BPSP_CUSTOM < addons/bpsp_custom/scripts/load_client_master_data.py
"""
from odoo import Command

DUMMY = 'DUMMY — ganti saat go-live'
TEMP_PASSWORD = 'BpspTemp2026'

company = env.company
partner = company.partner_id
indonesia = env.ref('base.id', raise_if_not_found=False)
partner.write({
    'name': 'PT Bangun Prima Sejati Propertindo',
    'street': 'Jalan Permata Puri Komplek Cipta Griya No. 1-5 Batu Aji - Batam',
    'phone': '0778 - 332344',
    'vat': '81.359.876.0.225.000',
    'email': False,
    'website': False,
    'country_id': indonesia.id if indonesia else False,
    'lang': 'id_ID',
})
company.name = partner.name

bank = env['res.bank'].search([('name', '=', 'BCA')], limit=1)
if not bank:
    bank = env['res.bank'].create({'name': 'BCA'})
account_number = '8550912024'
bank_account = env['res.partner.bank'].search([
    ('acc_number', '=', account_number),
    ('partner_id', '=', partner.id),
], limit=1)
if not bank_account:
    env['res.partner.bank'].create({
        'acc_number': account_number,
        'partner_id': partner.id,
        'bank_id': bank.id,
        'acc_holder_name': partner.name,
    })

if 'po_double_validation' in company._fields:
    company.po_double_validation = 'two_step'
    company.po_double_validation_amount = 50000000

params = env['ir.config_parameter'].sudo()
params.set_param('bpsp_custom.po_threshold_is_dummy', '1')
params.set_param(
    'bpsp_custom.pending_client_decisions',
    'Tipe rumah dan aturan satu SPK ditandai Perlu diubah, tetapi kotak pengganti kosong. '
    'Jam kerja sub-kontraktor tidak dijawab. Tetap dipakai: Type A/B/C, satu SPK per pekerjaan per unit, supervisor mengisi jam.',
)


def phone(number):
    digits = ''.join(character for character in str(number) if character.isdigit())
    if digits.startswith('62'):
        digits = '0' + digits[2:]
    elif not digits.startswith('0'):
        digits = '0' + digits
    return digits


def ensure_user(name, login, phone_number, group_xmlids):
    user = env['res.users'].search([('login', '=', login)], limit=1)
    groups = env['res.groups'].browse([env.ref(xmlid).id for xmlid in group_xmlids])
    values = {
        'name': name,
        'login': login,
        'email': login if not login.endswith('.invalid') else False,
        'phone': phone_number,
        'lang': 'id_ID',
        'tz': 'Asia/Jakarta',
        'group_ids': [Command.link(group.id) for group in groups],
    }
    if user:
        user.write(values)
    else:
        values['password'] = TEMP_PASSWORD
        user = env['res.users'].with_context(no_reset_password=True).create(values)
    return user


ensure_user('David Liang', 'vidz991@gmail.com', phone('82133886698'), [
    'project.group_project_manager',
    'bpsp_custom.group_spk_manager',
    'purchase.group_purchase_manager',
    'stock.group_stock_manager',
    'analytic.group_analytic_accounting',
])
ensure_user('Ruslan Weng', 'wengcizhen@gmail.com', phone('85264418488'), [
    'project.group_project_manager',
    'bpsp_custom.group_spk_manager',
    'analytic.group_analytic_accounting',
])
ensure_user('Farhan Aulia Rahman', 'farhan.aulia@bpsp.invalid', phone('82241160075'), [
    'project.group_project_manager',
    'bpsp_custom.group_spk_manager',
])
ensure_user('Elvin', 'elvin.procurement@bpsp.invalid', phone('82268318899'), [
    'purchase.group_purchase_user',
    'stock.group_stock_user',
    'bpsp_custom.group_spk_user',
])
ensure_user('Jani', 'jani.finance@bpsp.invalid', phone('81276507077'), [
    'account.group_account_invoice',
    'analytic.group_analytic_accounting',
    'purchase.group_purchase_user',
])

warehouse = env.ref('stock.warehouse0')
warehouse.name = 'Gudang Utama'
parent = warehouse.view_location_id


def ensure_location(name, comment):
    location = env['stock.location'].search([
        ('name', '=', name),
        ('location_id', '=', parent.id),
    ], limit=1)
    if not location:
        location = env['stock.location'].create({
            'name': name,
            'usage': 'internal',
            'location_id': parent.id,
            'company_id': company.id,
        })
    return location


aster_location = ensure_location('Aster Tropika', 'Kabil - Batam')
foresta_location = ensure_location('Villa Foresta', 'Tanjung Pinggir - Batam')
transfer = env.ref('bpsp_custom.action_transfer_to_site', raise_if_not_found=False)
if transfer:
    transfer.context = repr({
        'default_picking_type_id': warehouse.int_type_id.id,
        'default_location_id': warehouse.lot_stock_id.id,
        'default_location_dest_id': aster_location.id,
    })


def ensure_project(name, code, dummy_code=False):
    project = env['project.project'].search([('bpsp_code', '=', code)], limit=1)
    if not project:
        project = env['project.project'].create({
            'name': name,
            'bpsp_code': code,
            'allow_timesheets': True,
        })
    else:
        project.write({'name': name, 'allow_timesheets': True})
    if not project.account_id and hasattr(project, '_create_analytic_account'):
        project._create_analytic_account()
    if dummy_code and project.account_id:
        project.account_id.name = '%s (%s)' % (name, DUMMY)
    stages = {}
    for sequence, block_name in ((1, 'Blok A'), (2, 'Blok B')):
        stage = env['project.task.type'].search([
            ('name', '=', block_name),
            ('project_ids', 'in', project.id),
        ], limit=1)
        if not stage:
            stage = env['project.task.type'].create({
                'name': block_name,
                'sequence': sequence,
                'project_ids': [Command.link(project.id)],
            })
        stages[block_name] = stage
    units = [
        ('A', '01', 'a', 'Blok A'),
        ('A', '02', 'a', 'Blok A'),
        ('B', '01', 'b', 'Blok B'),
    ]
    for block, number, unit_type, stage_name in units:
        task_name = '%s-%s' % (block, number)
        task = env['project.task'].search([
            ('project_id', '=', project.id),
            ('bpsp_block', '=', block),
            ('bpsp_unit', '=', number),
        ], limit=1)
        values = {
            'name': task_name,
            'project_id': project.id,
            'bpsp_block': block,
            'bpsp_unit': number,
            'bpsp_unit_type': unit_type,
            'stage_id': stages[stage_name].id,
            'description': DUMMY,
        }
        if task:
            task.write(values)
        else:
            env['project.task'].create(values)
    return project


ensure_project('Aster Tropika', 'Astro')
ensure_project('Villa Foresta', 'VF', dummy_code=True)

category_by_code = {
    'STR': env.ref('bpsp_custom.product_category_str'),
    'ARC': env.ref('bpsp_custom.product_category_arc'),
    'PLB': env.ref('bpsp_custom.product_category_plb'),
    'ELC': env.ref('bpsp_custom.product_category_elc'),
    'FIN': env.ref('bpsp_custom.product_category_fin'),
    'DRW': env.ref('bpsp_custom.product_category_drw'),
    'LND': env.ref('bpsp_custom.product_category_lnd'),
    'OTH': env.ref('bpsp_custom.product_category_oth'),
}
unit = env.ref('uom.product_uom_unit')
materials = [
    ('DUMMY-SEMEN', 'Semen [DUMMY]', 'STR', 100),
    ('DUMMY-BESI', 'Besi Beton [DUMMY]', 'STR', 50),
    ('DUMMY-BATA', 'Bata Merah [DUMMY]', 'STR', 1000),
    ('DUMMY-KERAMIK', 'Keramik [DUMMY]', 'ARC', 80),
    ('DUMMY-PIPA', 'Pipa PVC [DUMMY]', 'PLB', 40),
    ('DUMMY-KABEL', 'Kabel NYM [DUMMY]', 'ELC', 30),
    ('DUMMY-CAT', 'Cat Tembok [DUMMY]', 'FIN', 20),
    ('DUMMY-KUSEN', 'Kusen Kayu [DUMMY]', 'DRW', 10),
    ('DUMMY-RUMPUT', 'Rumput [DUMMY]', 'LND', 20),
    ('DUMMY-PAKU', 'Paku [DUMMY]', 'OTH', 10),
]
product_by_code = {}
for code, name, category_code, min_qty in materials:
    product = env['product.product'].search([('default_code', '=', code)], limit=1)
    values = {
        'name': name,
        'default_code': code,
        'type': 'consu',
        'is_storable': True,
        'purchase_ok': True,
        'sale_ok': False,
        'categ_id': category_by_code[category_code].id,
        'uom_id': unit.id,
        'standard_price': 10000,
        'description': DUMMY,
    }
    if product:
        product.write(values)
    else:
        product = env['product.product'].create(values)
    product_by_code[code] = product
    orderpoint = env['stock.warehouse.orderpoint'].search([
        ('product_id', '=', product.id),
        ('location_id', '=', warehouse.lot_stock_id.id),
    ], limit=1)
    order_values = {
        'product_id': product.id,
        'location_id': warehouse.lot_stock_id.id,
        'product_min_qty': min_qty,
        'product_max_qty': min_qty * 2,
        'company_id': company.id,
    }
    if orderpoint:
        orderpoint.write(order_values)
    else:
        env['stock.warehouse.orderpoint'].create(order_values)

vendors = [
    ('DUMMY-BETON', 'CV Beton Jaya [DUMMY]', 'Struktur', 'Budi'),
    ('DUMMY-CAT', 'CV Cat Indah [DUMMY]', 'Finishing', 'Andi'),
    ('DUMMY-LISTRIK', 'CV Listrik Prima [DUMMY]', 'Elektrikal', 'Sari'),
    ('DUMMY-SUMBER', 'PT Sumber Material [DUMMY]', 'Vendor material', 'Dewi'),
]
for ref, name, note, contact in vendors:
    vendor = env['res.partner'].search([('ref', '=', ref)], limit=1)
    values = {
        'name': name,
        'ref': ref,
        'supplier_rank': 1,
        'company_type': 'company',
        'comment': '%s. Kontak %s. %s' % (DUMMY, contact, note),
        'lang': 'id_ID',
    }
    if vendor:
        vendor.write(values)
    else:
        env['res.partner'].create(values)

houses = {}
for code, label in (('A', 'Type A'), ('B', 'Type B'), ('C', 'Type C')):
    default_code = 'DUMMY-RUMAH-%s' % code
    house = env['product.product'].search([('default_code', '=', default_code)], limit=1)
    values = {
        'name': 'Rumah %s [DUMMY]' % label,
        'default_code': default_code,
        'type': 'consu',
        'purchase_ok': False,
        'sale_ok': False,
        'description': DUMMY,
    }
    houses[code] = house.write(values) and house if house else env['product.product'].create(values)
    if house:
        houses[code] = env['product.product'].search([('default_code', '=', default_code)], limit=1)

bom_material = {
    'STR': 'DUMMY-BATA',
    'ARC': 'DUMMY-KERAMIK',
    'PLB': 'DUMMY-PIPA',
    'ELC': 'DUMMY-KABEL',
    'FIN': 'DUMMY-CAT',
    'DRW': 'DUMMY-KUSEN',
    'LND': 'DUMMY-RUMPUT',
    'OTH': 'DUMMY-PAKU',
}
qty_by_type = {'A': 10, 'B': 12, 'C': 15}
for type_code, house in houses.items():
    for discipline_code, material_code in bom_material.items():
        bom_code = 'DUMMY-BOM-%s-%s' % (type_code, discipline_code)
        bom = env['mrp.bom'].search([('code', '=', bom_code)], limit=1)
        component = product_by_code[material_code]
        line_values = {
            'product_id': component.id,
            'product_qty': qty_by_type[type_code],
            'product_uom_id': unit.id,
        }
        if bom:
            bom.write({'product_qty': 1, 'product_tmpl_id': house.product_tmpl_id.id})
            if bom.bom_line_ids:
                bom.bom_line_ids[:1].write(line_values)
            else:
                bom.write({'bom_line_ids': [Command.create(line_values)]})
        else:
            env['mrp.bom'].create({
                'product_tmpl_id': house.product_tmpl_id.id,
                'product_qty': 1,
                'code': bom_code,
                'bom_line_ids': [Command.create(line_values)],
            })

env.cr.commit()
print('LOADED', company.name)
print('USERS', env['res.users'].search_count([('share', '=', False)]))
print('PROJECTS', env['project.project'].search([('bpsp_code', 'in', ['Astro', 'VF'])]).mapped('name'))
print('UNITS', env['project.task'].search_count([('description', 'ilike', 'DUMMY')]))
print('MATERIALS', len(product_by_code))
print('BOMS', env['mrp.bom'].search_count([('code', '=like', 'DUMMY-BOM-%')]))
print('SITES', aster_location.complete_name, foresta_location.complete_name)
