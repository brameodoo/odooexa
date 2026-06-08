import base64
import json
import re
import io
from datetime import datetime
import requests

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
        """ Extrae datos con OpenAI y valida que el archivo o la clave de rastreo no estén duplicados """
        self.ensure_one()
        self.line_ids.unlink()
        
        api_key = self.env['ir.config_parameter'].sudo().get_param('sgs.openai_api_key', '').strip()
        if not api_key:
            raise UserError(_("Por favor, configure primero la API Key de OpenAI en los parámetros del sistema (sgs.openai_api_key)."))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        lines_to_create = []

        for attachment in self.file_ids:
            # --- CANDADO 1: Validación por Checksum del Archivo ---
            # Si el archivo exacto ya existe vinculado a otro lote procesado anteriormente
            if attachment.checksum:
                existing_line = self.env['sgs.batch.deposit.wizard.line'].search([
                    ('wizard_id', '!=', self.id),
                    ('attachment_checksum', '=', attachment.checksum)
                ], limit=1)
                if existing_line:
                    lines_to_create.append((0, 0, {
                        'detected_rfc': 'DUPLICADO',
                        'status': 'error',
                        'notes': f'El archivo físico "{attachment.name}" ya fue procesado en un lote anterior.',
                        'attachment_id': attachment.id
                    }))
                    continue

            full_text = ""
            try:
                if not attachment.datas:
                    continue
                
                is_pdf = attachment.mimetype == 'application/pdf' or attachment.name.lower().endswith('.pdf')
                if is_pdf and pypdf:
                    pdf_bytes = base64.b64decode(attachment.datas)
                    pdf_file = io.BytesIO(pdf_bytes)
                    reader = pypdf.PdfReader(pdf_file)
                    if len(reader.pages) > 0:
                        full_text = reader.pages[0].extract_text() or ""
                
                force_vision_mode = False
                if not is_pdf or (is_pdf and not full_text.strip()):
                    force_vision_mode = True

                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Eres un asistente experto en contabilidad mexicana. Tu trabajo es extraer el RFC del BENEFICIARIO (LONGITUD 12 o 13 caracteres), el IMPORTE A TRANSFERIR (como número flotante), la FECHA DE APLICACIÓN (en formato YYYY-MM-DD) y la CLAVE DE RASTREO completa desde un comprobante SPEI de Banorte. Responde estrictamente en formato JSON con las llaves: rfc, amount, date, tracking_key."
                        },
                        {
                            "role": "user",
                            "content": full_text
                        }
                    ],
                    "response_format": { "type": "json_object" },
                    "temperature": 0.0
                }

                if force_vision_mode:
                    base64_data = attachment.datas.decode('utf-8') if isinstance(attachment.datas, bytes) else attachment.datas
                    mimetype = attachment.mimetype if attachment.mimetype else "application/pdf" if is_pdf else "image/png"
                    payload["messages"][1]["content"] = [
                        {"type": "text", "text": "Extrae el rfc, amount, date y tracking_key de este comprobante:"},
                        {"type": "image_url", "image_url": {"url": f"data:{mimetype};base64,{base64_data}"}}
                    ]

                response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=45)
                
                if response.status_code != 200:
                    raise ValidationError(f"OpenAI respondió con un error (Código {response.status_code})")

                res_json = response.json()
                ai_content = json.loads(res_json['choices'][0]['message']['content'])

                rfc = ai_content.get('rfc', '').strip().upper() if ai_content.get('rfc') else False
                amount = float(ai_content.get('amount', 0.0))
                tracking_key = ai_content.get('tracking_key', '').strip()
                
                date_val = fields.Date.context_today(self)
                if ai_content.get('date'):
                    try:
                        date_val = fields.Date.from_string(ai_content.get('date')[:10])
                    except Exception:
                        pass

                # --- CANDADO 2: Validación por Clave de Rastreo SPEI Banorte ---
                if tracking_key:
                    existing_deposit = self.env['sgs.perdiem.deposit'].search([
                        ('tracking_key', '=', tracking_key)
                    ], limit=1)
                    if existing_deposit:
                        lines_to_create.append((0, 0, {
                            'detected_rfc': rfc or 'ERROR',
                            'date': date_val,
                            'amount': amount,
                            'status': 'error',
                            'notes': f'Duplicado Bancario: La clave de rastreo SPEI {tracking_key} ya fue aplicada antes.',
                            'attachment_id': attachment.id,
                            'attachment_checksum': attachment.checksum
                        }))
                        continue

                custodian = False
                status = 'error'
                note = 'RFC no encontrado en ningún empleado.'

                if rfc:
                    employee = self.env['hr.employee'].search([('l10n_mx_rfc', '=', rfc)], limit=1)
                    if employee:
                        custodian = self.env['sgs.custodian'].search([('employee_id', '=', employee.id)], limit=1)
                        if custodian:
                            if amount > 0.0:
                                status = 'ready'
                                note = 'Listo para procesar.'
                            else:
                                note = 'Custodio identificado, pero el monto se leyó como $0.00.'
                        else:
                            note = f'Empleado {employee.name} hallado, pero no es Custodio SGS.'
                    else:
                        note = f'RFC {rfc} no asignado a ningún empleado.'
                else:
                    note = 'La IA no pudo determinar el RFC del Beneficiario.'

                lines_to_create.append((0, 0, {
                    'custodian_id': custodian.id if custodian else False,
                    'detected_rfc': rfc or 'NO DETECTADO',
                    'date': date_val,
                    'amount': amount,
                    'status': status,
                    'notes': note,
                    'attachment_id': attachment.id,
                    'attachment_checksum': attachment.checksum,
                    'tracking_key': tracking_key
                }))

            except Exception as e:
                lines_to_create.append((0, 0, {
                    'detected_rfc': 'ERROR',
                    'status': 'error',
                    'notes': str(e),
                    'attachment_id': attachment.id,
                    'attachment_checksum': attachment.checksum
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
                'week': f'Semana {datetime.now().isocalendar()[1]}',
                'tracking_key': line.tracking_key # Se guarda la clave de rastreo para bloquear futuros duplicados
            })
            created_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dispersión completada'),
                'message': _('Se crearon exitosamente %s depósitos de viáticos.') % created_count,
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
    attachment_checksum = fields.Char('Hash del Archivo') # Campo técnico para almacenar el checksum
    tracking_key = fields.Char('Clave de Rastreo') # Campo técnico para almacenar el SPEI
    status = fields.Selection([
        ('ready', 'Listo para procesar'),
        ('error', 'Error / Incompleto')
    ], string='Estado', default='error')
    notes = fields.Char('Observación / Diagnóstico')
