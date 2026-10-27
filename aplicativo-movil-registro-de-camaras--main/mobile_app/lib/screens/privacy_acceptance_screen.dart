import 'package:flutter/material.dart';

import 'privacy_and_permissions_screen.dart';

class PrivacyAcceptanceScreen extends StatefulWidget {
  final Future<void> Function() onAccept;

  const PrivacyAcceptanceScreen({
    super.key,
    required this.onAccept,
  });

  @override
  State<PrivacyAcceptanceScreen> createState() =>
      _PrivacyAcceptanceScreenState();
}

class _PrivacyAcceptanceScreenState extends State<PrivacyAcceptanceScreen> {
  bool _checked = false;
  bool _saving = false;

  Future<void> _accept() async {
    if (!_checked || _saving) return;
    setState(() => _saving = true);
    try {
      await widget.onAccept();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo guardar la aceptación: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(
                    Icons.verified_user_outlined,
                    size: 54,
                    color: colors.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Privacidad antes de continuar',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Lee el aviso para conocer qué datos usa AsisTech y cómo '
                    'funcionan el reconocimiento facial y los comandos de voz. '
                    'Debes aceptar el aviso y consentir el tratamiento descrito '
                    'para habilitar el inicio de sesión.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => const PrivacyAndPermissionsScreen(),
                      ),
                    ),
                    icon: const Icon(Icons.policy_outlined),
                    label: const Text('Leer aviso de privacidad'),
                  ),
                  const SizedBox(height: 12),
                  Card(
                    child: CheckboxListTile(
                      key: const Key('privacy_notice_checkbox'),
                      value: _checked,
                      onChanged: _saving
                          ? null
                          : (value) =>
                              setState(() => _checked = value ?? false),
                      controlAffinity: ListTileControlAffinity.leading,
                      title: const Text(
                        'He leído el aviso y doy mi consentimiento para tratar mis datos personales según lo descrito.',
                      ),
                      subtitle: const Text(
                        'La autorización específica para guardar una foto '
                        'facial se solicita aparte al enrolar al estudiante.',
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    key: const Key('accept_privacy_notice'),
                    onPressed: _checked && !_saving ? _accept : null,
                    child: _saving
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                            ),
                          )
                        : const Text('Aceptar y continuar'),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Si no aceptas, no podrás iniciar sesión ni usar la app. '
                    'La aceptación queda guardada en este dispositivo.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: colors.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
