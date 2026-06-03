# -*- coding: utf-8 -*-
import base64
import importlib.util
import secrets
from datetime import datetime, timedelta, time
from io import BytesIO
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SgsCustodian(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Char('Número de empleado', tracking=True)
    position = fields.Char('Puesto')
    phone = fields.Char('Teléfono')
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )
    initial_fund = fields.Monetary(
        'Fondo inicial',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    portal_token = fields.Char(
        'Token portal',
        copy=False,
        index=True,
        readonly=True,
        default=lambda self: secrets.token_urlsafe(24),
    )
    portal_url = fields.Char('Enlace portal', compute='_compute_portal_url')
    whatsapp_url = fields.Char('Enlace WhatsApp', compute='_compute_portal_url')
    portal_qr_code = fields.Binary('Código QR Portal', compute='_compute_portal_qr_code')

    deposit_ids = fields.One2many('sgs.perdiem.deposit', 'custodian_id', string='Depósitos')
    service_ids = fields.One2many('sgs.route.service', 'custodian_id', string='Servicios')
    fiscal_receipt_ids = fields.One2many(
        'sgs.fiscal.receipt',
        'custodian_id',
        string='Comprobantes fiscales',
    )

    total_deposits = fields.Monetary(
        'Total depositado',
        compute='_compute_amounts',
        currency_field='currency_id',
    )
    total_expenses = fields.Monetary(
        'Total gastos',
        compute='_compute_amounts',
        currency_field='currency_id',
    )
    total_fiscal = fields.Monetary(
        'Total fiscal comprobado',
        compute='_compute_amounts',
        currency_field='currency_id',
    )
    balance = fields.Monetary('Saldo', compute='_compute_amounts', currency_field='currency_id')

    pending_service_count = fields.Integer('Servicios pendientes', compute='_compute_amounts')
    late_service_count = fields.Integer('Servicios fuera de 12h', compute='_compute_amounts')

    compliance_state = fields.Selection(
        [
            ('blue', 'Sin gastos'),
            ('green', 'Al día'),
            ('yellow', 'Pendiente'),
            ('red', 'Atrasado / Rechazado'),
        ],
        string='Semáforo',
        compute='_compute_amounts',
    )

    @api.depends('portal_token', 'mobile_phone', 'phone', 'name')
    def _compute_portal_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.portal_url = f'{base}/sgs/custodio/{rec.portal_token}' if rec.portal_token else ''
            phone = ''.join(ch for ch in (rec.mobile_phone or rec.phone or '') if ch.isdigit())
            if phone and rec.portal_url:
                if len(phone) == 10:
                    phone = '52' + phone
                first_name = rec.name.split()[0] if rec.name else ''
                msg = _('Hola %(name)s, este es tu enlace de viáticos SGS: %(url)s') % {
                    'name': first_name,
                    'url': rec.portal_url,
                }
                rec.whatsapp_url = 'https://wa.me/%s?text=%s' % (phone, quote(msg))
            else:
                rec.whatsapp_url = ''

    @api.depends('portal_url')
    def _compute_portal_qr_code(self):
        qrcode_available = bool(importlib.util.find_spec('qrcode'))
        if qrcode_available:
            import qrcode

        for rec in self:
            if qrcode_available and rec.portal_url:
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(rec.portal_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color='black', back_color='white')
                temp = BytesIO()
                img.save(temp, format='PNG')
                rec.portal_qr_code = base64.b64encode(temp.getvalue())
            else:
                rec.portal_qr_code = False

    @api.depends(
        'initial_fund',
        'deposit_ids.amount',
        'service_ids.amount_total',
        'service_ids.status',
        'service_ids.is_late',
        'fiscal_receipt_ids.amount',
    )
    def _compute_amounts(self):
        for rec in self:
            deposits = sum(rec.deposit_ids.mapped('amount'))
            valid_services = rec.service_ids.filtered(lambda service: service.status != 'rejected')
            expenses = sum(valid_services.mapped('amount_total'))
            fiscal = sum(rec.fiscal_receipt_ids.mapped('amount'))
            rec.total_deposits = deposits
            rec.total_expenses = expenses
            rec.total_fiscal = fiscal
            rec.balance = rec.initial_fund + deposits - expenses
            rec.pending_service_count = len(rec.service_ids.filtered(lambda service: service.status == 'pending'))
            rec.late_service_count = len(
                rec.service_ids.filtered(lambda service: service.is_late and service.status != 'approved')
            )
            if not rec.service_ids:
                rec.compliance_state = 'blue'
            elif rec.late_service_count:
                rec.compliance_state = 'red'
            elif rec.pending_service_count:
                rec.compliance_state = 'yellow'
            else:
                rec.compliance_state = 'green'

    def action_regenerate_portal_token(self):
        for rec in self:
            rec.portal_token = secrets.token_urlsafe(24)
        return True

    def action_open_portal(self):
        self.ensure_one()
        if not self.portal_token:
            self.portal_token = secrets.token_urlsafe(24)
        return {
            'type': 'ir.actions.act_url',
            'url': self.portal_url,
            'target': 'new',
        }


class SgsFleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    sgs_custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodio SGS',
        tracking=True,
        help='Custodio responsable del vehículo para la operación SGS.',
    )


