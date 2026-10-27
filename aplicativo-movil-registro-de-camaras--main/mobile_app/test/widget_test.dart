import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:font_awesome_flutter/font_awesome_flutter.dart';

import 'package:asistech_app/main.dart';
import 'package:asistech_app/core/constants/app_colors.dart';
import 'package:asistech_app/core/theme/app_theme.dart';
import 'package:asistech_app/models/models.dart';
import 'package:asistech_app/screens/institutional_settings_view.dart';
import 'package:asistech_app/screens/privacy_acceptance_screen.dart';

void main() {
  testWidgets('opens the Asistech institutional login', (tester) async {
    await tester.pumpWidget(
      const AsisTechApp(initialPrivacyAccepted: true),
    );

    expect(find.text('ASISTECH'), findsOneWidget);
    expect(find.text('Iniciar sesión'), findsOneWidget);
    expect(find.text('Iniciar sesión con Microsoft 365'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Image &&
            widget.image is AssetImage &&
            (widget.image as AssetImage).assetName ==
                'assets/images/asistech_logo_cropped.png',
      ),
      findsOneWidget,
    );
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Image &&
            widget.image is AssetImage &&
            (widget.image as AssetImage).assetName ==
                'assets/images/microsoft_logo.png',
      ),
      findsOneWidget,
    );
    expect(find.text('Ingresar como Administrador'), findsOneWidget);
  });

  testWidgets('starts in dark mode without a theme transition error',
      (tester) async {
    await tester.pumpWidget(
      const AsisTechApp(
        initialThemeMode: ThemeMode.dark,
        initialPrivacyAccepted: true,
      ),
    );
    await tester.pumpAndSettle();

    expect(Theme.of(tester.element(find.text('Iniciar sesión'))).brightness,
        Brightness.dark);
    expect(tester.takeException(), isNull);
  });

  testWidgets('requires accepting privacy notice before login', (tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const AsisTechApp());

    expect(find.byType(PrivacyAcceptanceScreen), findsOneWidget);
    expect(find.text('Iniciar sesión con Microsoft 365'), findsNothing);
    expect(
      tester
          .widget<FilledButton>(
            find.byKey(const Key('accept_privacy_notice')),
          )
          .onPressed,
      isNull,
    );

    await tester.tap(find.byKey(const Key('privacy_notice_checkbox')));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<FilledButton>(
            find.byKey(const Key('accept_privacy_notice')),
          )
          .onPressed,
      isNotNull,
    );

    await tester.ensureVisible(find.byKey(const Key('accept_privacy_notice')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('accept_privacy_notice')));
    await tester.pumpAndSettle();

    expect(find.text('Iniciar sesión con Microsoft 365'), findsOneWidget);
    final preferences = await SharedPreferences.getInstance();
    expect(preferences.getString('asistech_privacy_version'), '2026-10-25-v1');
    expect(preferences.getString('asistech_privacy_accepted_at'), isNotNull);
  });

  testWidgets('settings exposes theme and account actions without EVA',
      (tester) async {
    var darkModeEnabled = false;
    final docente = Docente(
      id: 2,
      email: 'jordy.lema@upec.edu.ec',
      nombreCompleto: 'Jordy Lema',
      cedula: '',
      facultad: '',
      carrera: '',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: InstitutionalSettingsView(
          docente: docente,
          isDarkMode: false,
          onThemeModeChanged: (enabled) async {
            darkModeEnabled = enabled;
          },
          onChangeAccount: () {},
          onLogout: () {},
        ),
      ),
    );

    expect(find.text('Jordy Lema'), findsOneWidget);
    expect(find.text('Cambiar cuenta'), findsOneWidget);
    expect(find.text('Cerrar sesión'), findsOneWidget);
    expect(find.text('Privacidad y permisos'), findsOneWidget);
    expect(find.text('Portal EVA'), findsNothing);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is FaIcon &&
            widget.icon?.codePoint == FontAwesomeIcons.userGear.codePoint,
      ),
      findsOneWidget,
    );
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is FaIcon &&
            widget.icon?.codePoint ==
                FontAwesomeIcons.arrowRightFromBracket.codePoint,
      ),
      findsOneWidget,
    );

    await tester.tap(find.byType(SwitchListTile));
    await tester.pumpAndSettle();

    expect(darkModeEnabled, isTrue);
  });

  testWidgets('privacy screen explains data use and required permissions',
      (tester) async {
    final docente = Docente(
      id: 2,
      email: 'jordy.lema@upec.edu.ec',
      nombreCompleto: 'Jordy Lema',
      cedula: '',
      facultad: '',
      carrera: '',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: InstitutionalSettingsView(
          docente: docente,
          isDarkMode: false,
          onThemeModeChanged: (_) async {},
          onChangeAccount: () {},
          onLogout: () {},
        ),
      ),
    );

    await tester.tap(find.text('Privacidad y permisos'));
    await tester.pumpAndSettle();

    expect(find.text('Aceptación y autorización facial'), findsOneWidget);
    expect(find.text('Quién administra los datos'), findsOneWidget);
  });

  testWidgets('dark settings theme uses readable text colors', (tester) async {
    final docente = Docente(
      id: 2,
      email: 'jordy.lema@upec.edu.ec',
      nombreCompleto: 'Jordy Lema',
      cedula: '',
      facultad: '',
      carrera: '',
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.institutionalTheme,
        darkTheme: AppTheme.institutionalDarkTheme,
        themeMode: ThemeMode.dark,
        home: InstitutionalSettingsView(
          docente: docente,
          isDarkMode: true,
          onThemeModeChanged: (_) async {},
          onChangeAccount: () {},
          onLogout: () {},
        ),
      ),
    );

    final name = tester.widget<Text>(find.text('Jordy Lema'));
    final accountHeading = tester.widget<Text>(find.text('CUENTA'));
    expect(name.style?.color, const Color(0xFFF1F5F2));
    expect(accountHeading.style?.color, const Color(0xFF72C99A));
  });

  test('light theme retains its white surfaces and dark text', () {
    final lightTheme = AppTheme.institutionalTheme;

    expect(lightTheme.colorScheme.surface, Colors.white);
    expect(lightTheme.colorScheme.onSurface, Colors.black);
    expect(lightTheme.colorScheme.surfaceContainerHighest, Colors.white);
    expect(lightTheme.textTheme.bodyMedium?.fontFamily, 'Roboto');
    expect(lightTheme.iconTheme.color, AppColors.upecGreen);
    expect(lightTheme.bottomNavigationBarTheme.selectedItemColor,
        AppColors.upecGreen);
    expect(lightTheme.bottomNavigationBarTheme.unselectedItemColor,
        AppColors.borderDark);
  });

  test('dark theme uses Roboto and UPEC green for its icons', () {
    final darkTheme = AppTheme.institutionalDarkTheme;

    expect(darkTheme.textTheme.bodyMedium?.fontFamily, 'Roboto');
    expect(darkTheme.iconTheme.color, const Color(0xFF72C99A));
    expect(darkTheme.bottomNavigationBarTheme.selectedItemColor,
        const Color(0xFF72C99A));
  });
}
