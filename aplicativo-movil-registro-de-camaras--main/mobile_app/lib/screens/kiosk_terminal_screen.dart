import 'dart:async';
import 'dart:convert';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image/image.dart' as img;

import '../core/constants/app_colors.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class KioskTerminalScreen extends StatefulWidget {
  const KioskTerminalScreen({super.key});

  @override
  State<KioskTerminalScreen> createState() => _KioskTerminalScreenState();
}

class _KioskTerminalScreenState extends State<KioskTerminalScreen> {
  final FlutterTts _tts = FlutterTts();
  CameraController? _controller;
  String? _error;
  bool _processingFrame = false;
  bool _voiceReady = false;
  int _selectedMateriaId = 1;
  List<Materia> _materias = [];

  // Estado del visor biométrico: 'idle', 'success', 'warning', 'danger'
  String _biometricState = 'idle';
  String _badgeText = 'Buscando Rostro';
  String _studentName = 'Ubícate frente a la cámara';
  String _statusSubtitle = 'Mirada al frente para verificar tu asistencia';
  Timer? _resetTimer;
  DateTime _lastScanAt = DateTime.fromMillisecondsSinceEpoch(0);
  String _lastAnnouncedKey = '';

  @override
  void initState() {
    super.initState();
    // Bloqueo inmersivo de pantalla (Oculta botones de navegación de Android)
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
    _initializeVoice();
    _cargarMaterias();
    _startCamera();
  }

  @override
  void dispose() {
    _resetTimer?.cancel();
    _controller?.dispose();
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    SystemChrome.setPreferredOrientations(DeviceOrientation.values);
    super.dispose();
  }

  Future<void> _initializeVoice() async {
    try {
      await _tts.setLanguage('es-ES');
      await _tts.setSpeechRate(0.5);
      await _tts.setVolume(1.0);
      _voiceReady = true;
    } catch (e) {
      debugPrint('No se pudo iniciar voz: $e');
    }
  }

  Future<void> _announce(String message) async {
    if (!mounted || !_voiceReady) return;
    try {
      await _tts.stop();
      await _tts.speak(message);
    } catch (_) {}
  }

  Future<void> _cargarMaterias() async {
    try {
      final list = await ApiService.getMaterias();
      if (mounted && list.isNotEmpty) {
        setState(() {
          _materias = list;
          _selectedMateriaId = list.first.id;
        });
      }
    } catch (e) {
      debugPrint('No se pudieron cargar materias: $e');
    }
  }

