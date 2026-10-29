# AsisTech: Sistema Inteligente de Asistencia Móvil con Reconocimiento Facial y Asistente de Voz

[![Universidad Politécnica Estatal del Carchi](https://img.shields.io/badge/Universidad-UPEC-003366.svg)](https://www.upec.edu.ec)
[![Carrera](https://img.shields.io/badge/Carrera-Computaci%C3%B3n-0066cc.svg)](https://www.upec.edu.ec)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg)](https://flutter.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8.svg)](https://opencv.org)

> **Proyecto Semestral de Aplicaciones Móviles & Visión por Computador**  
> **Acceso actual:** Administrador (modo de desarrollo)  
> **Facultad:** Industrias Agropecuarias y Ciencias Ambientales (FIACA)  
> **Universidad Politécnica Estatal del Carchi (Tulcán, Ecuador - 2026)**

---

## 👥 Equipo de Desarrollo
* **Sebastián Reina** (Líder de Proyecto / Desarrollador Frontend Flutter)
* **Edelina Cadena** (Desarrolladora Backend, Base de Datos y QA)
* **Jordy Lema** (Especialista en Hardware IoT y Redes)
* **Melisa Ponce** (Desarrolladora de Visión por Computador)

---

## 📌 Descripción General
**AsisTech** es una solución integral diseñada para automatizar el control de asistencia en las aulas y laboratorios de la UPEC. El sistema combina:
1. **Motor de Visión Artificial (OpenCV + Python):** Detección biométrica facial de estudiantes en tiempo real mediante cámaras de alta velocidad.
2. **Asistente Virtual de Voz ("Carchito"):** Permite a los docentes activar la toma de lista mediante comandos verbales (*"Hola Carchito, toma asistencia"*).
3. **Aplicación Móvil Android (Flutter / Dart):** Dashboard interactivo en tiempo real con estadísticas, respaldo de edición manual y reportería.
4. **Base de Datos Persistente (SQLite / API REST):** Gestión segura de registros, horarios y paralelos.

---

## 🏗️ Arquitectura del Sistema

```
aplicativo-movil-registro-de-camaras-/
│
├── backend_vision/             # Motor de IA, Visión por Computador y API REST
│   ├── database.py             # Base de datos SQLite y persistencia de asistencias
│   ├── face_engine.py          # Detección y reconocimiento facial en vivo (OpenCV)
│   ├── models/                 # Modelos faciales YuNet y SFace requeridos
│   ├── carchito_voice.py       # Asistente virtual de voz "Carchito" (TTS & STT)
│   ├── server.py               # API REST del sistema
│   └── requirements.txt        # Dependencias de Python
│
├── mobile_app/                 # Aplicación Móvil en Flutter (Dart)
│   ├── lib/
│   │   ├── main.dart           # Punto de entrada de la aplicación móvil
│   │   └── screens/            # Pantallas (Dashboard, Carchito, Reportes)
│   └── pubspec.yaml            # Dependencias y configuración de Flutter
│
└── README.md                   # Documentación oficial del repositorio
```

---

## 🚀 Guía de Instalación y Ejecución

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Sebasdharma/aplicativo-movil-registro-de-camaras-.git
cd aplicativo-movil-registro-de-camaras-
```

### 2. Ejecutar el Backend y Motor de Visión (Python)
```bash
cd backend_vision
pip install -r requirements.txt
python server.py
```
El backend incluye los modelos YuNet y SFace necesarios para el reconocimiento
facial; su procedencia y licencias están documentadas en
[`backend_vision/models/README.md`](./backend_vision/models/README.md).
El backend proporciona la API de la app y una página web local (`/tablet-camera`)
para usar la cámara de una tablet desde Chrome sin instalar la app móvil.
La página requiere HTTPS local y permiso de cámara.

#### Usar la cámara de una tablet sin instalar AsisTech

1. Conecta el computador, el teléfono y la tablet a la misma Wi-Fi. Averigua
   con `ipconfig` la IPv4 Wi-Fi del computador.
2. En `backend_vision`, crea un certificado para esa IP y configura HTTPS:

   ```powershell
   python generate_local_cert.py 192.168.1.25
   $env:ASISTECH_TLS_CERT = "$PWD\certs\server.crt"
   $env:ASISTECH_TLS_KEY = "$PWD\certs\server.key"
   python server.py
   ```

   Sustituye `192.168.1.25` por la IPv4 actual. No compartas `certs\local-ca.key`
   ni `certs\server.key`.
3. En el dispositivo Android que usará Chrome como cámara, instala
   `backend_vision\certs\local-ca.crt` desde los ajustes como certificado de CA
   de usuario. La app móvil Android ya confía en esta CA incluida en
   `mobile_app\android\app\src\main\res\raw\asistech_local_ca.crt`.
4. Compila e instala la app del teléfono con la misma dirección HTTPS:

   ```powershell
   cd mobile_app
   flutter build apk --release --dart-define=API_BASE_URL=https://192.168.1.25:5000
   ```

5. En Chrome de la tablet, abre
   `https://192.168.1.25:5000/tablet-camera`, permite el acceso a la cámara y
   deja la página abierta. En el teléfono, abre **Cámaras** y pulsa **Escanear
   con OpenCV (tablet)**. Desde allí también puedes detener el escaneo.

Después de instalar la APK, no hace falta mantener el teléfono conectado por
USB: el teléfono, la tablet y el computador que ejecuta el backend deben estar
en la misma Wi-Fi. El backend debe permanecer encendido en el computador. El
reenvío `adb reverse` es solo para probar el emulador y no se usa en teléfonos
físicos.

La página no puede activar la cámara con Chrome cerrado ni sin el permiso inicial
del usuario. El video se envía al backend local por Wi-Fi para el reconocimiento;
no uses esta configuración en una red Wi-Fi pública. Si la IP cambia, regenera
el certificado y compila la app con la nueva dirección. Si vuelves a generar la
CA local, actualiza los certificados públicos
`asistech_local_ca.crt` y `asistech_local_server.crt` de la app antes de
compilarla; nunca copies la clave privada de la CA a la app.

### 3. Ejecutar la Aplicación Móvil (Flutter)
```bash
cd ../mobile_app
flutter pub get
flutter run
```

#### Abrir en Android Studio

Abre la carpeta `mobile_app` (no la raíz del repositorio) en Android Studio y
espera a que Gradle termine la sincronización. En **Tools > Device Manager**,
inicia un emulador Android o conecta un dispositivo con la depuración USB
activada; después selecciona `lib/main.dart` y pulsa **Run**. Android Studio
requiere Flutter y Dart configurados como plugins, además del Android SDK.

La publicación requiere configurar la firma y el identificador de la
aplicación Android, la autenticación institucional de Microsoft y una URL
HTTPS pública para el backend.

---

## 🛡️ Licencia y Propiedad Intelectual
Desarrollado con fines académicos para la **Universidad Politécnica Estatal del Carchi (UPEC)**.
