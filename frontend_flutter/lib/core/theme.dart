import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Brand palette
  static const Color bgPrimary = Color(0xFF090D16);
  static const Color bgCanvas = Color(0xFF0B132B);
  static const Color bgSurface = Color(0xFF1C2541);
  static const Color bgSurfaceElevated = Color(0xFF3A506B);

  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldLight = Color(0xFF34D399);
  static const Color emeraldDark = Color(0xFF065F46);
  static const Color emeraldGlow = Color(0x3310B981);

  static const Color cyan = Color(0xFF06B6D4);
  static const Color cyanDark = Color(0xFF0E7490);

  static const Color amber = Color(0xFFF59E0B);
  static const Color amberDark = Color(0xFF92400E);

  static const Color rose = Color(0xFFF43F5E);
  static const Color roseDark = Color(0xFF9F1239);

  static const Color borderSubtle = Color(0x1AFFFFFF);
  static const Color borderAccent = Color(0x5910B981);

  // Confidence Tiers
  static const Color goodTier = Color(0xFF10B981);
  static const Color reviewTier = Color(0xFFF59E0B);
  static const Color lowTier = Color(0xFFF43F5E);

  // Glass Panel Decorations
  static BoxDecoration glassPanel({
    Color? color,
    BorderRadius? borderRadius,
    Border? border,
  }) {
    return BoxDecoration(
      color: color ?? const Color(0xD91C2541),
      borderRadius: borderRadius ?? BorderRadius.circular(16),
      border: border ?? Border.all(color: borderSubtle, width: 1),
      boxShadow: const [
        BoxShadow(
          color: Color(0x66000000),
          blurRadius: 24,
          offset: Offset(0, 8),
        ),
      ],
    );
  }

  static BoxDecoration glassCard({
    BorderRadius? borderRadius,
    bool isHovered = false,
  }) {
    return BoxDecoration(
      color: const Color(0x403A506B),
      borderRadius: borderRadius ?? BorderRadius.circular(14),
      border: Border.all(
        color: isHovered ? borderAccent : borderSubtle,
        width: 1,
      ),
      boxShadow: isHovered
          ? const [
              BoxShadow(
                color: emeraldGlow,
                blurRadius: 18,
                offset: Offset(0, 4),
              ),
            ]
          : null,
    );
  }

  static ThemeData get darkTheme {
    final baseText = GoogleFonts.interTextTheme(ThemeData.dark().textTheme);

    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgPrimary,
      primaryColor: emerald,
      colorScheme: const ColorScheme.dark(
        primary: emerald,
        secondary: cyan,
        surface: bgSurface,
        error: rose,
      ),
      textTheme: baseText.copyWith(
        headlineLarge: GoogleFonts.playfairDisplay(
          fontSize: 32,
          fontWeight: FontWeight.bold,
          color: textPrimary,
          letterSpacing: -0.5,
        ),
        headlineMedium: GoogleFonts.playfairDisplay(
          fontSize: 24,
          fontWeight: FontWeight.bold,
          color: textPrimary,
          letterSpacing: -0.3,
        ),
        titleLarge: GoogleFonts.playfairDisplay(
          fontSize: 18,
          fontWeight: FontWeight.bold,
          color: textPrimary,
        ),
        titleMedium: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        bodyMedium: GoogleFonts.inter(
          fontSize: 13,
          color: textSecondary,
          height: 1.5,
        ),
        bodySmall: GoogleFonts.inter(
          fontSize: 11,
          color: textMuted,
        ),
        labelLarge: GoogleFonts.inter(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF0F172A),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFF334155)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFF334155)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: emerald, width: 1.5),
        ),
        hintStyle: GoogleFonts.inter(fontSize: 12, color: const Color(0xFF64748B)),
      ),
      dividerTheme: const DividerThemeData(
        color: Color(0xFF1E293B),
        thickness: 1,
      ),
    );
  }
}
