import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';

import '../core/constants/app_colors.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'privacy_and_permissions_screen.dart';

class InstitutionalSettingsView extends StatefulWidget {
  final Docente docente;
  final List<Materia> materias;
  final bool isDarkMode;
  final Future<void> Function(bool enabled) onThemeModeChanged;
  final VoidCallback onChangeAccount;
  final VoidCallback onLogout;

  const InstitutionalSettingsView({
    super.key,
    required this.docente,
    required this.materias,
    required this.isDarkMode,
    required this.onThemeModeChanged,
    required this.onChangeAccount,
    required this.onLogout,
  });

  @override
  State<InstitutionalSettingsView> createState() =>
      _InstitutionalSettingsViewState();
}

class _InstitutionalSettingsViewState extends State<InstitutionalSettingsView> {
  int? _materiaReporteId;
  DateTime _fechaReporte = DateTime.now();
  bool _exportandoReporte = false;

  @override
  void initState() {
    super.initState();
    _materiaReporteId =
        widget.materias.isEmpty ? null : widget.materias.first.id;
  }

  Future<void> _changeTheme(BuildContext context, bool enabled) async {
    try {
      await widget.onThemeModeChanged(enabled);
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo guardar el tema: $error')),
      );
    }
  }

  Future<void> _confirmAction(
    BuildContext context, {
    required String title,
    required String actionLabel,
    required VoidCallback onConfirm,
  }) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: const Text(
          'Se cerrará la sesión actual y volverás a la pantalla de acceso.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: Text(actionLabel),
          ),
        ],
      ),
    );
    if (confirmed == true && context.mounted) onConfirm();
  }

  Future<void> _seleccionarFechaReporte() async {
    final fecha = await showDatePicker(
      context: context,
      initialDate: _fechaReporte,
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
    );
    if (fecha != null && mounted) {
      setState(() => _fechaReporte = fecha);
    }
  }

  Future<void> _compartirReporte() async {
    Materia? materia;
    for (final item in widget.materias) {
      if (item.id == _materiaReporteId) {
        materia = item;
        break;
      }
    }
    if (materia == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Selecciona una materia.')),
      );
      return;
    }

    setState(() => _exportandoReporte = true);
    try {
      final bytes = await ApiService.descargarReporteAsistencia(
        materiaId: materia.id,
        docenteId: widget.docente.id,
        fecha: _fechaReporte,
      );
      if (!mounted) return;
      final fecha = DateFormat('yyyy-MM-dd').format(_fechaReporte);
      final fileName = 'asistencia-${materia.codigo}-$fecha.xlsx';
      await Share.shareXFiles(
        [
          XFile.fromData(
            bytes,
            name: fileName,
            mimeType:
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          ),
        ],
        subject: 'Asistencia ${materia.nombre} - $fecha',
        text: 'Reporte diario de asistencia de ${materia.nombre}.',
        sharePositionOrigin: _sharePositionOrigin(context),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'No se pudo exportar el reporte: '
            '${error.toString().replaceFirst('Exception: ', '')}',
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _exportandoReporte = false);
    }
  }

  Rect? _sharePositionOrigin(BuildContext context) {
    if (defaultTargetPlatform != TargetPlatform.iOS &&
        defaultTargetPlatform != TargetPlatform.macOS) {
      return null;
    }
    final renderObject = context.findRenderObject();
    if (renderObject is RenderBox && renderObject.hasSize) {
      return renderObject.localToGlobal(Offset.zero) & renderObject.size;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final email = widget.docente.email.isEmpty
        ? 'Cuenta institucional'
        : widget.docente.email;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                const CircleAvatar(
                  radius: 26,
                  backgroundColor: AppColors.upecGreen,
                  child: FaIcon(
                    FontAwesomeIcons.user,
                    color: Colors.white,
                    size: 21,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.docente.nombreCompleto,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        email,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'APARIENCIA',
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: colors.primary,
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 8),
        Card(
          child: SwitchListTile(
            secondary: FaIcon(
              widget.isDarkMode ? FontAwesomeIcons.moon : FontAwesomeIcons.sun,
              color: colors.primary,
              size: 19,
            ),
            title: const Text('Tema oscuro'),
            subtitle: Text(widget.isDarkMode ? 'Activado' : 'Desactivado'),
            value: widget.isDarkMode,
            onChanged: (enabled) => _changeTheme(context, enabled),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'REPORTES',
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: colors.primary,
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 8),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Reporte diario de asistencia',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Exporta una materia por archivo, con el detalle de cada hora '
                  'y el total de estudiantes con faltas, sin duplicarlos.',
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: _materiaReporteId,
                  decoration: const InputDecoration(
                    labelText: 'Materia',
                    border: OutlineInputBorder(),
                  ),
                  items: widget.materias
                      .map(
                        (materia) => DropdownMenuItem<int>(
                          value: materia.id,
                          child: Text(
                            '${materia.codigo} - ${materia.nombre}',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      )
                      .toList(),
                  onChanged: _exportandoReporte || widget.materias.isEmpty
                      ? null
                      : (materiaId) =>
                          setState(() => _materiaReporteId = materiaId),
                ),
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed:
                      _exportandoReporte ? null : _seleccionarFechaReporte,
                  icon: const Icon(Icons.calendar_today_outlined),
                  label: Text(DateFormat('dd/MM/yyyy').format(_fechaReporte)),
                ),
                const SizedBox(height: 10),
                FilledButton.icon(
                  onPressed: _exportandoReporte || widget.materias.isEmpty
                      ? null
                      : _compartirReporte,
                  icon: _exportandoReporte
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.file_download_outlined),
                  label: Text(
                    _exportandoReporte
                        ? 'Generando reporte...'
                        : 'Generar y guardar Excel',
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'PRIVACIDAD',
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: colors.primary,
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 8),
        Card(
          child: ListTile(
            leading: FaIcon(
              FontAwesomeIcons.shieldHalved,
              color: colors.primary,
              size: 19,
            ),
            title: const Text('Privacidad y permisos'),
            subtitle: const Text('Datos utilizados y permisos de AsisTech'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const PrivacyAndPermissionsScreen(),
              ),
            ),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          'CUENTA',
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: colors.primary,
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: FaIcon(
                  FontAwesomeIcons.userGear,
                  color: colors.primary,
                  size: 19,
                ),
                title: const Text('Cambiar cuenta'),
                subtitle: const Text('Iniciar sesión con otra cuenta'),
                onTap: () => _confirmAction(
                  context,
                  title: '¿Cambiar de cuenta?',
                  actionLabel: 'Cambiar cuenta',
                  onConfirm: widget.onChangeAccount,
                ),
              ),
              Divider(height: 1, color: colors.outlineVariant),
              ListTile(
                leading: const FaIcon(
                  FontAwesomeIcons.arrowRightFromBracket,
                  color: AppColors.stateAbsent,
                  size: 19,
                ),
                title: const Text('Cerrar sesión'),
                subtitle: const Text('Salir de AsisTech en este dispositivo'),
                onTap: () => _confirmAction(
                  context,
                  title: '¿Cerrar sesión?',
                  actionLabel: 'Cerrar sesión',
                  onConfirm: widget.onLogout,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
