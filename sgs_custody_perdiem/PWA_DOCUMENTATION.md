# Documentación PWA - SGS Control de Viáticos y Custodias v4.0

## Descripción General

La versión 4.0 del módulo SGS Control de Viáticos y Custodias incluye capacidades de **Progressive Web App (PWA)**, permitiendo que los custodios accedan al portal desde sus dispositivos móviles como si fuera una aplicación nativa.

## Características PWA

### 1. **Instalación en Pantalla de Inicio**
Los custodios pueden instalar la aplicación directamente en la pantalla de inicio de sus dispositivos:
- **iOS**: Abrir en Safari → Compartir → Añadir a pantalla de inicio
- **Android**: Abrir en Chrome → Menú → Instalar aplicación

### 2. **Funcionamiento Offline**
- Service Worker cachea automáticamente los datos
- Los custodios pueden ver información previamente cargada sin conexión
- Los datos se sincronizan automáticamente cuando se restaura la conexión

### 3. **Notificaciones Push**
- Notificaciones sobre servicios pendientes
- Alertas de cambios en estado de comprobantes
- Recordatorios de depósitos

### 4. **Sincronización en Background**
- Los datos se sincronizan automáticamente
- Los cambios se envían al servidor cuando hay conexión

## Archivos Creados

### Archivos Estáticos

#### `static/manifest.json`
Archivo de configuración PWA que define:
- Nombre y descripción de la app
- Iconos para diferentes tamaños
- Pantallas de inicio (splash screens)
- Atajos (shortcuts)
- Capacidad de compartir

#### `static/service-worker.js`
Service Worker que maneja:
- Caché de archivos
- Estrategia "Network First" para solicitudes
- Sincronización en background
- Notificaciones push
- Manejo de modo offline

#### `static/pwa-init.js`
Script de inicialización que:
- Registra el Service Worker
- Detecta si la app está instalada
- Maneja cambios de conectividad
- Solicita permisos de notificaciones
- Gestiona orientación del dispositivo

#### `static/pwa-styles.css`
Estilos optimizados para PWA:
- Diseño responsive
- Soporte para notch/safe areas
- Modo oscuro
- Modo offline visual
- Optimización para touch

### Archivos de Configuración

#### `views/pwa_head_template.xml`
Template XML con meta tags necesarios:
- Meta tags de compatibilidad móvil
- Iconos de Apple
- Open Graph tags
- Twitter Card tags
- Preload de recursos críticos

### Modelos Python

#### `models/pwa.py`
Nuevos modelos:

**SGSPushSubscription**
- Almacena suscripciones a notificaciones push
- Gestiona dispositivos y endpoints
- Detecta tipo de dispositivo
- Rastreo de intentos fallidos

**SGSPushNotificationLog**
- Registro de notificaciones enviadas
- Seguimiento de estado
- Mensajes de error

### Controladores

#### `controllers/pwa.py`
Endpoints PWA:

**POST /sgs/custodio/push-subscribe**
- Registra suscripción a push notifications
- Almacena endpoint y claves de encriptación

**POST /sgs/custodio/sync**
- Sincroniza datos pendientes
- Retorna servicios y comprobantes sin sincronizar

**POST /sgs/custodio/send-notification**
- Envía notificación push a custodio
- Requiere permisos de administrador

**GET /sgs/custodio/app-info**
- Retorna información de la app
- Estadísticas del custodio

**GET /sgs/custodio/offline-data**
- Retorna datos para modo offline
- Servicios y comprobantes recientes

## Integración en el Portal

### Paso 1: Incluir Meta Tags
En el template principal del portal (`views/portal_templates.xml`), incluir:

```xml
<t t-call="sgs_custody_perdiem.pwa_head_template"/>
```

### Paso 2: Incluir Scripts
Los scripts se cargan automáticamente desde `assets` en `__manifest__.py`:
- `pwa-styles.css` - Estilos
- `pwa-init.js` - Inicialización

