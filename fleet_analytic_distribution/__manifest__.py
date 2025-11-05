{
    'name': 'Fleet Analytic Distribution',
    'version': '17.0.1.0.0',
    'summary': 'Agrega campo de distribución analítica al vehículo',
    'category': 'Fleet',
    'author': 'Tu Nombre o Empresa',
    'depends': [
        'fleet',
        'analytic'  # necesario para los modelos analíticos
    ],
    'data': [
        'views/fleet_vehicle_view_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
