import 'package:flutter/material.dart';

class AppColors {
  // Paleta Oficial Universidad Politécnica Estatal del Carchi (UPEC)
  static const Color upecGreen = Color(0xFF006837);
  static const Color upecGreenDark = Color(0xFF004D28);
  static const Color upecGreenLight = Color(0xFF008746);
  static const Color upecYellow = Color(0xFFF4B400);
  static const Color upecYellowDark = Color(0xFFCC9600);
  static const Color upecYellowLight = Color(0xFFFFF8E1);
  static const Color background = Color(0xFFF4F6F8);
  static const Color border = Color(0xFFCED4DA);
  static const Color borderDark = Color(0xFFADB5BD);
  static const Color textPrimary = Color(0xFF000000);
  static const Color textSecondary = Color(0xFF000000);

  // Colores conservados para las pantallas auxiliares existentes.
  static const Color upecNavyDark = Color(0xFF070F26);
  static const Color upecBlue = Color(0xFF003366);
  static const Color accentCyan = Color(0xFF00D2FF);
  static const Color surfaceCard = Color(0xFF0B132B);
  static const Color borderGlass = Color(0x1AFFFFFF);
  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0xFF003366), Color(0xFF0B2545)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // Sistema de Estilo Facebook / Meta
  static const Color metaBlue = Color(0xFF1877F2);
  static const Color metaBgLight = Color(0xFFF0F2F5);
  static const Color metaCardBg = Color(0xFFFFFFFF);
  static const Color metaCardBorder = Color(0xFFE4E6EB);
  static const Color metaIconBg = Color(0xFFE4E6EB);
  static const Color metaIconHover = Color(0xFFD8DADF);
  static const Color metaTextPrimary = Color(0xFF000000);
  static const Color metaTextSecondary = Color(0xFF000000);
  static const Color metaTextMuted = Color(0xFF000000);
  static const Color metaBadgeRed = Color(0xFFE41E3F);

  // Estados Biométricos de Asistencia
  static const Color statePresent = Color(0xFF005A2B);
  static const Color statePresentBg = Color(0xFFE8F5E9);
  static const Color stateAbsent = Color(0xFFCC0000);
  static const Color stateAbsentBg = Color(0xFFFFEBEE);
  static const Color stateLate = Color(0xFF8B4000);
  static const Color stateLateBg = Color(0xFFFFF8E1);
  static const Color stateJustified = Color(0xFF1877F2);
  static const Color stateJustifiedBg = Color(0xFFE7F3FF);

  // Degradados Institucionales
  static const LinearGradient upecGradient = LinearGradient(
    colors: [upecGreen, upecGreenLight],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient yellowAccentGradient = LinearGradient(
    colors: [upecYellow, Color(0xFFFFA000)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
