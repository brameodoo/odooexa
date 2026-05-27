import base64
import secrets
from datetime import datetime, timedelta, time

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SgsCustodian(models.Model):
    _name = 'sgs.custodian'
    _description = 'Custodio SGS'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'name'

    name = fields.Char('Nombre completo', required=True, tracking=True)
    employee_number = fields.Char('No. empleado', tracking=True, index=True)
    position = fields.Char('Posición', tracking=True)
    phone = fields.Char('Teléfono WhatsApp')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    initial_fund = fields.Monetary('Fondo inicial', currency_field='currency_id', default=0.0, tracking=True)
    portal_token = fields.Char('Token portal', copy=False, index=True, readonly=True, default=lambda self: secrets.token_urlsafe(24))
    portal_url = fields.Char('Enlace portal', compute='_compute_portal_url')
    whatsapp_url = fields.Char('Enlace WhatsApp', compute='_compute_portal_url')

    deposit_ids = fields.One2many('sgs.perdiem.deposit', 'custodian_id', string='Depósitos')
    service_ids = fields.One2many('sgs.route.service', 'custodian_id', string='Servicios')
    fiscal_receipt_ids = fields.One2many('sgs.fiscal.receipt', 'custodian_id', string='Comprobantes fiscales')

    total_deposits = fields.Monetary('Total depositado', compute='_compute_amounts', currency_field='currency_id')
    total_expenses = fields.Monetary('Total gastos', compute='_compute_amounts', currency_field='currency_id')
    total_fiscal = fields.Monetary('Total fiscal comprobado', compute='_compute_amounts', currency_field='currency_id')
    balance = fields.Monetary('Saldo', compute='_compute_amounts', currency_field='currency_id')
    pending_service_count = fields.Integer('Servicios pendientes', compute='_compute_amounts')
    late_service_count = fields.Integer('Servicios fuera de 12h', compute='_compute_amounts')
    compliance_state = fields.Selection([
        ('blue', 'Sin gastos'),
        ('green', 'Al día'),
        ('yellow', 'Pendiente'),
        ('red', 'Atrasado / Rechazado'),
    ], string='Semáforo', compute='_compute_amounts')

    _sql_constraints = [
        ('employee_number_unique', 'unique(employee_number, company_id)', 'El número de empleado debe ser único por compañía.'),
    ]

    @api.depends('portal_token', 'phone')
    def _compute_portal_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.portal_url = f'{base}/sgs/custodio/{rec.portal_token}' if rec.portal_token else ''
            phone = ''.join(ch for ch in (rec.phone or '') if ch.isdigit())
            if phone and rec.portal_url:
                if len(phone) == 10:
                    phone = '52' + phone
                msg = f'Hola {rec.name.split()[0] if rec.name else ""}, este es tu enlace de viáticos SGS: {rec.portal_url}'
                rec.whatsapp_url = 'https://wa.me/%s?text=%s' % (phone, msg.replace(' ', '%20'))
            else:
                rec.whatsapp_url = ''

    @api.depends('initial_fund', 'deposit_ids.amount', 'service_ids.amount_total', 'service_ids.status', 'service_ids.is_late', 'fiscal_receipt_ids.amount')
    def _compute_amounts(self):
        for rec in self:
            deposits = sum(rec.deposit_ids.mapped('amount'))
            expenses = sum(rec.service_ids.filtered(lambda s: s.status != 'rejected').mapped('amount_total'))
            fiscal = sum(rec.fiscal_receipt_ids.mapped('amount'))
            pending = len(rec.service_ids.filtered(lambda s: s.status == 'pending'))
            late = len(rec.service_ids.filtered(lambda s: s.is_late and s.status != 'approved'))
            rejected = len(rec.service_ids.filtered(lambda s: s.status == 'rejected'))
            rec.total_deposits = deposits
            rec.total_expenses = expenses
            rec.total_fiscal = fiscal
            rec.balance = rec.initial_fund + deposits - expenses
            rec.pending_service_count = pending
            rec.late_service_count = late
            if not rec.service_ids:
                rec.compliance_state = 'blue'
            elif rejected or late:
                rec.compliance_state = 'red'
            elif pending:
                rec.compliance_state = 'yellow'
            else:
                rec.compliance_state = 'green'

    def action_regenerate_portal_token(self):
        for rec in self:
            rec.portal_token = secrets.token_urlsafe(24)
        return True

    def action_open_portal(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.portal_url, 'target': 'new'}


class SgsPerdiemDeposit(models.Model):
    _name = 'sgs.perdiem.deposit'
    _description = 'Depósito de viáticos SGS'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char('Referencia', compute='_compute_name', store=True)
    custodian_id = fields.Many2one('sgs.custodian', string='Custodio', required=True, ondelete='cascade', tracking=True)
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
            rec.name = '%s · %s · $%0.2f' % (rec.custodian_id.name or 'Custodio', rec.date or '', rec.amount or 0.0)

    @api.depends('date')
    def _compute_month(self):
        months = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
        for rec in self:
            rec.month = months[rec.date.month - 1] if rec.date else ''

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El monto del depósito debe ser mayor a cero.'))


