# -*- coding: utf-8 -*-
# fleet_sol/models/taller_solicitud.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class TallerSolicitud(models.Model):
    _name = 'taller.solicitud'
    _description = 'Solicitud de Taller'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos existentes
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
        ondelete='restrict', # Cambiado a 'restrict' para evitar borrado accidental si hay solicitudes
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
    tecnico_falla = fields.Text( # Quitamos 'size' para fields.Text
        string='Tecnico que reporta',
        required=False
    )
    odometro_unidad = fields.Char( # Cambiado a Char, el odómetro suele ser un número pero a veces puede incluir letras
        string='Odometro',
        required=True
    )
    fecha_solicitud = fields.Datetime(
        string='Fecha de Solicitud',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True # Añadido tracking
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

    # Campos para los testigos del tablero
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

# Si fields.Char con related no funciona para Selection/Char
    distrito_vehiculo = fields.Char(
        string='Distrito del Vehículo',
        compute='_compute_distrito_vehiculo',
        store=True # Para poder buscar y filtrar
    )

    # Campo relacionado para ver la etapa actual del vehículo directamente desde la solicitud
    # Esto es ÚTIL para la depuración y visualización en la UI
    vehiculo_stage_id = fields.Many2one(
        related='vehiculo_id.stage_id',
        string='Etapa Actual del Vehículo',
        readonly=True,
        store=True
    )

    @api.depends('vehiculo_id.x_studio_distrito_2')
    def _compute_distrito_vehiculo(self):
        for record in self:
            record.distrito_vehiculo = record.vehiculo_id.x_studio_distrito_2

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('taller.solicitud.sequence') or 'New'

        # Asignar analista por defecto si no está especificado
        if not vals.get('analista_id') and self.env.user.employee_id:
            vals['analista_id'] = self.env.user.employee_id.id
            
        res = super().create(vals)
        
        # Opcional: Si quieres que el vehículo se mueva a una etapa inicial
        # apenas se crea la solicitud, podrías hacerlo aquí, pero la CRON es para 24h.
        # Por ejemplo, moverlo a una etapa "Solicitud Creada" en el Kanban de Flota.
        
        return res

    def action_confirmar(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Solo puedes asignar fecha a solicitudes en estado Borrador."))
            
            record.state = 'assigned'
            # Puedes añadir la fecha de asignación aquí si corresponde
            # record.fecha_asignacion = fields.Datetime.now() # Si se asigna la fecha al confirmar

            # --- Lógica para enviar el correo electrónico ---
            try:
                # Buscar la plantilla de correo por su ID externo
                # Asegúrate de que 'fleet_sol.email_template_solicitud_asignada' exista en algún XML
                template = self.env.ref('fleet_sol.email_template_solicitud_asignada', raise_if_not_found=False)

                if template:
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
                raise UserError(_("Solo puedes marcar como 'Ingreso a Taller' solicitudes con fecha asignada."))
            record.state = 'in_workshop'
            record.fecha_ingreso_taller = fields.Datetime.now() # Actualiza la fecha al ingresar al taller

    def action_reparado(self):
        for record in self:
            if record.state != 'in_workshop':
                raise UserError(_("Solo puedes marcar como 'Salida de taller' solicitudes que han ingresado al taller."))
            record.state = 'repaired'
            record.fecha_reparacion_terminada = fields.Datetime.now()

    def action_cancelar(self):
        for record in self:
            if record.state == 'cancel':
                raise UserError(_("La solicitud ya está cancelada."))
            record.state = 'cancel'
            
    @api.model
    def _run_auto_set_to_workshop(self):
        """
        Método que busca solicitudes de taller que cumplen 24 horas desde su fecha_solicitud
        y actualiza la etapa del vehículo a 'Talleres'.
        """
        _logger.info("Iniciando tarea programada: _run_auto_set_to_workshop")

        # Calcula la fecha límite (hace 24 horas desde ahora)
        limit_date = datetime.now() - timedelta(hours=24)

        # Buscar solicitudes de taller donde:
        # 1. La fecha_solicitud sea anterior o igual a la fecha límite.
        # 2. El vehículo exista y su etapa NO sea ya 'Talleres' (o la etapa de "Ingreso a Taller" del vehículo).
        # 3. La solicitud en sí misma NO esté en estado 'repaired' (Salida de taller) o 'cancel'.
        # 4. Asumiendo que quieres que esto solo ocurra si la solicitud está en 'Abierto' o 'Fecha de cita'
        #    antes de forzar el movimiento a 'Talleres' en el vehículo.
        solicitudes_a_procesar = self.search([
            ('fecha_solicitud', '<=', limit_date),
            ('vehiculo_id', '!=', False), # Asegurarse de que el vehículo esté asignado
            ('vehiculo_id.active', '=', True), # Asegurarse de que el vehículo esté activo
            ('vehiculo_id.stage_id.name', '!=', 'Talleres'), # Reemplaza 'Talleres' por el nombre exacto de tu etapa Kanban
            ('state', 'not in', ['repaired', 'cancel', 'in_workshop']), # No procesar si ya se reparó, canceló o ya está en taller
        ])

        if not solicitudes_a_procesar:
            _logger.info("No se encontraron solicitudes para procesar.")
            return

        # Obtener el ID de la etapa 'Talleres' del modelo fleet.vehicle.stage
        # Asegúrate de que este nombre ('Talleres') coincida exactamente con tu etapa Kanban.
        taller_stage = self.env['fleet.vehicle.stage'].search([('name', '=', 'Talleres')], limit=1)
        if not taller_stage:
            _logger.error("No se encontró la etapa 'Talleres' en el modelo fleet.vehicle.stage. Por favor, asegúrate de crearla.")
            return

        _logger.info(f"Encontradas {len(solicitudes_a_procesar)} solicitudes para mover a la etapa 'Talleres'.")

        for solicitud in solicitudes_a_procesar:
            try:
                # Actualizar la etapa del vehículo
                solicitud.vehiculo_id.write({'stage_id': taller_stage.id})
                _logger.info(f"Vehículo '{solicitud.vehiculo_id.name}' (ID: {solicitud.vehiculo_id.id}) de la Solicitud '{solicitud.name}' (ID: {solicitud.id}) movido a la etapa '{taller_stage.name}'.")

                # Opcional: También puedes cambiar el estado de la solicitud de taller si lo deseas,
                # para que refleje que el vehículo ya fue enviado a taller automáticamente.
                # if solicitud.state != 'in_workshop': # Evitar redundancia si ya se movió manualmente
                #     solicitud.write({'state': 'in_workshop'})
                #     _logger.info(f"Estado de la Solicitud '{solicitud.name}' cambiado a 'Ingreso a Taller'.")

            except Exception as e:
                _logger.error(f"Error al procesar la solicitud {solicitud.name} (ID: {solicitud.id}) para mover el vehículo a taller: {e}")

        _logger.info("Tarea programada _run_auto_set_to_workshop finalizada.")
