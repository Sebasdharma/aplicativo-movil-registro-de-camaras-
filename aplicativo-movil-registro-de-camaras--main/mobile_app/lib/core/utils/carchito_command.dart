String? normalizeCarchitoCommand(
  String recognizedText, {
  required bool wakeWordActivated,
}) {
  var normalized = recognizedText
      .toLowerCase()
      .replaceAll('á', 'a')
      .replaceAll('é', 'e')
      .replaceAll('í', 'i')
      .replaceAll('ó', 'o')
      .replaceAll('ú', 'u')
      .replaceAll(RegExp(r'[^a-z0-9]+'), ' ')
      .trim();

  final wakeWord =
      RegExp(r'\b(?:hola|ola)\s+(?:carchito|cachito|car\s+chito)\b');
  final matches = wakeWord.allMatches(normalized);
  final match = matches.isEmpty ? null : matches.last;
  if (match != null) {
    final instruction = normalized.substring(match.end).trim();
    if (instruction.isEmpty) return 'hola carchito';
    return 'hola carchito $instruction';
  }

  if (!wakeWordActivated || normalized.isEmpty) return null;
  return 'hola carchito $normalized';
}

String selectSpanishSpeechLocale(Iterable<String> localeIds) {
  final locales = localeIds.toList();
  if (locales.isEmpty) return 'es_ES';

  String normalized(String locale) => locale.toLowerCase().replaceAll('_', '-');
  for (final preferred in ['es-ec', 'es-us', 'es-es']) {
    for (final locale in locales) {
      if (normalized(locale) == preferred) return locale;
    }
  }
  for (final locale in locales) {
    if (normalized(locale).startsWith('es-')) return locale;
  }
  return 'es_ES';
}
