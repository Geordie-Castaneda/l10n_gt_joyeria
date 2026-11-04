# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import time
import xlsxwriter
import base64
import io
from datetime import datetime, timedelta, date

class AsistenteReporteCompras(models.TransientModel):
    _name = 'l10n_gt_joyeria.asistente_reporte_compras'

    initial_folio = fields.Integer(string="Folio inicial", required=True, default=1)
    date_start    = fields.Date(string='Fecha inicio')
    date_end      = fields.Date(string='Fecha final')
    name          = fields.Char('Nombre archivo', size=32)
    file          = fields.Binary(string='Archivo', filters='.xlsx')

    def print_report_excel(self):
        for w in self:
            report_data = {}
            report_data['date_start'] = str(w.date_start)
            report_data['date_end']   = str(w.date_end)

            report_result     = self.env['report.l10n_gt_joyeria.reporte_compras']._get_purchases(report_data)
            company = self.env.company
            partner = company.partner_id

            # ── Dirección completa ─────────────────────────────────────────
            address_parts = []
            if partner.street:
                address_parts.append(partner.street)
            if partner.street2:
                address_parts.append(partner.street2)
            if partner.city:
                address_parts.append(partner.city)
            if partner.state_id:
                address_parts.append(partner.state_id.name)
            if partner.zip:
                address_parts.append(partner.zip)
            if partner.country_id:
                address_parts.append(partner.country_id.name)
            full_address = ', '.join(address_parts) if address_parts else ''

            # ── Workbook ───────────────────────────────────────────────────
            output_buffer     = io.BytesIO()
            workbook = xlsxwriter.Workbook(output_buffer)
            worksheet  = workbook.add_worksheet('Reporte compras')

            # ── Rastreo de anchos automático ───────────────────────────────
            column_widths = {}

            def update_width(column, value, fmt_type='text'):
                if value is None:
                    value = ''
                if fmt_type == 'currency':
                    display = f"Q{float(value):,.2f}"
                elif fmt_type == 'date':
                    display = value.strftime('%d/%m/%Y') if hasattr(value, 'strftime') else str(value)
                else:
                    display = str(value)
                column_widths[column] = max(column_widths.get(column, 0), len(display))

            def format_excel_date(value):
                if value is None:
                    return ''
                if isinstance(value, str):
                    try:
                        return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
                    except ValueError:
                        return value
                if hasattr(value, 'strftime'):
                    return value.strftime('%d/%m/%Y')
                return str(value)

            def write_cell(row, column, value, cell_format=None, cell_type='text'):
                if cell_type == 'number':
                    if cell_format is None:
                        cell_format = currency_format
                    worksheet.write_number(row, column, float(value) if value is not None else 0.0, cell_format)
                    update_width(column, value, 'currency')
                elif cell_type == 'date':
                    worksheet.write_datetime(row, column, value, cell_format)
                    update_width(column, value, 'date')
                else:
                    worksheet.write(row, column, value or '', cell_format)
                    update_width(column, value, 'text')

            # ── Formatos ───────────────────────────────────────────────────
            date_format     = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
            currency_format = workbook.add_format({'num_format': 'Q#,##0.00',  'border': 1})
            border_format   = workbook.add_format({'border': 1})
            alternate_date_format = workbook.add_format({
                'num_format': 'dd/mm/yyyy', 'border': 1, 'bg_color': '#F2F6FC',
            })
            alternate_currency_format = workbook.add_format({
                'num_format': 'Q#,##0.00', 'border': 1, 'bg_color': '#F2F6FC',
            })
            alternate_border_format = workbook.add_format({
                'border': 1, 'bg_color': '#F2F6FC',
            })
            total_text_format = workbook.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3',
            })
            total_currency_format = workbook.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3',
                'num_format': 'Q#,##0.00',
            })
            detail_header_format = workbook.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9E1F2', 'align': 'center',
            })
            detail_label_format = workbook.add_format({
                'border': 1, 'bg_color': '#F2F6FC',
            })
            detail_alt_label_format = workbook.add_format({
                'border': 1, 'bg_color': '#FFFFFF',
            })
            detail_value_format = workbook.add_format({
                'border': 1, 'bg_color': '#F2F6FC', 'num_format': '#,##0.00',
            })
            detail_alt_value_format = workbook.add_format({
                'border': 1, 'bg_color': '#FFFFFF', 'num_format': '#,##0.00',
            })
            detail_total_label_format = workbook.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3',
            })
            detail_total_value_format = workbook.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'num_format': '#,##0.00',
            })

            header_format = workbook.add_format({
                'bold': True, 'border': 1, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#D9E1F2', 'text_wrap': True
            })
            title_format = workbook.add_format({
                'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 13
            })
            centered_format = workbook.add_format({
                'align': 'center', 'valign': 'vcenter'
            })
            folio_header_format = workbook.add_format({
                'bold': True, 'align': 'right', 'valign': 'vcenter', 'font_size': 11
            })

            # ── FOLIO DEL LIBRO en encabezado (fila 0, lado derecho) ───────
            # El initial_folio es el número de folio de ESTE LIBRO,
            # se muestra en el encabezado UNA SOLA VEZ, no por documento.
            worksheet.merge_range(0, 11, 0, 16, f'FOLIO No. {w.initial_folio}', folio_header_format)

            # ── Título ─────────────────────────────────────────────────────
            worksheet.merge_range(1, 0, 1, 16, 'LIBRO DE COMPRAS Y SERVICIOS', title_format)

            # ── Datos de la empresa ────────────────────────────────────────
            worksheet.merge_range(3, 0, 3, 16,
                f"NUMERO DE IDENTIFICACION TRIBUTARIA: {partner.vat or ''}", centered_format)
            worksheet.merge_range(4, 0, 4, 16,
                f"NOMBRE COMERCIAL: {partner.name or ''}", centered_format)
            worksheet.merge_range(5, 0, 5, 16,
                f"DOMICILIO FISCAL: {full_address}", centered_format)
            worksheet.merge_range(6, 0, 6, 16,
                f"DEL: {format_excel_date(w.date_start)}  AL: {format_excel_date(w.date_end)}", centered_format)

            # ── Encabezados de columnas (fila 8) ──────────────────────────
            # COL  0 = Fecha
            # COL  1 = Documento
            # COL  2 = NIT
            # COL  3 = Serie
            # COL  4 = Numero del DTE
            # COL  5 = Proveedor
            # COL  6 = Compras
            # COL  7 = Compra de Activos
            # COL  8 = Combustible
            # COL  9 = Servicios
            # COL 10 = Importacion
            # COL 11 = Pequeño contribuyente
            # COL 12 = Exento
            # COL 13 = IVA
            # COL 14 = IDP
            # COL 15 = ISR Retención
            # COL 16 = Total
            isr_header = 'ISR Retencion'
            headers = [
                'Fecha', 'Documento', 'NIT', 'Serie', 'Numero del DTE', 'Proveedor',
                'Compras', 'Compra de Activos', 'Combustible', 'Servicios', 'Importacion',
                'Pequeño contribuyente', 'Exento', 'IVA', 'IDP', isr_header, 'Total'
            ]
            worksheet.set_row(8, 30)
            for col_num, header in enumerate(headers):
                write_cell(8, col_num, header, header_format)

            # ── Anchos de columna ──────────────────────────────────────────
            worksheet.set_column(0,  0, 12)   # Fecha
            worksheet.set_column(1,  1, 16)   # Documento
            worksheet.set_column(2,  2, 14)   # NIT
            worksheet.set_column(3,  3, 10)   # Serie
            worksheet.set_column(4,  4, 16)   # Numero DTE
            worksheet.set_column(5,  5, 32)   # Proveedor
            worksheet.set_column(6, 16, 14)   # Montos

            # ── Datos ──────────────────────────────────────────────────────
            worksheet_row = 9

            print('JOYERIA Excel: %s documentos, total IDP=%s' % (len(report_result['compras_lista']), report_result['total']['idp']))
            for purchase in report_result['compras_lista']:
                print('JOYERIA Excel fila=%s documento=%s IDP=%s total=%s' % (worksheet_row, purchase['documento'], purchase['idp'], purchase['total']))
                if (worksheet_row - 9) % 2:
                    row_date_format = alternate_date_format
                    row_currency_format = alternate_currency_format
                    row_border_format = alternate_border_format
                else:
                    row_date_format = date_format
                    row_currency_format = currency_format
                    row_border_format = border_format

                purchase_date = purchase['fecha']
                if isinstance(purchase_date, date):
                    purchase_date = datetime.combine(purchase_date, datetime.min.time())
                elif isinstance(purchase_date, str):
                    purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d')

                write_cell(worksheet_row,  0, purchase_date,                                    row_date_format, 'date')
                write_cell(worksheet_row,  1, purchase['documento'],                      row_border_format)
                write_cell(worksheet_row,  2, purchase['nit'],                            row_border_format)
                write_cell(worksheet_row,  3, purchase['serie'] or '',                    row_border_format)
                write_cell(worksheet_row,  4, purchase['numero_dte'] or '',               row_border_format)
                write_cell(worksheet_row,  5, purchase['proveedor'],                      row_border_format)
                write_cell(worksheet_row,  6, purchase['compra'],                         row_currency_format, 'number')
                write_cell(worksheet_row,  7, purchase['compra_de_activos'],              row_currency_format, 'number')
                write_cell(worksheet_row,  8, purchase['combustible'],                    row_currency_format, 'number')
                write_cell(worksheet_row,  9, purchase['servicio'],                       row_currency_format, 'number')
                write_cell(worksheet_row, 10, purchase['importacion'],                    row_currency_format, 'number')
                write_cell(worksheet_row, 11, purchase['pequenio'],                       row_currency_format, 'number')
                write_cell(worksheet_row, 12, purchase['compra_exento'] + purchase['servicio_exento'],
                           row_currency_format, 'number')
                write_cell(worksheet_row, 13, purchase['iva'],                            row_currency_format, 'number')
                write_cell(worksheet_row, 14, purchase['idp'],                            row_currency_format, 'number')
                write_cell(worksheet_row, 15, purchase['isr_retencion'],                  row_currency_format, 'number')
                write_cell(worksheet_row, 16, purchase['total'],                          row_currency_format, 'number')
                worksheet_row += 1

            # ── Fila de totales ────────────────────────────────────────────
            totals = report_result['total']
            for column in range(6):
                write_cell(worksheet_row, column, 'TOTALES' if column == 5 else '', total_text_format)
            write_cell(worksheet_row,  6, totals['compra'],            total_currency_format, 'number')
            write_cell(worksheet_row,  7, totals['compra_de_activos'], total_currency_format, 'number')
            write_cell(worksheet_row,  8, totals['combustible'],       total_currency_format, 'number')
            write_cell(worksheet_row,  9, totals['servicio'],          total_currency_format, 'number')
            write_cell(worksheet_row, 10, totals['importacion'],       total_currency_format, 'number')
            write_cell(worksheet_row, 11, totals['pequenio'],          total_currency_format, 'number')
            write_cell(worksheet_row, 12, totals['compra_exento'] + totals['servicio_exento'],
                       total_currency_format, 'number')
            write_cell(worksheet_row, 13, totals['iva'],               total_currency_format, 'number')
            write_cell(worksheet_row, 14, totals['idp'],               total_currency_format, 'number')
            write_cell(worksheet_row, 15, totals['isr_retencion'],     total_currency_format, 'number')
            write_cell(worksheet_row, 16, totals['total'],             total_currency_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row, 15, 'Documentos operados:', border_format)
            write_cell(worksheet_row, 16, report_result['documentos_operados'], border_format)

            # ── Sección CÁLCULO ────────────────────────────────────────────
            worksheet_row += 2

            worksheet.write(worksheet_row,  5, 'CÁLCULO', detail_header_format)
            worksheet.write(worksheet_row,  6, '',         detail_header_format)
            worksheet.write(worksheet_row,  7, '',         detail_header_format)
            worksheet.write(worksheet_row,  8, '',         detail_header_format)
            worksheet.write(worksheet_row, 11, '',         detail_header_format)
            worksheet.write(worksheet_row, 12, 'BASE',     detail_header_format)
            worksheet.write(worksheet_row, 13, 'IVA',      detail_header_format)
            worksheet.write(worksheet_row, 14, 'IDP',      detail_header_format)
            worksheet.write(worksheet_row, 15, 'TOTAL',    detail_header_format)

            worksheet_row += 1
            write_cell(worksheet_row,  5, 'IVA POR PAGAR',    detail_label_format)
            write_cell(worksheet_row,  6, '',                  detail_label_format)
            write_cell(worksheet_row,  7, '',                  detail_label_format)
            write_cell(worksheet_row,  8, report_result['total']['iva_por_pagar'], detail_value_format, 'number')
            write_cell(worksheet_row, 11, 'Pequeño contribuyente',       detail_label_format)
            write_cell(worksheet_row, 12, report_result['total']['pequenio'],       detail_value_format, 'number')
            write_cell(worksheet_row, 13, 0,                              detail_value_format, 'number')
            write_cell(worksheet_row, 14, 0,                              detail_value_format, 'number')
            write_cell(worksheet_row, 15, report_result['total']['pequenio'],       detail_value_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row,  5, 'RETENCION DE IVA',  detail_alt_label_format)
            write_cell(worksheet_row,  6, '',                   detail_alt_label_format)
            write_cell(worksheet_row,  7, '',                   detail_alt_label_format)
            write_cell(worksheet_row,  8, report_result['total']['valor_retencion_iva'], detail_alt_value_format, 'number')
            write_cell(worksheet_row, 11, 'Compra de Activos',               detail_alt_label_format)
            write_cell(worksheet_row, 12, report_result['total']['compra_de_activos'],  detail_alt_value_format, 'number')
            write_cell(worksheet_row, 13, report_result['total']['compra_de_activos'] * 0.12, detail_alt_value_format, 'number')
            write_cell(worksheet_row, 14, 0, detail_alt_value_format, 'number')
            write_cell(worksheet_row, 15, report_result['total']['compra_de_activos'] * 1.12, detail_alt_value_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row,  5, 'IVA POR COBRAR',   detail_label_format)
            write_cell(worksheet_row,  6, '',                  detail_label_format)
            write_cell(worksheet_row,  7, '',                  detail_label_format)
            write_cell(worksheet_row,  8, report_result['total']['iva'], detail_value_format, 'number')
            write_cell(worksheet_row, 11, 'Compras',           detail_label_format)
            write_cell(worksheet_row, 12, report_result['total']['compra'],         detail_value_format, 'number')
            write_cell(worksheet_row, 13, report_result['total']['compra'] * 0.12,  detail_value_format, 'number')
            write_cell(worksheet_row, 14, 0,                              detail_value_format, 'number')
            write_cell(worksheet_row, 15, report_result['total']['compra'] * 1.12,  detail_value_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row,  5, 'EXEN IVA', detail_alt_label_format)
            write_cell(worksheet_row,  6, '',          detail_alt_label_format)
            write_cell(worksheet_row,  7, '',          detail_alt_label_format)
            write_cell(worksheet_row,  8, report_result['total']['compra_exento'] + report_result['total']['servicio_exento'],
                       detail_alt_value_format, 'number')
            write_cell(worksheet_row, 11, 'Servicios', detail_alt_label_format)
            write_cell(worksheet_row, 12, report_result['total']['servicio'],          detail_alt_value_format, 'number')
            write_cell(worksheet_row, 13, report_result['total']['servicio'] * 0.12,   detail_alt_value_format, 'number')
            write_cell(worksheet_row, 14, 0,                                  detail_alt_value_format, 'number')
            write_cell(worksheet_row, 15, report_result['total']['servicio'] * 1.12,   detail_alt_value_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row,  5, 'CREDITO FISCAL PERIODO ANTERIOR', detail_label_format)
            write_cell(worksheet_row,  6, '',          detail_label_format)
            write_cell(worksheet_row,  7, '',          detail_label_format)
            write_cell(worksheet_row,  8, report_result['total']['credito_fiscal_periodo_anterior'], detail_value_format, 'number')
            write_cell(worksheet_row, 11, 'Importaciones C.A.', detail_label_format)
            write_cell(worksheet_row, 12, report_result['total']['importacion'],          detail_value_format, 'number')
            write_cell(worksheet_row, 13, report_result['total']['importacion'] * 0.12,   detail_value_format, 'number')
            write_cell(worksheet_row, 14, 0,                                    detail_value_format, 'number')
            write_cell(worksheet_row, 15, report_result['total']['importacion'] * 1.12,   detail_value_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row, 11, 'IDP', detail_alt_label_format)
            write_cell(worksheet_row, 12, 0, detail_alt_value_format, 'number')
            write_cell(worksheet_row, 13, 0, detail_alt_value_format, 'number')
            write_cell(worksheet_row, 14, report_result['total']['idp'], detail_alt_value_format, 'number')
            write_cell(worksheet_row, 15, report_result['total']['idp'], detail_alt_value_format, 'number')

            worksheet_row += 1
            write_cell(worksheet_row,  5, 'IVA POR PAGAR', detail_total_label_format)
            write_cell(worksheet_row,  6, '',               detail_total_label_format)
            write_cell(worksheet_row,  7, '',               detail_total_label_format)
            write_cell(worksheet_row,  8,
                report_result['total']['iva_por_pagar']
                + report_result['total']['valor_retencion_iva']
                - report_result['total']['iva']
                + report_result['total']['compra_exento']
                + report_result['total']['servicio_exento']
                + report_result['total']['credito_fiscal_periodo_anterior'],
                detail_total_value_format, 'number')

            worksheet_row += 1

            # ── Aplicar anchos automáticos solo a montos ───────────────────
            for column, width in column_widths.items():
                if column not in range(0, 6):
                    worksheet.set_column(column, column, min(width + 2, 50))

            workbook.close()
            file_data = base64.b64encode(output_buffer.getvalue())
            self.write({'file': file_data, 'name': 'libro_compras.xlsx'})

            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=%s&id=%s&field=file&filename_field=name&download=true' % (
                    self._name, self.id
                ),
                'target': 'new',
            }

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_gt_joyeria.asistente_reporte_compras',
            'res_id':    self.id,
            'type':      'ir.actions.act_window',
            'target':    'new',
        }
