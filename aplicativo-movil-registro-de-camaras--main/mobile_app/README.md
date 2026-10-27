# Aplicación móvil AsisTech

Esta es la aplicación multiplataforma del proyecto. La interfaz está
implementada en Flutter para Android e iOS: acceso docente, asistencia,
cámaras, Carchito y configuración.

La pantalla conserva la opción de **Microsoft 365** y el acceso temporal como
**Administrador** para pruebas locales. El inicio real de Microsoft 365 requiere
configurar la aplicación institucional; el acceso temporal de administrador no
es autenticación protegida y no debe exponerse a Internet.

El inicio con Microsoft está configurado para Android y valida el token de
identidad contra el tenant y el cliente de AsisTech. Solo las cuentas cuyo
correo ya esté registrado en la tabla `docentes` pueden abrir el panel docente;
una cuenta de estudiante puede autenticarse en Microsoft, pero no recibe
permisos docentes automáticamente. Para la compilación de depuración de
Android, Entra debe tener registrada la firma de depuración local. Las
compilaciones firmadas para distribución necesitan registrar también su firma
de producción.

La pestaña **Configuración** muestra la cuenta activa, permite cambiar de
cuenta o cerrar sesión y guarda la preferencia de tema claro/oscuro en el
dispositivo. El modo oscuro adapta los textos, tarjetas, campos y controles de
las pantallas de acceso, asistencia, cámaras y configuración, sin cambiar la
apariencia del tema claro. La interfaz usa tipografía Roboto y glifos Font
Awesome, familia de iconos usada por el sitio web de UPEC, con los colores
institucionales verde y amarillo. No se agregan logotipos institucionales.
Configuración también incluye **Privacidad y permisos**. El aviso disponible
es informativo y requiere que la institución responsable complete sus datos de
contacto, base legal, conservación y proceso de solicitudes antes de publicarlo
como política definitiva. Consulta [el aviso de privacidad](PRIVACY_POLICY.md).
En el primer inicio se exige aceptar ese aviso y consentir el tratamiento allí
descrito antes de habilitar el acceso; se guarda la versión y fecha localmente
en el dispositivo. Esa aceptación no se envía al backend ni sustituye la
autorización específica del estudiante (o su representante) para guardar una
foto facial, que se solicita por separado al enrolar el rostro.

El icono de la aplicación para Android e iOS se genera desde
`assets/images/asistech_logo_cropped.png`. El icono de 512 × 512 para la ficha
de Google Play está en `assets/images/asistech_play_store_icon.png`; generar los
iconos móviles requiere `dart run flutter_launcher_icons`. Esto prepara los
archivos gráficos, pero no publica la aplicación en la tienda. Android aplica
la forma de icono configurada por el launcher (círculo, cuadrado redondeado o
cuadrado); el icono adaptable usa el búho y el visto centrados para que esa
máscara no recorte el marco del logotipo completo.

## Abrir en Android Studio

Abre esta carpeta (`mobile_app`) en Android Studio, deja que Gradle sincronice
el proyecto y selecciona `lib/main.dart` como configuración de ejecución.
Necesitas los plugins Flutter y Dart, el Android SDK y un emulador Android o un
dispositivo con depuración USB activada. Ejecuta `flutter pub get` si Android
Studio no resuelve las dependencias automáticamente.

## Desarrollo

```bash
flutter pub get
flutter run
```

Para tomar asistencia por voz, selecciona la materia y di **«Hola Carchito,
toma lista de la materia de Aplicaciones Móviles»**. Carchito abre la vista
previa continua de la cámara frontal (si está disponible) y envía fotogramas
automáticamente aproximadamente una vez por segundo hasta detener el escaneo.
No se necesita capturar una foto para tomar asistencia. El backend compara los
rostros con las fotos faciales enroladas; confirma una identidad solo después
de tres fotogramas consecutivos con confianza suficiente. Los rostros
desconocidos o sin suficiente confianza no registran asistencia.

Carchito también responde a **«Hola Carchito, ayuda»** y
**«Hola Carchito, dame el reporte de asistencia»**. El reporte consulta los
registros del día para la materia seleccionada. La lista solo muestra
estudiantes inscritos en esa materia. El menú **Enrolar estudiante** los
inscribe en la materia actual y permite guardar primero sus datos académicos;
la foto facial y la autorización biométrica se pueden agregar después. Si
todavía no hay referencias
faciales, se puede probar la cámara en vivo, pero la app informa que no podrá
identificar ni registrar estudiantes. Los botones de comandos rápidos siguen
disponibles cuando el micrófono o el servicio de reconocimiento de voz del
dispositivo no funciona.

