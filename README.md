# 🦉 BúhoPass: Sistema Inteligente de Asistencia Móvil con Reconocimiento Facial y Asistente de Voz

[![Universidad Politécnica Estatal del Carchi](https://img.shields.io/badge/Universidad-UPEC-003366.svg)](https://www.upec.edu.ec)
[![Carrera](https://img.shields.io/badge/Carrera-Computaci%C3%B3n-0066cc.svg)](https://www.upec.edu.ec)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B.svg)](https://flutter.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8.svg)](https://opencv.org)

> **Proyecto Semestral de Aplicaciones Móviles & Visión por Computador**  
> **Docente:** Ing. Samuel Lascano  
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
**BúhoPass** es una solución integral diseñada para automatizar el control de asistencia en las aulas y laboratorios de la UPEC. El sistema combina:
1. **Motor de Visión Artificial (OpenCV + Python):** Detección biométrica facial de estudiantes en tiempo real mediante cámaras de alta velocidad.
2. **Asistente Virtual de Voz ("Carchito"):** Permite a los docentes activar la toma de lista mediante comandos verbales (*"Hola Carchito, toma asistencia"*).
3. **Aplicación Móvil Multiplataforma (Flutter / Dart):** Dashboard interactivo en tiempo real con estadísticas, respaldo de edición manual y reportería.
4. **Base de Datos Persistente (SQLite / API REST):** Gestión segura de registros, horarios y paralelos.

---

## 🏗️ Arquitectura del Sistema

```
aplicativo-movil-registro-de-camaras-/
│
├── backend_vision/             # Motor de IA, Visión por Computador y API REST
│   ├── database.py             # Base de datos SQLite y persistencia de asistencias
│   ├── face_engine.py          # Detección y reconocimiento facial en vivo (OpenCV)
│   ├── carchito_voice.py       # Asistente virtual de voz "Carchito" (TTS & STT)
│   ├── server.py               # Servidor web API y Dashboard interactivo en tiempo real
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
* Abre tu navegador en: **`http://localhost:5000`** para ver el Dashboard en tiempo real y probar la cámara o el asistente *Carchito*.

### 3. Ejecutar la Aplicación Móvil (Flutter)
```bash
cd ../mobile_app
flutter pub get
flutter run
```

---

## 🛡️ Licencia y Propiedad Intelectual
Desarrollado con fines académicos para la **Universidad Politécnica Estatal del Carchi (UPEC)**.
