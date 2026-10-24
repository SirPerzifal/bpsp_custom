import logging

from odoo import Command, api, models

_logger = logging.getLogger(__name__)

LANG_CODE = 'id_ID'
TIMEZONE = 'Asia/Jakarta'


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _bpsp_apply_foundation(self):
        """Company locale and warehouse skeleton from the construction SRS.

        Legal name, address, NPWP, and real site names stay untouched until
        the client data sheet is filled in.
        """
        self._bpsp_set_currency_idr()
        self._bpsp_install_bahasa()
        self._bpsp_set_timezone()
        self._bpsp_set_avco()
        self._bpsp_set_warehouse()
        self._bpsp_set_site_route()

    @api.model
    def _bpsp_set_currency_idr(self):
        idr = self.env.ref('base.IDR', raise_if_not_found=False)
        if not idr:
            _logger.warning('BPSP: currency IDR was not found.')
            return
        if not idr.active:
            idr.active = True
        company = self.env.company
        if company.currency_id != idr:
            company.currency_id = idr

    @api.model
    def _bpsp_install_bahasa(self):
        lang = self.env['res.lang'].with_context(active_test=False).search([
            ('code', '=', LANG_CODE),
        ], limit=1)
        if not lang:
            _logger.warning('BPSP: language %s was not found.', LANG_CODE)
            return
        if not lang.active:
            wizard = self.env['base.language.install'].create({
                'lang_ids': [Command.set(lang.ids)],
                'overwrite': False,
            })
            wizard.lang_install()
        self.env['ir.default'].set('res.partner', 'lang', LANG_CODE)
        company = self.env.company
        if company.partner_id.lang != LANG_CODE:
            company.partner_id.lang = LANG_CODE
        users = self.env['res.users'].search([('share', '=', False)])
        for user in users.filtered(lambda user: not user.lang or user.lang == 'en_US'):
            user.lang = LANG_CODE

    @api.model
    def _bpsp_set_timezone(self):
        self.env['ir.default'].set('res.users', 'tz', TIMEZONE)
        users = self.env['res.users'].search([('share', '=', False)])
        for user in users.filtered(lambda user: not user.tz or user.tz in ('UTC', 'GMT')):
            user.tz = TIMEZONE

    @api.model
    def _bpsp_set_avco(self):
        company = self.env.company
        if 'cost_method' not in company._fields:
            return
        if company.cost_method != 'average':
            company.cost_method = 'average'
        if hasattr(company, '_set_category_defaults'):
            company._set_category_defaults()
        categories = self.env['product.category'].search([])
        pending = categories.filtered(lambda category: category.property_cost_method != 'average')
        if pending:
            pending.write({'property_cost_method': 'average'})

    @api.model
    def _bpsp_set_warehouse(self):
        warehouse = self.env.ref('stock.warehouse0', raise_if_not_found=False)
        if not warehouse:
            return
        if warehouse.name in ('My Company', 'MyCompany'):
            warehouse.name = 'Gudang Utama'
        parent = warehouse.view_location_id
        if not parent:
            return
        location_model = self.env['stock.location']
        site = location_model.search([
            ('name', '=', 'Site Proyek'),
            ('location_id', '=', parent.id),
            ('company_id', '=', warehouse.company_id.id),
        ], limit=1)
        if not site:
            site = location_model.create({
                'name': 'Site Proyek',
                'usage': 'internal',
                'location_id': parent.id,
                'company_id': warehouse.company_id.id,
            })
        self.env['ir.model.data']._update_xmlids([{
            'xml_id': 'bpsp_custom.stock_location_site',
            'record': site,
            'noupdate': True,
        }])

    @api.model
    def _bpsp_set_site_route(self):
        """Pull route used only when stock is requested at the site location.

        It is not applied to products, so receipts stay in the main warehouse
        until someone transfers them.
        """
        warehouse = self.env.ref('stock.warehouse0', raise_if_not_found=False)
        site = self.env.ref('bpsp_custom.stock_location_site', raise_if_not_found=False)
        if not site and warehouse:
            site = self.env['stock.location'].search([
                ('name', '=', 'Site Proyek'),
                ('location_id', '=', warehouse.view_location_id.id),
            ], limit=1)
        if not warehouse or not site or not warehouse.int_type_id or not warehouse.lot_stock_id:
            return
        route = self.env.ref('bpsp_custom.route_wh_to_site', raise_if_not_found=False)
        if not route:
            route = self.env['stock.route'].create({
                'name': 'Gudang Utama ke Site',
                'product_selectable': False,
                'product_categ_selectable': False,
                'warehouse_selectable': False,
                'company_id': warehouse.company_id.id,
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': 'bpsp_custom.route_wh_to_site',
                'record': route,
                'noupdate': True,
            }])
        rule = self.env.ref('bpsp_custom.rule_wh_to_site', raise_if_not_found=False)
        if not rule:
            rule = self.env['stock.rule'].create({
                'name': 'Transfer Gudang Utama ke Site',
                'action': 'pull',
                'route_id': route.id,
                'location_src_id': warehouse.lot_stock_id.id,
                'location_dest_id': site.id,
                'picking_type_id': warehouse.int_type_id.id,
                'warehouse_id': warehouse.id,
                'procure_method': 'make_to_stock',
                'company_id': warehouse.company_id.id,
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': 'bpsp_custom.rule_wh_to_site',
                'record': rule,
                'noupdate': True,
            }])
