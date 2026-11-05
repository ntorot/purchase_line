from odoo import api, fields, models

class ReportPurchaseLineGenerator(models.AbstractModel):
    _name = 'report.purchase_line.report_purchase_line_template'
    _description = "Generador de Datos para Reporte de Líneas de Compra"

    @api.model
    def _get_report_values(self, docids, data=None):

        data = data or {}
        line_register_ids = data.get('purchase_lines_register_ids', [])
        
        purchase_lines_register_ids = self.env["report.purchase.line.data"].browse(
            line_register_ids
        )
        
        purchase_lines_register = []
        sum_cantidad = 0.0
        sum_precio_unit_ves = 0.0
        sum_subtotal_ves = 0.0

        for plri in purchase_lines_register_ids:
            sum_cantidad += plri.quantity 
            sum_precio_unit_ves += plri.unit_price_ves
            sum_subtotal_ves += plri.price_subtotal_ves
            
            vals = {
                "Nro de Pedido": plri.order_numbers,
                "Proveedor": plri.partner_id.name, 
                "Referencia": plri.ref,
                "Fecha Pedido": plri.date_order.strftime("%d/%m/%Y") if plri.date_order else '',
                "Cod Producto": plri.product_code,
                "Desc Producto": plri.product_name,
                "Cantidad": plri.quantity,
                "UdM": plri.product_uom_id.name,
                "Precio Unit. VES": plri.unit_price_ves,
                "Subtotal VES": plri.price_subtotal_ves,
            }
            purchase_lines_register.append(vals)

        docargs = {
            "doc_ids": docids,
            "doc_model": "report.purchase.line.wizard",
            "data": data,
            "company_id": self.env.company,
            "purchase_lines_register": purchase_lines_register,
            "sum_cantidad": round(sum_cantidad, 2),
            "sum_subtotal_ves": round(sum_subtotal_ves, 2),
        }
        return docargs