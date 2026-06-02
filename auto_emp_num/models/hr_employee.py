from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    registration_number = fields.Char(string="ID Empleado", copy=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('registration_number'):
                new_seq = self.env['ir.sequence'].next_by_code('hr.employee.number')
                vals['registration_number'] = new_seq
                # PIN automático basado en los números de la secuencia
                vals['pin'] = ''.join(filter(str.isdigit, new_seq))
        return super(HrEmployee, self).create(vals_list)

    def action_generate_numbers_by_seniority(self):
        # Buscamos empleados que no tengan ID asignado
        employees = self.search([('registration_number', '=', False)])
        
        if not employees:
            raise UserError("Todos los empleados ya tienen un número asignado.")

        # Ordenamos por fecha de creación (create_date). 
        # Como acabas de importar el Excel, el orden de creación respeta el archivo.
        sorted_employees = sorted(employees, key=lambda e: e.create_date)

        for emp in sorted_employees:
            new_seq = self.env['ir.sequence'].next_by_code('hr.employee.number')
            numeric_pin = ''.join(filter(str.isdigit, new_seq))
            
            emp.write({
                'registration_number': new_seq,
                'pin': numeric_pin
            })
        
        return {
            'effect': {
                'fadeout': 'slow',
                'message': f'Se asignaron {len(sorted_employees)} IDs correctamente.',
                'type': 'rainbow_man',
            }
        }
