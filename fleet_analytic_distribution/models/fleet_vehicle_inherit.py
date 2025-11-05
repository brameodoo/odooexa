from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    analytic_distribution_id = fields.Many2one(
        'account.analytic.distribution.model',
        string='Distribución Analítica',
        help='Permite definir un modelo de distribución analítica para este vehículo.'
    )
