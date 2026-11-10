import 'dart:async';
import 'dart:convert';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:image/image.dart' as img;

import '../core/constants/app_colors.dart';
import '../services/api_service.dart';

class LiveFaceScanScreen extends StatefulWidget {
  final int materiaId;
  final VoidCallback onAttendanceRegistered;

  const LiveFaceScanScreen({
    super.key,
    required this.materiaId,
    required this.onAttendanceRegistered,
  });

  @override
  State<LiveFaceScanScreen> createState() => _LiveFaceScanScreenState();
}

class _LiveFaceScanScreenState extends State<LiveFaceScanScreen> {
  final FlutterTts _tts = FlutterTts();
  CameraController? _controller;
  String? _error;
  String _status = 'Iniciando cámara en vivo...';
  bool _processingFrame = false;
  bool _stopping = false;
  bool _voiceReady = false;
  DateTime _lastScanAt = DateTime.fromMillisecondsSinceEpoch(0);
  DateTime? _lastUnknownAnnouncementAt;
  final Set<String> _identifiedStudents = {};
  late final Future<void> _voiceInitialization;

  // Estado del HUD biométrico: 'idle', 'success', 'warning', 'danger'
  String _biometricState = 'idle';
  String _badgeText = 'Buscando Rostro';
  String _studentName = 'Ubícate frente a la cámara';
  String _statusSubtitle = 'Mirada al frente para verificar tu asistencia';
  Timer? _resetTimer;

  @override
  void initState() {
    super.initState();
    _voiceInitialization = _initializeVoice();
    _startLiveScan();
  }