  Future<void> _seleccionarMateria() async {
    final seleccionada = await showDialog<int>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('Seleccionar Asignatura'),
        children: _materias.map((m) {
          return SimpleDialogOption(
            onPressed: () => Navigator.pop(ctx, m.id),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Text(
                '${m.nombre} (${m.nivelParalelo})',
                style: TextStyle(
                  fontWeight: m.id == _selectedMateriaId ? FontWeight.bold : FontWeight.normal,
                  color: m.id == _selectedMateriaId ? AppColors.upecGreen : null,
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
    if (seleccionada != null && mounted) {
      setState(() => _selectedMateriaId = seleccionada);
    }
  }

  Future<void> _startCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw StateError('No hay cámaras disponibles en el dispositivo.');
      }
      final camera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.yuv420,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() {
        _controller = controller;
      });
      await controller.startImageStream(_onCameraFrame);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Error al iniciar cámara: $e';
        });
      }
    }
  }

  void _onCameraFrame(CameraImage frame) {
    if (!mounted ||
        _processingFrame ||
        DateTime.now().difference(_lastScanAt) < const Duration(milliseconds: 900)) {
      return;
    }
    _processingFrame = true;
    _lastScanAt = DateTime.now();
    unawaited(_analyzeFrame(frame));
  }

  Future<void> _analyzeFrame(CameraImage frame) async {
    try {
      final jpeg = await compute(
        _cameraFrameToJpeg,
        <String, Object>{
          'width': frame.width,
          'height': frame.height,
          'format': frame.format.group.name,
          'planes': frame.planes
              .map(
                (p) => <String, Object>{
                  'bytes': p.bytes,
                  'bytesPerRow': p.bytesPerRow,
                  'bytesPerPixel': p.bytesPerPixel ?? 1,
                },
              )
              .toList(),
        },
      );

      final result = await ApiService.escanearRostroTelefono(
        materiaId: _selectedMateriaId,
        fotoBase64: base64Encode(jpeg),
        rotacion: _controller?.description.sensorOrientation ?? 0,
      );

      if (!mounted) return;
      final faces = result['rostros'] as List<dynamic>? ?? const [];
      _handleDetectionResult(faces);
    } catch (e) {
      debugPrint('Error en frame biométrico: $e');
    } finally {
      _processingFrame = false;
    }
  }

  void _handleDetectionResult(List<dynamic> faces) {
    final outsideSchedule = faces.cast<Map<String, dynamic>?>().firstWhere(
          (f) => f?['estado'] == 'fuera_horario',
          orElse: () => null,
        );
    final identified = faces
        .whereType<Map<String, dynamic>>()
        .where((f) => f['estado'] == 'identificado')
        .toList();
    final verifying = faces
        .whereType<Map<String, dynamic>>()
        .any((f) => f['estado'] == 'verificando');

    if (outsideSchedule != null) {
      final name = outsideSchedule['nombre']?.toString() ?? 'Estudiante';
      _setBiometricState(
        'warning',
        'Fuera de Horario',
        name,
        '⚠ Fuera del horario de clases. Asistencia no registrada.',
      );
      final key = 'outside:$name';
      if (key != _lastAnnouncedKey) {
        _lastAnnouncedKey = key;
        _announce('$name, te encuentras fuera del horario de clases.');
      }
    } else if (identified.isNotEmpty) {
      final names = identified.map((f) => f['nombre']?.toString() ?? 'Estudiante').toSet().join(', ');
      final isNew = identified.any((f) => f['registro_nuevo'] == true);
      final sub = isNew ? '✓ Asistencia tomada con éxito' : '✓ El estudiante ya consta presente';
      final key = 'ident:$names:$isNew';

      // MARCO VERDE + INFORMACIÓN DEL ESTUDIANTE EN HORARIO
      _setBiometricState(
        'success',
        'Asistencia Confirmada',
        names,
        sub,
      );

      if (key != _lastAnnouncedKey) {
        _lastAnnouncedKey = key;
        _announce(isNew ? '$names, asistencia registrada con éxito.' : '$names, ya estás registrado.');
      }
    } else if (verifying) {
      setState(() {
        _badgeText = 'Verificando...';
        _studentName = 'Mantén el rostro en el centro';
        _statusSubtitle = 'Confirmando identidad biométrica...';
      });
    } else if (faces.isNotEmpty) {
      _setBiometricState(
        'danger',
        'No Reconocido',
        'Rostro no reconocido',
        'El estudiante no se encuentra enrolado en esta materia.',
      );
    }
  }

  void _setBiometricState(String state, String badge, String name, String subtitle) {
    setState(() {
      _biometricState = state;
      _badgeText = badge;
      _studentName = name;
      _statusSubtitle = subtitle;
    });

    _resetTimer?.cancel();
    _resetTimer = Timer(const Duration(seconds: 4), () {
      if (mounted) {
        setState(() {
          _biometricState = 'idle';
          _badgeText = 'Buscando Rostro';
          _studentName = 'Ubícate frente a la cámara';
          _statusSubtitle = 'Mirada al frente para verificar tu asistencia';
        });
      }
    });
  }

  // DIÁLOGO CON PIN DOCENTE PARA DESBLOQUEAR Y SALIR
  Future<bool> _solicitarPinDocente() async {
    final pinController = TextEditingController();
    var pinError = false;

    final salir = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Row(
            children: [
              Icon(Icons.lock, color: AppColors.upecGreen),
              SizedBox(width: 10),
              Text('Seguridad Kiosco', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'El terminal está bloqueado. Ingresa el PIN Docente para salir del modo kiosco:',
                style: TextStyle(fontSize: 13),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: pinController,
                keyboardType: TextInputType.number,
                obscureText: true,
                maxLength: 4,
                autofocus: true,
                decoration: InputDecoration(
                  labelText: 'PIN Docente (Por defecto: 1234)',
                  errorText: pinError ? 'PIN incorrecto' : null,
                  prefixIcon: const Icon(Icons.pin),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancelar / Continuar en Kiosco'),
            ),
            FilledButton(
              onPressed: () {
                if (pinController.text.trim() == '1234') {
                  Navigator.pop(ctx, true);
                } else {
                  setDialogState(() {
                    pinError = true;
                  });
                }
              },
              child: const Text('Desbloquear'),
            ),
          ],
        ),
      ),
    );

    return salir ?? false;
  }

  @override
  Widget build(BuildContext context) {
    Color reticleColor;
    Color badgeBg;
    Color badgeTextColor;

    switch (_biometricState) {
      case 'success':
        reticleColor = const Color(0xFF00E676); // Verde brillante
        badgeBg = const Color(0x3300E676);
        badgeTextColor = const Color(0xFF00E676);
        break;
      case 'warning':
        reticleColor = const Color(0xFFFF9100); // Ámbar / Fuera de horario
        badgeBg = const Color(0x33FF9100);
        badgeTextColor = const Color(0xFFFF9100);
        break;
      case 'danger':
        reticleColor = const Color(0xFFFF1744); // Rojo
        badgeBg = const Color(0x33FF1744);
        badgeTextColor = const Color(0xFFFF1744);
        break;
      default:
        reticleColor = const Color(0xFF00D2FF); // Cian tecnológico
        badgeBg = Colors.white.withOpacity(0.12);
        badgeTextColor = Colors.white70;
    }

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final nav = Navigator.of(context);
        final salir = await _solicitarPinDocente();
        if (salir && mounted) {
          nav.pop();
        }
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: Stack(
          fit: StackFit.expand,
          children: [
            // VISTA DE CÁMARA
            if (_error != null)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    _error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white, fontSize: 16),
                  ),
                ),
              )
            else if (_controller == null || !_controller!.value.isInitialized)
              const Center(
                child: CircularProgressIndicator(color: AppColors.upecGreen),
              )
            else
              FittedBox(
                fit: BoxFit.cover,
                child: SizedBox(
                  width: _controller!.value.previewSize?.height ?? 1,
                  height: _controller!.value.previewSize?.width ?? 1,
                  child: CameraPreview(_controller!),
                ),
              ),

            // MIRA BIOMÉTRICA CON LÁSER
            Center(
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                width: 270,
                height: 350,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(32),
                  border: Border.all(
                    color: reticleColor,
                    width: _biometricState == 'idle' ? 2.5 : 4.0,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: reticleColor.withOpacity(_biometricState == 'idle' ? 0.25 : 0.6),
                      blurRadius: _biometricState == 'idle' ? 18 : 36,
                      spreadRadius: _biometricState == 'idle' ? 2 : 6,
                    ),
                  ],
                ),
                child: Stack(
                  children: [
                    // Esquinas decorativas
                    Positioned(
                      top: 10,
                      left: 10,
                      child: Container(
                        width: 20,
                        height: 20,
                        decoration: BoxDecoration(
                          border: Border(
                            top: BorderSide(color: reticleColor, width: 3),
                            left: BorderSide(color: reticleColor, width: 3),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 10,
                      right: 10,
                      child: Container(
                        width: 20,
                        height: 20,
                        decoration: BoxDecoration(
                          border: Border(
                            bottom: BorderSide(color: reticleColor, width: 3),
                            right: BorderSide(color: reticleColor, width: 3),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // BARRA SUPERIOR KIOSCO
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withOpacity(0.85),
                      Colors.transparent,
                    ],
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: AppColors.upecGreen,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Text(
                        'UPEC',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Terminal de Acceso AsisTech',
                            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                          InkWell(
                            onTap: _materias.isNotEmpty ? _seleccionarMateria : null,
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Flexible(
                                  child: Text(
                                    _materias.any((m) => m.id == _selectedMateriaId)
                                        ? '${_materias.firstWhere((m) => m.id == _selectedMateriaId).nombre} • Modo Kiosco'
                                        : 'Puerta de Aula • Modo Kiosco',
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.85),
                                      fontSize: 11,
                                      decoration: TextDecoration.underline,
                                    ),
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                const SizedBox(width: 4),
                                const Icon(Icons.arrow_drop_down, color: Colors.white70, size: 14),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Botón para salir (protegido con PIN)
                    IconButton(
                      icon: const Icon(Icons.lock_open, color: Colors.white70),
                      tooltip: 'Desbloquear y salir',
                      onPressed: () async {
                        final nav = Navigator.of(context);
                        final salir = await _solicitarPinDocente();
                        if (salir && mounted) {
                          nav.pop();
                        }
                      },
                    ),
                  ],
                ),
              ),
            ),

            // TARJETA INFERIOR FLOTANTE CON INFORMACIÓN
            Positioned(
              bottom: 24,
              left: 18,
              right: 18,
              child: Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: const Color(0xE60F172A),
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: Colors.white.withOpacity(0.12)),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x66000000),
                      blurRadius: 28,
                      offset: Offset(0, 10),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
                      decoration: BoxDecoration(
                        color: badgeBg,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        _badgeText,
                        style: TextStyle(
                          color: badgeTextColor,
                          fontWeight: FontWeight.w800,
                          fontSize: 11,
                          letterSpacing: 0.6,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _studentName,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 19,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _statusSubtitle,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.75),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Convertidor de frames de cámara a formato JPEG para la red neuronal
Uint8List _cameraFrameToJpeg(Map<String, Object> frame) {
  final width = frame['width']! as int;
  final height = frame['height']! as int;
  final format = frame['format']! as String;
  final planes = frame['planes']! as List<Map<String, Object>>;
  late img.Image image;

  if (format == 'bgra8888') {
    final plane = planes.first;
    final bytes = plane['bytes']! as Uint8List;
    image = img.Image.fromBytes(
      width: width,
      height: height,
      bytes: bytes.buffer,
      numChannels: 4,
      rowStride: plane['bytesPerRow']! as int,
      order: img.ChannelOrder.bgra,
    );
  } else if (format == 'yuv420') {
    image = img.Image(width: width, height: height, numChannels: 3);
    final yPlane = planes[0];
    final uPlane = planes[1];
    final vPlane = planes[2];
    final yBytes = yPlane['bytes']! as Uint8List;
    final uBytes = uPlane['bytes']! as Uint8List;
    final vBytes = vPlane['bytes']! as Uint8List;
    final yRowStride = yPlane['bytesPerRow']! as int;
    final uRowStride = uPlane['bytesPerRow']! as int;
    final vRowStride = vPlane['bytesPerRow']! as int;
    final uPixelStride = uPlane['bytesPerPixel']! as int;
    final vPixelStride = vPlane['bytesPerPixel']! as int;

    for (var h = 0; h < height; h++) {
      final uvh = h ~/ 2;
      for (var w = 0; w < width; w++) {
        final uvw = w ~/ 2;
        final yIndex = h * yRowStride + w;
        final uIndex = uvh * uRowStride + uvw * uPixelStride;
        final vIndex = uvh * vRowStride + uvw * vPixelStride;

        final y = yBytes[yIndex];
        final u = uBytes[uIndex] - 128;
        final v = vBytes[vIndex] - 128;

        final r = (y + 1.402 * v).round().clamp(0, 255);
        final g = (y - 0.344136 * u - 0.714136 * v).round().clamp(0, 255);
        final b = (y + 1.772 * u).round().clamp(0, 255);

        image.setPixelRgb(w, h, r, g, b);
      }
    }
  } else {
    throw UnsupportedError('Formato no soportado: $format');
  }

  return Uint8List.fromList(img.encodeJpg(image, quality: 65));
}
