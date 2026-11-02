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

    folio_inicial = fields.Integer(string="Folio Inicial", required=True, default=1)
    fecha_inicio  = fields.Date('Fecha inicio')
    fecha_fin     = fields.Date('Fecha fin')
    name          = fields.Char('Nombre archivo', size=32)
    archivo       = fields.Binary('Archivo', filters='.xlsx')

    def print_report_excel(self):
        for w in self:
            datos_reporte = {}
            datos_reporte['fecha_inicio'] = str(w.fecha_inicio)
            datos_reporte['fecha_fin']    = str(w.fecha_fin)

            res     = self.env['report.l10n_gt_joyeria.reporte_compras']._get_compras(datos_reporte)
            company = self.env.company
            partner = company.partner_id

            # ── Dirección completa ─────────────────────────────────────────
            partes = []
            if partner.street:
                partes.append(partner.street)
            if partner.street2:
                partes.append(partner.street2)
            if partner.city:
                partes.append(partner.city)
            if partner.state_id:
                partes.append(partner.state_id.name)
            if partner.zip:
                partes.append(partner.zip)
            if partner.country_id:
                partes.append(partner.country_id.name)
            direccion_completa = ', '.join(partes) if partes else ''

            # ── Workbook ───────────────────────────────────────────────────
            f     = io.BytesIO()
            libro = xlsxwriter.Workbook(f)
            hoja  = libro.add_worksheet('Reporte compras')

            # ── Rastreo de anchos automático ───────────────────────────────
            column_widths = {}

            def update_width(col, value, fmt_type='text'):
                if value is None:
                    value = ''
                if fmt_type == 'currency':
                    display = f"Q{float(value):,.2f}"
                elif fmt_type == 'date':
                    display = value.strftime('%d/%m/%Y') if hasattr(value, 'strftime') else str(value)
                else:
                    display = str(value)
                column_widths[col] = max(column_widths.get(col, 0), len(display))

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

            def write_cell(row, col, value, cell_format=None, cell_type='text'):
                if cell_type == 'number':
                    if cell_format is None:
                        cell_format = currency_format
                    hoja.write_number(row, col, float(value) if value is not None else 0.0, cell_format)
                    update_width(col, value, 'currency')
                elif cell_type == 'date':
                    hoja.write_datetime(row, col, value, cell_format)
                    update_width(col, value, 'date')
                else:
                    hoja.write(row, col, value or '', cell_format)
                    update_width(col, value, 'text')

            # ── Formatos ───────────────────────────────────────────────────
            date_format     = libro.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
            currency_format = libro.add_format({'num_format': 'Q#,##0.00',  'border': 1})
            border_format   = libro.add_format({'border': 1})
            alternate_date_format = libro.add_format({
                'num_format': 'dd/mm/yyyy', 'border': 1, 'bg_color': '#F2F6FC',
            })
            alternate_currency_format = libro.add_format({
                'num_format': 'Q#,##0.00', 'border': 1, 'bg_color': '#F2F6FC',
            })
            alternate_border_format = libro.add_format({
                'border': 1, 'bg_color': '#F2F6FC',
            })
            total_text_format = libro.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3',
            })
            total_currency_format = libro.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3',
                'num_format': 'Q#,##0.00',
            })
            detail_header_format = libro.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9E1F2', 'align': 'center',
            })
            detail_label_format = libro.add_format({
                'border': 1, 'bg_color': '#F2F6FC',
            })
            detail_alt_label_format = libro.add_format({
                'border': 1, 'bg_color': '#FFFFFF',
            })
            detail_value_format = libro.add_format({
                'border': 1, 'bg_color': '#F2F6FC', 'num_format': '#,##0.00',
            })
            detail_alt_value_format = libro.add_format({
                'border': 1, 'bg_color': '#FFFFFF', 'num_format': '#,##0.00',
            })
            detail_total_label_format = libro.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3',
            })
            detail_total_value_format = libro.add_format({
                'bold': True, 'border': 1, 'bg_color': '#D9EAD3', 'num_format': '#,##0.00',
            })

            header_format = libro.add_format({
                'bold': True, 'border': 1, 'align': 'center',
                'valign': 'vcenter', 'bg_color': '#D9E1F2', 'text_wrap': True
            })
            fmt_titulo = libro.add_format({
                'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 13
            })
            fmt_centrado = libro.add_format({
                'align': 'center', 'valign': 'vcenter'
            })
            fmt_folio_cabecera = libro.add_format({
                'bold': True, 'align': 'right', 'valign': 'vcenter', 'font_size': 11
            })

            # ── FOLIO DEL LIBRO en encabezado (fila 0, lado derecho) ───────
            # El folio_inicial es el número de folio de ESTE LIBRO,
            # se muestra en el encabezado UNA SOLA VEZ, no por documento.
            hoja.merge_range(0, 11, 0, 16, f'FOLIO No. {w.folio_inicial}', fmt_folio_cabecera)

            # ── Título ─────────────────────────────────────────────────────
            hoja.merge_range(1, 0, 1, 16, 'LIBRO DE COMPRAS Y SERVICIOS', fmt_titulo)

            # ── Datos de la empresa ────────────────────────────────────────
            hoja.merge_range(3, 0, 3, 16,
                f"NUMERO DE IDENTIFICACION TRIBUTARIA: {partner.vat or ''}", fmt_centrado)
            hoja.merge_range(4, 0, 4, 16,
                f"NOMBRE COMERCIAL: {partner.name or ''}", fmt_centrado)
            hoja.merge_range(5, 0, 5, 16,
                f"DOMICILIO FISCAL: {direccion_completa}", fmt_centrado)
            hoja.merge_range(6, 0, 6, 16,
                f"DEL: {format_excel_date(w.fecha_inicio)}  AL: {format_excel_date(w.fecha_fin)}", fmt_centrado)

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
            hoja.set_row(8, 30)
            for col_num, header in enumerate(headers):
                write_cell(8, col_num, header, header_format)

            # ── Anchos de columna ──────────────────────────────────────────
            hoja.set_column(0,  0, 12)   # Fecha
            hoja.set_column(1,  1, 16)   # Documento
            hoja.set_column(2,  2, 14)   # NIT
            hoja.set_column(3,  3, 10)   # Serie
            hoja.set_column(4,  4, 16)   # Numero DTE
            hoja.set_column(5,  5, 32)   # Proveedor
            hoja.set_column(6, 16, 14)   # Montos

            # ── Datos ──────────────────────────────────────────────────────
            fila = 9

            print('JOYERIA Excel: %s documentos, total IDP=%s' % (len(res['compras_lista']), res['total']['idp']))
            for compra in res['compras_lista']:
                print('JOYERIA Excel fila=%s documento=%s IDP=%s total=%s' % (fila, compra['documento'], compra['idp'], compra['total']))
                if (fila - 9) % 2:
                    row_date_format = alternate_date_format
                    row_currency_format = alternate_currency_format
                    row_border_format = alternate_border_format
                else:
                    row_date_format = date_format
                    row_currency_format = currency_format
                    row_border_format = border_format

                fecha = compra['fecha']
                if isinstance(fecha, date):
                    fecha = datetime.combine(fecha, datetime.min.time())
                elif isinstance(fecha, str):
                    fecha = datetime.strptime(fecha, '%Y-%m-%d')

                write_cell(fila,  0, fecha,                                    row_date_format, 'date')
                write_cell(fila,  1, compra['documento'],                      row_border_format)
                write_cell(fila,  2, compra['nit'],                            row_border_format)
                write_cell(fila,  3, compra['serie'] or '',                    row_border_format)
                write_cell(fila,  4, compra['numero_dte'] or '',               row_border_format)
                write_cell(fila,  5, compra['proveedor'],                      row_border_format)
                write_cell(fila,  6, compra['compra'],                         row_currency_format, 'number')
                write_cell(fila,  7, compra['compra_de_activos'],              row_currency_format, 'number')
                write_cell(fila,  8, compra['combustible'],                    row_currency_format, 'number')
                write_cell(fila,  9, compra['servicio'],                       row_currency_format, 'number')
                write_cell(fila, 10, compra['importacion'],                    row_currency_format, 'number')
                write_cell(fila, 11, compra['pequenio'],                       row_currency_format, 'number')
                write_cell(fila, 12, compra['compra_exento'] + compra['servicio_exento'],
                           row_currency_format, 'number')
                write_cell(fila, 13, compra['iva'],                            row_currency_format, 'number')
                write_cell(fila, 14, compra['idp'],                            row_currency_format, 'number')
                write_cell(fila, 15, compra['isr_retencion'],                  row_currency_format, 'number')
                write_cell(fila, 16, compra['total'],                          row_currency_format, 'number')
                fila += 1

            # ── Fila de totales ────────────────────────────────────────────
            totals = res['total']
            for col in range(6):
                write_cell(fila, col, 'TOTALES' if col == 5 else '', total_text_format)
            write_cell(fila,  6, totals['compra'],            total_currency_format, 'number')
            write_cell(fila,  7, totals['compra_de_activos'], total_currency_format, 'number')
            write_cell(fila,  8, totals['combustible'],       total_currency_format, 'number')
            write_cell(fila,  9, totals['servicio'],          total_currency_format, 'number')
            write_cell(fila, 10, totals['importacion'],       total_currency_format, 'number')
            write_cell(fila, 11, totals['pequenio'],          total_currency_format, 'number')
            write_cell(fila, 12, totals['compra_exento'] + totals['servicio_exento'],
                       total_currency_format, 'number')
            write_cell(fila, 13, totals['iva'],               total_currency_format, 'number')
            write_cell(fila, 14, totals['idp'],               total_currency_format, 'number')
            write_cell(fila, 15, totals['isr_retencion'],     total_currency_format, 'number')
            write_cell(fila, 16, totals['total'],             total_currency_format, 'number')

            fila += 1
            write_cell(fila, 15, 'Documentos operados:', border_format)
            write_cell(fila, 16, res['documentos_operados'], border_format)

            # ── Sección CÁLCULO ────────────────────────────────────────────
            fila += 2

            hoja.write(fila,  5, 'CÁLCULO', detail_header_format)
            hoja.write(fila,  6, '',         detail_header_format)
            hoja.write(fila,  7, '',         detail_header_format)
            hoja.write(fila,  8, '',         detail_header_format)
            hoja.write(fila, 11, '',         detail_header_format)
            hoja.write(fila, 12, 'BASE',     detail_header_format)
            hoja.write(fila, 13, 'IVA',      detail_header_format)
            hoja.write(fila, 14, 'TOTAL',    detail_header_format)

            fila += 1
            write_cell(fila,  5, 'IVA POR PAGAR',    detail_label_format)
            write_cell(fila,  6, '',                  detail_label_format)
            write_cell(fila,  7, '',                  detail_label_format)
            write_cell(fila,  8, res['total']['iva_por_pagar'], detail_value_format, 'number')
            write_cell(fila, 11, 'Pequeño contribuyente',       detail_label_format)
            write_cell(fila, 12, res['total']['pequenio'],       detail_value_format, 'number')
            write_cell(fila, 13, 0,                              detail_value_format, 'number')
            write_cell(fila, 14, res['total']['pequenio'],       detail_value_format, 'number')

            fila += 1
            write_cell(fila,  5, 'RETENCION DE IVA',  detail_alt_label_format)
            write_cell(fila,  6, '',                   detail_alt_label_format)
            write_cell(fila,  7, '',                   detail_alt_label_format)
            write_cell(fila,  8, res['total']['valor_retencion_iva'], detail_alt_value_format, 'number')
            write_cell(fila, 11, 'Compra de Activos',               detail_alt_label_format)
            write_cell(fila, 12, res['total']['compra_de_activos'],  detail_alt_value_format, 'number')
            write_cell(fila, 13, res['total']['compra_de_activos'] * 0.12, detail_alt_value_format, 'number')
            write_cell(fila, 14, res['total']['compra_de_activos'] * 1.12, detail_alt_value_format, 'number')

            fila += 1
            write_cell(fila,  5, 'IVA POR COBRAR',   detail_label_format)
            write_cell(fila,  6, '',                  detail_label_format)
            write_cell(fila,  7, '',                  detail_label_format)
            write_cell(fila,  8, res['total']['iva'], detail_value_format, 'number')
            write_cell(fila, 11, 'Compras',           detail_label_format)
            write_cell(fila, 12, res['total']['compra'],         detail_value_format, 'number')
            write_cell(fila, 13, res['total']['compra'] * 0.12,  detail_value_format, 'number')
            write_cell(fila, 14, res['total']['compra'] * 1.12,  detail_value_format, 'number')

            fila += 1
            write_cell(fila,  5, 'EXEN IVA', detail_alt_label_format)
            write_cell(fila,  6, '',          detail_alt_label_format)
            write_cell(fila,  7, '',          detail_alt_label_format)
            write_cell(fila,  8, res['total']['compra_exento'] + res['total']['servicio_exento'],
                       detail_alt_value_format, 'number')
            write_cell(fila, 11, 'Servicios', detail_alt_label_format)
            write_cell(fila, 12, res['total']['servicio'],          detail_alt_value_format, 'number')
            write_cell(fila, 13, res['total']['servicio'] * 0.12,   detail_alt_value_format, 'number')
            write_cell(fila, 14, res['total']['servicio'] * 1.12,   detail_alt_value_format, 'number')

            fila += 1
            write_cell(fila,  5, 'CREDITO FISCAL PERIODO ANTERIOR', detail_label_format)
            write_cell(fila,  6, '',          detail_label_format)
            write_cell(fila,  7, '',          detail_label_format)
            write_cell(fila,  8, res['total']['credito_fiscal_periodo_anterior'], detail_value_format, 'number')
            write_cell(fila, 11, 'Importaciones C.A.', detail_label_format)
            write_cell(fila, 12, res['total']['importacion'],          detail_value_format, 'number')
            write_cell(fila, 13, res['total']['importacion'] * 0.12,   detail_value_format, 'number')
            write_cell(fila, 14, res['total']['importacion'] * 1.12,   detail_value_format, 'number')

            fila += 1
            write_cell(fila,  5, 'IVA POR PAGAR', detail_total_label_format)
            write_cell(fila,  6, '',               detail_total_label_format)
            write_cell(fila,  7, '',               detail_total_label_format)
            write_cell(fila,  8,
                res['total']['iva_por_pagar']
                + res['total']['valor_retencion_iva']
                - res['total']['iva']
                + res['total']['compra_exento']
                + res['total']['servicio_exento']
                + res['total']['credito_fiscal_periodo_anterior'],
                detail_total_value_format, 'number')

            fila += 1

            # ── Aplicar anchos automáticos solo a montos ───────────────────
            for col, width in column_widths.items():
                if col not in range(0, 6):
                    hoja.set_column(col, col, min(width + 2, 50))

            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo': datos, 'name': 'libro_compras.xlsx'})

            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/?model=%s&id=%s&field=archivo&filename_field=name&download=true' % (
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
