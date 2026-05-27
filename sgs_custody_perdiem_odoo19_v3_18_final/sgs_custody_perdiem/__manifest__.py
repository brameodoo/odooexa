{
    'name': 'SGS Control de Viáticos y Custodias',
    'version': '19.0.1.0.1',
    'category': 'Operations/Logistics',
    'summary': 'Gestión de custodios, rutas, viáticos, comprobación de gastos y portal público por token.',
    'description': '''
SGS Control de Viáticos y Custodias
===================================

Módulo para administrar custodios de vehículos pesados, depósitos de viáticos, servicios de custodia en rutas, comprobación de gastos, casetas, facturas fiscales y validación administrativa. Incluye portal público por token para que los custodios reporten gastos sin usuario interno.
    ''',
    'author': 'Manus AI',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'portal'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/assets.xml',
        'views/menu.xml',
        'views/custody_views.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sgs_custody_perdiem/static/src/scss/sgs_portal.scss',
        ],
    },
    'application': True,
    'installable': True,
}
