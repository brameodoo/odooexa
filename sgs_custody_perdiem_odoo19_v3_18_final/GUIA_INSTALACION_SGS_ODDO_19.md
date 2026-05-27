# Guía de instalación y uso — SGS Control de Viáticos y Custodias para Odoo 19.0

## Alcance del módulo

El módulo **SGS Control de Viáticos y Custodias** fue preparado para una empresa dedicada a la custodia de vehículos pesados en rutas determinadas. Su diseño replica el flujo funcional del sistema original: administración de custodios, depósitos de viáticos, cierre de servicios, comprobación de gastos por categoría, captura de casetas, comprobantes fiscales y consulta de saldos.

La administración y gestión se realiza en el backend de Odoo. La captura operativa de gastos y comprobaciones se realiza en un portal público por token, de modo que los custodios no necesitan usuario interno de Odoo.

| Área | Función incluida |
|---|---|
| Backend Odoo | Catálogos, custodios, depósitos, validación de gastos, consulta de saldos y comprobantes |
| Portal público | Captura de cierre de servicio, casetas, evidencias y comprobantes fiscales |
| Seguridad | Grupo administrativo y acceso público únicamente mediante token individual |
| Estilo visual | Paleta oscura con acentos dorados, inspirada en un sistema operativo de control y monitoreo |

## Instalación

Copie la carpeta `sgs_custody_perdiem` dentro de la ruta de addons de su instancia Odoo 19.0. Después reinicie el servicio de Odoo, active el modo desarrollador, actualice la lista de aplicaciones e instale **SGS Control de Viáticos y Custodias**.

Una vez instalado, asigne a los usuarios administrativos el grupo **SGS Custodias / Administrador de Viáticos** desde la ficha del usuario. Los custodios externos no requieren usuario interno; se les comparte su enlace público desde la ficha del custodio.

## Uso básico

Primero registre los catálogos desde **SGS Viáticos / Configuración**, incluyendo clientes y vehículos. Después cree los custodios desde **SGS Viáticos / Operación / Custodios**, agregando número de empleado, teléfono, posición y fondo inicial. En esa misma ficha encontrará el enlace público de portal y el enlace de WhatsApp para compartirlo.

Los depósitos de viáticos se registran desde **SGS Viáticos / Operación / Depósitos**. Los servicios y gastos capturados desde el portal aparecerán en **Servicios / Gastos** con estado **Pendiente**, para que administración los pueda autorizar o rechazar.

## Flujo del portal

El custodio abre su enlace `/sgs/custodio/<token>`, consulta su saldo y captura el cierre de servicio. Puede registrar fecha, cliente, origen, destino, vehículo, compañero, viáticos, gasolina, hospedaje, gastos varios, casetas y evidencia general. También puede subir comprobantes fiscales con fecha, monto, concepto, proveedor, RFC e imagen.

Si un enlace se compromete o se desea invalidar, el administrador puede usar el botón **Regenerar token** en la ficha del custodio. Esto deja sin efecto el enlace anterior.

## Archivos principales

| Archivo | Propósito |
|---|---|
| `__manifest__.py` | Declaración del módulo, dependencias y assets |
| `models/custody.py` | Modelos de custodios, depósitos, servicios, casetas, facturas, vehículos y clientes |
| `controllers/portal.py` | Rutas públicas del portal por token |
| `views/custody_views.xml` | Vistas backend de administración |
| `views/portal_templates.xml` | Plantilla del portal público |
| `static/src/scss/sgs_portal.scss` | Estilos visuales del portal |
| `security/ir.model.access.csv` | Permisos del grupo administrativo |

## Notas técnicas

La validación realizada en este entorno confirma sintaxis Python correcta, XML bien formado y manifiesto legible. La prueba final de instalación debe hacerse dentro de una instancia real de Odoo 19.0, ya que las validaciones completas de vistas, widgets y dependencias se ejecutan dentro del propio servidor Odoo.

## Referencias

[1]: https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html "Module Manifests — Odoo 19.0 documentation"
[2]: https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html "Security in Odoo — Odoo 19.0 documentation"
[3]: https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html "Web Controllers — Odoo 19.0 documentation"
