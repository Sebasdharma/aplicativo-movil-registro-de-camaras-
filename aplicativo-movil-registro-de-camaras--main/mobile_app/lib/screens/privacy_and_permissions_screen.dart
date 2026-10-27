import 'package:flutter/material.dart';

class PrivacyAndPermissionsScreen extends StatelessWidget {
  const PrivacyAndPermissionsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Privacidad y permisos')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.info_outline, color: colors.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Aviso informativo del proyecto',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Antes de publicar o usar AsisTech institucionalmente, '
                    'la entidad responsable debe completar sus datos de '
                    'contacto, definir la base legal y aprobar los plazos de '
                    'conservación y el procedimiento para atender solicitudes.',
                  ),
                ],
              ),
            ),
          ),
          _section(
            context,
            'Quién administra los datos',
            'La institución que instale y opere AsisTech debe identificar '
                'formalmente a la entidad responsable y un contacto para '
                'consultas o solicitudes sobre datos personales. Esa '
                'información aún debe completarse para esta implementación.',
          ),
          _section(
            context,
            'Aceptación y autorización facial',
            'Antes de iniciar sesión, AsisTech solicita confirmar que se leyó '
                'el aviso y consentir el tratamiento de datos personales que '
                'allí se describe. La versión y la fecha de aceptación se '
                'guardan solo en este dispositivo; no se envían al backend. '
                'Esta aceptación general no reemplaza la autorización '
                'específica del estudiante o de su representante legal para '
                'guardar una foto facial, que se solicita por separado al '
                'enrolar un rostro.',
          ),
          _section(
            context,
            'Datos y finalidades',
            'Para gestionar cursos y asistencia se procesan nombres, código '
                'estudiantil, paralelo, materia y, si se proporciona, correo '
                'electrónico. Para el acceso docente se utiliza la cuenta '
                'institucional; el token de identidad de Microsoft se envía '
                'al backend configurado para verificarlo. La verificación '
                'consulta las claves públicas de Microsoft.\n\n'
                'Si se enrola un rostro, la foto facial se envía al backend y '
                'se guarda como archivo en su carpeta de datos. Durante el '
                'escaneo, los fotogramas de la cámara se envían al backend '
                'para reconocer rostros; ese flujo de reconocimiento no los '
                'guarda como archivos. Una coincidencia puede generar un '
                'registro de asistencia con estudiante, materia, hora, estado '
                'y método.',
          ),
          _section(
            context,
            'Carchito y reconocimiento de voz',
            'Al activar un comando de voz, el micrófono y el servicio de '
                'reconocimiento de voz disponible en el dispositivo producen '
                'una transcripción. El proveedor de ese servicio puede '
                'procesar audio según sus propias condiciones; AsisTech no '
                'puede garantizar que dicho procesamiento sea exclusivamente '
                'local. La transcripción se envía al backend configurado para '
                'interpretar el comando. Los comandos rápidos se pueden usar '
                'sin activar el micrófono.',
          ),
          _section(
            context,
            'Almacenamiento, transmisión y conservación',
            'La base de datos y las fotos faciales se almacenan en el backend '
                'que opere la instalación. La app no define una fecha de '
                'borrado automático ni ofrece actualmente una función para '
                'eliminar estos datos. La institución debe fijar y comunicar '
                'un plazo de conservación y un proceso de eliminación.\n\n'
                'La configuración de desarrollo permite HTTP hacia el backend '
                'local, que no cifra el tráfico. Antes de usar datos reales '
                'fuera de un entorno de pruebas, debe desplegarse y '
                'configurarse HTTPS. Microsoft y el proveedor de voz del '
                'dispositivo son servicios externos involucrados en sus '
                'respectivos flujos.',
          ),
          Text(
            'Permisos utilizados',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          const _PermissionTile(
            icon: Icons.camera_alt_outlined,
            title: 'Cámara',
            detail: 'Solo al iniciar el escaneo facial o capturar una foto '
                'para enrolamiento. Las imágenes se envían al backend.',
          ),
          const _PermissionTile(
            icon: Icons.mic_none,
            title: 'Micrófono y reconocimiento de voz',
            detail: 'Solo cuando se activa Carchito por voz. No es necesario '
                'para los comandos rápidos.',
          ),
          const _PermissionTile(
            icon: Icons.wifi,
            title: 'Internet',
            detail: 'Necesario para comunicarse con el backend y, al iniciar '
                'con Microsoft, validar la cuenta institucional.',
          ),
          const SizedBox(height: 12),
          _section(
            context,
            'Tus consultas y solicitudes',
            'Contacta a la entidad responsable que implemente la aplicación '
                'para consultar, corregir o solicitar la eliminación de datos. '
                'El nombre y el contacto institucional deben completarse en '
                'la política publicada y en mobile_app/PRIVACY_POLICY.md.',
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  static Widget _section(BuildContext context, String title, String body) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(body, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _PermissionTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String detail;

  const _PermissionTile({
    required this.icon,
    required this.title,
    required this.detail,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
        title: Text(title),
        subtitle: Text(detail),
      ),
    );
  }
}
