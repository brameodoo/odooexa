# Resumen Ejecutivo: Implementación de IA para Gestión de Viáticos (SGS)

## 1. Objetivo Estratégico
Optimizar el proceso de comprobación de gastos de los custodios mediante la automatización de la captura de datos, eliminando la carga administrativa manual y reduciendo errores en la clasificación fiscal de los documentos.

## 2. Funcionalidades Clave de la IA
*   **Extracción Automática (OCR):** Identificación inmediata de RFC del emisor, Razón Social, Fecha y Monto Total a partir de fotos o PDFs.
*   **Clasificación Fiscal Inteligente:** El sistema distingue automáticamente entre un **Comprobante Fiscal Digital (CFDI)** y un **Gasto No Deducible** (tickets, notas de remisión), facilitando la labor de contabilidad.
*   **Integración en Tiempo Real:** Los datos extraídos se vinculan directamente al saldo del custodio en Odoo, permitiendo un control financiero actualizado al minuto.
*   **Optimización de Costos:** Implementación basada en el modelo **GPT-4o-mini**, que ofrece un equilibrio óptimo entre precisión de lectura y bajo costo por transacción.

## 3. Beneficios para la Organización
*   **Eficiencia Operativa:** Reducción del 80% en el tiempo de captura de gastos por parte del personal administrativo.
*   **Precisión de Datos:** Eliminación de errores de dedo en montos y RFCs.
*   **Experiencia del Usuario:** Los custodios solo necesitan tomar una fotografía, eliminando la necesidad de conocimientos contables o fiscales.
*   **Transparencia:** Registro fotográfico vinculado a cada transacción para auditorías inmediatas.

## 4. Limitaciones Técnicas y Mitigación
| Limitación | Impacto | Estrategia de Mitigación |
| :--- | :--- | :--- |
| **Calidad de Imagen** | Documentos borrosos o con reflejos impiden la lectura. | Guía de buenas prácticas para custodios y validación manual en backend. |
| **Papel Térmico Dañado** | Tickets de gasolinera borrados por calor o tiempo. | Captura inmediata del gasto al momento de recibir el ticket. |
| **Conectividad** | Requiere acceso a internet para procesar con OpenAI. | El sistema permite la subida y procesa en cuanto hay conexión disponible. |

## 5. Conclusión
La integración de IA en el módulo SGS posiciona a la empresa a la vanguardia tecnológica en logística, transformando un proceso administrativo tedioso en un flujo digital ágil, escalable y con un alto grado de confiabilidad para la toma de decisiones financieras.
