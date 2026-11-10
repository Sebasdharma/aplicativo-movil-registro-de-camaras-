# AsisTech Cámara J2

APK independiente para usar un Galaxy J2 SM-J200M con Android 5.1.1 como
cámara frontal remota. Requiere que el teléfono y el servidor estén en la misma
red local.

## Comportamiento

- Se inicia al encender el teléfono y muestra una pantalla de espera atenuada.
- Mantiene el Wi-Fi disponible y consulta el backend cada dos segundos.
- Abre únicamente la cámara frontal al recibir la orden de iniciar escaneo.
- Envía fotogramas al backend y muestra los resultados breves de reconocimiento.
- Cierra la cámara automáticamente después de diez minutos o al recibir una
  orden de detener.
- Solicita permiso de cámara; necesita Internet, Wi-Fi y mantener activa la
  pantalla para recibir órdenes. No usa micrófono, contactos ni almacenamiento.

## Preparar el teléfono

1. Conecta el teléfono a la misma Wi-Fi que el backend y mantenlo conectado al
   cargador.
2. En los ajustes de seguridad, activa **Fijar ventanas** (o **Fijar
   aplicaciones**) y exige el PIN para salir del modo fijado.
3. Instala el APK y ábrelo. Acepta el permiso de cámara. La app solicita fijarse
   en pantalla; confirma el aviso del sistema.
4. Comprueba que aparezca **Conectado · esperando la orden del docente**.
5. Inicia el escaneo desde la app del docente. La cámara frontal se detendrá al
   cabo de diez minutos.

El modo de fijar pantalla reduce la manipulación casual, pero no equivale a
administrar el teléfono como dispositivo corporativo. Una restricción más
fuerte mediante Android Device Owner puede requerir restablecer y volver a
configurar el teléfono.

El APK se distribuye para instalación local, no mediante Google Play. Mantiene
un nivel objetivo de Android antiguo para funcionar en Android 5.1.1 y permitir
el inicio automático en ese dispositivo.

## Dirección del backend

El APK se compila por defecto para `http://172.20.245.88:5000`. Reserva esa
dirección en el router o cambia la dirección durante la compilación para que el
teléfono siempre encuentre el servidor:

```powershell
..\mobile_app\android\gradlew.bat assembleRelease -PcameraApiBaseUrl=http://IP_DEL_SERVIDOR:5000
```

El APK de salida está en `app\build\outputs\apk\release\app-release.apk`.
