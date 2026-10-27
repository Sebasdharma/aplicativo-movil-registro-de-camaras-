# Aviso de privacidad de AsisTech

**Estado:** borrador informativo del proyecto. No publicar ni usar como aviso
institucional definitivo hasta que la entidad responsable lo revise y complete
los campos pendientes.

## Responsable y contacto

La institución que despliegue y opere AsisTech debe indicar aquí su nombre
legal, domicilio y el contacto responsable de privacidad:

- Entidad responsable: **pendiente de designación institucional**.
- Contacto para consultas y solicitudes: **pendiente de completar**.

La implementación no define por sí sola la entidad responsable, la base legal
del tratamiento ni el procedimiento institucional para atender solicitudes.

## Datos que procesa y para qué

- **Acceso docente:** cuenta y datos de perfil institucional necesarios para
  validar el acceso y mostrar la cuenta. Al iniciar con Microsoft, la app envía
  el token de identidad al backend configurado. El backend valida el token y
  consulta las claves públicas de Microsoft.
- **Gestión académica y asistencia:** nombre, código estudiantil, paralelo,
  materia y correo electrónico cuando se proporciona; además, estado, hora,
  materia y método de los registros de asistencia.
- **Reconocimiento facial:** si se enrola a un estudiante, la foto se envía al
  backend y se almacena como archivo en el directorio de fotos faciales de esa
  instalación. Durante el escaneo, la cámara envía fotogramas al backend para
  comparar rostros con las fotos enroladas. El flujo de escaneo procesa los
  fotogramas recibidos y no los guarda como archivos. Una coincidencia puede
  crear un registro de asistencia.
- **Comandos de voz de Carchito:** al activar esta función, el servicio de
  reconocimiento de voz disponible en el dispositivo recibe el audio y genera
  una transcripción. El proveedor del servicio puede procesar audio conforme a
  sus propias condiciones; AsisTech no garantiza que ese procesamiento sea
  exclusivamente local. La transcripción se envía al backend para interpretar
  el comando. Los comandos rápidos no requieren micrófono.

## Permisos

- **Cámara:** escaneo facial y captura de la foto de enrolamiento.
- **Micrófono y reconocimiento de voz:** comandos hablados de Carchito,
  únicamente al activar esa función.
- **Internet:** comunicación con el backend y verificación del acceso con
  Microsoft.

La app no necesita permisos de ubicación, contactos ni acceso general a
archivos para los flujos descritos. Si se deniega cámara o micrófono, las
funciones asociadas no estarán disponibles; los comandos rápidos pueden
continuar funcionando sin micrófono.

## Almacenamiento, terceros y seguridad de transporte

Los datos académicos y de asistencia se guardan en la base de datos del
backend; las fotos faciales se guardan en su directorio de datos. La entidad
que administre el servidor controla ese almacenamiento. Microsoft interviene
en la autenticación y el proveedor del sistema de voz interviene cuando se
utiliza el dictado.

La configuración de desarrollo de Android permite HTTP hacia el backend local,
que no cifra el tráfico. Antes de procesar datos reales fuera de pruebas, la
institución debe desplegar el backend detrás de HTTPS y configurar la app para
usar esa dirección. El uso de HTTP de desarrollo no debe considerarse una
configuración de producción segura.

## Conservación y derechos

La app no configura una eliminación automática ni incluye actualmente una
función para eliminar fotos o registros. La institución responsable debe
establecer y publicar los plazos de conservación, los controles de acceso, la
base legal aplicable y el procedimiento para ejercer los derechos de las
personas. No se debe enrolar una foto facial para uso real sin la autorización
y revisión institucional que correspondan. La casilla de confirmación de
enrolamiento no sustituye esa revisión ni determina por sí sola la base legal.

Para consultas, corrección o eliminación, contactar al responsable
institucional indicado arriba. Completar esos datos y definir el procedimiento
es requisito previo a publicar este aviso como política definitiva.

## Aceptación en la aplicación

Antes de iniciar sesión, AsisTech solicita confirmar que la persona leyó este
aviso y consentir el tratamiento de datos personales descrito en él. La versión
aceptada y la fecha se guardan únicamente en el dispositivo; este prototipo no
transmite ese registro al backend ni constituye una constancia institucional
verificable de consentimiento. Una nueva versión del aviso volverá a solicitar
aceptación.

La aceptación general del aviso no autoriza por sí sola la captura o
conservación de datos biométricos. Cuando se enrola una foto facial, la app
solicita una autorización específica, que debe haber sido otorgada por el
estudiante o su representante legal cuando corresponda. La institución debe
validar y documentar ese proceso antes de usar datos reales.

## Cookies

La aplicación móvil nativa no utiliza cookies propias en los flujos descritos.
Esto no determina las cookies que pudieran utilizar sitios externos abiertos
por el usuario o los proveedores externos.
