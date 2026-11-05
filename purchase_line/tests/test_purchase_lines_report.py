from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestPurchaseLinesReport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.env.user.group_ids += cls.env.ref('account.group_account_manager')
        # Sin layout de documento Odoo devuelve el asistente de configuracion en vez
        # de la accion del reporte.
        cls.company.external_report_layout_id = cls.env.ref('web.external_layout_standard')

    def _bill(self, products):
        bill = self.env['account.move'].with_company(self.company).create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({
                'product_id': product.id, 'quantity': 2, 'price_unit': 10.0,
            }) for product in products],
        })
        bill.action_post()
        return bill

    def _wizard(self, bill):
        return self.env['purchase.lines.report'].with_context(
            active_model='account.move', active_ids=bill.ids).create({})

    def test_default_columns_are_loaded(self):
        columns = self.env['purchase.lines.report.column'].search([('active', '=', True)])
        self.assertTrue(columns, "El addon debe cargar las columnas por defecto")
        wizard = self._wizard(self.env['account.move'])
        self.assertEqual(wizard.columns_to_show_ids, columns)

    def test_wizard_builds_one_line_per_product_line_of_the_bill(self):
        bill = self._bill(self.product_a | self.product_b)

        wizard = self._wizard(bill)

        self.assertEqual(len(wizard.line_ids), 2)
        self.assertEqual(
            set(wizard.line_ids.mapped('partner_id')), {bill.partner_id})

    def test_xls_report_renders(self):
        bill = self._bill(self.product_a | self.product_b)
        wizard = self._wizard(bill)

        action = wizard.act_confirm_xls()
        self.assertEqual(action['type'], 'ir.actions.report')
        data = {
            'model': 'purchase.lines.report',
            'purchase_lines_register_ids': wizard.line_ids.ids,
            'columns_to_show_ids': wizard.columns_to_show_ids.ids,
        }
        content, report_format = self.env['ir.actions.report']._render_xlsx(
            'purchase_line.purchase_lines_xls_action_report', wizard.ids, data)

        self.assertEqual(report_format, 'xlsx')
        self.assertTrue(content.startswith(b'PK'), "El XLSX es un zip")

    def test_import_costs_report_renders(self):
        bill = self._bill(self.product_a)
        content, report_format = self.env['ir.actions.report']._render_xlsx(
            'purchase_line.import_costs_xls_action_report', bill.ids, None)

        self.assertEqual(report_format, 'xlsx')
        self.assertTrue(content.startswith(b'PK'))
