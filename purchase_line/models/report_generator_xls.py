# -*- coding: utf-8 -*-

from odoo import api, models
from datetime import datetime
import locale


class PurchaseLinesReportXlsx(models.AbstractModel):
    _name = "report.purchase_line.purchase_lines_xls_report"
    _inherit = "report.report_xlsx.abstract"
    _description = "Reporte de líneas de compra xlsx"

    def generate_xlsx_report(self, workbook, data, obj):
        wizard = self.env[obj._name].browse(obj.ids)
        columns = wizard.columns_to_show_ids.sorted("sequence")
        
        headers = [(col.field_name, col.name) for col in columns]
        
        sheet = workbook.add_worksheet("Lineas de Compra")
        
        format_header = workbook.add_format({"align": "justify", "bold": True})
        format_text = workbook.add_format({"align": "left", "bold": False})
        format_title = workbook.add_format({"align": "center", "bold": True, "font_size": 14})
        format_total = workbook.add_format({"align": "right", "bold": True, "num_format": '#,##0.00'})
        format_currency = workbook.add_format({"num_format": '#,##0.00'})
        
        # Encabezado principal
        company = self.env.user.company_id
        sheet.merge_range(0, 4, 0, 7, "REPORTE DE LÍNEAS DE COMPRA", format_title)
        sheet.merge_range(2, 0, 2, 3, company.name or "", format_header)
        sheet.merge_range(3, 0, 3, 3, "RIF: " + (company.vat or ""), format_header)
        
        # Escribir encabezados de columnas
        for idx, (field, label) in enumerate(headers):
            sheet.write(5, idx, label, format_header)
            sheet.set_column(idx, idx, 15) 
            
        for row_idx, line in enumerate(wizard.line_ids, start=6):
            for col_idx, (field, label) in enumerate(headers):
                value = getattr(line, field, "")
                
                if "date" in field and value:
                    if hasattr(value, 'strftime'):
                        value = value.strftime('%d/%m/%Y')
                    elif isinstance(value, str):
                        try:
                            value = datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
                        except Exception:
                            pass
                            
                elif hasattr(value, "name"):
                    value = value.name
                
                elif field in ["unit_price_ves", "unit_price_usd", "price_subtotal_ves", "price_subtotal_usd", "unit_cost", "total_cost", "packaging_qty"]:
                    value = float(value)
                    sheet.write(row_idx, col_idx, value, format_currency)
                    continue

               
                elif field in ["discount", "margen"]:
                    value = float(value)
                    format_percentage = workbook.add_format({'num_format': '0.00%'})
                    sheet.write(row_idx, col_idx, value / 100, format_percentage)
                    continue
                
                elif value is False or value is None:
                    value = ""
                
                
                sheet.write(row_idx, col_idx, value, format_text)
                
        sum_fields = [
            "quantity", "unit_price_ves", "unit_price_usd", "price_subtotal_ves",
            "price_subtotal_usd", "unit_cost", "total_cost"
        ]
        last_row = 6 + len(wizard.line_ids)
        
        first_non_numeric_idx = -1
        for idx, (field, label) in enumerate(headers):
            if field not in sum_fields:
                first_non_numeric_idx = idx
            else:
                break
                
        if first_non_numeric_idx >= 0:
            sheet.write(last_row, first_non_numeric_idx, 'Totales:', format_total)
        
        for col_idx, (field, label) in enumerate(headers):
            if field in sum_fields:
                total = 0.0
                for line in wizard.line_ids:
                    val = getattr(line, field, 0.0)
                    try:
                        total += float(val) 
                    except (ValueError, TypeError):
                        pass

                sheet.write(last_row, col_idx, total, format_total)