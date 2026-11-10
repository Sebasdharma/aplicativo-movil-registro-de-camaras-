# AsisTech — Registro de asistencia

Sistema académico de registro de asistencia de la Universidad Politécnica
Estatal del Carchi (UPEC). Combina un backend Python/Flask, reconocimiento
facial con OpenCV, una aplicación móvil Flutter para docentes y una aplicación
Android ligera para usar un Galaxy J2 como cámara remota.

## Componentes

- [`backend_vision/`](./aplicativo-movil-registro-de-camaras--main/backend_vision):
  API REST, reconocimiento facial, gestión de asistencia y asistente de voz.
- [`mobile_app/`](./aplicativo-movil-registro-de-camaras--main/mobile_app):
  aplicación Flutter para gestionar cámaras, cursos y reportes.
- [`j2_camera_app/`](./aplicativo-movil-registro-de-camaras--main/j2_camera_app):
  cliente Android independiente para un Galaxy J2 con Android 5.1.1.
- [Guía completa del proyecto](./aplicativo-movil-registro-de-camaras--main/README.md).

## Inicio rápido

1. Instala las dependencias del backend y ejecútalo:

   ```powershell
   cd aplicativo-movil-registro-de-camaras--main\backend_vision
   pip install -r requirements.txt
   python server.py
   ```

2. En otra terminal, inicia la app Flutter:

   ```powershell
   cd aplicativo-movil-registro-de-camaras--main\mobile_app
   flutter pub get
   flutter run
   ```

Para configurar HTTPS local, usar la cámara web de una tablet o compilar el
cliente J2, sigue la guía completa enlazada arriba y el
[README de la app J2](./aplicativo-movil-registro-de-camaras--main/j2_camera_app/README.md).

## Datos y privacidad

No agregues copias de seguridad de bases de datos, credenciales, claves
privadas ni fotografías de estudiantes al repositorio. Los archivos locales
`*.db.pre-*.bak` se excluyen mediante `.gitignore`.
