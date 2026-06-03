# -*- coding: utf-8 -*-
"""PWA JSON endpoints for the SGS custody portal."""

import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SGSCustodyPWAController(http.Controller):
    """PWA helpers for push subscriptions, sync and offline data."""

    def _json_payload(self):
        return getattr(request, 'jsonrequest', None) or {}

    def _employee_from_user(self):
        return request.env['hr.employee'].search([
            ('user_id', '=', request.env.user.id),
        ], limit=1)

    def _employee_from_token(self, token):
        return request.env['hr.employee'].sudo().search([
            ('portal_token', '=', token),
            ('active', '=', True),
        ], limit=1)

    def _serialize_service(self, service):
        return {
            'id': service.id,
            'name': service.name,
            'date': service.date.isoformat() if service.date else False,
            'status': service.status,
            'amount': service.amount_total,
            'client': service.client_id.name if service.client_id else '',
        }

    def _serialize_receipt(self, receipt):
        return {
            'id': receipt.id,
            'name': receipt.name,
            'date': receipt.date.isoformat() if receipt.date else False,
            'amount': receipt.amount,
            'description': receipt.description,
            'ocr_status': receipt.ocr_status,
        }

    @http.route('/sgs/custodio/push-subscribe', type='json', auth='user', methods=['POST'])
    def push_subscribe(self, **kwargs):
        employee = self._employee_from_user()
        if not employee:
            return {'status': 'error', 'message': 'No se encontró registro de empleado'}
        return self._create_push_subscription(employee, self._json_payload())

    @http.route('/sgs/custodio/<string:token>/push-subscribe', type='json', auth='public', methods=['POST'])
    def public_push_subscribe(self, token, **kwargs):
        employee = self._employee_from_token(token)
        if not employee:
            return {'status': 'error', 'message': 'Token inválido'}
        return self._create_push_subscription(employee, self._json_payload())

    def _create_push_subscription(self, employee, subscription):
        endpoint = subscription.get('endpoint')
        keys = subscription.get('keys', {})
        if not endpoint or not keys.get('auth') or not keys.get('p256dh'):
            return {'status': 'error', 'message': 'Suscripción incompleta'}

        values = {
            'employee_id': employee.id,
            'endpoint': endpoint,
            'auth': keys.get('auth'),
            'p256dh': keys.get('p256dh'),
            'user_agent': request.httprequest.headers.get('User-Agent', ''),
        }
        subscription_record = request.env['sgs.push.subscription'].sudo().search([
            ('endpoint', '=', endpoint),
        ], limit=1)
        if subscription_record:
            subscription_record.write(dict(values, is_active=True, failed_attempts=0))
        else:
            subscription_record = request.env['sgs.push.subscription'].sudo().create(values)

        _logger.info('Push subscription registrada para %s', employee.name)
        return {
            'status': 'success',
            'subscription_id': subscription_record.id,
            'message': 'Suscripción registrada correctamente',
        }

    @http.route('/sgs/custodio/sync', type='json', auth='user', methods=['POST'])
    def sync_pending_data(self, **kwargs):
        employee = self._employee_from_user()
        if not employee:
            return {'status': 'error', 'message': 'No se encontró registro de empleado'}
        return self._sync_payload(employee)

    @http.route('/sgs/custodio/<string:token>/sync', type='json', auth='public', methods=['POST'])
    def public_sync_pending_data(self, token, **kwargs):
        employee = self._employee_from_token(token)
        if not employee:
            return {'status': 'error', 'message': 'Token inválido'}
        return self._sync_payload(employee)

    def _sync_payload(self, employee):
        pending_services = request.env['sgs.route.service'].sudo().search_count([
            ('custodian_id', '=', employee.id),
            ('status', '=', 'pending'),
        ])
        pending_receipts = request.env['sgs.fiscal.receipt'].sudo().search_count([
            ('custodian_id', '=', employee.id),
            ('ocr_status', 'in', ['pending', 'processing']),
        ])
        _logger.info('Sincronización de datos para %s', employee.name)
        return {
            'status': 'success',
            'pending_services': pending_services,
            'pending_receipts': pending_receipts,
            'message': 'Datos sincronizados correctamente',
        }

    @http.route('/sgs/custodio/send-notification', type='json', auth='user', methods=['POST'])
    def send_notification(self, **kwargs):
        if not request.env.user.has_group('base.group_system'):
            return {'status': 'error', 'message': 'No tienes permisos para enviar notificaciones'}

        data = self._json_payload()
        employee_id = data.get('employee_id')
        title = data.get('title')
        body = data.get('body')
        action = data.get('action', 'open')
        employee = request.env['hr.employee'].sudo().browse(employee_id)
        if not employee.exists():
            return {'status': 'error', 'message': 'Empleado no encontrado'}

        subscriptions = request.env['sgs.push.subscription'].sudo().search([
            ('employee_id', '=', employee.id),
            ('is_active', '=', True),
        ])
        if not subscriptions:
            return {'status': 'warning', 'message': 'El empleado no tiene suscripciones activas'}

        for subscription in subscriptions:
            request.env['sgs.push.notification.log'].sudo().create({
                'subscription_id': subscription.id,
                'title': title,
                'body': body,
                'action': action,
                'status': 'pending',
            })

        _logger.info('Notificación registrada para %s suscripciones de %s', len(subscriptions), employee.name)
        return {
            'status': 'success',
            'sent_to': len(subscriptions),
            'message': 'Notificación registrada correctamente',
        }

    @http.route('/sgs/custodio/app-info', type='json', auth='user')
    def get_app_info(self, **kwargs):
        employee = self._employee_from_user()
        if not employee:
            return {'status': 'error', 'message': 'No se encontró registro de empleado'}
        return self._app_info_payload(employee)

    @http.route('/sgs/custodio/<string:token>/app-info', type='json', auth='public')
    def public_get_app_info(self, token, **kwargs):
        employee = self._employee_from_token(token)
        if not employee:
            return {'status': 'error', 'message': 'Token inválido'}
        return self._app_info_payload(employee)

    def _app_info_payload(self, employee):
        total_services = request.env['sgs.route.service'].sudo().search_count([
            ('custodian_id', '=', employee.id),
        ])
        pending_services = request.env['sgs.route.service'].sudo().search_count([
            ('custodian_id', '=', employee.id),
            ('status', '=', 'pending'),
        ])
        return {
            'status': 'success',
            'app_version': '4.0',
            'app_name': 'SGS Viáticos',
            'employee_name': employee.name,
            'employee_id': employee.id,
            'total_services': total_services,
            'pending_services': pending_services,
            'total_balance': employee.balance,
            'currency': employee.company_id.currency_id.symbol,
            'last_updated': fields.Datetime.now().isoformat(),
        }

    @http.route('/sgs/custodio/offline-data', type='json', auth='user')
    def get_offline_data(self, **kwargs):
        employee = self._employee_from_user()
        if not employee:
            return {'status': 'error', 'message': 'No se encontró registro de empleado'}
        return self._offline_data_payload(employee)

    @http.route('/sgs/custodio/<string:token>/offline-data', type='json', auth='public')
    def public_get_offline_data(self, token, **kwargs):
        employee = self._employee_from_token(token)
        if not employee:
            return {'status': 'error', 'message': 'Token inválido'}
        return self._offline_data_payload(employee)

    def _offline_data_payload(self, employee):
        services = request.env['sgs.route.service'].sudo().search([
            ('custodian_id', '=', employee.id),
        ], limit=50, order='date desc')
        receipts = request.env['sgs.fiscal.receipt'].sudo().search([
            ('custodian_id', '=', employee.id),
        ], limit=20, order='date desc')
        return {
            'status': 'success',
            'employee': {
                'id': employee.id,
                'name': employee.name,
                'balance': employee.balance,
                'currency': employee.company_id.currency_id.symbol,
            },
            'services': [self._serialize_service(service) for service in services],
            'receipts': [self._serialize_receipt(receipt) for receipt in receipts],
            'timestamp': fields.Datetime.now().isoformat(),
        }
