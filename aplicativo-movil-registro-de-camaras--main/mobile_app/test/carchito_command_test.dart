import 'package:flutter_test/flutter_test.dart';
import 'package:asistech_app/core/utils/carchito_command.dart';

void main() {
  group('normalizeCarchitoCommand', () {
    test('normalizes an activation phrase and command', () {
      expect(
        normalizeCarchitoCommand(
          '¡Hola Carchito, toma lista!',
          wakeWordActivated: false,
        ),
        'hola carchito toma lista',
      );
    });

    test('accepts a command after a separately recognized wake word', () {
      expect(
        normalizeCarchitoCommand(
          'Dame el reporte de asistencia',
          wakeWordActivated: true,
        ),
        'hola carchito dame el reporte de asistencia',
      );
    });

    test('uses the command after repeated wake words in one transcript', () {
      expect(
        normalizeCarchitoCommand(
          'Hola Cachito Hola Cachito toma lista',
          wakeWordActivated: false,
        ),
        'hola carchito toma lista',
      );
    });

    test('does not interpret speech before activation as a command', () {
      expect(
        normalizeCarchitoCommand(
          'toma lista',
          wakeWordActivated: false,
        ),
        isNull,
      );
    });
  });

  test('selects an available Ecuadorian Spanish locale', () {
    expect(
      selectSpanishSpeechLocale(['en_US', 'es-EC', 'es_ES']),
      'es-EC',
    );
  });

  test('falls back to Spanish when no Spanish locale is listed', () {
    expect(selectSpanishSpeechLocale(['en_US']), 'es_ES');
  });
}
