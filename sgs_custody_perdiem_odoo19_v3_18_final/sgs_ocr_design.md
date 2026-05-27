# Diseño de Integración OCR para Módulo SGS en Odoo 19.0

## 1. Objetivo
Automatizar la extracción de datos de comprobantes de gastos (fiscales y no fiscales) mediante OCR (OpenAI Vision API) para el módulo SGS, permitiendo a los custodios subir archivos y que el sistema procese la información automáticamente.

## 2. Modelos Afectados y Nuevos Campos

### `sgs.fiscal.receipt` (Comprobantes Fiscales)
Este modelo se extenderá para almacenar los datos extraídos por OCR y el estado del procesamiento.

| Campo             | Tipo de Dato | Descripción                                                              | Notas                                     |
| :---------------- | :----------- | :----------------------------------------------------------------------- | :---------------------------------------- |
| `ocr_raw_data`    | Text         | JSON crudo de la respuesta del OCR.                                      | Para depuración y auditoría.              |
| `ocr_status`      | Selection    | Estado del procesamiento OCR (Pendiente, Procesando, Exitoso, Fallido). | Control de flujo.                         |
| `ocr_error_message` | Text         | Mensaje de error si el OCR falla.                                        |                                           |
| `is_fiscal`       | Boolean      | Determina si el comprobante es fiscal (CFDI) o no.                       | Clasificación automática.                 |
| `rfc_emitter`     | Char         | RFC del emisor (extraído por OCR).                                       |                                           |
| `emitter_name`    | Char         | Nombre/Razón social del emisor (extraído por OCR).                       |                                           |
| `ocr_date`        | Date         | Fecha del comprobante (extraída por OCR).                                |                                           |
| `ocr_amount`      | Monetary     | Monto total del comprobante (extraído por OCR).                          |                                           |

### `sgs.route.service` (Servicios de Ruta)
Se añadirá un campo para vincular los comprobantes fiscales o no fiscales directamente al servicio.

| Campo             | Tipo de Dato | Descripción                                                              | Notas                                     |
| :---------------- | :----------- | :----------------------------------------------------------------------- | :---------------------------------------- |
| `ocr_receipt_ids` | One2many     | Relación con los comprobantes procesados por OCR asociados a este servicio. | Permite múltiples comprobantes por servicio. |

## 3. Controlador del Portal (`sgs_custody_perdiem/controllers/portal.py`)

Se añadirá una nueva ruta para la carga de archivos y el manejo de la respuesta.

- **Ruta:** `/sgs/custodio/<token>/upload_receipt`
- **Método:** `POST`
- **Funcionalidad:**
    1. Recibir el archivo (imagen/PDF) subido por el custodio.
    2. Validar el token del custodio.
    3. Crear un registro `sgs.fiscal.receipt` con el archivo adjunto y `ocr_status = 'pending'`.
    4. Encolar una tarea (usando `_cron` o `_job` si Odoo permite) para procesar el OCR en segundo plano, o llamar directamente a la función de procesamiento si es síncrono.
    5. Redirigir al custodio a la página de detalle del servicio o a una página de confirmación con el estado del procesamiento.

## 4. Lógica de Procesamiento OCR (`sgs_custody_perdiem/models/ocr_processor.py` - Nuevo Modelo)

Se creará un nuevo modelo o se extenderá `sgs.fiscal.receipt` con métodos para interactuar con la API de OpenAI.

### Nuevo Modelo: `sgs.ocr.processor` (o métodos en `sgs.fiscal.receipt`)

| Campo             | Tipo de Dato | Descripción                                                              | Notas                                     |
| :---------------- | :----------- | :----------------------------------------------------------------------- | :---------------------------------------- |
| `openai_api_key`  | Char         | Clave de API de OpenAI (almacenada de forma segura).                     | Se puede configurar en `ir.config_parameter`. |

### Métodos Clave:

- `_call_openai_vision_api(self, image_base64, prompt)`:
    - Recibe la imagen en base64 y un prompt.
    - Realiza la llamada HTTP a la API de OpenAI Vision.
    - Retorna la respuesta JSON.

- `_process_receipt_ocr(self, receipt_id)`:
    - Obtiene el registro `sgs.fiscal.receipt`.
    - Convierte el archivo adjunto a base64.
    - Define el prompt para OpenAI (ej: "Extrae RFC, nombre, fecha, total y determina si es CFDI o no de este comprobante en formato JSON.").
    - Llama a `_call_openai_vision_api`.
    - Parsea la respuesta JSON.
    - Actualiza los campos `rfc_emitter`, `emitter_name`, `ocr_date`, `ocr_amount`, `is_fiscal`, `ocr_raw_data`, `ocr_status` y `ocr_error_message` del registro `sgs.fiscal.receipt`.
    - Si `is_fiscal` es True, se puede intentar validar el RFC o estructura.

## 5. Vistas del Portal y Backend

### Portal (`sgs_custody_perdiem/views/portal_templates.xml`)
- Se modificará el formulario de carga de comprobantes para incluir un campo de tipo `file`.
- Se mostrará el estado del OCR (`ocr_status`) y los datos extraídos en la vista de detalle del comprobante.

### Backend (`sgs_custody_perdiem/views/custody_views.xml`)
- Se añadirán los nuevos campos (`ocr_raw_data`, `ocr_status`, `is_fiscal`, etc.) a la vista `form` de `sgs.fiscal.receipt` para que los administradores puedan revisar y corregir los datos extraídos por OCR.
- Se podría añadir un botón para re-procesar el OCR si es necesario.

## 6. Seguridad
- La API Key de OpenAI se almacenará en `ir.config_parameter` y se accederá a ella con `sudo()` para evitar exponerla en el código del cliente.
- Se implementarán validaciones de acceso para la ruta del portal.

## 7. Flujo de Usuario (Custodio)
1. El custodio accede a su portal con su token.
2. Selecciona un servicio y hace clic en "Subir Comprobante".
3. Sube una imagen o PDF del comprobante.
4. El sistema muestra un mensaje "Comprobante subido, procesando OCR..." y redirige a la vista del comprobante.
5. Una vez procesado, el comprobante muestra los datos extraídos y si es fiscal o no. El custodio puede revisar y, si es necesario, corregir manualmente los campos o solicitar una revisión al administrador.
