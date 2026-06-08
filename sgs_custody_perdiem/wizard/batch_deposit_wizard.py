import base64
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

    def extract_spei_data(self, full_text):
        """ TU PROPUESTA DE EXTRACCIÓN PERFECCIONADA """
        # Reemplazamos acentos comunes para evitar fallos en el .upper()
        text_clean = full_text.replace('Ó', 'O').replace('ó', 'o').replace('Ó', 'O')
        lines = [line.strip() for line in text_clean.splitlines() if line.strip()]
        
        result = {
            "rfc": None,
            "amount": 0.0,
            "date": fields.Date.context_today(self), # Por defecto hoy por Odoo 19
            "diagnostic": []
        }

        # 1. RFC Beneficiario
        for index, line in enumerate(lines):
            if "RFC" in line.upper() and "BENEFICIARIO" in line.upper():
                for offset in [0, 1, 2]:
                    if index + offset < len(lines):
                        potential_line = lines[index + offset]
                        # Limpieza estricta para el RFC
                        normalized = potential_line.replace(" ", "").replace('"', '').replace("'", "").upper()
                        rfc_match = re.search(r"\b([A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3})\b", normalized)
                        if rfc_match:
                            result["rfc"] = rfc_match.group(1)
                            break
                if result["rfc"]:
                    break
        if not result["rfc"]:
            result["diagnostic"].append("No se localizó RFC Beneficiario.")

        # 2. Importe a Transferir
        for index, line in enumerate(lines):
            if "IMPORTE" in line.upper() and "TRANSFERIR" in line.upper():
                for offset in [0, 1, 2]:
                    if index + offset < len(lines):
                        potential_line = lines[index + offset]
                        amount_match = re.search(r"([0-9,]+\.\d{2})", potential_line)
                        if amount_match:
                            result["amount"] = float(amount_match.group(1).replace(",", ""))
                            break
                if result["amount"] > 0.0:
                    break
        if result["amount"] == 0.0:
            result["diagnostic"].append("No se detectó Importe a Transferir.")

        # 3. Fecha de Aplicación
        for index, line in enumerate(lines):
            # Validamos tolerando acentos
            if "FECHA" in line.upper() and ("APLICACION" in line.upper() or "APLICACIÓN" in line.upper()):
                for offset in [0, 1, 2]:
                    if index + offset < len(lines):
                        potential_line = lines[index + offset]
                        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", potential_line)
                        if date_match:
                            try:
                                result["date"] = datetime.strptime(date_match.group(1).strip(), "%d/%m/%Y").date()
                            except Exception as e:
                                result["diagnostic"].append(f"Error al parsear fecha: {e}")
                            break
                if result["date"]:
                    break

        return result

    def action_process_deposits(self):
        self.ensure_one()
        self.line_ids.unlink()
        lines_to_create = []

        for attachment in self.file_ids:
            try:
                if not attachment.datas:
                    continue
                
                # Extracción local nativa
                pdf_bytes = base64.b64decode(attachment.datas)
                pdf_file = io.BytesIO(pdf_bytes)
                reader = pypdf.PdfReader(pdf_file)
                full_text = reader.pages[0].extract_text() if len(reader.pages) > 0 else ""

                if not full_text:
                    lines_to_create.append((0, 0, {
                        'detected_rfc': 'SIN TEXTO',
                        'status': 'error',
                        'notes': 'El PDF no contiene texto digital extraíble.',
                        'attachment_id': attachment.id
                    }))
                    continue

                # Ejecución de tu función
                parsed = self.extract_spei_data(full_text)

                # Vinculación e Inteligencia con los Modelos de Odoo
                custodian = False
                status = 'error'
                note = ", ".join(parsed["diagnostic"]) if parsed["diagnostic"] else "Listo para procesar."
                
                if parsed["rfc"]:
                    employee = self.env['hr.employee'].search([('l10n_mx_rfc', '=', parsed["rfc"])], limit=1)
                    if employee:
                        custodian = self.env['sgs.custodian'].search([('employee_id', '=', employee.id)], limit=1)
                        if custodian:
                            if parsed["amount"] > 0.0:
                                status = 'ready'
                                note = 'Listo para procesar.'
                            else:
                                note = 'Custodio identificado, pero el monto sigue siendo $0.00.'
                        else:
                            note = f'Empleado {employee.name} hallado, pero no tiene ficha de Custodio SGS.'
                    else:
                        note = f'RFC {parsed["rfc"]} no asignado a ningún empleado.'

                lines_to_create.append((0, 0, {
                    'custodian_id': custodian.id if custodian else False,
                    'detected_rfc': parsed["rfc"] or 'NO DETECTADO',
                    'date': parsed["date"],
                    'amount': parsed["amount"],
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
            raise UserError(_('No hay depósitos válidos con montos mayores a cero listos para procesar.'))

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
                'message': _('Se procesaron exitosamente %s depósitos de viáticos.') % created_count,
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
