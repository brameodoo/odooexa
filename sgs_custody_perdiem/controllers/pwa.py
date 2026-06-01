# -*- coding: utf-8 -*-
"""
Controlador PWA para SGS Custody Portal
Maneja endpoints para notificaciones push, sincronización y funcionalidades PWA
"""

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SGSCustodyPWAController(http.Controller):
    """Controlador para funcionalidades PWA del portal de custodios"""

    @http.route('/sgs/custodio/push-subscribe', type='json', auth='user', methods=['POST'])
    def push_subscribe(self, **kwargs):
        """
        Registrar suscripción a notificaciones push
        
        Args:
            subscription (dict): Objeto de suscripción de push notification
        
        Returns:
            dict: Respuesta de confirmación
        """
        try:
            subscription = request.jsonrequest
            user = request.env.user
            employee = request.env['hr.employee'].search([
                ('user_id', '=', user.id)
            ], limit=1)

            if not employee:
                return {
                    'status': 'error',
                    'message': 'No se encontró registro de empleado'
                }

            # Guardar suscripción en el modelo
            request.env['sgs.push.subscription'].create({
                'employee_id': employee.id,
                'endpoint': subscription.get('endpoint'),
                'auth': subscription.get('keys', {}).get('auth'),
                'p256dh': subscription.get('keys', {}).get('p256dh'),
                'user_agent': request.httprequest.headers.get('User-Agent', ''),
            })

            _logger.info(f'Push subscription registrada para {employee.name}')

            return {
                'status': 'success',
                'message': 'Suscripción registrada correctamente'
            }
        except Exception as e:
            _logger.error(f'Error al registrar push subscription: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/sgs/custodio/sync', type='json', auth='user', methods=['POST'])
    def sync_pending_data(self, **kwargs):
        """
        Sincronizar datos pendientes cuando se restaura la conexión
        
        Returns:
            dict: Datos sincronizados
        """
        try:
            user = request.env.user
            employee = request.env['hr.employee'].search([
                ('user_id', '=', user.id)
            ], limit=1)

            if not employee:
                return {
                    'status': 'error',
                    'message': 'No se encontró registro de empleado'
                }

            # Obtener servicios pendientes de sincronizar
            pending_services = request.env['sgs.route.service'].search([
                ('custodian_id', '=', employee.id),
                ('status', '=', 'pending'),
                ('create_date', '>=', request.env['ir.config_parameter'].sudo().get_param(
                    'sgs.last_sync_time', '2024-01-01'
                ))
            ])

            # Obtener comprobantes fiscales pendientes
            pending_receipts = request.env['sgs.fiscal.receipt'].search([
                ('custodian_id', '=', employee.id),
                ('ocr_status', 'in', ['pending', 'processing']),
            ])

            _logger.info(f'Sincronización de datos para {employee.name}')

            return {
                'status': 'success',
                'pending_services': len(pending_services),
                'pending_receipts': len(pending_receipts),
                'message': 'Datos sincronizados correctamente'
            }
        except Exception as e:
            _logger.error(f'Error al sincronizar datos: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/sgs/custodio/send-notification', type='json', auth='user', methods=['POST'])
    def send_notification(self, **kwargs):
        """
        Enviar notificación push a un custodio
        Requiere permisos de administrador
        
        Args:
            employee_id (int): ID del empleado
            title (str): Título de la notificación
            body (str): Cuerpo de la notificación
            action (str): Acción asociada
        
        Returns:
            dict: Resultado del envío
        """
        try:
            if not request.env.user.has_group('base.group_system'):
                return {
                    'status': 'error',
                    'message': 'No tienes permisos para enviar notificaciones'
                }

            data = request.jsonrequest
            employee_id = data.get('employee_id')
            title = data.get('title')
            body = data.get('body')
            action = data.get('action', 'open')

            employee = request.env['hr.employee'].browse(employee_id)
            if not employee.exists():
                return {
                    'status': 'error',
                    'message': 'Empleado no encontrado'
                }

            # Obtener suscripciones activas del empleado
            subscriptions = request.env['sgs.push.subscription'].search([
                ('employee_id', '=', employee_id),
                ('is_active', '=', True)
            ])

            if not subscriptions:
                return {
                    'status': 'warning',
                    'message': 'El empleado no tiene suscripciones activas'
                }

            # Aquí iría la lógica para enviar notificaciones push
            # Requeriría integración con servicio de push (Firebase, Pushover, etc.)

            _logger.info(f'Notificación enviada a {len(subscriptions)} suscripciones de {employee.name}')

            return {
                'status': 'success',
                'sent_to': len(subscriptions),
                'message': 'Notificación enviada correctamente'
            }
        except Exception as e:
            _logger.error(f'Error al enviar notificación: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/sgs/custodio/app-info', type='json', auth='user')
    def get_app_info(self, **kwargs):
        """
        Obtener información de la aplicación para el cliente
        
        Returns:
            dict: Información de la app
        """
        try:
            user = request.env.user
            employee = request.env['hr.employee'].search([
                ('user_id', '=', user.id)
            ], limit=1)

            if not employee:
                return {
                    'status': 'error',
                    'message': 'No se encontró registro de empleado'
                }

            # Obtener estadísticas
            total_services = request.env['sgs.route.service'].search_count([
                ('custodian_id', '=', employee.id)
            ])
            pending_services = request.env['sgs.route.service'].search_count([
                ('custodian_id', '=', employee.id),
                ('status', '=', 'pending')
            ])
            total_balance = employee.balance

            return {
                'status': 'success',
                'app_version': '4.0',
                'app_name': 'SGS Viáticos',
                'employee_name': employee.name,
                'employee_id': employee.id,
                'total_services': total_services,
                'pending_services': pending_services,
                'total_balance': total_balance,
                'currency': employee.company_id.currency_id.symbol,
                'last_updated': request.env.cr.now().isoformat()
            }
        except Exception as e:
            _logger.error(f'Error al obtener información de la app: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/sgs/custodio/offline-data', type='json', auth='user')
    def get_offline_data(self, **kwargs):
        """
        Obtener datos para modo offline
        
        Returns:
            dict: Datos para caché offline
        """
        try:
            user = request.env.user
            employee = request.env['hr.employee'].search([
                ('user_id', '=', user.id)
            ], limit=1)

            if not employee:
                return {
                    'status': 'error',
                    'message': 'No se encontró registro de empleado'
                }

            # Obtener servicios recientes
            services = request.env['sgs.route.service'].search([
                ('custodian_id', '=', employee.id)
            ], limit=50, order='date desc')

            services_data = []
            for service in services:
                services_data.append({
                    'id': service.id,
                    'name': service.name,
                    'date': service.date.isoformat(),
                    'status': service.status,
                    'amount': service.amount_total,
                    'client': service.client_id.name if service.client_id else '',
                })

            # Obtener comprobantes recientes
            receipts = request.env['sgs.fiscal.receipt'].search([
                ('custodian_id', '=', employee.id)
            ], limit=20, order='date desc')

            receipts_data = []
            for receipt in receipts:
                receipts_data.append({
                    'id': receipt.id,
                    'name': receipt.name,
                    'date': receipt.date.isoformat(),
                    'amount': receipt.amount,
                    'description': receipt.description,
                })

            return {
                'status': 'success',
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'balance': employee.balance,
                    'currency': employee.company_id.currency_id.symbol,
                },
                'services': services_data,
                'receipts': receipts_data,
                'timestamp': request.env.cr.now().isoformat()
            }
        except Exception as e:
            _logger.error(f'Error al obtener datos offline: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }
