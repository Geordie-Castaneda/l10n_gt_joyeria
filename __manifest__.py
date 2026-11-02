# -*- coding: utf-8 -*-
{
    'name': 'Guatemala - Libro de compras Joyeria',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Libro de compras con desglose de IDP',
    'depends': ['base', 'l10n_gt_extra'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/reporte_compras.xml',
    ],
    'demo': ['demo/demo.xml'],
    'installable': True,
    'license': 'Other OSI approved licence',
}
