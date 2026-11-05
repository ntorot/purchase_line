# -*- coding: utf-8 -*-
import logging
from odoo import models, api
from odoo.tools import format_date

_logger = logging.getLogger(__name__)

class ReportBalanceMesClean(models.AbstractModel):
    _name = 'report.purchase_line.report_balance_mes_clean'
    _description = 'Cálculo de líneas limpias para el reporte de Balance'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("=== [PYTHON] Formateando Periodo con Mes Completo ===")
        
        custom_context = self.env.context.get('custom_report_options', {})
        report_id = self.env.context.get('active_id') or custom_context.get('report_id')

        if not report_id:
            report_model_id = self.env['account.report'].search([('type', '=', 'balance_sheet')], limit=1)
        else:
            report_model_id = self.env['account.report'].browse(int(report_id))

        options = dict(custom_context) if custom_context else {}
        if report_model_id and 'report_id' not in options:
            options['report_id'] = report_model_id.id

        raw_lines = []
        if report_model_id and options:
            try:
                raw_lines = report_model_id._get_lines(options)
            except Exception as e:
                _logger.error("Error al obtener líneas: %s", e)

        cleaned_lines = []
        for line in raw_lines:
            line_id = str(line.get('id', ''))
            
            is_real_account = 'account.account' in line_id or line.get('account_id')
            if not is_real_account:
                continue

            columns = line.get('columns', [])
            debe_mes = 0.0
            haber_mes = 0.0
            
            if len(columns) >= 4:
                debe_mes = columns[2].get('no_format', 0.0) or 0.0
                haber_mes = columns[3].get('no_format', 0.0) or 0.0

            if debe_mes != 0.0 or haber_mes != 0.0:
                full_name = line.get('name', '').strip()
                code = ""
                account_name = full_name
                
                # Separación de código y cuenta
                if full_name and full_name[0].isdigit():
                    parts = full_name.split(' ', 1)
                    if len(parts) > 1:
                        code = parts[0]
                        account_name = parts[1]

                cleaned_lines.append({
                    'code': code,
                    'name': account_name,
                    'debe': debe_mes,
                    'haber': haber_mes,
                })

        date_options = options.get('date', {}) if options else {}
        context_month = "Periodo Actual"
        
        date_from = date_options.get('date_from')
        date_to = date_options.get('date_to')
        
        if date_from and date_to:
            lang_code = self.env.user.lang or 'es_VE'
            try:
                f_from = format_date(self.env, date_from, date_format='MMMM YYYY', lang_code=lang_code)
                context_month = f_from.capitalize()
            except Exception:
                context_month = date_options.get('string', 'Periodo Actual')
        else:
            context_month = date_options.get('string', 'Periodo Actual')

        return {
            'doc_ids': docids,
            'doc_model': 'account.report',
            'docs': report_model_id,
            'context_month': context_month,
            'lines': cleaned_lines,
        }


class ReportLibroMayorClean(models.AbstractModel):
    _name = 'report.purchase_line.report_libro_mayor_clean'
    _description = 'Cálculo para el Libro Mayor (Saldos Finales)'

    @api.model
    def _get_report_values(self, docids, data=None):
        custom_context = self.env.context.get('custom_report_options', {})
        report_id = self.env.context.get('active_id') or custom_context.get('report_id')


        if not report_id:
            report_model_id = self.env['account.report'].search([('type', '=', 'balance_sheet')], limit=1)
        else:
            report_model_id = self.env['account.report'].browse(int(report_id))

        options = dict(custom_context) if custom_context else {}
        raw_lines = report_model_id._get_lines(options) if report_model_id else []

        cleaned_lines = []
        for line in raw_lines:
            line_id = str(line.get('id', ''))
            if 'account.account' in line_id or line.get('account_id'):
                columns = line.get('columns', [])
                if len(columns) >= 6:
                    debe_f = columns[4].get('no_format', 0.0) or 0.0
                    haber_f = columns[5].get('no_format', 0.0) or 0.0
                    
                    if debe_f != 0.0 or haber_f != 0.0:
                        full_name = line.get('name', '').strip()
                        account_name = full_name.split(' ', 1)[1] if full_name and full_name[0].isdigit() else full_name
                        
                        cleaned_lines.append({
                            'name': account_name,
                            'debe': debe_f,
                            'haber': haber_f,
                        })

        lang_code = self.env.user.lang or 'es_VE'
        date_from = options.get('date', {}).get('date_from')
        context_month = format_date(self.env, date_from, date_format='MMMM YYYY', lang_code=lang_code).capitalize() if date_from else "Periodo Actual"

        return {
            'doc_ids': docids,
            'doc_model': 'account.report',
            'docs': report_model_id,
            'context_month': context_month,
            'lines': cleaned_lines,
        }