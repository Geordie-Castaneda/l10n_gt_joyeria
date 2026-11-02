# -*- encoding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class LibroCompras(models.AbstractModel):
    _name = 'report.l10n_gt_joyeria.reporte_compras'

    def _get_conversion(self, move_id):
        conversion = {'impuesto': 0, 'total': 0}
        total_sin_impuesto = 0
        total_total = 0

        amount_untaxed = 0
        amount_tax = 0
        amount_total = 0
        amount_residual = 0
        amount_untaxed_signed = 0
        amount_tax_signed = 0
        amount_total_signed = 0
        amount_residual_signed = 0

        for move in move_id:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.user_type_id.move_type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1

            amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            amount_total = sign * (total_currency if len(currencies) == 1 else total)
            amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            amount_untaxed_signed = -total_untaxed
            amount_tax_signed = -total_tax
            amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            amount_residual_signed = total_residual

            # print(move.name)
            print(amount_untaxed)
            print(amount_tax)
            print(amount_total)
            print(amount_residual)
            print(amount_untaxed_signed)
            print(amount_total_signed)
            print(amount_residual_signed)

            if amount_residual_signed < 0:
                print('IF')
                print(amount_residual_signed)
                print(amount_tax_signed)
                conversion['impuesto'] = (amount_tax_signed * -1)
                conversion['total'] = amount_residual_signed * -1
            else:
                conversion['impuesto'] = (amount_tax_signed)
                conversion['total'] = amount_residual_signed
            print(move.name)
            print(conversion)

        return conversion


    def _get_impuesto_iva(self, tax_ids):
        impuesto_iva = False
        if len(tax_ids) > 0:
            for linea in tax_ids:
                if 'IVA' in linea.name:
                    impuesto_iva = True
                    print('si hay iva')
        return impuesto_iva


    def _get_compras(self, datos):
        compras_lista = []
        gastos_no_lista = []
        print(self.env.company)

        compra_ids = self.env['account.move'].search([('company_id', '=', self.env.company.id),
                                                      ('date', '<=', datos['fecha_fin']),
                                                      ('date', '>=', datos['fecha_inicio']), ('state', '=', 'posted'),
                                                      ('move_type', 'in', ['in_invoice', 'in_refund'])])
        total = {
            'compra': 0, 'compra_exento': 0, 'servicio': 0, 'servicio_exento': 0,
            'importacion': 0, 'pequenio': 0, 'iva': 0, 'isr_retencion': 0, 'total': 0,
            'iva_por_pagar': 0, 'valor_retencion_iva': 0, 'compra_de_activos': 0,
            'credito_fiscal_periodo_anterior': 0, 'combustible': 0, 'idp': 0
        }
        total_gastos_no = 0
        documentos_operados = 0
        print('JOYERIA compras: fechas=%s a %s, documentos encontrados=%s' % (datos['fecha_inicio'], datos['fecha_fin'], len(compra_ids)))
        print()
        if compra_ids:

            for compra in compra_ids:
                print('JOYERIA documento id=%s nombre=%s tipo=%s moneda=%s' % (compra.id, compra.name, compra.move_type, compra.currency_id.name))
                print()
                if 'RECIB' not in compra.journal_id.code:

                    if hasattr(compra, 'feel_serie') and compra.feel_serie:
                        serie = compra.feel_serie
                    elif hasattr(compra, 'serie_factura') and compra.serie_factura:
                        serie = compra.serie_factura
                    else:
                        serie = ''

                    # Para el campo 'numero_dte'
                    if hasattr(compra, 'num_factura') and compra.num_factura:
                        numero_dte = compra.num_factura
                    elif hasattr(compra, 'feel_numero') and compra.feel_numero:
                        numero_dte = compra.feel_numero
                    else:
                        numero_dte = ''
                    documentos_operados += 1
                    print(compra.name)
                    dic = {
                        'id': compra.id,
                        'fecha': compra.date,
                        'documento': compra.ref if compra.ref else compra.name,
                        'proveedor': compra.partner_id.name if compra.partner_id else '',
                        'nit': compra.partner_id.vat if compra.partner_id.vat else '',
                        'serie': compra.feel_serie if hasattr(compra, 'feel_serie') and compra.feel_serie else (
                            compra.serie_factura if hasattr(compra, 'serie_factura') and compra.serie_factura else ''),
                        'numero_dte': compra.num_factura if hasattr(compra, 'num_factura') and compra.num_factura else (
                            compra.feel_numero if hasattr(compra, 'feel_numero') and compra.feel_numero else ''),
                        'compra': 0,
                        'compra_exento': 0,
                        'servicio': 0,
                        'servicio_exento': 0,
                        'importacion': 0,
                        'pequenio': 0,
                        'iva': 0,
                        'isr_retencion': 0,
                        'total': 0,
                        'compra_de_activos': 0,
                        'combustible': 0,
                        'idp': 0
                    }

                    for linea in compra.invoice_line_ids:
                        print('JOYERIA linea documento=%s linea=%s producto=%s subtotal=%s impuestos=%s' % (compra.name, linea.id, linea.product_id.display_name or linea.name, linea.price_subtotal, linea.tax_ids.mapped('name')))
                        impuesto_iva = False
                        impuesto_iva = self._get_impuesto_iva(linea.tax_ids)
                        if compra.currency_id.id != compra.company_id.currency_id.id:
                            if ((linea.product_id or linea.name) and (('COMISION POR SERVICIOS' not in (linea.product_id.name or '')) or (
                                    'COMISIONES BANCARIAS' not in (linea.product_id.name or '')) or (
                                                                'Servicios y Comisiones' not in (linea.product_id.name or '')))):
                                if len(linea.tax_ids) > 0:
                                    monto_convertir_precio = linea.price_unit

                                    if linea.product_id:
                                        r = linea.tax_ids.compute_all(monto_convertir_precio, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)
                                    else:
                                        r = linea.tax_ids.compute_all(monto_convertir_precio, currency=compra.currency_id, quantity=linea.quantity, partner=compra.partner_id)

                                    for i in r['taxes']:
                                        tax = self.env['account.tax'].browse(i['id'])
                                        tax_name = (tax.name or i.get('name') or '').upper()
                                        tax_amount = compra.currency_id._convert(i['amount'], compra.company_id.currency_id, compra.company_id, compra.invoice_date or compra.date)
                                        if 'IDP' in tax_name:
                                            dic['idp'] += tax_amount
                                        elif 'IVA' in tax_name:
                                            dic['iva'] += tax_amount
                                        if tax.es_isr_retencion:
                                            dic['isr_retencion'] += abs(tax_amount)
                                        print('JOYERIA impuesto documento=%s linea=%s impuesto=%s monto_moneda=%s monto_compania=%s' % (compra.name, linea.id, tax_name, i['amount'], tax_amount))

                                    monto_convertir = compra.currency_id._convert(
                                        linea.price_subtotal,
                                        compra.company_id.currency_id,
                                        compra.company_id,
                                        compra.invoice_date or compra.date
                                    )

                                    if linea.product_id.can_be_asset:
                                        dic['compra_de_activos'] += monto_convertir
                                    elif compra.tipo_gasto == 'combustible':
                                        dic['combustible'] += monto_convertir
                                    else:
                                        if compra.tipo_gasto == 'mixto':
                                            if linea.product_id.type == 'consu':
                                                dic['compra'] += monto_convertir
                                            else:
                                                dic['servicio'] += monto_convertir
                                        elif compra.tipo_gasto == 'importacion':
                                            dic['importacion'] += monto_convertir
                                        else:
                                            if linea.product_id.type == 'consu':
                                                dic['compra'] += monto_convertir
                                            else:
                                                dic['servicio'] += monto_convertir

                                    if compra.partner_id.pequenio_contribuyente:
                                        dic['compra'] = 0
                                        dic['servicio'] = 0
                                        dic['importacion'] = 0
                                        dic['compra_exento'] = 0
                                        dic['servicio_exento'] = 0
                                        dic['iva'] = 0
                                        dic['pequenio'] += monto_convertir

                                    # dic['total']
                                else:
                                    monto_convertir = compra.currency_id._convert(
                                        linea.price_total,
                                        compra.company_id.currency_id,
                                        compra.company_id,
                                        compra.invoice_date or compra.date
                                    )
                                    if linea.product_id.can_be_asset:
                                        dic['compra_de_activos'] += monto_convertir
                                    elif compra.tipo_gasto == 'combustible':
                                        dic['combustible'] += monto_convertir
                                    else:
                                        if compra.tipo_gasto == 'varios':
                                            if linea.product_id.type == 'consu':
                                                dic['compra'] += monto_convertir
                                            else:
                                                dic['servicio'] += monto_convertir
                                        elif compra.tipo_gasto == 'importacion':
                                            dic['importacion'] += monto_convertir
                                        else:
                                            if linea.product_id.type == 'consu':
                                                dic['compra'] += monto_convertir
                                            else:
                                                dic['servicio'] += monto_convertir

                                    if compra.partner_id.pequenio_contribuyente:
                                        dic['compra'] = 0
                                        dic['servicio'] = 0
                                        dic['importacion'] = 0
                                        dic['compra_exento'] = 0
                                        dic['servicio_exento'] = 0
                                        dic['iva'] = 0
                                        dic['pequenio'] += monto_convertir

                        else:
                            print("WELP")
                            print(linea.product_id.name)
                            print(linea.product_id)
                            if ((linea.product_id or linea.name) and (('COMISION POR SERVICIOS' not in (linea.product_id.name or '')) or (
                                    'COMISIONES BANCARIAS' not in (linea.product_id.name or '')) or (
                                                                'Servicios y Comisiones' not in (linea.product_id.name or '')))):
                                if len(linea.tax_ids) > 0:
                                    # monto_convertir_precio = compra.currency_id.with_context(date=compra.invoice_date).compute(linea.price_unit, compra.company_id.currency_id)

                                    if linea.product_id:
                                        r = linea.tax_ids.compute_all(linea.price_unit, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)
                                    else:
                                        r = linea.tax_ids.compute_all(linea.price_unit, currency=compra.currency_id, quantity=linea.quantity, partner=compra.partner_id)

                                    for i in r['taxes']:
                                        tax = self.env['account.tax'].browse(i['id'])
                                        tax_name = (tax.name or i.get('name') or '').upper()
                                        tax_amount = compra.currency_id._convert(i['amount'], compra.company_id.currency_id, compra.company_id, compra.invoice_date or compra.date)
                                        if 'IDP' in tax_name:
                                            dic['idp'] += tax_amount
                                        elif 'IVA' in tax_name:
                                            dic['iva'] += tax_amount
                                        if tax.es_isr_retencion:
                                            dic['isr_retencion'] += abs(tax_amount)
                                        print('JOYERIA impuesto documento=%s linea=%s impuesto=%s monto_moneda=%s monto_compania=%s' % (compra.name, linea.id, tax_name, i['amount'], tax_amount))

                                    if linea.product_id.can_be_asset:
                                        dic['compra_de_activos'] += linea.price_subtotal
                                    elif compra.tipo_gasto == 'combustible':
                                        dic['combustible'] += linea.price_subtotal
                                    else:
                                        if compra.tipo_gasto == 'mixto':
                                            if linea.product_id.type == 'consu':
                                                dic['compra'] += linea.price_subtotal
                                            else:
                                                dic['servicio'] += linea.price_subtotal
                                        elif compra.tipo_gasto == 'importacion':
                                            dic['importacion'] += linea.price_subtotal
                                        else:
                                            if linea.product_id.type == 'consu':
                                                dic['compra'] += linea.price_subtotal
                                            else:
                                                dic['servicio'] += linea.price_subtotal

                                    if compra.partner_id.pequenio_contribuyente:
                                        dic['compra'] = 0
                                        dic['servicio'] = 0
                                        dic['importacion'] = 0
                                        dic['compra_exento'] = 0
                                        dic['servicio_exento'] = 0
                                        dic['iva'] = 0
                                        dic['pequenio'] += linea.price_total


                                else:
                                    if linea.product_id.type == 'consu':
                                        dic['compra_exento'] += linea.price_total
                                    else:
                                        dic['servicio_exento'] += linea.price_total

                                    if compra.partner_id.pequenio_contribuyente:
                                        dic['compra'] = 0
                                        dic['servicio'] = 0
                                        dic['importacion'] = 0
                                        dic['compra_exento'] = 0
                                        dic['servicio_exento'] = 0
                                        dic['pequenio'] += linea.price_total

                    dic['total'] = dic['compra'] + dic['servicio'] + dic['compra_exento'] + dic['servicio_exento'] + \
                                   dic['importacion'] + dic['iva'] + dic['idp'] + dic['pequenio'] + dic['compra_de_activos'] + dic[
                                       'combustible'] - dic['isr_retencion']

                    if compra.move_type in ['in_refund']:
                        # dic['total'] = dic['compra'] - dic['servicio'] - dic['compra_exento'] - dic['servicio_exento'] - dic['importacion'] - dic['iva'] - dic['pequenio']

                        dic['compra'] = dic['compra'] * -1
                        dic['compra_exento'] = dic['compra_exento'] * -1
                        dic['servicio'] = dic['servicio'] * -1
                        dic['servicio_exento'] = dic['servicio_exento'] * -1
                        dic['importacion'] = dic['importacion'] * -1
                        dic['pequenio'] = dic['pequenio'] * -1
                        dic['iva'] = dic['iva'] * -1
                        dic['isr_retencion'] = dic['isr_retencion'] * -1
                        dic['total'] = dic['total'] * -1
                        dic['compra_de_activos'] = dic['compra_de_activos'] * -1
                        dic['combustible'] = dic['combustible'] * -1
                        dic['idp'] = dic['idp'] * -1
                    for campo in ('compra', 'compra_exento', 'servicio', 'servicio_exento', 'importacion', 'pequenio', 'iva', 'idp', 'isr_retencion', 'total', 'compra_de_activos', 'combustible'):
                        total[campo] += dic[campo]
                    print('JOYERIA resumen documento=%s compra=%s servicio=%s iva=%s idp=%s total=%s' % (compra.name, dic['compra'], dic['servicio'], dic['iva'], dic['idp'], dic['total']))
                    print()
                    compras_lista.append(dic)
                else:
                    print(compra.name)
                    print("HA")
                    # GASTOS NO DEDUCIBLES
                    dic = {
                        'id': compra.id,
                        'fecha': compra.date,
                        'documento': compra.name,
                        'proveedor': compra.partner_id.name if compra.partner_id else '',
                        'nit': compra.partner_id.vat if compra.partner_id.vat else '',
                        'total': compra.amount_total
                    }
                    total_gastos_no += compra.amount_total
                    gastos_no_lista.append(dic)

        # # Obtener el IVA por pagar y el total de retenciones desde el reporte de ventas
        # ventas_res = self.env['report.l10n_gt_joyeria.reporte_libro_ventas']._get_ventas({
        #     'fecha_inicio': datos['fecha_inicio'],
        #     'fecha_fin': datos['fecha_fin']
        # })
        # total['iva_por_pagar'] = ventas_res['total']['iva']
        # total['valor_retencion_iva'] = ventas_res['total']['total_retenciones']

        # Obtener el crédito fiscal del período anterior
        fecha_inicio = datetime.strptime(datos['fecha_inicio'], '%Y-%m-%d').date()
        fecha_fin_anterior = fecha_inicio - timedelta(days=1)
        fecha_inicio_anterior = fecha_fin_anterior - timedelta(days=4)
        credito_fiscal_move = self.env['account.move'].search([('date', '>=', fecha_inicio_anterior),
                                                               ('date', '<=', fecha_fin_anterior),
                                                               ('state', '=', 'posted'), (
                                                                   'fiscal_credit', '=',
                                                                   True)], limit=1, order='date desc')
        if credito_fiscal_move:
            total['credito_fiscal_periodo_anterior'] = credito_fiscal_move.amount_total

        return {'compras_lista': compras_lista, 'total': total, 'documentos_operados': documentos_operados,
                'gastos_no': gastos_no_lista, 'total_gastos_no': total_gastos_no}

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            '_get_compras': self._get_compras,
        }