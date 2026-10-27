import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import '../core/constants/app_colors.dart';
import '../models/models.dart';
import 'privacy_and_permissions_screen.dart';

class InstitutionalSettingsView extends StatelessWidget {
  final Docente docente;
  final bool isDarkMode;
  final Future<void> Function(bool enabled) onThemeModeChanged;
  final VoidCallback onChangeAccount;
  final VoidCallback onLogout;

  const InstitutionalSettingsView({
    super.key,
    required this.docente,
    required this.isDarkMode,
    required this.onThemeModeChanged,
    required this.onChangeAccount,
    required this.onLogout,
  });

  Future<void> _changeTheme(BuildContext context, bool enabled) async {
    try {
      await onThemeModeChanged(enabled);
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

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final email =
        docente.email.isEmpty ? 'Cuenta institucional' : docente.email;

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
                        docente.nombreCompleto,
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
              isDarkMode ? FontAwesomeIcons.moon : FontAwesomeIcons.sun,
              color: colors.primary,
              size: 19,
            ),
            title: const Text('Tema oscuro'),
            subtitle: Text(isDarkMode ? 'Activado' : 'Desactivado'),
            value: isDarkMode,
            onChanged: (enabled) => _changeTheme(context, enabled),
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
                  onConfirm: onChangeAccount,
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
                  onConfirm: onLogout,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
