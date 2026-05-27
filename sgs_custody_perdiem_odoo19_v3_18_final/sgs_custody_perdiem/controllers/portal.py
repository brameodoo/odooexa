import base64

from odoo import fields, http, _
from odoo.http import request
from werkzeug.exceptions import NotFound


class SgsCustodyPortal(http.Controller):

    def _format_amount(self, amount, currency):
        symbol = currency.symbol or '$'
        formatted_amount = "{:,.2f}".format(amount or 0.0)
        return f"{symbol} {formatted_amount}"

    def _get_custodian(self, token):
        custodian = request.env['sgs.custodian'].sudo().search([('portal_token', '=', token), ('active', '=', True)], limit=1)
        if not custodian:
            raise NotFound()
        return custodian

    @http.route(['/sgs/custodio/<string:token>'], type='http', auth='public', website=True, sitemap=False)
    def custodian_home(self, token, **kw):
        custodian = self._get_custodian(token)
        services = request.env['sgs.route.service'].sudo().search([('custodian_id', '=', custodian.id)], limit=20, order='date desc, id desc')
        deposits = request.env['sgs.perdiem.deposit'].sudo().search([('custodian_id', '=', custodian.id)], limit=10, order='date desc, id desc')
        fiscal = request.env['sgs.fiscal.receipt'].sudo().search([('custodian_id', '=', custodian.id)], limit=10, order='date desc, id desc')
        clients = request.env['sgs.client'].sudo().search([('active', '=', True)], order='name')
        vehicles = request.env['sgs.vehicle'].sudo().search([('active', '=', True)], order='plate')
        return request.render('sgs_custody_perdiem.portal_custodian_home', {
            'custodian': custodian,
            'services': services,
            'deposits': deposits,
            'fiscal_receipts': fiscal,
            'clients': clients,
            'vehicles': vehicles,
            'token': token,
            'format_amount': self._format_amount,
        })

    @http.route(['/sgs/custodio/<string:token>/servicio'], type='http', auth='public', methods=['POST'], website=True, csrf=True, sitemap=False)
    def submit_service(self, token, **post):
        custodian = self._get_custodian(token)
        client = False
        if post.get('client_id'):
            client = request.env['sgs.client'].sudo().browse(int(post['client_id']))
        vehicle = False
        if post.get('vehicle_id'):
            vehicle = request.env['sgs.vehicle'].sudo().browse(int(post['vehicle_id']))
        vals = {
            'custodian_id': custodian.id,
            'date': post.get('date') or fields.Date.today(),
            'client_id': client.id if client and client.exists() else False,
            'origin': post.get('origin'),
            'destination': post.get('destination'),
            'companion': post.get('companion'),
            'vehicle_id': vehicle.id if vehicle and vehicle.exists() else False,
            'comments': post.get('comments'),
            'amount_perdiem': float(post.get('amount_perdiem') or 0),
            'amount_fuel': float(post.get('amount_fuel') or 0),
            'amount_lodging': float(post.get('amount_lodging') or 0),
            'amount_misc': float(post.get('amount_misc') or 0),
            'misc_detail': post.get('misc_detail'),
            'status': 'pending',
        }
        upload = request.httprequest.files.get('evidence')
        if upload and upload.filename:
            vals['evidence_filename'] = upload.filename
            vals['evidence_image'] = base64.b64encode(upload.read())
        service = request.env['sgs.route.service'].sudo().create(vals)
        toll_names = request.httprequest.form.getlist('toll_name[]')
        toll_amounts = request.httprequest.form.getlist('toll_amount[]')
        toll_files = request.httprequest.files.getlist('toll_image[]')
        for idx, name in enumerate(toll_names):
            amount = float(toll_amounts[idx] or 0) if idx < len(toll_amounts) else 0
            if not name and not amount:
                continue
            line_vals = {'service_id': service.id, 'name': name or 'Caseta', 'amount': amount}
            if idx < len(toll_files) and toll_files[idx] and toll_files[idx].filename:
                line_vals['image_filename'] = toll_files[idx].filename
                line_vals['image'] = base64.b64encode(toll_files[idx].read())
            request.env['sgs.toll.line'].sudo().create(line_vals)
        return request.redirect('/sgs/custodio/%s?ok=servicio' % token)

    @http.route(['/sgs/custodio/<string:token>/fiscal'], type='http', auth='public', methods=['POST'], website=True, csrf=True, sitemap=False)
    def submit_fiscal(self, token, **post):
        custodian = self._get_custodian(token)
        # Si se sube una imagen, priorizamos el OCR
        upload = request.httprequest.files.get('image')
        
        vals = {
            'custodian_id': custodian.id,
            'date': post.get('date') or fields.Date.today(),
            'amount': float(post.get('amount') or 0),
            'description': post.get('description') or _('Comprobante fiscal'),
            'provider': post.get('provider'),
            'provider_vat': (post.get('provider_vat') or '').upper(),
        }
        
        if upload and upload.filename:
            vals['image_filename'] = upload.filename
            vals['image'] = base64.b64encode(upload.read())
            # Marcamos para procesamiento OCR
            vals['ocr_status'] = 'pending'
        
        receipt = request.env['sgs.fiscal.receipt'].sudo().create(vals)
        
        # Si hay imagen, disparamos el OCR de forma síncrona para esta versión
        # (En producción se recomienda asíncrono)
        if receipt.image:
            receipt.action_process_ocr()
            
        return request.redirect('/sgs/custodio/%s?ok=fiscal' % token)