El estudiante puede tener hasta diez fotos faciales adicionales, además de su
foto de referencia original. La app captura y envía hasta cinco fotos por
solicitud; se pueden agregar más en una segunda solicitud. Las fotos anteriores
se conservan.

La base local incluye las cinco materias y los bloques del horario de Séptimo,
paralelo A mañana. Al seleccionar una materia, la franja amarilla muestra sus
días, horas y si corresponde a clase o tutoría. Los códigos COMP-704 y
COMP-705 son identificadores temporales, ya que la imagen del horario no
incluye códigos oficiales. La imagen tampoco indica aula; por eso se muestra
como no indicada en vez de conservar un aula de demostración.

La asistencia se desglosa en un punto por cada hora lectiva del horario del
día; las tutorías no generan puntos. El docente puede marcar cada hora
manualmente. Si no se registra asistencia dentro de los primeros 10 minutos
de un bloque de clase, sus horas se marcan como ausentes. Un escaneo facial
durante la primera hora del bloque marca todas sus horas; si se inicia durante
una hora posterior, marca esa hora y las siguientes, sin cambiar las horas
anteriores. Los registros de demostración conocidos se ocultan desactivando
esos estudiantes, sin borrar sus registros históricos.

La interpretación de comandos y los reportes se procesan en el backend
configurado. El audio se procesa mediante el servicio de reconocimiento de voz
disponible en el teléfono o emulador, cuyas condiciones dependen de su
proveedor; la transcripción se envía al backend. Los fotogramas del escaneo
facial también se envían al backend configurado.

La opción «Escanear con Cámara OpenCV en Vivo» usa la cámara conectada al
equipo que ejecuta el backend y se puede finalizar con «Terminar escaneo
OpenCV». El escaneo con la cámara del teléfono tiene su propio botón
«Detener escaneo».

La foto frontal y la autorización solo son necesarias cuando se añade una
referencia biométrica. Se pueden agregar hasta cinco fotos autorizadas por
estudiante, además de la referencia anterior; se conservan las referencias
anteriores al agregar nuevas. Para mejorar la comparación, captura de tres a
cinco fotos nítidas con el rostro
centrado, cambiando ligeramente el ángulo y la iluminación, sin filtros ni
otras personas en el encuadre. Si aún no se dispone de fotos, el estudiante
puede quedar inscrito sin enrolar el rostro. Las fotos y el modelo se guardan
en el backend local. Para desarrollo Android, la app usa HTTP hacia
el backend local (`10.0.2.2:5000` desde el emulador); configura HTTPS antes de
publicar.
El reconocimiento actual usa OpenCV LBPH con una foto de referencia: es un
prototipo, incluye referencias volteadas para tolerar la orientación espejo de
la cámara frontal, no incluye detección de suplantación y puede dejar rostros
sin identificar. La app anuncia por voz el resultado solo después de recibir
la confirmación del backend. Revisa manualmente los resultados y no uses una
coincidencia facial como única prueba de asistencia.

La compilación y firma de iOS requieren macOS y Xcode. Antes de publicar,
configura la firma, los identificadores de tienda, la autenticación de
Microsoft 365 y la URL HTTPS pública del backend. Consulta también la
[guía general del proyecto](../README.md).

## Configuracion del backend para iOS y Android

Para usar el backend desplegado, define su URL HTTPS al ejecutar o compilar la
app:

```bash
flutter run --dart-define=API_BASE_URL=https://tu-servidor.example
flutter build appbundle --dart-define=API_BASE_URL=https://tu-servidor.example
flutter build ios --dart-define=API_BASE_URL=https://tu-servidor.example
```

Sin esa variable, Android Emulator usa `10.0.2.2` y el simulador iOS usa
`127.0.0.1` como direcciones de desarrollo. En un dispositivo fisico, usa la
URL HTTPS accesible desde ese dispositivo. Para pruebas en una red Wi-Fi local, usa la IPv4 actual del adaptador Wi-Fi de
la computadora que ejecuta el backend (en Windows puedes verla con
`ipconfig`). Por ejemplo, en la red universitaria actual:

```bash
flutter build apk --release --dart-define=API_BASE_URL=http://172.20.237.44:5000
```

Conecta el telefono a la misma red Wi-Fi y permite el puerto TCP 5000 en el
firewall solo desde la red local. La IP puede cambiar al cambiar de red o al
reconectar la computadora; actualizala al compilar de nuevo. La compilacion de
iOS requiere macOS y Xcode.
