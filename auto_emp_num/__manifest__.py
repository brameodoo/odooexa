{
    'name': 'Auto Employee Number & PIN by Seniority',
    'version': '19.0.1.0.0',
    'summary': 'Genera ID de empleado EMP00001 y sincroniza el PIN basado en fecha de contrato',
    'category': 'Human Resources',
    'author': 'Xentinell IA assist',
    'depends': ['hr'],
    'data': [
        'data/ir_sequence_data.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
