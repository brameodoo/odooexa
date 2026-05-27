# Caso de Uso: Demostración del Sistema SGS (Viáticos con IA)

Este documento sirve como guion para realizar una demostración impactante a la gerencia, mostrando el flujo completo desde la ruta hasta la administración.

---

## Escenario de la Demo
**Personaje:** Juan, un custodio que acaba de terminar una ruta de 12 horas y necesita comprobar sus gastos antes de irse a descansar.
**Objetivo:** Mostrar cómo Juan registra un gasto en menos de 30 segundos y cómo la gerencia lo ve reflejado al instante.

---

## Paso 1: El Portal del Custodio (Experiencia Móvil)
1.  **Acceso:** Abre el enlace del portal en un celular (o simula la vista móvil en el navegador).
2.  **Visualización:** Muestra el **Saldo Disponible** destacado en dorado. Explica que Juan sabe exactamente cuánto dinero le queda por comprobar.
3.  **Acción "Wow" (Cámara Directa):**
    *   Haz clic en "Seleccionar archivo" en la sección de Comprobantes.
    *   *Comenta:* "Noten cómo se abre la cámara automáticamente, sin que Juan tenga que buscar en su galería".
    *   Toma una foto de una factura real (o sube el archivo de prueba).
4.  **Procesamiento:** Haz clic en "Subir y Procesar con IA".
    *   Muestra el mensaje verde de éxito.
    *   *Comenta:* "En este momento, la IA de OpenAI está leyendo la factura, extrayendo el RFC, el monto y verificando si es deducible".

---

## Paso 2: La Magia de la IA
1.  Espera 10 segundos y refresca la página.
2.  **Resultado:** Muestra cómo el registro de $0.00 ahora tiene el **Monto Real**, el **Nombre del Proveedor** y la etiqueta **"Fiscal"** o **"No Deducible"**.
3.  *Punto Clave:* "Juan no tuvo que escribir ni una sola letra. La IA clasificó el gasto por él".

---

## Paso 3: Control Administrativo (Backend Odoo)
1.  Cambia a la pestaña de Odoo (Administrador).
2.  Ve a **SGS Custodias > Operaciones > Custodios**.
3.  Abre la ficha del custodio usado en la demo.
4.  **Visibilidad:** Muestra cómo el gasto ya aparece en la pestaña "Comprobantes Fiscales" con todos los datos llenos.
5.  **Validación:** Abre el registro del comprobante y muestra el campo `ocr_raw_data` (opcional, para mostrar la "inteligencia" detrás).
6.  *Punto Clave:* "La administración ya tiene el RFC y el monto listo para exportar a contabilidad, sin haber movido un solo dedo".

---

## Paso 4: Cierre de Servicio (Resumen de Ruta)
1.  Regresa al portal y muestra el formulario "Cerrar servicio".
2.  Explica que aquí Juan desglosa sus gastos de casetas, gasolina y viáticos de forma estructurada.
3.  *Punto Clave:* "Al finalizar, el saldo de Juan se actualiza automáticamente, cerrando el ciclo de la ruta de forma transparente".

---

## Conclusión de la Demo (Mensaje para Gerencia)
*   **Control:** "Pasamos de tickets perdidos y hojas de Excel a un control digital absoluto".
*   **Ahorro:** "Reducimos el tiempo de oficina y evitamos errores en la recuperación de IVA".
*   **Tecnología:** "SGS no es solo un programa, es una herramienta inteligente que trabaja para la empresa".
