import base64
import re
from datetime import datetime
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class SgsBatchDepositWizard(models.TransientModel):
    _name = 'sgs.batch.deposit.wizard'
    _description = 'Asistente de Carga Masiva de Viáticos'

    # Campo para arrastrar múltiples PDFs/Imágenes simultáneamente
    file_ids = fields.Many2many('ir.attachment', string='Comprobantes de Pago (Banorte)', required=True)
    line_ids = fields.One2many('sgs.batch.deposit.wizard.line', 'wizard_id', string='Depósitos Detectados')

    def action_process_with_ia(self):
        """ Envía cada archivo a la API de Google Cloud para extraer RFC, Fecha y Monto """
        self.ensure_one()
        # Limpiar líneas previas si re-procesan
        self.line_ids.unlink()
        
        # Obtener API Key desde los parámetros o usar la tuya de Google Cloud
        api_key = self.env['ir.config_parameter'].sudo().get_param('sgs.google_cloud_api_key', '')
        if not api_key:
            # Llave de respaldo basada en tu captura de pantalla
            api_key = 'AIzaSyBglupqy-xD6ioWugEO9ZhR8w7Rs9pb_4M'

        url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
        lines_to_create = []

        for attachment in self.file_ids:
            # Codificar el archivo en Base64 para mandarlo a Google
            base64_data = attachment.datas.decode('utf-8')
            
            payload = {
                "requests": [{
                    "image": {"content": base64_data},
                    "features": [{"type": "TEXT_DETECTION"}]
                }]
            }

            try:
                response = requests.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    text_annotations = result.get('responses', [{}])[0].get('textAnnotations', [])
                    if not text_annotations:
                        continue
                        
                    full_text = text_annotations[0].get('description', '')
                    
                    # --- Análisis de Datos con Expresiones Regulares sobre el texto de Banorte ---
                    # --- Regex ultra-flexibles y tolerantes para el formato de Banorte ---
                
                # 1. Busca el RFC quitando comillas opcionales, espacios y saltos de línea intermedios
                rfc_match = re.search(r'RFC\s*Beneficiario\s*[:,\s"-\s]*([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})', full_text, re.IGNORECASE)
                rfc = rfc_match.group(1).upper() if rfc_match else False
                
                # 2. Busca el Importe tolerando el signo de pesos escapado de los visores de PDF (\$)
                amount_match = re.search(r'Importe\s*a\s*Transferir\s*[:,\s"-\s]*\\?\$?\s*([0-9,]+\.\d{2})', full_text, re.IGNORECASE)
                amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
                
                # 3. Busca la Fecha de Aplicación
                date_match = re.search(r'Fecha\s*Aplicación\s*[:,\s"-\s]*(\d{2}/\d{2}/\d{4})', full_text, re.IGNORECASE)
                date_val = fields.Date.context_today(self)
                if date_match:
                    try:
                        date_val = datetime.strptime(date_match.group(1), '%d/%m/%Y').date()
                    except Exception:
                        pass

                    # --- Mapeo Automático al Custodio por medio de su RFC ---
                    custodian = False
                    status = 'error'
                    note = 'RFC no encontrado en ningún empleado.'
                    
                    if rfc:
                        # Buscamos al empleado oficial que tenga este RFC de nómina mexicana
                        employee = self.env['hr.employee'].search([('l10n_mx_rfc', '=', rfc)], limit=1)
                        if employee:
                            # Buscamos su ficha de custodio vinculada
                            custodian = self.env['sgs.custodian'].search([('employee_id', '=', employee.id)], limit=1)
                            if custodian:
                                status = 'ready'
                                note = 'Listo para procesar.'
                            else:
                                note = f'Empleado {employee.name} hallado, pero no está registrado como Custodio SGS.'
                        else:
                            note = f'RFC {rfc} no asignado a ningún empleado de nómina.'

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
                    'detected_rfc': 'ERROR API',
                    'status': 'error',
                    'notes': f'Fallo de conexión con Google Cloud: {str(e)}'
                }))

        self.write({'line_ids': lines_to_create})
        
        # Reabrir el wizard para mostrar la tabla con los resultados
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sgs.batch.deposit.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_confirm_deposits(self):
        """ Toma todas las líneas aprobadas y crea los depósitos físicos en el módulo """
        self.ensure_one()
        ready_lines = self.line_ids.filtered(lambda l: l.status == 'ready' and l.custodian_id)
        if not ready_lines:
            raise UserError(_('No hay depósitos válidos con estado "Listo para procesar".'))

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
                'title': _('Dispersión Exitosa'),
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
    status = fields.Selection([
        ('ready', 'Listo para procesar'),
        ('error', 'Error / Incompleto')
    ], string='Estado', default='error')
    notes = fields.Char('Observación / Diagnóstico')