class SgsClient(models.Model):
    _name = 'sgs.client'
    _description = 'Cliente SGS'
    _order = 'name'

    name = fields.Char('Nombre', required=True)
    active = fields.Boolean('Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        required=True,
    )


class SgsPerdiemDeposit(models.Model):
    _name = 'sgs.perdiem.deposit'
    _description = 'Depósito de viáticos SGS'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Referencia', compute='_compute_name', store=True)
    custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodio',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    company_id = fields.Many2one(related='custodian_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='custodian_id.currency_id', readonly=True)
    date = fields.Date('Fecha de depósito', required=True, default=fields.Date.context_today, tracking=True)
    month = fields.Char('Mes', compute='_compute_month', store=True)
    week = fields.Char('Semana / período')
    concept = fields.Char('Concepto', default='Depósito semanal viáticos')
    amount = fields.Monetary('Monto', currency_field='currency_id', required=True, tracking=True)

    @api.depends('custodian_id', 'date', 'amount')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s · %s · $%0.2f' % (
                rec.custodian_id.name or 'Custodio',
                rec.date or '',
                rec.amount or 0.0,
            )

    @api.depends('date')
    def _compute_month(self):
        months = [
            'ENERO',
            'FEBRERO',
            'MARZO',
            'ABRIL',
            'MAYO',
            'JUNIO',
            'JULIO',
            'AGOSTO',
            'SEPTIEMBRE',
            'OCTUBRE',
            'NOVIEMBRE',
            'DICIEMBRE',
        ]
        for rec in self:
            rec.month = months[rec.date.month - 1] if rec.date else ''

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El monto del depósito debe ser mayor a cero.'))


