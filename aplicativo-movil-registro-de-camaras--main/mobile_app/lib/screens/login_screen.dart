import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_appauth/flutter_appauth.dart';
import '../core/constants/app_colors.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'institutional_dashboard_screen.dart';

const _microsoftClientId = '6a39d754-3c15-4599-b074-3925b7c7e77e';
const _microsoftTenantId = '0a42bec9-732b-45d1-977d-3b8d3ac98c2b';
const _microsoftRedirectUri =
    'msauth://com.upec.asistech/X54L9FCoo2sz3mliy68X+jdGO3I=';

class LoginScreen extends StatefulWidget {
  final Future<void> Function(bool enabled) onThemeModeChanged;

  const LoginScreen({
    super.key,
    required this.onThemeModeChanged,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _cargando = false;
  String? _estadoInicioMicrosoft;

  Future<void> _iniciarSesionMicrosoft() async {
    setState(() {
      _cargando = true;
      _estadoInicioMicrosoft = 'Conectando con Microsoft...';
    });

    try {
      final response = await const FlutterAppAuth()
          .authorizeAndExchangeCode(
            AuthorizationTokenRequest(
              _microsoftClientId,
              _microsoftRedirectUri,
              serviceConfiguration: AuthorizationServiceConfiguration(
                authorizationEndpoint:
                    'https://login.microsoftonline.com/$_microsoftTenantId/oauth2/v2.0/authorize',
                tokenEndpoint:
                    'https://login.microsoftonline.com/$_microsoftTenantId/oauth2/v2.0/token',
              ),
              scopes: const ['openid', 'profile', 'email'],
              promptValues: const ['select_account'],
            ),
          )
          .timeout(const Duration(seconds: 90));
      final idToken = response.idToken;
      if (idToken == null || idToken.isEmpty) {
        throw Exception('Microsoft no devolvió un token de identidad.');
      }

      if (mounted) {
        setState(() {
          _estadoInicioMicrosoft =
              'Microsoft respondió. Verificando la cuenta con el servidor...';
        });
      }
      final docente = await ApiService.loginMicrosoft(idToken);
      if (mounted) _abrirPanel(docente);
    } on TimeoutException {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Microsoft no respondió. Verifica que el teléfono tenga '
              'internet y vuelve a intentarlo.',
            ),
          ),
        );
      }
    } on FlutterAppAuthUserCancelledException {
      // The user closed Microsoft sign-in without selecting an account.
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo iniciar sesión: $error')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _cargando = false;
          _estadoInicioMicrosoft = null;
        });
      }
    }
  }

  Future<void> _iniciarSesionAdministrador() async {
    setState(() {
      _cargando = true;
      _estadoInicioMicrosoft = null;
    });

    try {
      final docente = await ApiService.loginAdministrador();
      if (mounted) {
        _abrirPanel(docente);
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo iniciar sesión: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _abrirPanel(Docente docente) {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => InstitutionalDashboardScreen(
          docente: docente,
          onThemeModeChanged: widget.onThemeModeChanged,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 18),
                  decoration: BoxDecoration(
                    color: colors.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: colors.outlineVariant),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 60,
                        height: 60,
                        decoration: BoxDecoration(
                          border: Border.all(color: colors.outlineVariant),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.asset(
                            'assets/images/asistech_logo_cropped.png',
                            fit: BoxFit.cover,
                            filterQuality: FilterQuality.high,
                          ),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'ASISTECH',
                              style: TextStyle(
                                color: colors.onSurface,
                                fontSize: 17,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            SizedBox(height: 3),
                            Text(
                              'Tulcán • Facultad FIACA',
                              style: TextStyle(
                                color: colors.onSurfaceVariant,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: colors.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: colors.outlineVariant),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Iniciar sesión',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: colors.onSurface,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Usa tu cuenta institucional o el acceso temporal de administrador.',
                        style: TextStyle(
                          fontSize: 12,
                          color: colors.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 18),
                      OutlinedButton(
                        onPressed: _cargando ? null : _iniciarSesionMicrosoft,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: colors.onSurface,
                          side: BorderSide(color: colors.outline),
                          padding: const EdgeInsets.symmetric(vertical: 13),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(20),
                          ),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Image(
                              image: AssetImage(
                                'assets/images/microsoft_logo.png',
                              ),
                              width: 18,
                              height: 18,
                            ),
                            SizedBox(width: 12),
                            Flexible(
                              child: Text(
                                'Iniciar sesión con Microsoft 365',
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed:
                            _cargando ? null : _iniciarSesionAdministrador,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.upecGreen,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(20),
                          ),
                          elevation: 0,
                        ),
                        child: _cargando && _estadoInicioMicrosoft == null
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: <Widget>[
                                  Icon(
                                    Icons.admin_panel_settings,
                                    size: 20,
                                  ),
                                  SizedBox(width: 12),
                                  Text(
                                    'Ingresar como Administrador',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.white,
                                    ),
                                  ),
                                ],
                              ),
                      ),
                      if (_cargando && _estadoInicioMicrosoft != null) ...[
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              height: 16,
                              width: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                            SizedBox(width: 10),
                            Flexible(
                              child: Text(
                                _estadoInicioMicrosoft!,
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 30),
                Text(
                  'Facultad FIACA • Carrera de Computación',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: colors.onSurfaceVariant,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
