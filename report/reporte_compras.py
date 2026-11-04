# -*- encoding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class PurchaseBookReport(models.AbstractModel):
    _name = 'report.l10n_gt_joyeria.reporte_compras'

    def _get_conversion(self, moves):
        conversion = {'impuesto': 0, 'total': 0}
        total_without_tax = 0
        grand_total = 0

        amount_untaxed = 0
        amount_tax = 0
        amount_total = 0
        amount_residual = 0
        amount_untaxed_signed = 0
        amount_tax_signed = 0
        amount_total_signed = 0
        amount_residual_signed = 0

        for move in moves:
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


    def _has_vat_tax(self, tax_ids):
        tax_iva = False
        if len(tax_ids) > 0:
            for tax in tax_ids:
                if 'IVA' in tax.name:
                    tax_iva = True
                    print('si hay iva')
        return tax_iva


    def _get_purchases(self, report_data):
        purchases = []
        non_deductible_expenses = []
        print(self.env.company)

        purchase_ids = self.env['account.move'].search([('company_id', '=', self.env.company.id),
                                                      ('date', '<=', report_data['date_end']),
                                                      ('date', '>=', report_data['date_start']), ('state', '=', 'posted'),
                                                      ('move_type', 'in', ['in_invoice', 'in_refund'])])
        total = {
            'compra': 0, 'compra_exento': 0, 'servicio': 0, 'servicio_exento': 0,
            'importacion': 0, 'pequenio': 0, 'iva': 0, 'isr_retencion': 0, 'total': 0,
            'iva_por_pagar': 0, 'valor_retencion_iva': 0, 'compra_de_activos': 0,
            'credito_fiscal_periodo_anterior': 0, 'combustible': 0, 'idp': 0
        }
        total_non_deductible_expenses = 0
        processed_documents = 0
        print('JOYERIA compras: fechas=%s a %s, documentos encontrados=%s' % (report_data['date_start'], report_data['date_end'], len(purchase_ids)))
        print()
        if purchase_ids:

            for purchase in purchase_ids:
                print('JOYERIA documento id=%s nombre=%s tipo=%s moneda=%s' % (purchase.id, purchase.name, purchase.move_type, purchase.currency_id.name))
                print()
                if 'RECIB' not in purchase.journal_id.code:

                    if hasattr(purchase, 'feel_serie') and purchase.feel_serie:
                        invoice_series = purchase.feel_serie
                    elif hasattr(purchase, 'serie_factura') and purchase.serie_factura:
                        invoice_series = purchase.serie_factura
                    else:
                        invoice_series = ''

                    # Para el campo 'numero_dte'
                    if hasattr(purchase, 'num_factura') and purchase.num_factura:
                        dte_number = purchase.num_factura
                    elif hasattr(purchase, 'feel_numero') and purchase.feel_numero:
                        dte_number = purchase.feel_numero
                    else:
                        dte_number = ''
                    processed_documents += 1
                    print(purchase.name)
                    document_data = {
                        'id': purchase.id,
                        'fecha': purchase.date,
                        'documento': purchase.ref if purchase.ref else purchase.name,
                        'proveedor': purchase.partner_id.name if purchase.partner_id else '',
                        'nit': purchase.partner_id.vat if purchase.partner_id.vat else '',
                        'serie': purchase.feel_serie if hasattr(purchase, 'feel_serie') and purchase.feel_serie else (
                            purchase.serie_factura if hasattr(purchase, 'serie_factura') and purchase.serie_factura else ''),
                        'numero_dte': purchase.num_factura if hasattr(purchase, 'num_factura') and purchase.num_factura else (
                            purchase.feel_numero if hasattr(purchase, 'feel_numero') and purchase.feel_numero else ''),
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

                    for invoice_line in purchase.invoice_line_ids:
                        print('JOYERIA linea documento=%s linea=%s producto=%s subtotal=%s impuestos=%s' % (purchase.name, invoice_line.id, invoice_line.product_id.display_name or invoice_line.name, invoice_line.price_subtotal, invoice_line.tax_ids.mapped('name')))
                        tax_iva = False
                        tax_iva = self._has_vat_tax(invoice_line.tax_ids)
                        if purchase.currency_id.id != purchase.company_id.currency_id.id:
                            if ((invoice_line.product_id or invoice_line.name) and (('COMISION POR SERVICIOS' not in (invoice_line.product_id.name or '')) or (
                                    'COMISIONES BANCARIAS' not in (invoice_line.product_id.name or '')) or (
                                                                'Servicios y Comisiones' not in (invoice_line.product_id.name or '')))):
                                if len(invoice_line.tax_ids) > 0:
                                    amount_to_convert_before_tax = invoice_line.price_unit

                                    if invoice_line.product_id:
                                        tax_computation = invoice_line.tax_ids.compute_all(amount_to_convert_before_tax, currency=purchase.currency_id, quantity=invoice_line.quantity, product=invoice_line.product_id, partner=purchase.partner_id)
                                    else:
                                        tax_computation = invoice_line.tax_ids.compute_all(amount_to_convert_before_tax, currency=purchase.currency_id, quantity=invoice_line.quantity, partner=purchase.partner_id)

                                    for tax_entry in tax_computation['taxes']:
                                        tax = self.env['account.tax'].browse(tax_entry['id'])
                                        tax_name = (tax.name or tax_entry.get('name') or '').upper()
                                        tax_amount = purchase.currency_id._convert(tax_entry['amount'], purchase.company_id.currency_id, purchase.company_id, purchase.invoice_date or purchase.date)
                                        if 'IDP' in tax_name:
                                            document_data['idp'] += tax_amount
                                        elif 'IVA' in tax_name:
                                            document_data['iva'] += tax_amount
                                        if tax.es_isr_retencion:
                                            document_data['isr_retencion'] += abs(tax_amount)
                                        print('JOYERIA impuesto documento=%s linea=%s impuesto=%s monto_moneda=%s monto_compania=%s' % (purchase.name, tax.id, tax_name, tax_entry['amount'], tax_amount))

                                    converted_amount = purchase.currency_id._convert(
                                        invoice_line.price_subtotal,
                                        purchase.company_id.currency_id,
                                        purchase.company_id,
                                        purchase.invoice_date or purchase.date
                                    )

                                    if invoice_line.product_id.can_be_asset:
                                        document_data['compra_de_activos'] += converted_amount
                                    elif purchase.tipo_gasto == 'combustible':
                                        document_data['combustible'] += converted_amount
                                    else:
                                        if purchase.tipo_gasto == 'mixto':
                                            if invoice_line.product_id.type == 'consu':
                                                document_data['compra'] += converted_amount
                                            else:
                                                document_data['servicio'] += converted_amount
                                        elif purchase.tipo_gasto == 'importacion':
                                            document_data['importacion'] += converted_amount
                                        else:
                                            if invoice_line.product_id.type == 'consu':
                                                document_data['compra'] += converted_amount
                                            else:
                                                document_data['servicio'] += converted_amount

                                    if purchase.partner_id.pequenio_contribuyente:
                                        document_data['compra'] = 0
                                        document_data['servicio'] = 0
                                        document_data['importacion'] = 0
                                        document_data['compra_exento'] = 0
                                        document_data['servicio_exento'] = 0
                                        document_data['iva'] = 0
                                        document_data['pequenio'] += converted_amount

                                    # document_data['total']
                                else:
                                    converted_amount = purchase.currency_id._convert(
                                        invoice_line.price_total,
                                        purchase.company_id.currency_id,
                                        purchase.company_id,
                                        purchase.invoice_date or purchase.date
                                    )
                                    if invoice_line.product_id.can_be_asset:
                                        document_data['compra_de_activos'] += converted_amount
                                    elif purchase.tipo_gasto == 'combustible':
                                        document_data['combustible'] += converted_amount
                                    else:
                                        if purchase.tipo_gasto == 'varios':
                                            if invoice_line.product_id.type == 'consu':
                                                document_data['compra'] += converted_amount
                                            else:
                                                document_data['servicio'] += converted_amount
                                        elif purchase.tipo_gasto == 'importacion':
                                            document_data['importacion'] += converted_amount
                                        else:
                                            if invoice_line.product_id.type == 'consu':
                                                document_data['compra'] += converted_amount
                                            else:
                                                document_data['servicio'] += converted_amount

                                    if purchase.partner_id.pequenio_contribuyente:
                                        document_data['compra'] = 0
                                        document_data['servicio'] = 0
                                        document_data['importacion'] = 0
                                        document_data['compra_exento'] = 0
                                        document_data['servicio_exento'] = 0
                                        document_data['iva'] = 0
                                        document_data['pequenio'] += converted_amount

                        else:
                            print("WELP")
                            print(invoice_line.product_id.name)
                            print(invoice_line.product_id)
                            if ((invoice_line.product_id or invoice_line.name) and (('COMISION POR SERVICIOS' not in (invoice_line.product_id.name or '')) or (
                                    'COMISIONES BANCARIAS' not in (invoice_line.product_id.name or '')) or (
                                                                'Servicios y Comisiones' not in (invoice_line.product_id.name or '')))):
                                if len(invoice_line.tax_ids) > 0:
                                    # amount_to_convert_before_tax = purchase.currency_id.with_context(date=purchase.invoice_date).compute(invoice_line.price_unit, purchase.company_id.currency_id)

                                    if invoice_line.product_id:
                                        tax_computation = invoice_line.tax_ids.compute_all(invoice_line.price_unit, currency=purchase.currency_id, quantity=invoice_line.quantity, product=invoice_line.product_id, partner=purchase.partner_id)
                                    else:
                                        tax_computation = invoice_line.tax_ids.compute_all(invoice_line.price_unit, currency=purchase.currency_id, quantity=invoice_line.quantity, partner=purchase.partner_id)

                                    for tax_entry in tax_computation['taxes']:
                                        tax = self.env['account.tax'].browse(tax_entry['id'])
                                        tax_name = (tax.name or tax_entry.get('name') or '').upper()
                                        tax_amount = purchase.currency_id._convert(tax_entry['amount'], purchase.company_id.currency_id, purchase.company_id, purchase.invoice_date or purchase.date)
                                        if 'IDP' in tax_name:
                                            document_data['idp'] += tax_amount
                                        elif 'IVA' in tax_name:
                                            document_data['iva'] += tax_amount
                                        if tax.es_isr_retencion:
                                            document_data['isr_retencion'] += abs(tax_amount)
                                        print('JOYERIA impuesto documento=%s linea=%s impuesto=%s monto_moneda=%s monto_compania=%s' % (purchase.name, tax.id, tax_name, tax_entry['amount'], tax_amount))

                                    if invoice_line.product_id.can_be_asset:
                                        document_data['compra_de_activos'] += invoice_line.price_subtotal
                                    elif purchase.tipo_gasto == 'combustible':
                                        document_data['combustible'] += invoice_line.price_subtotal
                                    else:
                                        if purchase.tipo_gasto == 'mixto':
                                            if invoice_line.product_id.type == 'consu':
                                                document_data['compra'] += invoice_line.price_subtotal
                                            else:
                                                document_data['servicio'] += invoice_line.price_subtotal
                                        elif purchase.tipo_gasto == 'importacion':
                                            document_data['importacion'] += invoice_line.price_subtotal
                                        else:
                                            if invoice_line.product_id.type == 'consu':
                                                document_data['compra'] += invoice_line.price_subtotal
                                            else:
                                                document_data['servicio'] += invoice_line.price_subtotal

                                    if purchase.partner_id.pequenio_contribuyente:
                                        document_data['compra'] = 0
                                        document_data['servicio'] = 0
                                        document_data['importacion'] = 0
                                        document_data['compra_exento'] = 0
                                        document_data['servicio_exento'] = 0
                                        document_data['iva'] = 0
                                        document_data['pequenio'] += invoice_line.price_total


                                else:
                                    if invoice_line.product_id.type == 'consu':
                                        document_data['compra_exento'] += invoice_line.price_total
                                    else:
                                        document_data['servicio_exento'] += invoice_line.price_total

                                    if purchase.partner_id.pequenio_contribuyente:
                                        document_data['compra'] = 0
                                        document_data['servicio'] = 0
                                        document_data['importacion'] = 0
                                        document_data['compra_exento'] = 0
                                        document_data['servicio_exento'] = 0
                                        document_data['pequenio'] += invoice_line.price_total

                    document_data['total'] = document_data['compra'] + document_data['servicio'] + document_data['compra_exento'] + document_data['servicio_exento'] + \
                                   document_data['importacion'] + document_data['iva'] + document_data['idp'] + document_data['pequenio'] + document_data['compra_de_activos'] + document_data[
                                       'combustible'] - document_data['isr_retencion']

                    if purchase.move_type in ['in_refund']:
                        # document_data['total'] = document_data['compra'] - document_data['servicio'] - document_data['compra_exento'] - document_data['servicio_exento'] - document_data['importacion'] - document_data['iva'] - document_data['pequenio']

                        document_data['compra'] = document_data['compra'] * -1
                        document_data['compra_exento'] = document_data['compra_exento'] * -1
                        document_data['servicio'] = document_data['servicio'] * -1
                        document_data['servicio_exento'] = document_data['servicio_exento'] * -1
                        document_data['importacion'] = document_data['importacion'] * -1
                        document_data['pequenio'] = document_data['pequenio'] * -1
                        document_data['iva'] = document_data['iva'] * -1
                        document_data['isr_retencion'] = document_data['isr_retencion'] * -1
                        document_data['total'] = document_data['total'] * -1
                        document_data['compra_de_activos'] = document_data['compra_de_activos'] * -1
                        document_data['combustible'] = document_data['combustible'] * -1
                        document_data['idp'] = document_data['idp'] * -1
                    for key in ('compra', 'compra_exento', 'servicio', 'servicio_exento', 'importacion', 'pequenio', 'iva', 'idp', 'isr_retencion', 'total', 'compra_de_activos', 'combustible'):
                        total[key] += document_data[key]
                    print('JOYERIA resumen documento=%s compra=%s servicio=%s iva=%s idp=%s total=%s' % (purchase.name, document_data['compra'], document_data['servicio'], document_data['iva'], document_data['idp'], document_data['total']))
                    print()
                    purchases.append(document_data)
                else:
                    print(purchase.name)
                    print("HA")
                    # GASTOS NO DEDUCIBLES
                    document_data = {
                        'id': purchase.id,
                        'fecha': purchase.date,
                        'documento': purchase.name,
                        'proveedor': purchase.partner_id.name if purchase.partner_id else '',
                        'nit': purchase.partner_id.vat if purchase.partner_id.vat else '',
                        'total': purchase.amount_total
                    }
                    total_non_deductible_expenses += purchase.amount_total
                    non_deductible_expenses.append(document_data)

        # # Obtener el IVA por pagar y el total de retenciones desde el reporte de ventas
        # ventas_res = self.env['report.l10n_gt_joyeria.reporte_libro_ventas']._get_ventas({
        #     'date_start': report_data['date_start'],
        #     'date_end': report_data['date_end']
        # })
        # total['iva_por_pagar'] = ventas_res['total']['iva']
        # total['valor_retencion_iva'] = ventas_res['total']['total_retenciones']

        # Obtener el crédito fiscal del período anterior
        start_date = datetime.strptime(report_data['date_start'], '%Y-%m-%d').date()
        previous_period_end_date = start_date - timedelta(days=1)
        previous_period_start_date = previous_period_end_date - timedelta(days=4)
        previous_fiscal_credit_move = self.env['account.move'].search([('date', '>=', previous_period_start_date),
                                                               ('date', '<=', previous_period_end_date),
                                                               ('state', '=', 'posted'), (
                                                                   'fiscal_credit', '=',
                                                                   True)], limit=1, order='date desc')
        if previous_fiscal_credit_move:
            total['credito_fiscal_periodo_anterior'] = previous_fiscal_credit_move.amount_total

        return {'compras_lista': purchases, 'total': total, 'documentos_operados': processed_documents,
                'gastos_no': non_deductible_expenses, 'total_gastos_no': total_non_deductible_expenses}

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            '_get_compras': self._get_purchases,
        }