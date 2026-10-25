{
    'name': 'BPSP Customization',
    'version': '19.0.1.0.0',
    'category': 'Customization',
    'summary': 'Construction SPK layer on standard Project, Purchase, MRP, Inventory & Timesheets',
    'description': """
BPSP Construction Management customization.

Standard Odoo modules are pulled via depends (auto-install with this module).
Custom work is limited to the SPK (Surat Perintah Kerja) layer on top.
    """,
    'depends': [
        # Core
        'base',
        'mail',
        # Project & planning (units as tasks, Gantt/timeline)
        'project',
        'project_enterprise',
        # Procurement (RFQ → PO; Purchase Request; PO ↔ stock)
        'purchase',
        'purchase_requisition',
        'purchase_stock',
        # Materials / BoM
        'mrp',
        # Inventory & warehouse + AVCO valuation
        'stock',
        'stock_account',
        # Cost centers / budget vs actuals
        'analytic',
        # Labor hours on SPK / unit task
        'hr_timesheet',
        # Sub-contractor portal access (optional logging)
        'portal',
    ],
    'data': [
        'security/spk_security.xml',
        'security/ir.model.access.csv',
        'security/spk_rules.xml',
        'data/product_category_data.xml',
        'data/construction_discipline_data.xml',
        'data/foundation_setup.xml',
        'views/construction_spk_views.xml',
        'views/project_task_views.xml',
        'views/menus.xml',
        'views/favicon_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {},
    'author': 'GWU-Studio',
    'license': 'LGPL-3',
}
