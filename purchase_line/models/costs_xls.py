# -*- coding: utf-8 -*-

from odoo import models
from datetime import datetime

class ImportCostsXlsReport(models.AbstractModel):
    _name = 'report.purchase_line.report_import_costs_xls'  
    _inherit = 'report.report_xlsx.abstract'
    _description = "Reporte de Costos de Importación XLSX"

    def _get_columns_def(self):
        return [
            {'label': 'N° Expediente', 'field': 'x_nexpediente', 'width': 15, 'format_key': 'format_text'},
            {'label': 'Orden de Compra', 'field': 'order_numbers', 'width': 18, 'format_key': 'format_text'},
            {'label': 'Fecha PO', 'field': 'order_date', 'width': 12, 'format_key': 'format_text'},  
            {'label': 'Proveedor', 'field': 'partner_id', 'width': 30, 'format_key': 'format_text'},
            {'label': 'N° Recepción', 'field': 'receipt_number', 'width': 18, 'format_key': 'format_text'},
            {'label': 'Fecha Recepción Efectiva', 'field': 'date_one', 'width': 15, 'format_key': 'format_text'},  
            {'label': 'Producto', 'field': 'product_name', 'width': 40, 'format_key': 'format_text'},
            # COMENTADO: {'label': 'Tasa Aplicada', 'field': 'tasa', 'width': 10, 'format_key': 'format_currency'},
            {'label': 'Cantidades', 'field': 'cantidades', 'width': 12, 'format_key': 'format_currency_qty'},
            {'label': 'Costo Unitario (VES)', 'field': 'unit_cost', 'width': 18, 'format_key': 'format_currency'},
            {'label': 'Costo Total (VES)', 'field': 'total_cost', 'width': 18, 'format_key': 'format_currency'},
            {'label': 'Costo Unitario (USD)', 'field': 'unit_price_usd', 'width': 18, 'format_key': 'format_currency'},
            {'label': 'Costo Total (USD)', 'field': 'price_subtotal_usd', 'width': 18, 'format_key': 'format_currency'},
            {'label': 'N° Costo Destino (LC)', 'field': 'costo_destino_number', 'width': 20, 'format_key': 'format_text'},
            {'label': 'Fecha Costo Destino (LC)', 'field': 'date_costo_destino', 'width': 18, 'format_key': 'format_date'},  
            {'label': 'Concepto Costo Destino (LC)', 'field': 'concepto_costo', 'width': 25, 'format_key': 'format_text'},
            {'label': 'Costo Adicional Destino (VES)', 'field': 'costo_adicional_destino', 'width': 25, 'format_key': 'format_currency'},
            {'label': 'Costo Adicional Destino (USD)', 'field': 'costo_adicional_destino_usd', 'width': 25, 'format_key': 'format_currency'},
            {'label': 'Costo Total Importación (VES)', 'field': 'total_import_ves', 'width': 28, 'format_key': 'format_currency_bold'},
            {'label': 'Costo Total Importación (USD)', 'field': 'total_import_usd', 'width': 28, 'format_key': 'format_currency_bold'},
        ]

    def _get_report_data_list(self, records):
        report_data = []
        account_moves = records
        
        for am in account_moves.filtered(lambda am: am.move_type in ["in_invoice", "in_refund"]):
            x_nexpediente = str(getattr(am, 'x_nexpediente', '')) if getattr(am, 'x_nexpediente', False) else ''
            tasa_factura_principal = getattr(am, 'x_tasa', 0.0)
            
            purchase_order_ids = am.purchase_id
            if not purchase_order_ids and am.invoice_origin:
                purchase_order_ids = self.env["purchase.order"].search(
                    [("name", "=", am.invoice_origin), ("state", "not in", ["cancel"])]
                )
            order_numbers = ", ".join(purchase_order_ids.mapped("name")) if purchase_order_ids else ""
            order_date = (", ".join(fecha.strftime("%d/%m/%Y") for fecha in purchase_order_ids.mapped("date_order")) if purchase_order_ids else "")

            receipts = self.env['stock.picking'].search([
                ('purchase_id', 'in', purchase_order_ids.ids if purchase_order_ids else []),
                ('state', '=', 'done')
            ], order='date_done desc')
            
            receipt_numbers = ", ".join(receipts.mapped('name'))
            date_one = receipts[0].date_done.strftime("%d/%m/%Y") if receipts and receipts[0].date_done else ""
            
            landed_costs = self.env['stock.landed.cost'].search([('vendor_bill_id', '=', am.id)])
            if not landed_costs and receipts:
                 landed_costs = self.env['stock.landed.cost'].search([('picking_ids', 'in', receipts.ids)])
            
            invoice_line_map = {}
            for ili in am.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
                product_id = ili.product_id.id
                unit_price_ves = 0.0
                unit_price_usd = 0.0
                price_subtotal_usd = 0.0  
                
                if am.currency_id.name == "VES":
                    unit_price_ves = ili.price_unit
                    unit_price_usd = round(ili.price_unit / tasa_factura_principal, 2) if tasa_factura_principal else 0.0
                    price_subtotal_usd = round(ili.price_subtotal / tasa_factura_principal, 2) if tasa_factura_principal else 0.0
                elif am.currency_id.name == "USD":
                    unit_price_ves = round(ili.price_unit * tasa_factura_principal, 2) if tasa_factura_principal else 0.0
                    unit_price_usd = ili.price_unit
                    price_subtotal_usd = ili.price_subtotal
                
                total_cost_ves = unit_price_ves * ili.quantity
                product_name = ili.product_id.name or ''

                if product_id in invoice_line_map:
                    invoice_line_map[product_id]["cantidades"] += ili.quantity
                    invoice_line_map[product_id]["total_cost"] += total_cost_ves
                    invoice_line_map[product_id]["price_subtotal_usd"] += price_subtotal_usd
                else:
                    invoice_line_map[product_id] = {
                        "product_name": product_name,
                        "cantidades": ili.quantity,
                        "unit_cost": unit_price_ves,  
                        "total_cost": total_cost_ves,
                        "unit_price_usd": unit_price_usd,
                        "price_subtotal_usd": price_subtotal_usd,
                        "running_total_ves": total_cost_ves,
                        "running_total_usd": price_subtotal_usd,
                        "is_base_cost_used": False,
                    }

            if landed_costs:
                for landed_cost in landed_costs:
                    lc_number = landed_cost.name or ''  
                    lc_date = landed_cost.date.strftime("%d/%m/%Y") if landed_cost.date else ''
                    bill_of_cost = landed_cost.vendor_bill_id
                    tasa_costo_especifica = getattr(bill_of_cost, 'x_tasa', tasa_factura_principal) or tasa_factura_principal

                    for valuation_adjustment in landed_cost.valuation_adjustment_lines:
                        product_id = valuation_adjustment.product_id.id
                        costo_aplicado = valuation_adjustment.additional_landed_cost
                        cost_description = valuation_adjustment.cost_line_id.name or ''  

                        if product_id not in invoice_line_map:
                             continue  
                        
                        base_data = invoice_line_map[product_id]
                        costo_adicional_destino_usd = round(costo_aplicado / tasa_costo_especifica, 2) if tasa_costo_especifica else 0.0
                        
                        base_data["running_total_ves"] += costo_aplicado
                        base_data["running_total_usd"] += costo_adicional_destino_usd

                        base_cost_ves_line = 0.0
                        base_cost_usd_line = 0.0
                        qty_line = 0.0 
                        
                        if not base_data["is_base_cost_used"]:
                            base_cost_ves_line = base_data["total_cost"]
                            base_cost_usd_line = base_data["price_subtotal_usd"]
                            qty_line = base_data["cantidades"] 
                            base_data["is_base_cost_used"] = True 

                        vals = {
                            "x_nexpediente": x_nexpediente, 
                            "tasa": tasa_costo_especifica,
                            "order_numbers": order_numbers,  
                            "order_date": order_date,
                            "partner_id": am.partner_id.name or '',  
                            "receipt_number": receipt_numbers,
                            "date_one": date_one,
                            "product_name": base_data["product_name"],  
                            "cantidades": qty_line, 
                            "unit_cost": base_data["unit_cost"] if base_cost_ves_line > 0.0 else 0.0,  
                            "total_cost": base_cost_ves_line,  
                            "unit_price_usd": base_data["unit_price_usd"] if base_cost_usd_line > 0.0 else 0.0,
                            "price_subtotal_usd": base_cost_usd_line,  
                            "costo_destino_number": lc_number,  
                            "date_costo_destino": lc_date,  
                            "concepto_costo": cost_description,  
                            "costo_adicional_destino": costo_aplicado,
                            "costo_adicional_destino_usd": costo_adicional_destino_usd,
                            "total_import_ves": base_data["running_total_ves"],
                            "total_import_usd": base_data["running_total_usd"],
                            "product_id": product_id,
                            "final_qty_for_subtotal": base_data["cantidades"],
                        }
                        report_data.append(vals)

            for product_id, base_data in invoice_line_map.items():
                 if not base_data["is_base_cost_used"]:
                     vals = {
                         "x_nexpediente": x_nexpediente,
                         "tasa": tasa_factura_principal,
                         "order_numbers": order_numbers,  
                         "order_date": order_date,
                         "partner_id": am.partner_id.name or '',  
                         "receipt_number": receipt_numbers,
                         "date_one": date_one,
                         "product_name": base_data["product_name"],  
                         "cantidades": base_data["cantidades"],
                         "unit_cost": base_data["unit_cost"],  
                         "total_cost": base_data["total_cost"],
                         "unit_price_usd": base_data["unit_price_usd"],
                         "price_subtotal_usd": base_data["price_subtotal_usd"],
                         "costo_destino_number": '',  
                         "date_costo_destino": '',  
                         "concepto_costo": 'COSTO BASE DE FACTURA',
                         "costo_adicional_destino": 0.0,
                         "costo_adicional_destino_usd": 0.0,
                         "total_import_ves": base_data["total_cost"],
                         "total_import_usd": base_data["price_subtotal_usd"],
                         "product_id": product_id,
                         "final_qty_for_subtotal": base_data["cantidades"],
                     }
                     report_data.append(vals)

        report_data.sort(key=lambda x: (x.get('order_numbers', ''), x.get('product_name', '')))
        final_report_data = []
        last_key = None  
        
        for line in report_data:
            persistent_key = (line.get('order_numbers', ''), line.get('product_id', ''))
            line['group_key_id'] = persistent_key 
            if persistent_key == last_key and last_key is not None:
                for f in ['x_nexpediente','order_numbers','order_date','partner_id','receipt_number','date_one','product_name']:
                    line[f] = ''
                for f in ['cantidades','unit_cost','total_cost','unit_price_usd','price_subtotal_usd']:
                    line[f] = 0.0
            final_report_data.append(line)
            last_key = persistent_key
        return final_report_data

    def generate_xlsx_report(self, workbook, data, records):
        report_data_list = self._get_report_data_list(records)
        sheet = workbook.add_worksheet("Costos de Importación")
        
        format_header = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        format_title = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
        format_text = workbook.add_format({'align': 'left'})
        format_date = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        format_currency = workbook.add_format({'num_format': '#,##0.00'})
        format_currency_qty = workbook.add_format({'num_format': '#,##0.00'})
        format_currency_zero_blank = workbook.add_format({'num_format': '#,##0.00;;""'})
        format_currency_bold = workbook.add_format({'num_format': '#,##0.00', 'bold': True})
        format_subtotal_text = workbook.add_format({'bold': True, 'bg_color': '#DEEBF7', 'border': 1, 'align': 'right'})
        format_subtotal = workbook.add_format({'bold': True, 'bg_color': '#DEEBF7', 'border': 1, 'num_format': '#,##0.00'})
        format_grand_total_text = workbook.add_format({'bold': True, 'bg_color': '#B7E1CD', 'border': 2, 'align': 'right'})
        format_grand_total = workbook.add_format({'bold': True, 'bg_color': '#B7E1CD', 'border': 2, 'num_format': '#,##0.00'})

        format_map = {
            'format_text': format_text,
            'format_date': format_date,
            'format_currency': format_currency,
            'format_currency_qty': format_currency_qty,
            'format_currency_bold': format_currency_bold,
            'format_currency_zero_blank': format_currency_zero_blank,
        }

        company = records[0].company_id if records else self.env.company
        columns_def = self._get_columns_def()
        num_columns = len(columns_def)
        merge_range_end = chr(ord('A') + num_columns - 1)
        sheet.merge_range(f'A1:{merge_range_end}1', "REPORTE DE COSTOS DE IMPORTACIÓN APLICADOS", format_title)
        sheet.write('A3', company.name or "")
        sheet.write('A4', "RIF: " + (company.vat or ""))
        
        row_start = 6
        for idx, col_def in enumerate(columns_def):
            sheet.write(row_start, idx, col_def['label'], format_header)
            sheet.set_column(idx, idx, col_def['width'])
            
        row = row_start + 1 
        # AJUSTE DE ÍNDICES: Al comentar 'tasa', todas las columnas siguientes bajan un número
        COL_INDICES = {
            'cantidades': 7, 
            'unit_cost': 8, 
            'total_cost': 9, 
            'unit_price_usd': 10, 
            'price_subtotal_usd': 11,
            'costo_adicional_destino': 15, 
            'costo_adicional_destino_usd': 16,
            'total_import_ves': 17, 
            'total_import_usd': 18, 
        }
        
        current_product_key = None
        subtotal_cells_ves = []
        subtotal_cells_usd = []
        last_line_in_group = None
        
        def write_subtotal(sheet, current_row_idx, last_line):
            nonlocal subtotal_cells_ves, subtotal_cells_usd
            if not last_line: return False
            
            sheet.merge_range(current_row_idx, 0, current_row_idx, COL_INDICES['cantidades']-1, 'P. UNITARIO DE IMPORTACIÓN FINAL:', format_subtotal_text)
            
            qty = last_line.get('final_qty_for_subtotal') or 1.0
            total_ves = last_line.get('total_import_ves', 0.0)
            total_usd = last_line.get('total_import_usd', 0.0)

            sheet.write(current_row_idx, COL_INDICES['unit_cost'], total_ves / qty, format_subtotal)
            sheet.write(current_row_idx, COL_INDICES['total_import_ves'], total_ves, format_subtotal)
            sheet.write(current_row_idx, COL_INDICES['unit_price_usd'], total_usd / qty, format_subtotal)
            sheet.write(current_row_idx, COL_INDICES['total_import_usd'], total_usd, format_subtotal)
            
            subtotal_cells_ves.append(f'{chr(ord("A") + COL_INDICES["total_import_ves"])}{current_row_idx + 1}')
            subtotal_cells_usd.append(f'{chr(ord("A") + COL_INDICES["total_import_usd"])}{current_row_idx + 1}')
            return True

        for line in report_data_list:
            new_product_key = line.get('group_key_id')
            if current_product_key is not None and new_product_key != current_product_key:
                if write_subtotal(sheet, row, last_line_in_group):
                    row += 1 
            
            current_product_key = new_product_key
            last_line_in_group = line
            col = 0
            for col_def in columns_def:
                field_name = col_def['field']
                val = line.get(field_name, '')
                fmt = format_map.get(col_def['format_key'], format_text)
                
                # Verificamos si es una de las columnas numéricas para aplicar formato blanco si es cero
                if field_name in COL_INDICES and val == 0.0 and line.get('order_numbers') == '':
                    fmt = format_currency_zero_blank

                if col_def['format_key'] == 'format_date' and val:
                    try:
                        date_obj = datetime.strptime(val, '%d/%m/%Y').date()
                        sheet.write(row, col, date_obj, fmt)
                    except:
                        sheet.write(row, col, val, format_text)
                else:
                    sheet.write(row, col, val, fmt)
                col += 1
            row += 1 

        if report_data_list:
            if write_subtotal(sheet, row, last_line_in_group):
                row += 1 
        
        if subtotal_cells_ves:
            row += 1 
            sheet.merge_range(row, 0, row, COL_INDICES['costo_adicional_destino_usd'], 'TOTAL GENERAL:', format_grand_total_text)
            sheet.write(row, COL_INDICES['total_import_ves'], f'=SUM({",".join(subtotal_cells_ves)})', format_grand_total)
            sheet.write(row, COL_INDICES['total_import_usd'], f'=SUM({",".join(subtotal_cells_usd)})', format_grand_total)

        sheet.freeze_panes(row_start + 1, 0)