import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

import '../core/constants/app_colors.dart';
import '../services/api_service.dart';

class InstitutionalCarchitoView extends StatefulWidget {
  final int materiaId;
  final VoidCallback onCommandCompleted;

  const InstitutionalCarchitoView({
    super.key,
    required this.materiaId,
    required this.onCommandCompleted,
  });

  @override
  State<InstitutionalCarchitoView> createState() =>
      _InstitutionalCarchitoViewState();
}

class _InstitutionalCarchitoViewState extends State<InstitutionalCarchitoView> {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _flutterTts = FlutterTts();
  bool _speechReady = false;
  bool _listening = false;
  bool _processing = false;
  String _status = 'Presione para hablar o usar comandos de voz';
  String _message =
      '¡Saludos colega docente! Soy Carchito, su asistente en el aula de la UPEC. ¿Desea tomar asistencia ahora o conocer el reporte de ausencias?';

  @override
  void initState() {
    super.initState();
    _initializeSpeech();
    _initTts();
  }

  Future<void> _initTts() async {
    await _flutterTts.setLanguage("es-ES");
    await _flutterTts.setSpeechRate(0.5);
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);
  }

  Future<void> _speak(String text) async {
    try {
      await _flutterTts.speak(text);
    } catch (_) {}
  }

  @override
  void dispose() {
    _speech.stop();
    _flutterTts.stop();
    super.dispose();
  }

  Future<void> _initializeSpeech() async {
    try {
      final available = await _speech.initialize(
        onStatus: (status) {
          if (mounted && status == 'notListening') {
            setState(() => _listening = false);
          }
        },
        onError: (error) {
          if (mounted) {
            setState(() {
              _listening = false;
              _status =
                  'Micrófono no disponible en emulador (use comandos abajo)';
            });
          }
        },
      );
      if (mounted) setState(() => _speechReady = available);
    } catch (error) {
      if (mounted) {
        setState(() => _status = 'Reconocimiento de voz simulado activo');
      }
    }
  }

  Future<void> _toggleMicrophone() async {
    if (_processing) return;

    // Si no está listo el speech (ej. en emulador), abrir diálogo para simular comandos de voz
    if (!_speechReady) {
      _mostrarDialogoComandoVoz();
      return;
    }

    if (_listening) {
      await _speech.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }

    setState(() {
      _listening = true;
      _status = 'Escuchando voz del docente...';
    });
    await _speech.listen(
      listenOptions: stt.SpeechListenOptions(localeId: 'es_ES'),
      onResult: (result) {
        if (result.finalResult && result.recognizedWords.trim().isNotEmpty) {
          _sendCommand(result.recognizedWords.trim());
        }
      },
    );
  }

  void _mostrarDialogoComandoVoz() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Asistente de Voz Carchito (Simulador IA)',
                style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                    color: Colors.black),
              ),
              const SizedBox(height: 6),
              const Text(
                'Seleccione un comando de voz para que Carchito lo ejecute y responda en voz alta:',
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
              const SizedBox(height: 14),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _sendCommand('Hola Carchito, toma la asistencia del aula');
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.upecGreen,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20)),
                ),
                icon: const Icon(Icons.mic, color: Colors.white),
                label: const Text('🗣️ "Hola Carchito, toma la asistencia"',
                    style: TextStyle(
                        color: Colors.white, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.pop(context);
                  _sendCommand('Hola Carchito, reporte de asistencia');
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.upecYellow,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20)),
                ),
                icon: const Icon(Icons.bar_chart, color: Colors.black),
                label: const Text('📊 "Carchito, dame el reporte de ausencias"',
                    style: TextStyle(
                        color: Colors.black, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _sendCommand(String command) async {
    if (!mounted) return;
    setState(() {
      _listening = false;
      _processing = true;
      _message = 'Procesando: "$command"...';
      _status = 'Procesando comando';
    });
    try {
      final result = await ApiService.enviarComandoCarchito(
        command,
        materiaId: widget.materiaId,
      );
      if (!mounted) return;
      final respuesta =
          result['mensaje']?.toString() ?? 'Carchito procesó el comando.';
      setState(() {
        _message = respuesta;
        _status = 'Comando procesado con éxito';
      });
      await _speak(respuesta);
      widget.onCommandCompleted();
    } catch (error) {
      if (mounted) {
        setState(() {
          _message = 'No se pudo enviar el comando a Carchito: $error';
          _status = 'Error de conexión';
        });
        await _speak('Ocurrió un error de conexión.');
      }
    } finally {
      if (mounted) setState(() => _processing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(14, 16, 14, 15),
            decoration: BoxDecoration(
              color: AppColors.upecGreen,
              border: Border.all(color: AppColors.upecYellow, width: 2),
            ),
            child: Column(
              children: [
                Container(
                  width: 90,
                  height: 90,
                  padding: const EdgeInsets.all(3),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(color: AppColors.upecYellow, width: 3),
                  ),
                  child: ClipOval(
                    child: Image.asset(
                      'assets/images/carchito.png',
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Icon(
                        Icons.support_agent,
                        color: AppColors.upecGreen,
                        size: 48,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Carchito Virtual UPEC',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                const Text(
                  'Mascota & Asistente Institucional de Aula • Tulcán',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: AppColors.upecYellow,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(vertical: 14),
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: AppColors.background,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: Text(
              _message,
              style: const TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
          Semantics(
            button: true,
            label: _listening ? 'Detener micrófono' : 'Hablar a Carchito',
            child: InkWell(
              onTap: _toggleMicrophone,
              customBorder: const CircleBorder(),
              child: Container(
                width: 62,
                height: 62,
                decoration: BoxDecoration(
                  color:
                      _listening ? AppColors.stateAbsent : AppColors.upecGreen,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.upecYellow, width: 3),
                ),
                child: _processing
                    ? const Padding(
                        padding: EdgeInsets.all(18),
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : Icon(
                        _listening ? Icons.stop : Icons.mic,
                        color: Colors.white,
                        size: 28,
                      ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _status,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 11,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 18),
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'COMANDOS DE VOZ DEL AULA:',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const SizedBox(height: 6),
          _CommandButton(
            label: '🗣️  "Hola Carchito, toma la asistencia"',
            onPressed: _processing
                ? null
                : () => _sendCommand(
                      'Hola Carchito, toma la asistencia del aula',
                    ),
          ),
          const SizedBox(height: 6),
          _CommandButton(
            label: '📊  "Carchito, dame el reporte de ausencias"',
            onPressed: _processing
                ? null
                : () => _sendCommand('Carchito, reporte de asistencia'),
          ),
        ],
      ),
    );
  }
}

class _CommandButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;

  const _CommandButton({required this.label, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.textPrimary,
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          side: const BorderSide(color: AppColors.border),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
