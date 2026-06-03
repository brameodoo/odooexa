# -*- coding: utf-8 -*-
import base64
import logging

from odoo import fields, http, _
from odoo.http import request
from werkzeug.exceptions import BadRequest, NotFound

_logger = logging.getLogger(__name__)


class SgsCustodyPortal(http.Controller):
    """Public token portal for custodians to report services and receipts."""

    def _format_amount(self, amount, currency):
        symbol = currency.symbol or '$'
        formatted_amount = '{:,.2f}'.format(amount or 0.0)
        return f'{symbol} {formatted_amount}'

    def _get_custodian(self, token):
        custodian = request.env['hr.employee'].sudo().search([
            ('portal_token', '=', token),
            ('active', '=', True),
        ], limit=1)
        if not custodian:
            raise NotFound()
        return custodian

    def _to_float(self, value):
        if not value:
            return 0.0
        normalized = str(value).replace(',', '').strip()
        try:
            return float(normalized)
        except ValueError as exc:
            raise BadRequest(_('Importe inválido: %s') % value) from exc

    def _to_int_or_false(self, value):
        if not value:
            return False
        try:
            return int(value)
        except ValueError as exc:
            raise BadRequest(_('Identificador inválido: %s') % value) from exc

    def _encode_upload(self, upload):
        if upload and upload.filename:
            return upload.filename, base64.b64encode(upload.read())
        return False, False

    @http.route(['/sgs/custodio/<string:token>'], type='http', auth='public', website=True, sitemap=False)
    def custodian_home(self, token, **kw):
        custodian = self._get_custodian(token)
        services = request.env['sgs.route.service'].sudo().search([
            ('custodian_id', '=', custodian.id),
        ], limit=20, order='date desc, id desc')
        deposits = request.env['sgs.perdiem.deposit'].sudo().search([
            ('custodian_id', '=', custodian.id),
        ], limit=10, order='date desc, id desc')
        fiscal = request.env['sgs.fiscal.receipt'].sudo().search([
            ('custodian_id', '=', custodian.id),
        ], limit=10, order='date desc, id desc')
        clients = request.env['sgs.client'].sudo().search([('active', '=', True)], order='name')
        vehicles = request.env['fleet.vehicle'].sudo().search([], order='name')
        employees = request.env['hr.employee'].sudo().search([
            ('active', '=', True),
            ('id', '!=', custodian.id),
        ], order='name')
        return request.render('sgs_custody_perdiem.portal_custodian_home', {
            'custodian': custodian,
            'services': services,
            'deposits': deposits,
            'fiscal_receipts': fiscal,
            'clients': clients,
            'vehicles': vehicles,
            'employees': employees,
            'token': token,
            'ok': kw.get('ok'),
            'format_amount': self._format_amount,
        })

    @http.route(
        ['/sgs/custodio/<string:token>/servicio'],
        type='http',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=True,
        sitemap=False,
    )
    def submit_service(self, token, **post):
        custodian = self._get_custodian(token)
        client_id = self._to_int_or_false(post.get('client_id'))
        vehicle_id = self._to_int_or_false(post.get('vehicle_id'))
        companion_id = self._to_int_or_false(post.get('companion_id'))

        vals = {
            'custodian_id': custodian.id,
            'date': post.get('date') or fields.Date.today(),
            'client_id': client_id,
            'origin': post.get('origin'),
            'destination': post.get('destination'),
            'companion_id': companion_id,
            'vehicle_id': vehicle_id,
            'comments': post.get('comments'),
            'amount_perdiem': self._to_float(post.get('amount_perdiem')),
            'amount_fuel': self._to_float(post.get('amount_fuel')),
            'amount_lodging': self._to_float(post.get('amount_lodging')),
            'amount_misc': self._to_float(post.get('amount_misc')),
            'misc_detail': post.get('misc_detail'),
            'status': 'pending',
        }

        upload = request.httprequest.files.get('evidence')
        filename, content = self._encode_upload(upload)
        if content:
            vals['evidence_filename'] = filename
            vals['evidence_image'] = content

        service = request.env['sgs.route.service'].sudo().create(vals)
        toll_names = request.httprequest.form.getlist('toll_name[]')
        toll_amounts = request.httprequest.form.getlist('toll_amount[]')
        toll_files = request.httprequest.files.getlist('toll_image[]')

        for idx, name in enumerate(toll_names):
            amount = self._to_float(toll_amounts[idx]) if idx < len(toll_amounts) else 0.0
            if not name and not amount:
                continue
            line_vals = {
                'service_id': service.id,
                'name': name or _('Caseta'),
                'amount': amount,
            }
            if idx < len(toll_files):
                toll_filename, toll_content = self._encode_upload(toll_files[idx])
                if toll_content:
                    line_vals['image_filename'] = toll_filename
                    line_vals['image'] = toll_content
            request.env['sgs.toll.line'].sudo().create(line_vals)

        return request.redirect('/sgs/custodio/%s?ok=servicio' % token)

    @http.route(
        ['/sgs/custodio/<string:token>/fiscal'],
        type='http',
        auth='public',
        methods=['POST'],
        website=True,
        csrf=True,
        sitemap=False,
    )
    def submit_fiscal(self, token, **post):
        custodian = self._get_custodian(token)
        vals = {
            'custodian_id': custodian.id,
            'date': post.get('date') or fields.Date.today(),
            'amount': self._to_float(post.get('amount')),
            'description': post.get('description') or _('Comprobante fiscal'),
            'provider': post.get('provider'),
            'provider_vat': (post.get('provider_vat') or '').upper(),
        }

        upload = request.httprequest.files.get('image')
        filename, content = self._encode_upload(upload)
        if content:
            vals.update({
                'image_filename': filename,
                'image': content,
                'ocr_status': 'pending',
            })

        receipt = request.env['sgs.fiscal.receipt'].sudo().create(vals)
        if receipt.image:
            receipt.action_process_ocr()

        return request.redirect('/sgs/custodio/%s?ok=fiscal' % token)