class SgsClient(models.Model):
    _name = 'sgs.client'
    _description = 'Cliente SGS'
    _order = 'name'

    name = fields.Char('Cliente / Razón social', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [('name_unique', 'unique(name)', 'El cliente ya existe.')]


class SgsVehicle(models.Model):
    _name = 'sgs.vehicle'
    _description = 'Vehículo SGS'
    _order = 'plate, brand, model'

    name = fields.Char('Vehículo', compute='_compute_name', store=True)
    brand = fields.Char('Marca', required=True)
    model = fields.Char('Modelo')
    year = fields.Char('Año')
    plate = fields.Char('Placas', required=True, index=True)
    color = fields.Char('Color')
    assigned_to = fields.Char('Asignado a')
    active = fields.Boolean(default=True)

    @api.depends('brand', 'model', 'year', 'plate')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s %s %s · %s' % (rec.brand or '', rec.model or '', rec.year or '', rec.plate or '')

    @api.onchange('plate', 'brand', 'model')
    def _uppercase_vehicle(self):
        for rec in self:
            if rec.plate:
                rec.plate = rec.plate.upper()
            if rec.brand:
                rec.brand = rec.brand.upper()
            if rec.model:
                rec.model = rec.model.upper()


class SgsRouteService(models.Model):
    _name = 'sgs.route.service'
    _description = 'Servicio de custodia y gasto SGS'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Folio', default='Nuevo', copy=False, readonly=True, tracking=True)
    custodian_id = fields.Many2one('sgs.custodian', string='Custodio', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='custodian_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='custodian_id.currency_id', readonly=True)
    date = fields.Date('Fecha del servicio', required=True, default=fields.Date.context_today, tracking=True)
    submit_datetime = fields.Datetime('Fecha/hora de captura', default=fields.Datetime.now, readonly=True)
    client_id = fields.Many2one('sgs.client', string='Cliente')
    origin = fields.Char('Origen')
    destination = fields.Char('Destino')
    companion = fields.Char('Compañero / segundo custodio')
    vehicle_id = fields.Many2one('sgs.vehicle', string='Vehículo')
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
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('approved', 'Autorizado'),
        ('rejected', 'Rechazado'),
    ], default='pending', required=True, tracking=True)
    validation_note = fields.Text('Observación de validación')
    is_late = fields.Boolean('Fuera de 12h', compute='_compute_is_late', store=True)

    @api.depends('amount_perdiem', 'amount_fuel', 'amount_lodging', 'amount_misc', 'toll_line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.amount_tolls = sum(rec.toll_line_ids.mapped('amount'))
            rec.amount_total = rec.amount_perdiem + rec.amount_fuel + rec.amount_lodging + rec.amount_misc + rec.amount_tolls

    @api.depends('date', 'submit_datetime')
    def _compute_is_late(self):
        for rec in self:
            if rec.date and rec.submit_datetime:
                deadline = datetime.combine(rec.date, time.min) + timedelta(hours=36)
                # Se usa el cierre del día del servicio + 12 horas como ventana práctica.
                rec.is_late = rec.submit_datetime > deadline
            else:
                rec.is_late = False

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            if rec.vehicle_id:
                rec.vehicle_snapshot = rec.vehicle_id.name
                rec.plate_snapshot = rec.vehicle_id.plate

    @api.constrains('amount_misc', 'misc_detail')
    def _check_amounts(self):
        for rec in self:
            if rec.amount_misc > 0 and not rec.misc_detail:
                raise ValidationError(_('Debes especificar el detalle de gastos varios.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                cust = self.env['sgs.custodian'].browse(vals.get('custodian_id'))
                seq = self.env['ir.sequence'].next_by_code('sgs.route.service') or '0001'
                emp = cust.employee_number or str(cust.id or '')
                vals['name'] = 'F-%s-%s' % (emp, seq)
            if vals.get('vehicle_id') and not vals.get('vehicle_snapshot'):
                veh = self.env['sgs.vehicle'].browse(vals['vehicle_id'])
                vals['vehicle_snapshot'] = veh.name
                vals['plate_snapshot'] = veh.plate
        return super().create(vals_list)

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
    custodian_id = fields.Many2one('sgs.custodian', string='Custodio', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='custodian_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='custodian_id.currency_id', readonly=True)
    date = fields.Date('Fecha factura', required=True, default=fields.Date.context_today)
    amount = fields.Monetary('Monto', currency_field='currency_id', required=True, tracking=True)
    description = fields.Char('Concepto / descripción', required=True)
    provider = fields.Char('Proveedor / razón social')
    provider_vat = fields.Char('RFC proveedor')
    image = fields.Binary('Foto factura')
    image_filename = fields.Char('Archivo')

    # Campos OCR
    ocr_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido')
    ], string='Estado OCR', default='pending', tracking=True)
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
            rec.name = '%s · %s · %s' % (rec.custodian_id.name or 'Custodio', rec.date or '', rec.description or 'Factura')

    @api.constrains('amount', 'ocr_status')
    def _check_amount(self):
        for rec in self:
            # Permitimos monto 0 si el OCR no ha terminado exitosamente
            # Esto evita bloqueos durante el proceso de carga y análisis
            if rec.amount <= 0 and rec.ocr_status == 'success':
                raise ValidationError(_('El monto del comprobante fiscal debe ser mayor a cero.'))
