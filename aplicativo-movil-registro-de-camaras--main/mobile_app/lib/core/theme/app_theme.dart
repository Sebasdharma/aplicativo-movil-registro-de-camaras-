import 'package:flutter/material.dart';
import '../constants/app_colors.dart';

class AppTheme {
  static ThemeData get institutionalTheme {
    final lightTextTheme = ThemeData.light(useMaterial3: true).textTheme.apply(
          fontFamily: 'Roboto',
          bodyColor: AppColors.textPrimary,
          displayColor: AppColors.textPrimary,
        );

    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Roboto',
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.background,
      textTheme: lightTextTheme,
      iconTheme: const IconThemeData(
        color: AppColors.upecGreen,
        size: 20,
      ),
      colorScheme: const ColorScheme.light(
        primary: AppColors.upecGreen,
        secondary: AppColors.upecYellow,
        surface: Colors.white,
        onPrimary: Colors.white,
        onSurface: AppColors.textPrimary,
        onSurfaceVariant: AppColors.textSecondary,
        outline: AppColors.borderDark,
        outlineVariant: AppColors.border,
        surfaceContainerHighest: Colors.white,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.upecGreen,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero),
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: 'Roboto',
          color: Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.bold,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.border),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.upecGreen,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto',
            fontWeight: FontWeight.bold,
            fontSize: 13,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.white,
        selectedItemColor: AppColors.upecGreen,
        unselectedItemColor: AppColors.borderDark,
        type: BottomNavigationBarType.fixed,
        elevation: 2,
        selectedLabelStyle: TextStyle(
          fontFamily: 'Roboto',
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
        unselectedLabelStyle: TextStyle(
          fontFamily: 'Roboto',
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  static ThemeData get institutionalDarkTheme {
    const background = Color(0xFF101714);
    const surface = Color(0xFF1B2420);
    const border = Color(0xFF35443C);
    const textPrimary = Color(0xFFF1F5F2);
    const textSecondary = Color(0xFFB8C4BD);
    final darkTextTheme = ThemeData.dark(useMaterial3: true).textTheme.apply(
          fontFamily: 'Roboto',
          bodyColor: textPrimary,
          displayColor: textPrimary,
        );

    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Roboto',
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      colorScheme: const ColorScheme.dark(
        primary: Color(0xFF72C99A),
        secondary: AppColors.upecYellow,
        surface: surface,
        onPrimary: Color(0xFF062012),
        onSurface: textPrimary,
      ),
      textTheme: darkTextTheme,
      iconTheme: const IconThemeData(
        color: Color(0xFF72C99A),
        size: 20,
      ),
      listTileTheme: const ListTileThemeData(
        textColor: textPrimary,
        iconColor: textSecondary,
        subtitleTextStyle: TextStyle(color: textSecondary),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.upecGreenDark,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.zero),
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: 'Roboto',
          color: Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.bold,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: border),
        ),
      ),
      dialogTheme: const DialogThemeData(
        backgroundColor: surface,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
        contentTextStyle: TextStyle(color: textSecondary),
      ),
      dividerTheme: const DividerThemeData(color: border),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: Color(0xFF303A35),
        contentTextStyle: TextStyle(color: textPrimary),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: const Color(0xFF72C99A)),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: textPrimary,
          side: const BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        hintStyle: const TextStyle(color: textSecondary),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: border),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? const Color(0xFF72C99A)
              : textSecondary,
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: Color(0xFF72C99A),
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        elevation: 2,
      ),
    );
  }
}
