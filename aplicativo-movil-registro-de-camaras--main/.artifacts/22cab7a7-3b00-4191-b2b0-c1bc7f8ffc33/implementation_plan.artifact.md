# Plan de Implementación: Control de Asistencia por Horas (Regla de 10 min) y Cámara del Teléfono

## Resumen del Objetivo
Implementar dos características clave en el sistema **AsisTech UPEC**:
1. **Control de asistencia por horas (Hora 1 y Hora 2):**
   - Si transcurren más de 10 minutos desde el inicio de la clase (ej. 07:00 -> 07:10) sin registro en la **Hora 1**, se marca automáticamente como **Falta (Ausente)**.
   - Si el estudiante ingresa y escanea su rostro en la **Hora 2**, se registra la asistencia únicamente para la Hora 2, manteniendo el estado correspondiente de la Hora 1.
2. **Cámara del Teléfono para Reconocimiento Facial:**
   - Integración de la cámara nativa del teléfono móvil en la app de Flutter para escanear rostros y registrar la asistencia directamente.

## Cambios Propuestos

### 1. Backend Python (`backend_vision/`)
#### [MODIFY] [database.py](file:///C:/Users/jordy/Downloads/aplicativo-movil-registro-de-camaras--main/aplicativo-movil-registro-de-camaras--main/backend_vision/database.py)
- Actualizar la tabla `asistencias` para soportar campos por hora:
  - `hora_1_estado` (Presente, Ausente, Atrasado, etc.)
  - `hora_1_hora`
  - `hora_2_estado`
  - `hora_2_hora`
- Implementar la lógica de evaluación automática de la regla de los 10 minutos para la Hora 1 y registro dinámico para la Hora 2 según la hora actual del servidor.

#### [MODIFY] [server.py](file:///C:/Users/jordy/Downloads/aplicativo-movil-registro-de-camaras--main/aplicativo-movil-registro-de-camaras--main/backend_vision/server.py)
- Añadir/actualizar endpoints API para procesar escaneo facial indicando la hora/sesión activa.

### 2. App Móvil Flutter (`mobile_app/`)
#### [MODIFY] [pubspec.yaml](file:///C:/Users/jordy/Downloads/aplicativo-movil-registro-de-camaras--main/aplicativo-movil-registro-de-camaras--main/mobile_app/pubspec.yaml)
- Añadir dependencia `camera` o soporte de captura multimedia para escaneo de rostros con la cámara del teléfono.

#### [MODIFY] [institutional_camera_view.dart](file:///C:/Users/jordy/Downloads/aplicativo-movil-registro-de-camaras--main/aplicativo-movil-registro-de-camaras--main/mobile_app/lib/screens/institutional_camera_view.dart)
- Reemplazar la simulación de cámara IoT por la vista previa de la cámara del teléfono móvil con botón de "Escanear Rostro" y envío al backend.

## Plan de Verificación

### Pruebas Manuales
- Verificar que al pasar los 10 minutos de inicio de clase se asigne automáticamente Ausente en la Hora 1.
- Verificar que al simular o capturar el rostro en la Hora 2, se registre la asistencia en la Hora 2.
- Probar el escaneo con la cámara del teléfono en la vista de cámaras.
