{
    'name': 'Solicitudes Taller Vehicular',
    'version': '1.0',
    'category': 'Fleet Management',
    'summary': 'Gestión de solicitudes de ingreso a taller mecánico de la flota vehicular',
    'description': """
Módulo para registrar y gestionar solicitudes de ingreso al taller mecánico.
Cada solicitud es realizada por un analista y contiene información del vehículo, falla reportada, fechas de solicitud y asignación.
    """,
    'author': 'Tu Nombre o Empresa',
    'depends': ['base', 'fleet', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template.xml', # ¡Añade esta línea!  
        'data/mail_template_data.xml', # ¡Añade esta línea!        
        'views/taller_solicitud_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