  void _setBiometricState(
    String state,
    String badge,
    String name,
    String subtitle,
  ) {
    if (!mounted) return;
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

  Future<void> _initializeVoice() async {
    try {
      await _tts.setLanguage('es-ES');
      await _tts.setSpeechRate(0.48);
      await _tts.setVolume(1.0);
      _voiceReady = true;
    } catch (error) {
      debugPrint('No se pudo iniciar la voz de asistencia: $error');
    }
  }

  Future<void> _announce(String message) async {
    try {
      await _voiceInitialization;
      if (!mounted || !_voiceReady) return;
      await _tts.stop();
      await _tts.speak(message);
    } catch (error) {
      debugPrint('No se pudo anunciar el estado de asistencia: $error');
    }
  }

  Future<void> _startLiveScan() async {
    CameraController? controller;
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw StateError('El teléfono no informa ninguna cámara disponible.');
      }
      final camera = cameras.firstWhere(
        (item) => item.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      controller = CameraController(
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
        _status = 'Escaneando rostros en vivo...';
      });
      await controller.startImageStream(_processFrame);
    } catch (error) {
      await controller?.dispose();
      if (mounted) {
        setState(() {
          _error = error.toString();
          _status = 'No se pudo iniciar el escaneo';
        });
      }
    }
  }

  void _processFrame(CameraImage frame) {
    if (!mounted ||
        _processingFrame ||
        DateTime.now().difference(_lastScanAt) <
            const Duration(milliseconds: 900)) {
      return;
    }

    _processingFrame = true;
    _lastScanAt = DateTime.now();
    unawaited(_scanFrame(frame));
  }

  Future<void> _scanFrame(CameraImage frame) async {
    try {
      final jpeg = await compute(
        _cameraFrameToJpeg,
        <String, Object>{
          'width': frame.width,
          'height': frame.height,
          'format': frame.format.group.name,
          'planes': frame.planes
              .map(
                (plane) => <String, Object>{
                  'bytes': plane.bytes,
                  'bytesPerRow': plane.bytesPerRow,
                  'bytesPerPixel': plane.bytesPerPixel ?? 1,
                },
              )
              .toList(),
        },
      );
      final result = await ApiService.escanearRostroTelefono(
        materiaId: widget.materiaId,
        fotoBase64: base64Encode(jpeg),
        rotacion: _controller?.description.sensorOrientation ?? 0,
      );
      if (!mounted) return;

      final faces = result['rostros'] as List<dynamic>? ?? const [];
      final newlyIdentified = <String>[];
      var attendanceChanged = false;
      var attendanceRejected = false;
      final confirmingIdentity = faces.any(
        (item) => (item as Map<String, dynamic>)['estado'] == 'verificando',
      );
      final detectedUnknown = faces.any(
        (item) => (item as Map<String, dynamic>)['estado'] == 'desconocido',
      );
      final hasIdentified = faces.any(
        (item) => (item as Map<String, dynamic>)['estado'] == 'identificado',
      );
      final fueraDeHorario = faces.cast<Map<String, dynamic>?>().firstWhere(
            (face) => face?['estado'] == 'fuera_horario',
            orElse: () => null,
          );
      for (final item in faces) {
        final face = item as Map<String, dynamic>;
        if (face['estado'] != 'identificado' &&
            face['estado'] != 'fuera_horario') {
          continue;
        }
        final name = face['nombre']?.toString() ?? 'Estudiante';
        final code = face['codigo']?.toString() ?? name;
        if (_identifiedStudents.add(code)) newlyIdentified.add(name);
        if (face['estado'] == 'fuera_horario') {
          attendanceRejected = true;
        } else {
          attendanceChanged =
              attendanceChanged || face['registro_nuevo'] == true;
        }
      }

      if (fueraDeHorario != null) {
        final nombreFuera = fueraDeHorario['nombre']?.toString() ?? 'Estudiante';
        _setBiometricState(
          'warning',
          'Fuera de Horario',
          nombreFuera,
          '⚠ Fuera del horario de clases. Asistencia no registrada.',
        );
      } else if (hasIdentified) {
        final identifiedNames = faces
            .whereType<Map<String, dynamic>>()
            .where((face) => face['estado'] == 'identificado')
            .map((face) => face['nombre']?.toString() ?? 'Estudiante')
            .toSet()
            .join(', ');
        final sub = attendanceChanged
            ? '✓ Asistencia tomada con éxito'
            : '✓ El estudiante ya consta presente';
        _setBiometricState('success', 'Asistencia Confirmada', identifiedNames, sub);
      } else if (confirmingIdentity) {
        setState(() {
          _badgeText = 'Verificando...';
          _studentName = 'Mantén el rostro centrado';
          _statusSubtitle = 'Confirmando identidad biométrica...';
        });
      } else if (detectedUnknown) {
        _setBiometricState(
          'danger',
          'No Reconocido',
          'Rostro no reconocido',
          'Estudiante no enrolado en esta materia.',
        );
      }

      setState(() {
        _status = faces.isEmpty
            ? 'Buscando rostros...'
            : fueraDeHorario != null
                ? 'Fuera de horario'
                : hasIdentified
                    ? 'Asistencia correcta'
                    : confirmingIdentity
                        ? 'Confirmando la identidad; mantén el rostro centrado...'
                        : detectedUnknown
                            ? 'Desconocido'
                            : 'Escaneo continuo activo.';
      });
      if (hasIdentified) _lastUnknownAnnouncementAt = null;
      if (newlyIdentified.isNotEmpty && attendanceRejected) {
        unawaited(_announce('Fuera de horario'));
      } else if (newlyIdentified.isNotEmpty) {
        unawaited(_announce('Asistencia correcta'));
      } else if (detectedUnknown &&
          (_lastUnknownAnnouncementAt == null ||
              DateTime.now().difference(_lastUnknownAnnouncementAt!) >=
                  const Duration(seconds: 8))) {
        _lastUnknownAnnouncementAt = DateTime.now();
        unawaited(_announce('Desconocido'));
      }
      if (attendanceChanged) {
        widget.onAttendanceRegistered();
      }
    } catch (error) {
      if (mounted) setState(() => _status = 'Error de escaneo: $error');
    } finally {
      _processingFrame = false;
    }
  }

  Future<void> _stopScan() async {
    if (_stopping) return;
    _stopping = true;
    final controller = _controller;
    if (controller != null) {
      if (controller.value.isStreamingImages) {
        await controller.stopImageStream();
      }
      await controller.dispose();
    }
    if (mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    _resetTimer?.cancel();
    final controller = _controller;
    if (controller != null) unawaited(controller.dispose());
    unawaited(_tts.stop());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    final colors = Theme.of(context).colorScheme;

    Color reticleColor;
    Color badgeBg;
    Color badgeTextColor;

    switch (_biometricState) {
      case 'success':
        reticleColor = const Color(0xFF00E676); // Verde Neón
        badgeBg = const Color(0x3300E676);
        badgeTextColor = const Color(0xFF00E676);
        break;
      case 'warning':
        reticleColor = const Color(0xFFFF9100); // Ámbar / Naranja
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('Escaneo facial en vivo'),
        backgroundColor: AppColors.upecGreen,
        foregroundColor: Colors.white,
        leading: IconButton(
          tooltip: 'Detener escaneo',
          onPressed: _stopScan,
          icon: const Icon(Icons.close),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  ColoredBox(
                    color: Colors.black,
                    child: _error != null
                        ? Center(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Text(
                                'No se pudo iniciar la cámara.\n$_error',
                                textAlign: TextAlign.center,
                                style: const TextStyle(color: Colors.white),
                              ),
                            ),
                          )
                        : controller == null || !controller.value.isInitialized
                            ? const Center(
                                child: CircularProgressIndicator(
                                  color: AppColors.upecGreen,
                                ),
                              )
                            : FittedBox(
                                fit: BoxFit.cover,
                                child: SizedBox(
                                  width:
                                      controller.value.previewSize?.height ?? 1,
                                  height:
                                      controller.value.previewSize?.width ?? 1,
                                  child: CameraPreview(controller),
                                ),
                              ),
                  ),

                  // MIRA BIOMÉTRICA CON LÁSER
                  if (controller != null && controller.value.isInitialized)
                    Center(
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        width: 260,
                        height: 330,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(32),
                          border: Border.all(
                            color: reticleColor,
                            width: _biometricState == 'idle' ? 2.5 : 4.0,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: reticleColor.withOpacity(
                                _biometricState == 'idle' ? 0.25 : 0.6,
                              ),
                              blurRadius: _biometricState == 'idle' ? 18 : 36,
                              spreadRadius: _biometricState == 'idle' ? 2 : 6,
                            ),
                          ],
                        ),
                        child: Stack(
                          children: [
                            Positioned(
                              top: 10,
                              left: 10,
                              child: Container(
                                width: 20,
                                height: 20,
                                decoration: BoxDecoration(
                                  border: Border(
                                    top: BorderSide(
                                        color: reticleColor, width: 3),
                                    left: BorderSide(
                                        color: reticleColor, width: 3),
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
                                    bottom: BorderSide(
                                        color: reticleColor, width: 3),
                                    right: BorderSide(
                                        color: reticleColor, width: 3),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                  // TARJETA FLOTANTE CON INFORMACIÓN BIOMÉTRICA
                  Positioned(
                    bottom: 16,
                    left: 16,
                    right: 16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xE60F172A),
                        borderRadius: BorderRadius.circular(20),
                        border:
                            Border.all(color: Colors.white.withOpacity(0.12)),
                        boxShadow: const [
                          BoxShadow(
                            color: Color(0x66000000),
                            blurRadius: 24,
                            offset: Offset(0, 8),
                          ),
                        ],
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: badgeBg,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              _badgeText,
                              style: TextStyle(
                                color: badgeTextColor,
                                fontWeight: FontWeight.w800,
                                fontSize: 11,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _studentName,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            _statusSubtitle,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.75),
                              fontSize: 11,
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
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              color: colors.surface,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.radar, color: colors.primary),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _status,
                          style: TextStyle(
                            color: colors.onSurface,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Estudiantes identificados en esta sesión: '
                    '${_identifiedStudents.length}',
                    style: TextStyle(color: colors.onSurface),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Mantén el teléfono apuntando al aula. El reconocimiento '
                    'se actualiza automáticamente; no se toma una foto manual.',
                    style: TextStyle(
                      fontSize: 12,
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _stopping ? null : _stopScan,
                  icon: const Icon(Icons.stop_circle_outlined),
                  label: const Text('Detener escaneo'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

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
    if (planes.length < 3) {
      throw StateError('La cámara devolvió un formato YUV incompleto.');
    }
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

    for (var y = 0; y < height; y++) {
      final yOffset = y * yRowStride;
      final uvRow = y >> 1;
      for (var x = 0; x < width; x++) {
        final uvColumn = x >> 1;
        final luminance = yBytes[yOffset + x].toInt();
        final u = uBytes[uvRow * uRowStride + uvColumn * uPixelStride] - 128;
        final v = vBytes[uvRow * vRowStride + uvColumn * vPixelStride] - 128;
        final red = (luminance + 1.402 * v).round().clamp(0, 255);
        final green =
            (luminance - 0.344136 * u - 0.714136 * v).round().clamp(0, 255);
        final blue = (luminance + 1.772 * u).round().clamp(0, 255);
        image.setPixelRgb(x, y, red, green, blue);
      }
    }
  } else {
    throw StateError('Formato de fotograma no compatible: $format');
  }

  return Uint8List.fromList(img.encodeJpg(image, quality: 65));
}
