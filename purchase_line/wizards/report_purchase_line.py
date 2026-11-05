# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import json
import re
from datetime import datetime


class ResUsers(models.Model):
    _inherit = 'res.users'

    purchase_lines_report_column_ids = fields.Many2many(
        comodel_name='purchase.lines.report.column',
        string='Columnas reporte líneas de compra',
        domain=[('active', '=', True)],
    )


class PurchaseLinesReport(models.TransientModel):
    _name = "purchase.lines.report"
    _description = "Reporte de líneas de compra"

    line_ids = fields.One2many(
        string="Lineas de Factura de Proveedor",
        comodel_name="purchase.lines.report.register",
        inverse_name="return_id",
    )

    columns_to_show_ids = fields.Many2many(
        comodel_name='purchase.lines.report.column',
        string='Columnas a mostrar',
        domain=[('active', '=', True)],
    )

    @api.model
    def default_get(self, fields_list):
        res = super(PurchaseLinesReport, self).default_get(fields_list)
        
        user = self.env.user
        if user.purchase_lines_report_column_ids:
            res['columns_to_show_ids'] = [(6, 0, user.purchase_lines_report_column_ids.ids)]
        else:
            all_columns = self.env['purchase.lines.report.column'].search([('active', '=', True)])
            res['columns_to_show_ids'] = [(6, 0, all_columns.ids)]

        register_ids = []
        
        # Filtra solo Facturas de Proveedor (in_invoice) o Notas de Crédito de Proveedor (in_refund)
        account_move_ids = self.env["account.move"].search(
            [("id", "in", self.env.context.get("active_ids", [])),
             ("move_type", "in", ["in_invoice", "in_refund"])]
        )
        
        if account_move_ids:
            for am in account_move_ids:
                purchase_order_ids = None
                
                lotes = am._get_invoiced_lot_values()
                
                if am.invoice_origin:
                    purchase_order_ids = self.env["purchase.order"].search(
                        [("name", "=", am.invoice_origin), ("state", "not in", ["cancel"])]
                    )

                if am.invoice_line_ids:
                    for ili in am.invoice_line_ids:
                        if ili.display_type == "product":
                            discount = ili.discount
                            
                            unit_price_ves = 0.0
                            unit_price_usd = 0.0
                            price_subtotal_ves = 0.0
                            price_subtotal_usd = 0.0
                            
                            tasa = getattr(am, 'x_tasa', 0.0)

                            if am.currency_id.name == "VES":
                                unit_price_ves = ili.price_unit
                                unit_price_usd = round(ili.price_unit / tasa, 2) if tasa else 0.0
                                price_subtotal_ves = ili.price_subtotal
                                price_subtotal_usd = round(ili.price_subtotal / tasa, 2) if tasa else 0.0

                            elif am.currency_id.name == "USD":
                                unit_price_ves = round(ili.price_unit * tasa, 2) if tasa else 0.0
                                unit_price_usd = ili.price_unit
                                price_subtotal_ves = round(ili.price_subtotal * tasa, 2) if tasa else 0.0
                                price_subtotal_usd = ili.price_subtotal



                            lote = ""
                            stock_move_lines = self.env['stock.move.line'].search([
                                ('move_id.purchase_line_id.invoice_lines', 'in', ili.id),
                                ('lot_id', '!=', False)
                            ])
                            
                            if not stock_move_lines and purchase_order_ids:
                                for po in purchase_order_ids:
                                    receipts = self.env['stock.picking'].search([
                                        ('purchase_id', '=', po.id),
                                        ('state', '=', 'done')
                                    ])
                                    
                                    if receipts:
                                        stock_move_lines = self.env['stock.move.line'].search([
                                            ('picking_id', 'in', receipts.ids),
                                            ('product_id', '=', ili.product_id.id),
                                            ('lot_id', '!=', False) 
                                        ], limit=1)
                                    
                            if stock_move_lines:
                                lote = stock_move_lines[0].lot_id.name
                            """ Obtener Lote
                            lote = ""
                            if lotes:
                                for l in lotes:
                                    if l["product_name"] == ili.product_id.display_name:
                                        lote = l.get("lot_name", "")
                                        break"""
                                        
                            unit_cost = unit_price_ves
                            total_cost = unit_cost * ili.quantity
                            
                            margen = 0.0 
                            
                            # Obtener categoría del producto
                            product_categ_id = ili.product_id.categ_id.id if ili.product_id.categ_id else False
                            
                            packaging_qty = 0.0
                            packaging_uom_id = False
                            
                            if purchase_order_ids:
                                for po in purchase_order_ids:
                                    po_line = po.order_line.filtered(lambda l: l.product_id.id == ili.product_id.id)
                                    if po_line:
                                        packaging_qty = getattr(po_line[0], 'product_packaging_qty', 0.0)
                                        uom = getattr(po_line[0], 'product_uom_id', False) or getattr(po_line[0], 'product_uom', False)
                                        packaging_uom_id = uom.id if uom else False
                                        break

                            partner_shipping = am.partner_shipping_id or am.partner_id
                            delivery_address = partner_shipping.contact_address_complete if hasattr(partner_shipping, 'contact_address_complete') else partner_shipping.contact_address or False

                            if not delivery_address:
                                delivery_address = ''
                            delivery_address = ','.join([x.strip() for x in delivery_address.split(',')])

                            #numero de recepcion
                            receipt_numbers = ""
                            if purchase_order_ids:
                                receipts = self.env['stock.picking'].search([
                                    ('purchase_id', 'in', purchase_order_ids.ids),
                                    ('state', '=', 'done')
                                ])
                                if receipts:
                                    receipt_numbers = ", ".join(receipts.mapped('name'))
                            
                            estados = {
                                'not_paid': 'No Pagado',
                                'in_payment': 'En Proceso de Pago',
                                'paid': 'Pagado',
                                'partial': 'Parcial',
                                'reversed': 'Revertido',
                                'invoicing_legacy': 'Facturación Legada',
                                'unknown': 'Desconocido',
                                '': '',
                            }
                            payment_state = estados.get(am.payment_state, am.payment_state) if hasattr(am, 'payment_state') else ''

                            vals = {
                                "order_numbers": ", ".join(
                                    purchase_order_ids.mapped("name") if purchase_order_ids else ""
                                ),
                                "order_date": (
                                    ", ".join(
                                        fecha.strftime("%d/%m/%Y")
                                        for fecha in purchase_order_ids.mapped("date_order")
                                    )
                                    if purchase_order_ids
                                    else ""
                                ),
                                "partner_id": am.partner_id.id, # Proveedor
                                "product_id": ili.product_id.id,
                                "team_id": am.team_id.id if hasattr(am, 'team_id') else False,
                                "seller_id": am.invoice_user_id.id if hasattr(am, 'invoice_user_id') else False,
                                "quantity": ili.quantity,
                                "product_uom_id": ili.product_uom_id.id,
                                "ref": am.ref, # Referencia de Factura
                                "invoice_date": am.invoice_date,
                                "discount": discount,
                                "invoice_rate": tasa,
                                "unit_price_ves": unit_price_ves,
                                "unit_price_usd": unit_price_usd,
                                "price_subtotal_ves": price_subtotal_ves,
                                "price_subtotal_usd": price_subtotal_usd,
                                "currency_invoice_id": am.currency_id.id,
                                "lote": lote,
                                "unit_cost": unit_cost, # Costo = Precio Unitario VES
                                "total_cost": total_cost,
                                "margen": round(margen, 2),
                                "product_categ_id": product_categ_id,
                                "packaging_qty": packaging_qty,
                                "packaging_uom_id": packaging_uom_id,
                                "delivery_address": delivery_address,
                                "payment_state": payment_state,
                                "receipt_number": receipt_numbers,
                            }

                            register_id = self.env[
                                "purchase.lines.report.register"
                            ].create(vals)
                            register_ids.append(register_id.id)

        res["line_ids"] = [(6, 0, register_ids)]
        return res

    def write(self, vals):
        if 'columns_to_show_ids' in vals:
            self.env.user.purchase_lines_report_column_ids = [(6, 0, vals['columns_to_show_ids'][0][2])]
        return super().write(vals)

    def act_confirm(self):
        data = {
            "model": "purchase.lines.report",
            "purchase_lines_register_ids": self.line_ids.ids,
            "columns_to_show_ids": self.columns_to_show_ids.ids,
        }
        raise UserError("Implementar la acción de reporte PDF (purchase_lines_pdf_action_report)")

    def act_confirm_xls(self):
        data = {
            "model": "purchase.lines.report",
            "purchase_lines_register_ids": self.line_ids.ids,
            "columns_to_show_ids": self.columns_to_show_ids.ids,
        }
        return self.env.ref(
            "purchase_line.purchase_lines_xls_action_report"
        ).report_action(self, data=data)


