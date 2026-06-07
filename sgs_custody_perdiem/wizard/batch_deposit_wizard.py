import base64
import re
import io
from datetime import datetime
import requests

# Importación segura del extractor de PDFs nativo de Odoo
try:
    import pypdf
except ImportError:
    try:
        import PyPDF2 as pypdf
    except ImportError:
        pypdf = False

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class SgsBatchDepositWizard(models.TransientModel):
    _name = 'sgs.batch.deposit.wizard'
    _description = 'Asistente de Carga Masiva de Viáticos'

    file_ids = fields.Many2many('ir.attachment', string='Comprobantes de Pago (Banorte)', required=True)
    line_ids = fields.One2many('sgs.batch.deposit.wizard.line', 'wizard_id', string='Depósitos Detectados')

    def action_process_deposits(self):
        """ Procesa PDFs localmente en el servidor e imágenes vía Google Vision """
        self.ensure_one()
        self.line_ids.unlink()
        
        api_key = self.env['ir.config_parameter'].sudo().get_param('sgs.google_cloud_api_key', '').strip()
        if not api_key:
            api_key = 'AIzaSyBglupqy-xD6ioWugEO9ZhR8w7Rs9pb_4M'

        lines_to_create = []

        for attachment in self.file_ids:
            full_text = ""
            rfc = False
            amount = 0.0
            date_val = fields.Date.context_today(self)
            
            try:
                if not attachment.datas:
                    continue
                
                is_pdf = attachment.mimetype == 'application/pdf' or attachment.name.lower().endswith('.pdf')
                
                # --- RUTA A: COMPROBANTES PDF (Extracción Local Segura sin API Key) ---
                if is_pdf:
                    if pypdf:
                        pdf_bytes = base64.b64decode(attachment.datas)
                        pdf_file = io.BytesIO(pdf_bytes)
                        reader = pypdf.PdfReader(pdf_file)
                        if len(reader.pages) > 0:
                            full_text = reader.pages[0].extract_text()
                    else:
                        raise ValidationError("La librería pypdf no está disponible en el entorno del servidor.")
                
                # --- RUTA B: FOTOS / IMÁGENES (Usa endpoint estándar compatible con tu API Key) ---
                else:
                    base64_data = attachment.datas.decode('utf-8') if isinstance(attachment.datas, bytes) else attachment.datas
                    url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
                    payload = {
                        "requests": [{
                            "image": {"content": base64_data},
                            "features": [{"type": "TEXT_DETECTION"}]
                        }]
                    }
                    response = requests.post(url, json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        text_annotations = result.get('responses', [{}])[0].get('textAnnotations', [])
                        if text_annotations:
                            full_text = text_annotations[0].get('description', '')
                    else:
                        raise ValidationError(f'Google Vision rechazó la imagen (Error {response.status_code})')

                if not full_text:
                    lines_to_create.append((0, 0, {
                        'detected_rfc': 'SIN TEXTO',
                        'status': 'error',
                        'notes': 'No se pudo extraer texto del archivo.',
                        'attachment_id': attachment.id
                    }))
                    continue

                # --- Procesamiento Regex sobre texto plano ---
                # --- Procesamiento Regex con Validación Estricta de Estructura Mexicana ---
                
                # 1. RFC: Forzamos a que tenga exactamente 6 dígitos numéricos centrales y 3 de homoclave
                rfc_match = re.search(r'RFC\s*Beneficiario[\s\S]*?([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})', full_text, re.IGNORECASE)
                if rfc_match:
                    # Validamos que no sea un falso positivo corto como la clave de rastreo
                    potential_rfc = rfc_match.group(1).upper()
                    if len(potential_rfc) >= 12:
                        rfc = potential_rfc
                    else:
                        rfc = False
                else:
                    rfc = False
                
                # 2. Importe: Buscamos el monto asegurando que capture los dígitos posteriores al signo de pesos
                amount_match = re.search(r'Importe\s*a\s*Transferir[\s\S]*?\$?\s*([0-9,]+\.\d{2})', full_text, re.IGNORECASE)
                amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
                
                # 3. Fecha de Aplicación
                date_match = re.search(r'Fecha\s*Aplicación[\s\S]*?(\d{2}/\d{2}/\d{4})', full_text, re.IGNORECASE)
                    
                if date_match:
                    try:
                        date_val = datetime.strptime(date_match.group(1).strip(), '%d/%m/%Y').date()
                    except Exception:
                        pass

                # --- Mapeo e Inteligencia de Negocio ---
                custodian = False
                status = 'error'
                note = 'RFC no encontrado en ningún empleado.'
                
                if rfc:
                    employee = self.env['hr.employee'].search([('l10n_mx_rfc', '=', rfc)], limit=1)
                    if employee:
                        custodian = self.env['sgs.custodian'].search([('employee_id', '=', employee.id)], limit=1)
                        if custodian:
                            status = 'ready'
                            note = 'Listo para procesar.'
                        else:
                            note = f'Empleado {employee.name} hallado, pero no tiene ficha de Custodio SGS.'
                    else:
                        note = f'RFC {rfc} no asignado a ningún empleado en Recursos Humanos.'
                else:
                    note = 'No se localizó la etiqueta RFC Beneficiario en el documento.'

                lines_to_create.append((0, 0, {
                    'custodian_id': custodian.id if custodian else False,
                    'detected_rfc': rfc or 'NO DETECTADO',
                    'date': date_val,
                    'amount': amount,
                    'status': status,
                    'notes': note,
                    'attachment_id': attachment.id
                }))

            except Exception as e:
                lines_to_create.append((0, 0, {
                    'detected_rfc': 'ERROR',
                    'status': 'error',
                    'notes': str(e),
                    'attachment_id': attachment.id
                }))

        self.write({'line_ids': lines_to_create})
        
        action = self.env['ir.actions.act_window']._for_xml_id('sgs_custody_perdiem.action_sgs_batch_deposit_wizard')
        action['res_id'] = self.id
        return action

    def action_confirm_deposits(self):
        self.ensure_one()
        ready_lines = self.line_ids.filtered(lambda l: l.status == 'ready' and l.custodian_id)
        if not ready_lines:
            raise UserError(_('No hay depósitos válidos listos para procesar.'))

        deposit_obj = self.env['sgs.perdiem.deposit']
        created_count = 0

        for line in ready_lines:
            deposit_obj.create({
                'custodian_id': line.custodian_id.id,
                'date': line.date,
                'amount': line.amount,
                'concept': f'Dispersión masiva Banorte - Ref: {line.detected_rfc}',
                'week': f'Semana {datetime.now().isocalendar()[1]}'
            })
            created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dispersión completada'),
                'message': _('Se procesaron exitosamente %s depósitos.') % created_count,
                'type': 'success',
                'sticky': False,
            }
        }

class SgsBatchDepositWizardLine(models.TransientModel):
    _name = 'sgs.batch.deposit.wizard.line'
    _description = 'Línea Temporal de Depósito'

    wizard_id = fields.Many2one('sgs.batch.deposit.wizard', ondelete='cascade')
    custodian_id = fields.Many2one('sgs.custodian', string='Custodio Identificado')
    detected_rfc = fields.Char('RFC Detectado')
    date = fields.Date('Fecha Pago')
    amount = fields.Float('Monto ($)')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo de Origen')
    status = fields.Selection([
        ('ready', 'Listo para procesar'),
        ('error', 'Error / Incompleto')
    ], string='Estado', default='error')
    notes = fields.Char('Observación / Diagnóstico')