### Paso 3: Botón de Instalación (Opcional)
En el template del portal, añadir:

```html
<button id="install-app-btn" class="btn btn-primary">
    Instalar Aplicación
</button>
```

## Flujo de Funcionamiento

### Instalación
1. Usuario abre el portal en navegador móvil
2. Script `pwa-init.js` se ejecuta
3. Service Worker se registra
4. Navegador muestra opción de instalar
5. Usuario toca "Instalar"
6. App se añade a pantalla de inicio

### Uso Offline
1. Usuario abre la app instalada
2. Service Worker intercepta solicitudes
3. Si hay conexión: obtiene datos del servidor y cachea
4. Si no hay conexión: usa datos en caché
5. Cuando se restaura conexión: sincroniza automáticamente

### Notificaciones Push
1. Usuario otorga permiso de notificaciones
2. Suscripción se registra en servidor
3. Servidor envía notificaciones cuando hay eventos
4. Usuario recibe notificación en dispositivo
5. Toque abre la app

## Configuración del Servidor

### Requisitos Python
```bash
pip install qrcode pywebpush
```

### Configuración de Notificaciones Push (Opcional)
Para enviar notificaciones push, se necesita:
1. VAPID keys (generar con `pywebpush`)
2. Servicio de push (Firebase Cloud Messaging, Pushover, etc.)
3. Configurar en settings de Odoo

### Generar VAPID Keys
```python
from pywebpush import generate_vapid_keys

vapid_keys = generate_vapid_keys()
print("Public Key:", vapid_keys['public_key'])
print("Private Key:", vapid_keys['private_key'])
```

## Seguridad

### Consideraciones
1. **HTTPS Requerido**: PWA solo funciona en HTTPS (excepto localhost)
2. **Token Portal**: Mantener seguro el token del custodio
3. **Encriptación**: Las claves de push se encriptan
4. **CORS**: Configurar correctamente para notificaciones

### Permisos
- Notificaciones: Usuario debe otorgar permiso
- Cámara: Para captura de evidencia
- Ubicación: Opcional para geolocalización

## Optimización

### Caché
- Service Worker cachea automáticamente
- Estrategia: Network First (red primero, caché si falla)
- Limpieza automática de caché antiguo

### Performance
- Estilos optimizados para móvil
- Iconos en múltiples tamaños
- Preload de recursos críticos
- Compresión de imágenes

### Compatibilidad
- iOS 11.3+
- Android 5.0+ (Chrome 39+)
- Fallback para navegadores antiguos

## Monitoreo

### Logs
- Verificar `sgs.push.subscription` para suscripciones activas
- Revisar `sgs.push.notification.log` para historial de notificaciones
- Monitorear intentos fallidos en `failed_attempts`

### Diagnóstico
```python
# En consola de Odoo
env['sgs.push.subscription'].search([('is_active', '=', True)])
env['sgs.push.notification.log'].search([], limit=10, order='create_date desc')
```

## Troubleshooting

### La app no se instala
- Verificar que está en HTTPS
- Revisar que `manifest.json` es válido
- Comprobar que Service Worker se registra sin errores

### Notificaciones no llegan
- Verificar permisos en dispositivo
- Revisar `failed_attempts` en suscripción
- Comprobar endpoint en `sgs.push.subscription`

### Datos no se sincronizan
- Verificar conectividad
- Revisar logs del Service Worker
- Comprobar que endpoints están disponibles

## Próximas Mejoras

- [ ] Integración con Firebase Cloud Messaging
- [ ] Geolocalización en tiempo real
- [ ] Cámara para captura de evidencia
- [ ] Almacenamiento local IndexedDB
- [ ] Sincronización bidireccional
- [ ] Modo oscuro nativo
- [ ] Soporte para wearables

## Referencias

- [MDN - Progressive Web Apps](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [Web.dev - PWA](https://web.dev/progressive-web-apps/)
- [Service Workers API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)

## Soporte

Para problemas o sugerencias, contactar al equipo de desarrollo.
