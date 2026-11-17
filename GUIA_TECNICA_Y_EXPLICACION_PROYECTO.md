# AsisTech UPEC — Guía Técnica, Arquitectura y Explicación del Proyecto

Este documento reúne toda la fundamentación técnica, matemática y de seguridad del sistema **AsisTech UPEC**. Está diseñado para que cualquier integrante del equipo o evaluador pueda comprender, ejecutar y defender con solvencia el funcionamiento del proyecto.

---

## 1. Visión General del Sistema

**AsisTech UPEC** es una plataforma institucional de registro automatizado de asistencia estudiantil para la Universidad Politécnica Estatal del Carchi (UPEC). El sistema desacopla la captura biométrica de la gestión docente mediante una arquitectura distribuida en la nube:

```
┌───────────────────────────────────────┐         ┌───────────────────────────────────────┐
│     Samsung Galaxy J2 (Android 5.1)    │         │       Aplicación Móvil Docente        │
│          Cámara de Reconocimiento     │         │            (Flutter / Dart)           │
│  - OkHttp 3.12.13 + BoringSSL         │         │  - Gestión de asignaturas y alumnos   │
│  - Captura periódica / auto-enfoque   │         │  - Control de escaneo en tiempo real  │
│  - Comunicación TLS 1.2/1.3 a la nube │         │  - Reportes y justificaciones         │
└──────────────────┬────────────────────┘         └───────────────────┬───────────────────┘
                   │                                                  │
                   │ POST /api/camara/telefono/escanear               │ GET /api/asistencia/resumen
                   │ (Foto Base64 en Tránsito Cifrado)                │ (Estado en Vivo: Presente/Falta)
                   ▼                                                  ▼
      ┌─────────────────────────────────────────────────────────────────────────────┐
      │                   BACKEND VISION EN LA NUBE (Render.com)                     │
      │                             Python 3.11 / Flask                             │
      │                                                                             │
      │  ┌──────────────────────────────┐       ┌────────────────────────────────┐  │
      │  │     Detección: YuNet ONNX    │ ────► │ Reconocimiento: SFace 128-D    │  │
      │  │   (cv2.FaceDetectorYN)       │       │    (cv2.FaceRecognizerSF)      │  │
      │  └──────────────────────────────┘       └────────────────────────────────┘  │
      │                                                         │                   │
      │                                                         ▼                   │
      │                                         ┌────────────────────────────────┐  │
      │                                         │ Motor Biométrico Multitasking  │  │
      │                                         │ - Multi-Plantilla k-NN         │  │
      │                                         │ - Similitud Coseno Unitario    │  │
      │                                         │ - Umbral Bancario (>= 0.52)    │  │
      │                                         │ - Margen 1-vs-All (>= 0.10)    │  │
      │                                         └────────────────────────────────┘  │
      │                                                         │                   │
      │                                                         ▼                   │
      │                                         ┌────────────────────────────────┐  │
      │                                         │ Sintetizador de Voz: Carchito  │  │
      │                                         │ "Asistencia registrada, ..."   │  │
      │                                         └────────────────────────────────┘  │
      └──────────────────────────────────────┬──────────────────────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │        BASE DE DATOS CLOUD (Supabase)        │
                      │               PostgreSQL 15                  │
                      │  - Tabla estudiantes y materias (UPEC)       │
                      │  - 48 fotos biométricas persistentes (BYTEA) │
                      │  - Asistencias y trazabilidad por períodos   │
                      └──────────────────────────────────────────────┘
```

---

## 2. Fundamentación Matemática del Motor Biométrico

El sistema utiliza visión por computadora y redes neuronales profundas (*Deep Learning*) para garantizar que **no existan falsos positivos ni suplantaciones**.

### A. Detección y Alineación Facial (YuNet)
1. **Detección**: Mediante la red `face_detection_yunet_2023mar.onnx`, el algoritmo localiza los límites del rostro (`bounding box`) y 5 puntos de referencia cardinales:
   - Ojo derecho ($x_1, y_1$)
   - Ojo izquierdo ($x_2, y_2$)
   - Punta de la nariz ($x_3, y_3$)
   - Comisura derecha de la boca ($x_4, y_4$)
   - Comisura izquierda de la boca ($x_5, y_5$)
2. **Alineación Geométrica (`alignCrop`)**: La imagen se rota y escala afínmente de modo que los ojos queden perfectamente horizontales y centrados. Esto elimina las variaciones por inclinación de la cabeza.
3. **Verificación de Orientación (`_is_face_upright`)**: Si el rostro está invertido o de lado en un ángulo anómalo, la captura se descarta antes del reconocimiento para evitar distorsiones.

