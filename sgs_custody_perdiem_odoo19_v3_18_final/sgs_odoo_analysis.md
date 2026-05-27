# Análisis funcional del sistema original SGS Control de Viáticos

El archivo compartido corresponde a una aplicación web monolítica en HTML, CSS y JavaScript orientada al control de viáticos de custodios que acompañan vehículos pesados en rutas. La interfaz usa una identidad visual oscura con azul marino, dorado, verde y rojo, con tarjetas KPI, tablas compactas y botones de acción rápida.

## Entidades identificadas

| Entidad original | Campos principales detectados | Equivalente propuesto en Odoo |
|---|---|---|
| Custodios | nombre, número de empleado, posición, teléfono, fondo inicial | `sgs.custodian` |
| Depósitos / viáticos entregados | custodio, fecha, mes, semana, concepto, monto | `sgs.perdiem.deposit` |
| Servicios / gastos de ruta | folio, custodio, fecha, cliente, origen, destino, compañero, vehículo, placas, viáticos, gasolina, casetas, hospedaje, varios, especificación, comentarios, estado | `sgs.route.service` |
| Casetas | servicio, nombre, monto, foto | `sgs.toll.line` |
| Comprobantes fiscales | custodio, fecha, monto, descripción, proveedor, RFC, foto | `sgs.fiscal.receipt` |
| Vehículos | marca, modelo, año, placas, color, asignado a | `sgs.vehicle` |
| Clientes | nombre | `sgs.client` |

## Flujos identificados

El administrador mantiene la base de custodios, vehículos y clientes; registra depósitos semanales; valida gastos reportados; revisa saldos por custodio; identifica custodios con saldo agotado; exporta información y consulta estado de cuenta. El custodio accede por un enlace individual, sin usuario interno, donde ve su saldo, registra un cierre de servicio con desglose de gastos y sube comprobantes fiscales.

## Reglas funcionales relevantes

El saldo del custodio se calcula como fondo inicial más depósitos menos gastos reportados. Cada servicio genera folio secuencial por custodio. Los gastos tienen estados de validación: pendiente, autorizado y rechazado. Los gastos registrados después de 12 horas se marcan como fuera de tiempo. Los gastos varios requieren especificación. Las casetas pueden tener líneas múltiples con imagen por comprobante.

## Diseño visual a conservar

La paleta principal es fondo azul casi negro `#060C18`, superficies `#0C1526` y `#12203A`, acento dorado `#C8A84B`, verde positivo `#27AE60` y rojo negativo `#C0392B`. En Odoo se recomienda mantener esta apariencia principalmente en el portal público, mientras que el backend debe usar vistas nativas de Odoo con decoraciones, kanban, listas, formularios y acciones para asegurar compatibilidad y mantenibilidad.

## Decisión de implementación

El módulo Odoo debe concentrar la administración en backend mediante modelos, menús, acciones, reglas de seguridad y vistas XML. El portal debe operar con tokens públicos seguros por custodio para permitir captura sin usuario interno, usando controladores HTTP, plantillas QWeb y adjuntos `ir.attachment` para evidencia fotográfica.


## Referencias oficiales consultadas

La documentación oficial de Odoo 19 confirma que un módulo instalable se declara mediante `__manifest__.py`, con metadatos, dependencias y listas de archivos `data` y `demo`. También confirma que la seguridad debe modelarse con `ir.model.access` y reglas de registro asociadas a grupos, y que los formularios web públicos pueden implementarse con controladores HTTP usando rutas decoradas con `@route(..., auth='public')`.

| Tema | Fuente oficial |
|---|---|
| Manifiesto de módulo | https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html |
| Seguridad, ACL y reglas | https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html |
| Controladores web | https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html |