class SgsRouteService(models.Model):
    _name = 'sgs.route.service'
    _description = 'Servicio de custodia y gasto SGS'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Folio', default='Nuevo', copy=False, readonly=True, tracking=True)
    custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodio',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    company_id = fields.Many2one(related='custodian_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='custodian_id.currency_id', readonly=True)
    date = fields.Date('Fecha del servicio', required=True, default=fields.Date.context_today, tracking=True)
    submit_datetime = fields.Datetime('Fecha/hora de captura', default=fields.Datetime.now, readonly=True)
    client_id = fields.Many2one('sgs.client', string='Cliente')
    origin = fields.Char('Origen')
    destination = fields.Char('Destino')
    companion_id = fields.Many2one('hr.employee', string='Compañero / segundo custodio')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo', tracking=True)
    vehicle_snapshot = fields.Char('Vehículo usado')
    plate_snapshot = fields.Char('Placas')
    comments = fields.Text('Comentarios / aclaraciones')
    amount_perdiem = fields.Monetary('Viáticos', currency_field='currency_id', default=0.0)
    amount_fuel = fields.Monetary('Gasolina', currency_field='currency_id', default=0.0)
    amount_lodging = fields.Monetary('Hospedaje', currency_field='currency_id', default=0.0)
    amount_misc = fields.Monetary('Gastos varios', currency_field='currency_id', default=0.0)
    misc_detail = fields.Char('Especificación gastos varios')
    toll_line_ids = fields.One2many('sgs.toll.line', 'service_id', string='Casetas')
    amount_tolls = fields.Monetary('Casetas', compute='_compute_total', currency_field='currency_id', store=True)
    amount_total = fields.Monetary('Total servicio', compute='_compute_total', currency_field='currency_id', store=True)
    evidence_image = fields.Binary('Evidencia general')
    evidence_filename = fields.Char('Nombre archivo evidencia')
    status = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('approved', 'Autorizado'),
            ('rejected', 'Rechazado'),
        ],
        default='pending',
        required=True,
        tracking=True,
    )
    validation_note = fields.Text('Observación de validación')
    is_late = fields.Boolean('Fuera de 12h', compute='_compute_is_late', store=True)

    @api.depends('amount_perdiem', 'amount_fuel', 'amount_lodging', 'amount_misc', 'toll_line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.amount_tolls = sum(rec.toll_line_ids.mapped('amount'))
            rec.amount_total = (
                rec.amount_perdiem
                + rec.amount_fuel
                + rec.amount_lodging
                + rec.amount_misc
                + rec.amount_tolls
            )

    @api.depends('date', 'submit_datetime')
    def _compute_is_late(self):
        for rec in self:
            if rec.date and rec.submit_datetime:
                deadline = datetime.combine(rec.date, time.min) + timedelta(hours=36)
                rec.is_late = rec.submit_datetime > deadline
            else:
                rec.is_late = False

    def _get_vehicle_snapshot_values(self, vehicle):
        return {
            'vehicle_snapshot': vehicle.display_name if vehicle else False,
            'plate_snapshot': vehicle.license_plate if vehicle else False,
        }

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            rec.update(rec._get_vehicle_snapshot_values(rec.vehicle_id))

    @api.constrains('amount_misc', 'misc_detail')
    def _check_amounts(self):
        for rec in self:
            if rec.amount_misc > 0 and not rec.misc_detail:
                raise ValidationError(_('Debes especificar el detalle de gastos varios.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                cust = self.env['hr.employee'].browse(vals.get('custodian_id'))
                seq = self.env['ir.sequence'].next_by_code('sgs.route.service') or '0001'
                emp = cust.employee_number or str(cust.id or '')
                vals['name'] = 'F-%s-%s' % (emp, seq)
            if vals.get('vehicle_id') and not vals.get('vehicle_snapshot'):
                vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
                vals.update(self._get_vehicle_snapshot_values(vehicle))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('vehicle_id') and not vals.get('vehicle_snapshot'):
            vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
            vals.update(self._get_vehicle_snapshot_values(vehicle))
        return super().write(vals)

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_pending(self):
        self.write({'status': 'pending'})


class SgsTollLine(models.Model):
    _name = 'sgs.toll.line'
    _description = 'Caseta de servicio SGS'
    _order = 'id'

    service_id = fields.Many2one('sgs.route.service', string='Servicio', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='service_id.currency_id', readonly=True)
    name = fields.Char('Caseta / peaje', required=True)
    amount = fields.Monetary('Monto', currency_field='currency_id', required=True)
    image = fields.Binary('Foto de comprobante')
    image_filename = fields.Char('Archivo')

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El monto de la caseta debe ser mayor a cero.'))


class SgsFiscalReceipt(models.Model):
    _name = 'sgs.fiscal.receipt'
    _description = 'Comprobante fiscal SGS'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Referencia', compute='_compute_name', store=True)
    custodian_id = fields.Many2one(
        'hr.employee',
        string='Custodio',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    company_id = fields.Many2one(related='custodian_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='custodian_id.currency_id', readonly=True)
    date = fields.Date('Fecha factura', required=True, default=fields.Date.context_today)
    amount = fields.Monetary('Monto', currency_field='currency_id', required=True, tracking=True)
    description = fields.Char('Concepto / descripción', required=True)
    provider = fields.Char('Proveedor / razón social')
    provider_vat = fields.Char('RFC proveedor')
    image = fields.Binary('Foto factura')
    image_filename = fields.Char('Archivo')
    ocr_status = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('processing', 'Procesando'),
            ('success', 'Exitoso'),
            ('failed', 'Fallido'),
        ],
        string='Estado OCR',
        default='pending',
        tracking=True,
    )
    ocr_raw_data = fields.Text('Datos crudos OCR')
    ocr_error_message = fields.Text('Error OCR')
    is_fiscal = fields.Boolean('Es comprobante fiscal', default=False)
    rfc_emitter = fields.Char('RFC Emisor (OCR)')
    emitter_name = fields.Char('Nombre Emisor (OCR)')
    ocr_date = fields.Date('Fecha (OCR)')
    ocr_amount = fields.Monetary('Monto (OCR)', currency_field='currency_id')

    @api.depends('custodian_id', 'date', 'description')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s · %s · %s' % (
                rec.custodian_id.name or 'Custodio',
                rec.date or '',
                rec.description or 'Factura',
            )

    def action_process_ocr(self):
        """Process OCR for the uploaded fiscal receipt image.

        The module defines the OCR fields and exposes the button in the form
        view, but no OCR provider is bundled by default. This method keeps the
        view valid and gives users a clear result instead of failing with a
        missing-action validation error during module installation.
        """
        for rec in self:
            if not rec.image:
                raise ValidationError(_('Debes adjuntar una imagen antes de procesar OCR.'))

            rec.write({
                'ocr_status': 'failed',
                'ocr_error_message': _(
                    'No hay un motor OCR configurado. Captura los datos del comprobante manualmente '
                    'o configura una integración OCR antes de volver a procesarlo.'
                ),
                'ocr_raw_data': False,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OCR no configurado'),
                'message': _(
                    'La acción existe, pero falta configurar el proveedor OCR. '
                    'Puedes capturar los datos del comprobante manualmente.'
                ),
                'type': 'warning',
                'sticky': False,
            },
        }

    @api.constrains('amount', 'ocr_status')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0 and rec.ocr_status == 'success':
                raise ValidationError(_('El monto del comprobante fiscal debe ser mayor a cero.'))