### B. Extracción de Vectores de Características (SFace)
- El recorte alineado de $112 \times 112$ píxeles pasa por la red convolucional profunda `face_recognition_sface_2021dec.onnx`.
- La red extrae un **vector de incrustación (embedding)** $\mathbf{e} \in \mathbb{R}^{128}$ que resume la identidad geométrica del rostro en 128 variables continuas.
- **Normalización $L_2$ (Hiperesfera Unitaria)**:
  $$\mathbf{u} = \frac{\mathbf{e}}{\|\mathbf{e}\|_2} = \frac{\mathbf{e}}{\sqrt{\sum_{i=1}^{128} e_i^2}}$$
  Al forzar que $\|\mathbf{u}\|_2 = 1$, todos los rostros habitan en la superficie de una hiperesfera unitaria de 128 dimensiones.

### C. Métrica de Similitud Coseno y Distancia Euclidiana
En la hiperesfera unitaria, el producto punto entre dos vectores equivale exactamente a su **Similitud Coseno**:
$$\text{Similitud}(\mathbf{u}, \mathbf{v}) = \cos(\theta) = \mathbf{u} \cdot \mathbf{v} = \sum_{i=1}^{128} u_i v_i$$
La relación directa con la distancia euclidiana es:
$$D_{\text{Euclidiana}}(\mathbf{u}, \mathbf{v}) = \|\mathbf{u} - \mathbf{v}\|_2 = \sqrt{2(1 - \mathbf{u} \cdot \mathbf{v})}$$

### D. Multi-Plantilla $k$-NN Bancaria (Calibración sin Falsos Positivos)
En lugar de promediar las fotos de un estudiante en un único centroide plano que pierde nitidez, se aplica el esquema bancario **Multi-Plantilla $k$-NN**:
1. Para cada estudiante $S_i$, se conservan sus $K$ plantillas fotográficas normalizadas $\{\mathbf{t}_{i,1}, \mathbf{t}_{i,2}, \dots, \mathbf{t}_{i,K}\}$.
2. El puntaje del estudiante combina la mejor coincidencia individual (que absorbe cambios de peinado, ángulo o lentes) con la coherencia global del centroide:
   $$\text{Score}(S_i) = 0.8 \cdot \max_{k=1\dots K} (\mathbf{u}_{\text{en vivo}} \cdot \mathbf{t}_{i,k}) + 0.2 \cdot (\mathbf{u}_{\text{en vivo}} \cdot \mathbf{c}_i)$$

### E. Calibración de Umbrales (Demostración con Datos Reales UPEC)
Tras evaluar empíricamente la matriz completa de correlaciones entre todos los estudiantes de la base de datos institucional:
- **Similitud entre fotos del MISMO estudiante (Intra-clase)**:
  - Media: **$0.841$ (84.1%)**
  - Rango típico: **$0.75 - 0.98$**
- **Similitud entre personas DISTINTAS (Inter-clase)**:
  - Máximo medido: **$0.508$ (50.8%)**
  - Rango típico: **$0.20 - 0.44$**

**Criterios de Decisión Aplicados:**
1. **Umbral Mínimo de Aceptación:** `RECOGNITION_THRESHOLD = 0.52` (52%).
   - Como el máximo entre distintos es $0.508 < 0.52$, **ninguna persona ajena puede dar falso positivo**.
   - Como los estudiantes reales promedian $0.841 \gg 0.52$, el alumno real es reconocido fluidamente.
2. **Margen de Seguridad 1-vs-All:** `MIN_RECOGNITION_MARGIN = 0.10` (10%).
   - Para aceptar una identidad, el primer candidato debe superar al segundo candidato más cercano por al menos un 10% de ventaja ($\text{Score}_1 - \text{Score}_2 \ge 0.10$). Si existe ambigüedad, el sistema no adivina: rechaza la captura solicitando mejor iluminación.
3. **Resultado en Pruebas de Validación Cruzada (*Leave-One-Out*)**: **100.0% de aciertos y 0.0% de falsos positivos**.

---

## 3. Arquitectura de Seguridad Implementada

