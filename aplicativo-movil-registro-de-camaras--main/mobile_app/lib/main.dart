import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/theme/app_theme.dart';
import 'screens/login_screen.dart';
import 'screens/privacy_acceptance_screen.dart';
import 'services/api_service.dart';

const _privacyAcceptanceVersion = '2026-10-25-v1';
const _privacyAcceptanceVersionKey = 'asistech_privacy_version';
const _privacyAcceptanceDateKey = 'asistech_privacy_accepted_at';
const _localCaCertificateAsset =
    'android/app/src/main/res/raw/asistech_local_ca.crt';
const _localServerCertificateAsset =
    'android/app/src/main/res/raw/asistech_local_server.crt';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _configureLocalHttpCertificateTrust();
  var initialThemeMode = ThemeMode.light;
  var initialPrivacyAccepted = false;
  try {
    final preferences = await SharedPreferences.getInstance();
    if (preferences.getBool('asistech_dark_mode') ?? false) {
      initialThemeMode = ThemeMode.dark;
    }
    initialPrivacyAccepted =
        preferences.getString(_privacyAcceptanceVersionKey) ==
            _privacyAcceptanceVersion;
  } catch (error, stackTrace) {
    FlutterError.reportError(
      FlutterErrorDetails(
        exception: error,
        stack: stackTrace,
        library: 'AsisTech startup preferences',
        context: ErrorDescription(
          'while loading the saved theme and privacy acceptance',
        ),
      ),
    );
  }
  SystemChrome.setSystemUIOverlayStyle(
    SystemUiOverlayStyle(
      statusBarColor: const Color(0xFF004D26),
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: initialThemeMode == ThemeMode.dark
          ? const Color(0xFF101714)
          : Colors.white,
      systemNavigationBarIconBrightness: initialThemeMode == ThemeMode.dark
          ? Brightness.light
          : Brightness.dark,
    ),
  );
  runApp(
    AsisTechApp(
      initialThemeMode: initialThemeMode,
      initialPrivacyAccepted: initialPrivacyAccepted,
    ),
  );
}

Future<void> _configureLocalHttpCertificateTrust() async {
  try {
    final certificate = await rootBundle.load(_localCaCertificateAsset);
    final serverCertificatePem =
        await rootBundle.loadString(_localServerCertificateAsset);
    final serverCertificateBase64 = serverCertificatePem
        .replaceAll('-----BEGIN CERTIFICATE-----', '')
        .replaceAll('-----END CERTIFICATE-----', '')
        .replaceAll(RegExp(r'\s'), '');
    final serverCertificateDer = base64Decode(serverCertificateBase64);
    final securityContext = SecurityContext(withTrustedRoots: true)
      ..setTrustedCertificatesBytes(certificate.buffer.asUint8List());
    HttpOverrides.global = _LocalCertificateHttpOverrides(
      securityContext,
      Uri.parse(ApiService.baseUrl),
      serverCertificateDer,
    );
  } catch (error, stackTrace) {
    FlutterError.reportError(
      FlutterErrorDetails(
        exception: error,
        stack: stackTrace,
        library: 'AsisTech HTTPS configuration',
        context: ErrorDescription(
          'while configuring trust for the local backend certificate',
        ),
      ),
    );
  }
}

class _LocalCertificateHttpOverrides extends HttpOverrides {
  final SecurityContext _securityContext;
  final Uri _apiUri;
  final List<int> _serverCertificateDer;

  _LocalCertificateHttpOverrides(
    this._securityContext,
    this._apiUri,
    this._serverCertificateDer,
  );

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    return super.createHttpClient(_securityContext)
      ..badCertificateCallback = (certificate, host, port) {
        return _apiUri.scheme == 'https' &&
            host == _apiUri.host &&
            port == _apiUri.port &&
            listEquals(certificate.der, _serverCertificateDer) &&
            DateTime.now().isAfter(certificate.startValidity) &&
            DateTime.now().isBefore(certificate.endValidity);
      };
  }
}

class AsisTechApp extends StatefulWidget {
  final ThemeMode initialThemeMode;
  final bool initialPrivacyAccepted;

  const AsisTechApp({
    super.key,
    this.initialThemeMode = ThemeMode.light,
    this.initialPrivacyAccepted = false,
  });

  @override
  State<AsisTechApp> createState() => _AsisTechAppState();
}

class _AsisTechAppState extends State<AsisTechApp> {
  static const _darkModePreferenceKey = 'asistech_dark_mode';
  late ThemeMode _themeMode = widget.initialThemeMode;
  late bool _privacyAccepted = widget.initialPrivacyAccepted;

  Future<void> _acceptPrivacyNotice() async {
    final preferences = await SharedPreferences.getInstance();
    final acceptedAtSaved = await preferences.setString(
      _privacyAcceptanceDateKey,
      DateTime.now().toUtc().toIso8601String(),
    );
    final versionSaved = await preferences.setString(
      _privacyAcceptanceVersionKey,
      _privacyAcceptanceVersion,
    );
    if (!acceptedAtSaved || !versionSaved) {
      throw StateError('No se pudo guardar la aceptación del aviso.');
    }
    if (mounted) setState(() => _privacyAccepted = true);
  }

  Future<void> _setDarkMode(bool enabled) async {
    setState(() {
      _themeMode = enabled ? ThemeMode.dark : ThemeMode.light;
    });
    _updateSystemBars(enabled);

    final preferences = await SharedPreferences.getInstance();
    final saved = await preferences.setBool(_darkModePreferenceKey, enabled);
    if (!saved) {
      throw StateError('No se pudo guardar la preferencia del tema.');
    }
  }

  void _updateSystemBars(bool darkMode) {
    SystemChrome.setSystemUIOverlayStyle(
      SystemUiOverlayStyle(
        statusBarColor: const Color(0xFF004D26),
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor:
            darkMode ? const Color(0xFF101714) : Colors.white,
        systemNavigationBarIconBrightness:
            darkMode ? Brightness.light : Brightness.dark,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AsisTech - Asistencia Inteligente',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.institutionalTheme,
      darkTheme: AppTheme.institutionalDarkTheme,
      themeMode: _themeMode,
      themeAnimationDuration: Duration.zero,
      home: _privacyAccepted
          ? LoginScreen(onThemeModeChanged: _setDarkMode)
          : PrivacyAcceptanceScreen(onAccept: _acceptPrivacyNotice),
    );
  }
}
