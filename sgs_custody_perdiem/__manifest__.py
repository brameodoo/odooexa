# -*- coding: utf-8 -*-
{
    'name': 'SGS Control de Viáticos y Custodias',
    'version': '19.0.1.0.0',
    'category': 'Operations/Logistics',
    'summary': 'Gestión de custodios, rutas, viáticos y comprobación de gastos.',
    'description': '''
SGS Control de Viáticos y Custodias
===================================

Módulo para administrar custodios, depósitos de viáticos, servicios de custodia,
comprobación de gastos, casetas, comprobantes fiscales y portal público por token.
    ''',
    'author': 'Manus AI',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'portal',
        'hr',
        'fleet',
        'contacts',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/menu.xml',
        'views/custody_views.xml',
        'views/pwa_head_template.xml',
        'views/portal_templates.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
}