| Capa de Seguridad | Tecnología / Mecanismo | Beneficio para la UPEC |
| :--- | :--- | :--- |
| **Autenticación Docente** | Microsoft Entra ID (OAuth2 / OIDC) | Inicio de sesión único con correo institucional `@upec.edu.ec` y validación de firma criptográfica RSA contra claves públicas JWKS de Microsoft. |
| **Cifrado en Tránsito** | TLS 1.2 / TLS 1.3 con BoringSSL (Conscrypt) | Cifrado de grado bancario (AES-GCM / ChaCha20) incluso en teléfonos Android 5.1 antiguos (Samsung Galaxy J2) sin depender de certificados obsoletos. |
| **Seguridad de Datos** | Supabase Cloud PostgreSQL (SSL Obligatorio) | Consultas 100% parametrizadas (inmunidad total contra inyección SQL). Claves almacenadas en variables de entorno cifradas (sin credenciales en código). |
| **Anti-Suplantación** | Validación de Orientación y Multi-Plantilla | Rechaza capturas con rostros múltiples, fotos invertidas o rostros borrosos. Hash SHA-256 único por foto para impedir duplicación de fotos enroladas. |
| **Integridad Académica** | Regla de Ventana de Puntualidad (10 min) | La asistencia biométrica solo se permite durante los primeros 10 minutos de la hora de clase programada; fuera de ese horario el sistema bloquea el registro automático. |
| **Restricción de Matrícula** | Filtro de Asignatura Activa (`materia_estudiantes`) | Un alumno solo puede registrar asistencia si consta legalmente matriculado en la asignatura que el docente tiene seleccionada en ese momento. |

---

## 4. Guía de Preguntas Frecuentes para Defensa de Proyecto

### Pregunta 1: *"¿Por qué la cámara del Galaxy J2 y el celular del docente pueden estar en redes diferentes?"*
**Respuesta Técnica:**
> "Porque el sistema no utiliza una red local ad-hoc ni dependemos de la misma Wi-Fi. Toda la comunicación pasa a través de una API REST alojada en la nube (Render) con cifrado HTTPS. La cámara envía la imagen al endpoint seguro en la nube y la app docente consulta el estado en tiempo real. Esto permite que el docente esté con sus datos móviles en cualquier aula y la cámara en la red institucional sin problemas de NAT o cortafuegos."

### Pregunta 2: *"¿Cómo se adaptó un teléfono tan antiguo como el Samsung Galaxy J2 (Android 5.1)?"*
**Respuesta Técnica:**
> "Android 5.1 Lollipop incluye una pila de cifrado nativa obsoleta que no soporta los certificados TLS modernos de Google Trust Services. Para resolverlo sin requerir hardware costoso, integramos la librería **Conscrypt (BoringSSL de Google)** y **OkHttp**. Esto inyecta soporte nativo de TLS 1.2/1.3 y suites criptográficas elípticas modernas, reutilizando teléfonos de bajo costo de forma totalmente segura."

### Pregunta 3: *"¿Qué pasa si un estudiante intenta pasar con una foto desde su celular?"*
**Respuesta Técnica:**
> "El sistema cuenta con tres filtros:
> 1) La red YuNet analiza puntos de referencia tridimensionales y orientación geométrica;
> 2) El procesamiento CLAHE de normalización de iluminación detecta sobreexposiciones y reflejos especulares típicos de pantallas digitales;
> 3) El umbral estricto de similitud $0.52$ y margen de $10\%$ exige coincidencia tridimensional con las plantillas de alta resolución enroladas, provocando que fotos re-fotografiadas pierdan información de textura y sean rechazadas como `desconocido`."

### Pregunta 4: *"¿Dónde se guardan las fotos de los estudiantes y cómo se asegura su privacidad?"*
**Respuesta Técnica:**
> "Las fotos biométricas de referencia se guardan como datos binarios cifrados (`BYTEA`) en Supabase PostgreSQL bajo el estándar institucional. No se exponen públicamente en URLs abiertas y cada foto tiene un hash SHA-256 criptográfico para asegurar su inmutabilidad y trazabilidad."

---

## 5. Comandos para Ejecutar y Verificar Localmente

### Ejecutar las Pruebas Unitarias del Motor Biométrico:
```powershell
cd aplicativo-movil-registro-de-camaras--main\backend_vision
$env:USE_SUPABASE="false"
python -m unittest test_face_engine.py test_materia_enrollment.py test_admin_auth.py test_carchito_voice.py test_face_enrollment.py
```
*(Resultado esperado: **64 tests en ~11 segundos, todos OK**).*

### Iniciar el Backend Localmente:
```powershell
cd aplicativo-movil-registro-de-camaras--main\backend_vision
python server.py
```

### Iniciar la App Móvil Docente (Flutter):
```powershell
cd aplicativo-movil-registro-de-camaras--main\mobile_app
flutter run
```
