import base64
from odoo import fields, http, _
from odoo.http import request
from werkzeug.exceptions import NotFound

class SgsCustodyPortal(http.Controller):

    def _format_amount(self, amount, currency):
        symbol = currency.symbol or '$'
        formatted_amount = "{:,.2f}".format(amount or 0.0)
        return f"{symbol} {formatted_amount}"

    def _get_custodian_from_session(self):
        """ Verifica si el custodio tiene una sesión activa mediante cookies """
        custodian_id = request.httprequest.cookies.get('sgs_custodian_id')
        session_token = request.httprequest.cookies.get('sgs_session_token')
        
        if custodian_id and session_token:
            custodian = request.env['sgs.custodian'].sudo().search([
                ('id', '=', int(custodian_id)),
                ('portal_token', '=', session_token),
                ('active', '=', True)
            ], limit=1)
            return custodian
        return False

    @http.route(['/sgs/login'], type='http', auth='public', website=True, sitemap=False)
    def sgs_portal_login(self, **post):
        """ Pantalla de inicio de sesión por No. de Empleado y NIP """
        error_msg = False
        
        # Si ya tiene sesión activa, lo mandamos directo al home
        if self._get_custodian_from_session():
            return request.redirect('/sgs/custodio')

        if request.httprequest.method == 'POST':
            employee_num = (post.get('employee_number') or '').strip()
            pin = (post.get('pin') or '').strip()
            
            # Buscar al custodio que coincida con las credenciales
            custodian = request.env['sgs.custodian'].sudo().search([
                ('employee_number', '=', employee_num),
                ('pin_access', '=', pin),
                ('active', '=', True)
            ], limit=1)
            
            if custodian:
                # Login Exitoso: Redirigir al home del portal inyectando las cookies de sesión (válidas por 90 días)
                response = request.redirect('/sgs/custodio')
                response.set_cookie('sgs_custodian_id', str(custodian.id), max_age=90*24*60*60, httponly=True)
                response.set_cookie('sgs_session_token', custodian.portal_token, max_age=90*24*60*60, httponly=True)
                return response
            else:
                error_msg = "Número de empleado o NIP incorrectos. Verifica con Administración."

        return request.render('sgs_custody_perdiem.sgs_portal_login_template', {'error': error_msg})

    @http.route(['/sgs/logout'], type='http', auth='public', website=True, sitemap=False)
    def sgs_portal_logout(self):
        """ Cierra la sesión borrando las cookies """
        response = request.redirect('/sgs/login')
        response.delete_cookie('sgs_custodian_id')
        response.delete_cookie('sgs_session_token')
        return response

    @http.route(['/sgs/custodio'], type='http', auth='public', website=True, sitemap=False)
    def custodian_home(self, **kw):
        """ Nueva Ruta Principal Protegida - Ya no expone el token en la URL """
        custodian = self._get_custodian_from_session()
        if not custodian:
            return request.redirect('/sgs/login')
            
        services = request.env['sgs.route.service'].sudo().search([('custodian_id', '=', custodian.id)], limit=20, order='date desc, id desc')
        deposits = request.env['sgs.perdiem.deposit'].sudo().search([('custodian_id', '=', custodian.id)], limit=10, order='date desc, id desc')
        fiscal = request.env['sgs.fiscal.receipt'].sudo().search([('custodian_id', '=', custodian.id)], limit=10, order='date desc, id desc')
        clients = request.env['sgs.client'].sudo().search([('active', '=', True)], order='name')
        
        vehicles = request.env['fleet.vehicle'].sudo().search([('active', '=', True)], order='license_plate')
        employees = request.env['hr.employee'].sudo().search([('active', '=', True), ('id', '!=', custodian.employee_id.id)], order='name')

        return request.render('sgs_custody_perdiem.portal_custodian_home', {
            'custodian': custodian,
            'services': services,
            'deposits': deposits,
            'fiscal_receipts': fiscal,
            'clients': clients,
            'vehicles': vehicles,
            'employees': employees,
            'token': custodian.portal_token, # Lo pasamos internamente para procesar los forms POST seguros
            'format_amount': self._format_amount,
        })
        

    @http.route(['/sgs/custodio/<string:token>/servicio'], type='http', auth='public', methods=['POST'], website=True, csrf=True, sitemap=False)
    def submit_service(self, token, **post):
        """ Procesa el servicio validando de forma estricta los archivos adjuntos """
        custodian = self._get_custodian(token)
        client = False
        if post.get('client_id'):
            client = request.env['sgs.client'].sudo().browse(int(post['client_id']))
            
        vehicle_id_val = False
        if post.get('vehicle_id'):
            try:
                fleet_vehicle = request.env['fleet.vehicle'].sudo().browse(int(post['vehicle_id']))
                if fleet_vehicle.exists():
                    vehicle_id_val = fleet_vehicle.id
            except Exception:
                vehicle_id_val = False

        companion_text = "Voy solo"
        if post.get('companion_employee_id'):
            emp = request.env['hr.employee'].sudo().browse(int(post['companion_employee_id']))
            if emp.exists():
                companion_text = emp.name

        # --- VALIDACIÓN DE COMPROBANTES MANDATORIOS ---
        amount_fuel = float(post.get('amount_fuel') or 0)
        amount_lodging = float(post.get('amount_lodging') or 0)
        
        fuel_file = request.httprequest.files.get('fuel_ticket')
        lodging_file = request.httprequest.files.get('lodging_ticket')
        
        # Si hay monto pero no hay archivo o viene sin nombre (vacío), detenemos la operación de forma segura
        if amount_fuel > 0 and (not fuel_file or not fuel_file.filename):
            return request.make_response("<script>alert('Error: La foto del ticket de gasolina es obligatoria si registraste un monto.'); window.history.back();</script>")
            
        if amount_lodging > 0 and (not lodging_file or not lodging_file.filename):
            return request.make_response("<script>alert('Error: El comprobante de hospedaje es obligatorio si registraste un monto.'); window.history.back();</script>")

        start_dt = post.get('start_datetime')
        end_dt = post.get('end_datetime')
        if start_dt:
            start_dt = start_dt.replace('T', ' ')
        if end_dt:
            end_dt = end_dt.replace('T', ' ')

        vals = {
            'custodian_id': custodian.id,
            'date': start_dt[:10] if start_dt else fields.Date.today(),
            'start_datetime': start_dt or False,
            'end_datetime': end_dt or False,
            'client_id': client.id if client and client.exists() else False,
            'origin': post.get('origin'),
            'destination': post.get('destination'),
            'companion': companion_text,
            'vehicle_id': vehicle_id_val,
            'comments': post.get('comments'),
            'amount_perdiem': float(post.get('amount_perdiem') or 0),
            'amount_fuel': amount_fuel,
            'amount_lodging': amount_lodging,
            'amount_misc': float(post.get('amount_misc') or 0),
            'misc_detail': post.get('misc_detail'),
            'status': 'pending',
        }

        # Procesar y guardar archivos de gasolina e higiene si fueron cargados
        if fuel_file and fuel_file.filename:
            vals['fuel_ticket_filename'] = fuel_file.filename
            vals['fuel_ticket'] = base64.b64encode(fuel_file.read())
            
        if lodging_file and lodging_file.filename:
            vals['lodging_ticket_filename'] = lodging_file.filename
            vals['lodging_ticket'] = base64.b64encode(lodging_file.read())

        upload = request.httprequest.files.get('evidence')
        if upload and upload.filename:
            vals['evidence_filename'] = upload.filename
            vals['evidence_image'] = base64.b64encode(upload.read())
            
        service = request.env['sgs.route.service'].sudo().create(vals)
        
        # --- PROCESAR CASETAS (Validación extra) ---
        toll_names = request.httprequest.form.getlist('toll_name[]')
        toll_amounts = request.httprequest.form.getlist('toll_amount[]')
        toll_files = request.httprequest.files.getlist('toll_image[]')
        
        for idx, name in enumerate(toll_names):
            amount = float(toll_amounts[idx] or 0) if idx < len(toll_amounts) else 0
            if not name and not amount:
                continue
                
            # Validación estricta para casetas: si hay monto, tiene que haber foto de la caseta
            t_file = toll_files[idx] if idx < len(toll_files) else False
            if amount > 0 and (not t_file or not t_file.filename):
                # Como el servicio principal ya se creó, le permitimos continuar pero registramos la alerta en comentarios administrativos
                service.comments = (service.comments or '') + f"\n[ALERTA ADM] Se registró monto para caseta '{name}' por ${amount} sin foto de evidencia."
                continue

            line_vals = {'service_id': service.id, 'name': name or 'Caseta', 'amount': amount}
            if t_file and t_file.filename:
                line_vals['image_filename'] = t_file.filename
                line_vals['image'] = base64.b64encode(t_file.read())
            request.env['sgs.toll.line'].sudo().create(line_vals)
            
        return request.redirect('/sgs/custodio/%s?ok=servicio' % token)

    @http.route(['/sgs/custodio/<string:token>/fiscal'], type='http', auth='public', methods=['POST'], website=True, csrf=True, sitemap=False)
    def submit_fiscal(self, token, **post):
        custodian = self._get_custodian(token)
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
            vals['ocr_status'] = 'pending'
        
        receipt = request.env['sgs.fiscal.receipt'].sudo().create(vals)
        
        if receipt.image:
            receipt.action_process_ocr()
            
        return request.redirect('/sgs/custodio/%s?ok=fiscal' % token)
