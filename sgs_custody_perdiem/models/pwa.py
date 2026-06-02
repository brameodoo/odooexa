# -*- coding: utf-8 -*-
"""Modelos para gestionar suscripciones y logs de notificaciones push PWA."""

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SGSPushSubscription(models.Model):
    """Almacena suscripciones a notificaciones push del portal SGS."""

    _name = 'sgs.push.subscription'
    _description = 'Suscripción a Notificaciones Push'
    _order = 'create_date desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade',
        index=True,
    )
    endpoint = fields.Char(
        'Endpoint',
        required=True,
        help='URL del endpoint de push notification',
    )
    auth = fields.Char(
        'Auth Key',
        required=True,
        help='Clave de autenticación para push notification',
    )
    p256dh = fields.Char(
        'P256DH Key',
        required=True,
        help='Clave pública para encriptación',
    )
    user_agent = fields.Char(
        'User Agent',
        help='User Agent del dispositivo que se suscribió',
    )
    device_type = fields.Selection(
        [
            ('mobile', 'Móvil'),
            ('tablet', 'Tablet'),
            ('desktop', 'Escritorio'),
            ('unknown', 'Desconocido'),
        ],
        string='Tipo de Dispositivo',
        compute='_compute_device_type',
        store=True,
    )
    is_active = fields.Boolean(
        'Activo',
        default=True,
        index=True,
        help='Indica si la suscripción está activa',
    )
    last_notification = fields.Datetime(
        'Última Notificación',
        help='Fecha de la última notificación enviada',
    )
    failed_attempts = fields.Integer(
        'Intentos Fallidos',
        default=0,
        help='Número de intentos fallidos de envío',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True,
    )

    _sql_constraints = [
        ('endpoint_unique', 'unique(endpoint)', 'El endpoint ya existe'),
    ]

    @api.depends('user_agent')
    def _compute_device_type(self):
        """Detecta el tipo de dispositivo basado en el User Agent."""
        for record in self:
            ua = (record.user_agent or '').lower()
            if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
                record.device_type = 'mobile'
            elif 'tablet' in ua or 'ipad' in ua:
                record.device_type = 'tablet'
            elif 'windows' in ua or 'macintosh' in ua or 'linux' in ua:
                record.device_type = 'desktop'
            else:
                record.device_type = 'unknown'

    @api.constrains('auth', 'p256dh')
    def _check_keys(self):
        """Valida que las claves mínimas de encriptación estén presentes."""
        for record in self:
            if not record.auth or len(record.auth) < 20:
                raise ValidationError(_('La clave de autenticación no es válida'))
            if not record.p256dh or len(record.p256dh) < 20:
                raise ValidationError(_('La clave P256DH no es válida'))

    def mark_failed(self):
        """Marca un intento fallido y desactiva la suscripción tras varios errores."""
        for record in self:
            record.failed_attempts += 1
            if record.failed_attempts >= 5:
                record.is_active = False

    def mark_success(self):
        """Marca un envío exitoso."""
        for record in self:
            record.last_notification = fields.Datetime.now()
            record.failed_attempts = 0

    @api.model
    def cleanup_inactive(self):
        """Limpia suscripciones inactivas antiguas."""
        cutoff_date = fields.Datetime.now() - timedelta(days=30)
        inactive_subs = self.search([
            ('is_active', '=', False),
            ('last_notification', '<', cutoff_date),
        ])
        inactive_subs.unlink()


class SGSPushNotificationLog(models.Model):
    """Registra el historial de notificaciones push enviadas."""

    _name = 'sgs.push.notification.log'
    _description = 'Log de Notificaciones Push'
    _order = 'create_date desc'

    subscription_id = fields.Many2one(
        'sgs.push.subscription',
        string='Suscripción',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        related='subscription_id.employee_id',
        store=True,
    )
    title = fields.Char('Título', required=True)
    body = fields.Text('Cuerpo')
    action = fields.Char('Acción')
    status = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('sent', 'Enviada'),
            ('failed', 'Fallida'),
            ('expired', 'Expirada'),
        ],
        string='Estado',
        default='pending',
        index=True,
    )
    error_message = fields.Text('Mensaje de Error')
    sent_date = fields.Datetime('Fecha de Envío')
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True,
    )

    def mark_sent(self):
        """Marca la notificación como enviada."""
        for record in self:
            record.status = 'sent'
            record.sent_date = fields.Datetime.now()

    def mark_failed(self, error_message):
        """Marca la notificación como fallida."""
        for record in self:
            record.status = 'failed'
            record.error_message = error_message
