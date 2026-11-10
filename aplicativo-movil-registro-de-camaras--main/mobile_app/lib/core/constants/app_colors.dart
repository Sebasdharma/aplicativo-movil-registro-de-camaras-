import 'package:flutter/material.dart';

class AppColors {
  // Paleta Oficial Universidad Politécnica Estatal del Carchi (UPEC) - Moderna 2026
  static const Color upecGreen = Color(0xFF008746);
  static const Color upecGreenDark = Color(0xFF00522B);
  static const Color upecGreenLight = Color(0xFF10B981);
  static const Color upecYellow = Color(0xFFF59E0B);
  static const Color upecYellowDark = Color(0xFFD97706);
  static const Color upecYellowLight = Color(0xFFFEF3C7);
  
  // Fondos y Superficies Modernas
  static const Color background = Color(0xFFF8FAFC); // Slate 50
  static const Color surfaceCard = Color(0xFFFFFFFF);
  static const Color border = Color(0xFFE2E8F0); // Slate 200
  static const Color borderDark = Color(0xFFCBD5E1); // Slate 300
  
  // Tipografía de Alta Gama (Slate Navy en lugar de negro puro)
  static const Color textPrimary = Color(0xFF0F172A); // Slate 900
  static const Color textSecondary = Color(0xFF64748B); // Slate 500
  static const Color textMuted = Color(0xFF94A3B8); // Slate 400

  // Colores Tech y Acentos
  static const Color upecNavyDark = Color(0xFF070F26);
  static const Color upecBlue = Color(0xFF1E3A8A);
  static const Color accentCyan = Color(0xFF06B6D4);
  static const Color borderGlass = Color(0x1AFFFFFF);

  static const LinearGradient cardGradient = LinearGradient(
    colors: [Color(0xFF00522B), Color(0xFF0B2545)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // Sistema de Estilo Dashboard / Cards
  static const Color metaBlue = Color(0xFF2563EB);
  static const Color metaBgLight = Color(0xFFF1F5F9);
  static const Color metaCardBg = Color(0xFFFFFFFF);
  static const Color metaCardBorder = Color(0xFFE2E8F0);
  static const Color metaIconBg = Color(0xFFF1F5F9);
  static const Color metaIconHover = Color(0xFFE2E8F0);
  static const Color metaTextPrimary = Color(0xFF0F172A);
  static const Color metaTextSecondary = Color(0xFF475569);
  static const Color metaTextMuted = Color(0xFF94A3B8);
  static const Color metaBadgeRed = Color(0xFFEF4444);

  // Estados Biométricos de Asistencia Modernos (Pastel + Tono Fuerte)
  static const Color statePresent = Color(0xFF059669); // Emerald 600
  static const Color statePresentBg = Color(0xFFECFDF5); // Emerald 50
  static const Color stateAbsent = Color(0xFFDC2626); // Red 600
  static const Color stateAbsentBg = Color(0xFFFEF2F2); // Red 50
  static const Color stateLate = Color(0xFFD97706); // Amber 600
  static const Color stateLateBg = Color(0xFFFFFBEB); // Amber 50
  static const Color stateJustified = Color(0xFF4F46E5); // Indigo 600
  static const Color stateJustifiedBg = Color(0xFFEEF2FF); // Indigo 50

  // Degradados Institucionales
  static const LinearGradient upecGradient = LinearGradient(
    colors: [Color(0xFF008746), Color(0xFF10B981)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient yellowAccentGradient = LinearGradient(
    colors: [Color(0xFFF59E0B), Color(0xFFD97706)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
