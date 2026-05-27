import base64
import json
import logging
import requests
import io
from PIL import Image
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SgsFiscalReceipt(models.Model):
    _inherit = 'sgs.fiscal.receipt'

    def action_process_ocr(self):
        """Inicia el proceso de OCR para el comprobante."""
        for rec in self:
            if not rec.image:
                continue
            rec.write({'ocr_status': 'processing', 'ocr_error_message': False})
            # En un entorno real, esto podría ser un job asíncrono
            rec._process_ocr_with_openai()

    def _process_ocr_with_openai(self):
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param('sgs.openai_api_key')
        if not api_key:
            self.write({
                'ocr_status': 'failed',
                'ocr_error_message': 'No se ha configurado la API Key de OpenAI en los parámetros del sistema (sgs.openai_api_key).'
            })
            return

        try:
            # Optimizar imagen antes de enviar
            img_raw = base64.b64decode(self.image)
            img = Image.open(io.BytesIO(img_raw))
            
            # Redimensionar si es muy grande (max 1200px)
            max_size = 1200
            if max(img.size) > max_size:
                ratio = max_size / float(max(img.size))
                new_size = tuple([int(x * ratio) for x in img.size])
                img = img.resize(new_size, Image.LANCZOS)
            
            # Convertir a JPEG y comprimir
            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=85)
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Prompt optimizado para comprobantes de México
            prompt = """
            Analiza esta imagen de un comprobante de gasto. 
            Extrae la siguiente información en formato JSON:
            - is_fiscal: boolean (true si es un CFDI/Factura con RFC, false si es un ticket/nota de remisión)
            - rfc_emitter: string (RFC del emisor si es fiscal)
            - emitter_name: string (Nombre o razón social del emisor)
            - date: string (Fecha en formato YYYY-MM-DD)
            - total: number (Monto total con impuestos)
            - description: string (Breve descripción del gasto, ej: "Consumo de alimentos", "Combustible", "Peaje")
            
            Responde ÚNICAMENTE con el objeto JSON, sin texto adicional.
            """

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 1000,
                "response_format": {"type": "json_object"}
            }

            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Limpiar posible formato markdown del JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            data = json.loads(content)
            
            # Actualizar campos
            vals = {
                'ocr_status': 'success',
                'ocr_raw_data': content,
                'is_fiscal': data.get('is_fiscal', False),
                'rfc_emitter': data.get('rfc_emitter'),
                'emitter_name': data.get('emitter_name'),
                'ocr_date': data.get('date'),
                'ocr_amount': data.get('total', 0.0),
                'ocr_error_message': False
            }
            
            # Si el usuario no ha llenado los campos manuales, sugerir los del OCR
            if not self.provider_vat:
                vals['provider_vat'] = data.get('rfc_emitter')
            if not self.provider:
                vals['provider'] = data.get('emitter_name')
            if not self.amount:
                vals['amount'] = data.get('total', 0.0)
            if not self.description or self.description == 'Factura':
                vals['description'] = data.get('description', 'Factura procesada por OCR')
            if self.date == fields.Date.context_today(self):
                vals['date'] = data.get('date')

            self.write(vals)

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    error_msg = e.response.text[:200]
            _logger.error("Error de API OpenAI: %s", error_msg)
            self.write({
                'ocr_status': 'failed',
                'ocr_error_message': f"OpenAI Error: {error_msg}"
            })
        except Exception as e:
            _logger.error("Error inesperado en OCR: %s", str(e))
            self.write({
                'ocr_status': 'failed',
                'ocr_error_message': f"Error inesperado: {str(e)}"
            })
