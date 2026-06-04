# SGS Control de Viáticos y Custodias para Odoo 19.0

Este módulo implementa la gestión administrativa de custodios, depósitos de viáticos, servicios de custodia, gastos por categoría, casetas, comprobantes fiscales, vehículos y clientes. También incluye un portal público por token para que los custodios capturen gastos y facturas sin tener usuario interno de Odoo.

## Instalación

Copie la carpeta `sgs_custody_perdiem` dentro de la ruta de addons de Odoo 19.0, actualice la lista de aplicaciones e instale **SGS Control de Viáticos y Custodias**. Después, asigne el grupo **SGS Custodias / Administrador de Viáticos** a los usuarios administrativos que operarán el módulo.

## Uso básico

Primero registre vehículos y clientes desde **SGS Viáticos / Configuración**. Después cree custodios desde **SGS Viáticos / Operación / Custodios**. En la ficha de cada custodio encontrará su enlace de portal y el enlace de WhatsApp para compartirlo. Los depósitos se registran desde **Depósitos** y los gastos se validan desde **Servicios / Gastos**.

## Portal público

Cada custodio tiene un token único. El enlace `/sgs/custodio/<token>` permite ver saldo, registrar cierre de servicio y subir comprobantes fiscales. Si se regenera el token, el enlace anterior deja de funcionar.