class PurchaseLinesReportLines(models.TransientModel):
    _name = "purchase.lines.report.register"
    _description = "Registro reporte de líneas de compra"

    return_id = fields.Many2one(
        comodel_name="purchase.lines.report", string="Purchase Report"
    )
    # Campos adaptados
    order_numbers = fields.Char(string="Número de PO", readonly=True, store=True)
    partner_id = fields.Many2one(
        "res.partner", string="Proveedor", readonly=True, store=True
    )
    ref = fields.Char(string="Ref. Factura", readonly=True, store=True)
    invoice_date = fields.Date(
        string="Fecha Factura", readonly=True, store=True)
    team_id = fields.Many2one(
        "crm.team", string="Equipo", readonly=True, store=True)
    seller_id = fields.Many2one(
        "res.users", string="Comprador", readonly=True, store=True
    )
    product_id = fields.Many2one(
        comodel_name="product.product", string="Producto", readonly=True
    )
    product_code = fields.Char(
        related="product_id.default_code",
        string="Código del Producto",
        readonly=True,
        store=True,
    )
    product_name = fields.Char(
        related="product_id.name",
        string="Descripción del Producto",
        readonly=True,
        store=True,
    )
    quantity = fields.Float(string="Cantidad", readonly=True)
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom", string="UdM", readonly=True
    )
    discount = fields.Float(
        string="Discount (%)", digits="Discount", default=0.0)
    invoice_rate = fields.Float(
        string="Tasa Factura", readonly=True, store=True, digits=(12, 4)
    )
    unit_price_ves = fields.Float(
        string="Precio Unit. VES", readonly=True, store=True)
    unit_price_usd = fields.Float(
        string="Precio Unit. USD", readonly=True, store=True)
    price_subtotal_ves = fields.Float(
        string="Subtotal VES", readonly=True, store=True)
    price_subtotal_usd = fields.Float(
        string="Subtotal USD", readonly=True, store=True)
    currency_invoice_id = fields.Many2one(
        "res.currency", string="Moneda Factura", readonly=True, store=True
    )
    order_date = fields.Char(string="Fecha de PO", readonly=True)
    lote = fields.Char(string="Lote", readonly=True)
    unit_cost = fields.Float(string="Costo/Precio Compra (VES)", readonly=True, store=True)
    total_cost = fields.Float(string="Costo Total", readonly=True, store=True)
    margen = fields.Float(string="Margen %", readonly=True, store=True)
    product_categ_id = fields.Many2one(
        comodel_name="product.category", string="Categoría del Producto", readonly=True, store=True
    )
    packaging_qty = fields.Float(string="Cantidad Embalaje", readonly=True, store=True)
    packaging_uom_id = fields.Many2one(
        comodel_name="uom.uom", string="Unidad Embalaje", readonly=True, store=True
    )
    delivery_address = fields.Char(string="Dirección de Entrega", readonly=True, store=True)
    payment_state = fields.Char(string="Estado de Pago", readonly=True, store=True)
    receipt_number = fields.Char(string="Nº de Recepción", readonly=True, store=True)