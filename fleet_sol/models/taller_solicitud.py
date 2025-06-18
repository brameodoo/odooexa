# -*- coding: utf-8 -*-
# models/taller_solicitud.py

from odoo import models, fields, api, _ # Asegúrate de importar _ para traducciones
from odoo.exceptions import UserError
import logging # Importar el módulo de logging

_logger = logging.getLogger(__name__) # ¡Esta línea faltaba o estaba mal colocada!

class TallerSolicitud(models.Model):
    _name = 'taller.solicitud'
    _description = 'Solicitud de Taller'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default='New'
    )
    analista_id = fields.Many2one(
        'hr.employee',
        string='Analista',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    vehiculo_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True,
        ondelete='cascade', # Opcional: define el comportamiento al borrar la solicitud
        help="El vehículo para el cual se solicita el taller."
    )
    descripcion_falla = fields.Text(
        string='Descripción de la Falla',
        required=True
    )
    telefono_analista = fields.Char(
        related='analista_id.work_phone',
        string='Teléfono del Analista',
        readonly=True
    )
    tecnico_falla = fields.Text(
        string='Tecnico que reporta',
        size=15, # <--- Límite de 10 caracteres
        required=False
    )
    odometro_unidad = fields.Text(
        string='Odometro',
        size=10, # <--- Límite de 10 caracteres
        required=True
    )
    fecha_solicitud = fields.Datetime(
        string='Fecha de Solicitud',
        default=fields.Datetime.now,
        readonly=True
    )
    fecha_asignacion = fields.Datetime(
        string='Fecha de Asignación',
        tracking=True
    )
    fecha_ingreso_taller = fields.Datetime(
        string='Fecha de Ingreso a Taller',
        tracking=True
    )
    fecha_reparacion_terminada = fields.Datetime(
        string='Fecha de Reparación Terminada',
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Abierto'),
        ('assigned', 'Fecha de cita'),
        ('in_workshop', 'Ingreso a Taller'),
        ('repaired', 'Salida de taller'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)

        # Nuevos campos para los testigos del tablero
    check_engine = fields.Boolean(
        string='Check Engine',
        help='Indica si el testigo Check Engine está encendido.'
    )
    nivel_aceite = fields.Boolean(
        string='Testigo Nivel de Aceite',
        help='Indica si el testigo de Nivel de Aceite está encendido.'
    )
    temperatura_auto = fields.Boolean(
        string='Testigo Temperatura Auto',
        help='Indica si el testigo de Temperatura del Auto está encendido.'
    )
    bateria_auto = fields.Boolean(
        string='Testigo Batería del Auto',
        help='Indica si el testigo de Batería del Auto está encendido.'
    )
    sensor_abs = fields.Boolean(
        string='Testigo Sensor ABS',
        help='Indica si el testigo del Sensor ABS está encendido.'
    )
    direccion_volante = fields.Boolean(
        string='Testigo Dirección (volante)',
        help='Indica si el testigo de Dirección (volante) está encendido.'
    )
    frenos = fields.Boolean(
        string='Testigo Frenos',
        help='Indica si el testigo de Frenos está encendido.'
    )

        # NUEVO CAMPO: Distrito del Vehículo
    distrito_vehiculo = fields.Selection(
        related='vehiculo_id.x_studio_distrito_2', # Aquí es donde se relaciona con el campo del vehículo
        string='Distrito del Vehículo',
        readonly=True # Es de solo lectura porque toma el valor del vehículo
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('taller.solicitud') or 'New'

                # Asignar analista por defecto si no está especificado
        if not vals.get('analista_id') and self.env.user.employee_id:
            vals['analista_id'] = self.env.user.employee_id.id
            
        return super().create(vals)

    def action_confirmar(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo puedes asignar fecha a solicitudes en estado Borrador.")
            
            record.state = 'assigned' # Cambiar el estado a 'assigned'

            # --- Lógica para enviar el correo electrónico ---
            try:
                # Buscar la plantilla de correo por su ID externo
                template = self.env.ref('fleet_sol.email_template_solicitud_asignada', raise_if_not_found=False)

                if template:
                    # Enviar el correo usando la plantilla
                    template.send_mail(record.id, force_send=True, raise_exception=True)
                    _logger.info(f"Correo de asignación de fecha enviado para la solicitud {record.name} al analista {record.analista_id.name}.")
                else:
                    _logger.warning("No se encontró la plantilla de correo 'fleet_sol.email_template_solicitud_asignada'. "
                                    "Asegúrate de que el archivo XML de la plantilla esté cargado y el ID sea correcto.")
            except Exception as e:
                _logger.error(f"Error al enviar el correo de asignación de fecha para la solicitud {record.name}: {e}")
                # Opcional: Mostrar un UserError si quieres que el usuario vea el problema en la interfaz
                # raise UserError(_("No se pudo enviar el correo de notificación: %s") % e)

    def action_ingresar_taller(self):
        for record in self:
            if record.state != 'assigned':
                raise UserError("Solo puedes marcar como 'Ingreso a Taller' solicitudes con fecha asignada.")
            record.state = 'in_workshop'
            #record.fecha_ingreso_taller = fields.Datetime.now()

    def action_reparado(self):
        for record in self:
            if record.state != 'in_workshop':
                raise UserError("Solo puedes marcar como 'Reparado' solicitudes que han ingresado al taller.")
            record.state = 'repaired'
            record.fecha_reparacion_terminada = fields.Datetime.now()

    def action_cancelar(self):
        for record in self:
            if record.state == 'cancel':
                raise UserError("La solicitud ya está cancelada.")
            record.state = 'cancel'
