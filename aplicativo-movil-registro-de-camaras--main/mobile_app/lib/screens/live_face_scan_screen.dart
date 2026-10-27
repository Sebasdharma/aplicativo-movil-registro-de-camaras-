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

  @override
  void initState() {
    super.initState();
    _voiceInitialization = _initializeVoice();
    _startLiveScan();
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
      var attendanceRegistered = false;
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
          attendanceRegistered = attendanceRegistered ||
              face['asistencia_registrada'] == true ||
              face['registro_nuevo'] == true;
          attendanceChanged =
              attendanceChanged || face['registro_nuevo'] == true;
        }
      }

      setState(() {
        _status = faces.isEmpty
            ? 'Buscando rostros...'
            : fueraDeHorario != null
                ? 'Estudiante detectado y reconocido: '
                    '${fueraDeHorario['nombre'] ?? 'Estudiante'}. '
                    'Asistencia no registrada por horario: '
                    '${fueraDeHorario['mensaje'] ?? 'revisa el horario de clase.'}'
                : hasIdentified
                    ? attendanceRegistered
                        ? 'Reconocido: ${faces.whereType<Map<String, dynamic>>().where((face) => face['estado'] == 'identificado').map((face) => face['nombre'] ?? 'Estudiante').join(', ')}. Presente.'
                        : 'Identidad reconocida: '
                            '${newlyIdentified.isNotEmpty ? newlyIdentified.join(', ') : 'Estudiante'}.'
                    : confirmingIdentity
                        ? 'Confirmando la identidad; mantén el rostro centrado...'
                        : detectedUnknown
                            ? 'Rostro detectado, pero no hay una coincidencia confiable.'
                            : 'Escaneo continuo activo.';
      });
      if (hasIdentified) _lastUnknownAnnouncementAt = null;
      if (newlyIdentified.isNotEmpty && attendanceRejected) {
        final reason = fueraDeHorario?['mensaje']?.toString() ??
            'no hay una clase lectiva activa.';
        unawaited(
          _announce(
            'Estudiante detectado y reconocido: '
            '${newlyIdentified.join(', ')}, '
            'pero no se registró la asistencia. $reason',
          ),
        );
      } else if (newlyIdentified.isNotEmpty && attendanceChanged) {
        unawaited(
          _announce(
            'Se reconoció a ${newlyIdentified.join(', ')}. '
            'Asistencia tomada exitosamente.',
          ),
        );
      } else if (newlyIdentified.isNotEmpty && attendanceRegistered) {
        unawaited(
          _announce(
            'Se reconoció a ${newlyIdentified.join(', ')}. '
            'El estudiante ya consta presente.',
          ),
        );
      } else if (newlyIdentified.isNotEmpty) {
        unawaited(
          _announce('Se reconoció a ${newlyIdentified.join(', ')}.'),
        );
      } else if (detectedUnknown &&
          (_lastUnknownAnnouncementAt == null ||
              DateTime.now().difference(_lastUnknownAnnouncementAt!) >=
                  const Duration(seconds: 8))) {
        _lastUnknownAnnouncementAt = DateTime.now();
        unawaited(_announce('No se reconoce al estudiante'));
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
    final controller = _controller;
    if (controller != null) unawaited(controller.dispose());
    unawaited(_tts.stop());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    final colors = Theme.of(context).colorScheme;
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
              child: Center(
                child: ColoredBox(
                  color: Colors.black,
                  child: _error != null
                      ? Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(
                            'No se pudo iniciar la cámara.\n$_error',
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white),
                          ),
                        )
                      : controller == null || !controller.value.isInitialized
                          ? const CircularProgressIndicator(
                              color: AppColors.upecGreen,
                            )
                          : CameraPreview(controller),
                ),
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
