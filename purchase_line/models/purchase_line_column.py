# -*- coding: utf-8 -*-

from odoo import fields, models

class PurchaseLinesReportColumn(models.Model):
    _name = 'purchase.lines.report.column'
    _description = 'Columnas disponibles para reporte de líneas de compra'
    _order = 'sequence, name'

    name = fields.Char(string='Etiqueta', required=True)
    field_name = fields.Char(string='Campo técnico', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(default=True)