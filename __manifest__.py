# -*- coding: utf-8 -*-
{
    'name': 'Guatemala - Libro de compras y devoluciones Joyeria',
    'version': '18.0.1.1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Libro de compras y asistente de devolución de inventario para notas de crédito',
    'description': '''
Incluye el libro de compras de joyería y un asistente para notas de crédito de cliente.
El asistente relaciona las entregas de venta, permite seleccionar productos a devolver
y crea transferencias de devolución estándar pendientes de validación.
''',
    'depends': ['base', 'account', 'l10n_gt_extra', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/credit_note_return_wizard.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/reporte_compras.xml',
    ],
    'demo': ['demo/demo.xml'],
    'installable': True,
    'license': 'LGPL-3',
}
