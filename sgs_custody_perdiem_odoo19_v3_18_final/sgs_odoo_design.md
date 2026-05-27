# Diseño técnico del módulo `sgs_custody_perdiem` para Odoo 19.0

## Objetivo

El módulo `sgs_custody_perdiem` centraliza en Odoo la administración de custodios, vehículos, clientes, depósitos de viáticos, servicios de custodia en ruta, gastos comprobados, casetas y comprobantes fiscales. El backend de Odoo será utilizado por administración y dirección; el portal público por token permitirá que cada custodio reporte gastos y facturas sin requerir un usuario interno.

## Estructura funcional

| Área | Implementación en Odoo | Propósito |
|---|---|---|
| Backend administrativo | Modelos, vistas tree/form/kanban/search, acciones y menús | Alta de catálogos, depósitos, validación y consulta de saldos |
| Portal de custodios | Controladores HTTP públicos con token individual | Captura de servicios, gastos y comprobantes fiscales |
| Seguridad | Grupo de usuario `SGS Administrador de Viáticos`, ACL y token público | Evitar acceso público al backend y limitar portal por enlace firmado |
| Evidencias | `ir.attachment` ligado a servicios, casetas y facturas | Guardar fotos de tickets, casetas y comprobantes fiscales |
| Indicadores | Campos calculados y kanban | Saldo, total depositado, total gastado, estado de cumplimiento |

## Modelos propuestos

| Modelo | Descripción | Campos principales |
|---|---|---|
| `sgs.custodian` | Custodio operativo | nombre, número empleado, posición, teléfono, fondo inicial, token portal, depósitos, servicios, comprobantes, saldo |
| `sgs.perdiem.deposit` | Entrega de viáticos | custodio, fecha, semana, mes, concepto, monto |
| `sgs.route.service` | Servicio/cierre de ruta | folio, custodio, fecha, cliente, origen, destino, compañero, vehículo, placas, importes por categoría, total, estado, fuera de tiempo |
| `sgs.toll.line` | Casetas dentro de un servicio | nombre, monto, imagen |
| `sgs.fiscal.receipt` | Comprobante fiscal | custodio, fecha, monto, descripción, proveedor, RFC, imagen |
| `sgs.vehicle` | Catálogo de vehículos | marca, modelo, año, placas, color, asignado a |
| `sgs.client` | Catálogo de clientes | nombre |

## Flujo de captura por portal

El administrador abre la ficha de un custodio y copia su enlace público. El custodio abre el enlace, visualiza su saldo, movimientos recientes y dos formularios principales: **Cerrar servicio** y **Subir comprobante fiscal**. Al guardar un servicio, el sistema genera un folio secuencial por custodio, guarda los importes por categoría, almacena evidencias y deja el gasto en estado **Pendiente**. Administración valida posteriormente cada servicio como **Autorizado** o **Rechazado**, capturando observaciones cuando sea necesario.

## Compatibilidad Odoo 19.0

La estructura respeta el patrón de módulo estándar con `__manifest__.py`, dependencias `base`, `web`, `mail` y `portal`, archivos XML en `data`, `security`, `views` y `templates`, controladores Python en `controllers`, modelos en `models` y estilos en `static/src/scss`. El portal se implementa con rutas públicas y comprobación explícita de token para no conceder permisos de lectura general al usuario público.

## Paleta visual

| Uso | Color |
|---|---|
| Fondo principal | `#060C18` |
| Superficie | `#0C1526` |
| Superficie secundaria | `#12203A` |
| Borde | `#1E3A5F` |
| Acento dorado | `#C8A84B` |
| Positivo | `#27AE60` |
| Negativo | `#C0392B` |
| Texto principal | `#EEF2F8` |
| Texto secundario | `#8BA5C5` |

## Entregable esperado

Se generará un paquete ZIP con el módulo completo, instalable en una instancia Odoo 19.0 mediante la carpeta de addons. El módulo incluirá datos demo mínimos para permitir una primera prueba funcional.

## Referencias

[1]: https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html "Module Manifests — Odoo 19.0 documentation"
[2]: https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html "Security in Odoo — Odoo 19.0 documentation"
[3]: https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html "Web Controllers — Odoo 19.0 documentation"
