from odoo import fields, models

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    analytic_distribution_id = fields.Many2one(
        'account.analytic.distribution.model',
        string='Distribución Analítica',
        help='Modelo de distribución analítica aplicado a este vehículo.'
    )
