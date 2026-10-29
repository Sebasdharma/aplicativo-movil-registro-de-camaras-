import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/constants/app_colors.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'live_face_scan_screen.dart';

class InstitutionalCameraView extends StatefulWidget {
  final int materiaId;
  final bool autoStartPhoneCamera;
  final VoidCallback? onAttendanceRegistered;

  const InstitutionalCameraView({
    super.key,
    required this.materiaId,
    this.autoStartPhoneCamera = false,
    this.onAttendanceRegistered,
  });

  @override
  State<InstitutionalCameraView> createState() =>
      _InstitutionalCameraViewState();
}

class _InstitutionalCameraViewState extends State<InstitutionalCameraView> {
  final FlutterTts _remoteResultTts = FlutterTts();
  List<DispositivoIoT> _devices = [];
  bool _loading = true;
  bool _startingCamera = false;
  bool _opencvScanActive = false;
  bool _autoStartHandled = false;
  bool _tabletCameraEnabled = false;
  bool _tabletRoleChecked = false;
  bool _pollingTabletCommand = false;
  bool _remoteScanRouteOpen = false;
  String? _tabletCameraId;
  String? _tabletConnectionError;
  List<Map<String, dynamic>> _remoteTablets = [];
  final Map<String, String> _lastRemoteSpokenEvents = {};
  Timer? _tabletHeartbeatTimer;
  Timer? _remoteTabletsTimer;
  late final Future<void> _remoteVoiceInitialization;

  @override
  void initState() {
    super.initState();
    _remoteVoiceInitialization = _initializeRemoteVoice();
    _loadDevices();
    _refreshRemoteTablets();
    _remoteTabletsTimer = Timer.periodic(
      const Duration(seconds: 3),
      (_) => _refreshRemoteTablets(),
    );
    if (widget.autoStartPhoneCamera) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !_autoStartHandled) {
          _autoStartHandled = true;
          _scanWithPhoneCamera();
        }
      });
    }
  }

  @override
  void dispose() {
    _tabletHeartbeatTimer?.cancel();
    _remoteTabletsTimer?.cancel();
    unawaited(_remoteResultTts.stop());
    super.dispose();
  }

  Future<void> _initializeRemoteVoice() async {
    try {
      await _remoteResultTts.setLanguage('es-ES');
      await _remoteResultTts.setSpeechRate(0.48);
      await _remoteResultTts.setVolume(1.0);
    } catch (error) {
      debugPrint('No se pudo preparar la voz de resultados OpenCV: $error');
    }
  }

  Future<void> _announceRemoteResult(String message) async {
    try {
      await _remoteVoiceInitialization;
      if (!mounted) return;
      await _remoteResultTts.stop();
      await _remoteResultTts.speak(message);
    } catch (error) {
      debugPrint(
          'No se pudo anunciar el resultado de la cámara remota: $error');
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_tabletRoleChecked) return;
    _tabletRoleChecked = true;
    final isTablet = MediaQuery.sizeOf(context).shortestSide >= 600;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(_initializeTabletCamera(isTablet));
    });
  }

  Future<void> _initializeTabletCamera(bool isTablet) async {
    final preferences = await SharedPreferences.getInstance();
    final enabled = isTablet ||
        (preferences.getBool('asistech_tablet_camera_enabled') ?? false);
    if (!enabled || !mounted) return;
    final id = preferences.getString('asistech_tablet_camera_id') ??
        _newTabletCameraId();
    await preferences.setBool('asistech_tablet_camera_enabled', true);
    await preferences.setString('asistech_tablet_camera_id', id);
    if (!mounted) return;
    setState(() {
      _tabletCameraId = id;
      _tabletCameraEnabled = true;
    });
    _startTabletHeartbeat();
  }

  String _newTabletCameraId() {
    final random = Random.secure();
    return List<int>.generate(16, (_) => random.nextInt(256))
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join();
  }

  void _startTabletHeartbeat() {
    _tabletHeartbeatTimer?.cancel();
    unawaited(_pollTabletCommand());
    _tabletHeartbeatTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _pollTabletCommand(),
    );
  }

  Future<void> _pollTabletCommand() async {
    final id = _tabletCameraId;
    if (!_tabletCameraEnabled || id == null || _pollingTabletCommand) return;
    _pollingTabletCommand = true;
    try {
      final response = await ApiService.heartbeatTabletCamera(
        tabletId: id,
        name: 'Tablet AsisTech',
        active: _remoteScanRouteOpen,
      );
      if (mounted && _tabletConnectionError != null) {
        setState(() => _tabletConnectionError = null);
      }
      final command = response['command'] as Map<String, dynamic>?;
      if (command == null || !mounted) return;
      if (command['action'] == 'iniciar' && !_remoteScanRouteOpen) {
        final materiaId = command['materia_id'];
        if (materiaId is int) {
          unawaited(_scanWithPhoneCamera(
            materiaId: materiaId,
            remotelyStarted: true,
          ));
        }
      } else if (command['action'] == 'detener' &&
          _remoteScanRouteOpen &&
          Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
    } catch (error) {
      if (mounted && _tabletConnectionError == null) {
        setState(() => _tabletConnectionError = error.toString());
      }
    } finally {
      _pollingTabletCommand = false;
    }
  }

  Future<void> _refreshRemoteTablets() async {
    try {
      final devices = await ApiService.getTabletCameras();
      if (!mounted) return;
      for (final tablet in devices) {
        final tabletId = tablet['tablet_id'] as String?;
        final result = tablet['resultado'];
        if (tabletId == null || result is! Map<String, dynamic>) continue;
        final eventId = result['evento_id']?.toString();
        final message = result['mensaje']?.toString();
        if (eventId == null ||
            message == null ||
            message.isEmpty ||
            _lastRemoteSpokenEvents[tabletId] == eventId) {
          continue;
        }
        _lastRemoteSpokenEvents[tabletId] = eventId;
        unawaited(_announceRemoteResult(message));
      }
      if (mounted) setState(() => _remoteTablets = devices);
    } catch (error) {
      debugPrint('No se pudieron consultar las tablets: $error');
    }
  }

  Future<void> _commandRemoteTablet(
    Map<String, dynamic> tablet,
    String action,
  ) async {
    if (_startingCamera) return;
    final tabletId = tablet['tablet_id'] as String?;
    if (tabletId == null) return;
    setState(() => _startingCamera = true);
    try {
      final response = await ApiService.commandTabletCamera(
        tabletId: tabletId,
        action: action,
        materiaId: widget.materiaId,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            response['mensaje']?.toString() ?? 'Se envió la orden a la tablet.',
          ),
        ),
      );
      await _refreshRemoteTablets();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo controlar la tablet: $error')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _startingCamera = false);
      }
    }
  }

  @override
  void didUpdateWidget(covariant InstitutionalCameraView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!oldWidget.autoStartPhoneCamera && widget.autoStartPhoneCamera) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _scanWithPhoneCamera();
      });
    }
  }

  Future<void> _loadDevices() async {
    setState(() => _loading = true);
    try {
      final devices = await ApiService.getDispositivosIoT();
      if (mounted) setState(() => _devices = devices);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudieron cargar las cámaras: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _startScan([DispositivoIoT? device]) async {
    if (_startingCamera) return;
    setState(() => _startingCamera = true);
    try {
      final result = await ApiService.iniciarEscaneoCamara(
        materiaId: widget.materiaId,
        dispositivoId: device?.id,
      );
      if (!mounted) return;
      setState(() {
        _opencvScanActive = true;
        if (device != null) device.estado = 'Transmitiendo';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['mensaje']?.toString() ?? 'Escaneo de cámara iniciado.',
          ),
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo iniciar la cámara: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _startingCamera = false);
    }
  }

  Future<void> _startOpenCvScan() async {
    final remoteTablets = _remoteTablets
        .where((tablet) => tablet['tablet_id'] != _tabletCameraId)
        .toList();
    if (remoteTablets.isEmpty) {
      await _startScan();
      return;
    }

    Map<String, dynamic>? selectedTablet;
    if (remoteTablets.length == 1) {
      selectedTablet = remoteTablets.single;
    } else {
      selectedTablet = await showDialog<Map<String, dynamic>>(
        context: context,
        builder: (dialogContext) => SimpleDialog(
          title: const Text('Selecciona la tablet cámara'),
          children: [
            for (final tablet in remoteTablets)
              SimpleDialogOption(
                onPressed: () => Navigator.pop(dialogContext, tablet),
                child: Text(tablet['nombre'] as String? ?? 'Tablet Android'),
              ),
          ],
        ),
      );
    }
    if (selectedTablet == null || !mounted) return;
    final action =
        selectedTablet['estado'] == 'Transmitiendo' ? 'detener' : 'iniciar';
    await _commandRemoteTablet(selectedTablet, action);
  }

  Future<void> _stopOpenCvScan() async {
    if (_startingCamera) return;
    setState(() => _startingCamera = true);
    try {
      final result = await ApiService.detenerEscaneoCamara();
      if (!mounted) return;
      setState(() {
        _opencvScanActive = false;
        for (final device in _devices) {
          if (device.estado == 'Transmitiendo') device.estado = 'Conectado';
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['mensaje']?.toString() ?? 'Escaneo OpenCV terminado.',
          ),
        ),
      );
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo detener el escaneo: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _startingCamera = false);
    }
  }

  Future<void> _scanWithPhoneCamera({
    int? materiaId,
    bool remotelyStarted = false,
  }) async {
    if (_startingCamera && !remotelyStarted) return;
    if (remotelyStarted) _remoteScanRouteOpen = true;
    try {
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => LiveFaceScanScreen(
            materiaId: materiaId ?? widget.materiaId,
            onAttendanceRegistered: () => widget.onAttendanceRegistered?.call(),
          ),
        ),
      );
    } finally {
      if (remotelyStarted) _remoteScanRouteOpen = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final remoteScanActive = _remoteTablets.any(
      (tablet) =>
          tablet['tablet_id'] != _tabletCameraId &&
          tablet['estado'] == 'Transmitiendo',
    );
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.upecGreen),
      );
    }
    return RefreshIndicator(
      color: AppColors.upecGreen,
      onRefresh: _loadDevices,
      child: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          Container(
            padding: const EdgeInsets.only(bottom: 7),
            decoration: const BoxDecoration(
              border: Border(
                bottom: BorderSide(color: AppColors.upecYellow, width: 2),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.videocam,
                  color: AppColors.upecGreen,
                  size: 18,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Dispositivos IoT en Aula',
                    style: TextStyle(
                      color: colors.onSurface,
                      fontSize: 14,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                  color: AppColors.upecGreen,
                  child: Text(
                    _opencvScanActive ? 'ESCANEO EN VIVO' : 'OPENCV ACTIVO',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 8,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 10),
          if (_tabletCameraEnabled && _tabletConnectionError != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                'Cámara sin conexión: $_tabletConnectionError',
                style: TextStyle(color: colors.error, fontSize: 10),
              ),
            ),
          const SizedBox(height: 10),
          if (_remoteTablets
              .any((tablet) => tablet['tablet_id'] != _tabletCameraId)) ...[
            Text(
              'Tablets disponibles para OpenCV',
              style: TextStyle(
                color: colors.onSurface,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 6),
          ],
          for (final tablet in _remoteTablets)
            if (tablet['tablet_id'] != _tabletCameraId) ...[
              _RemoteTabletCard(
                tablet: tablet,
                busy: _startingCamera,
                onCommand: (action) => _commandRemoteTablet(tablet, action),
              ),
              const SizedBox(height: 8),
            ],
          if (_devices.isEmpty &&
              !_tabletCameraEnabled &&
              !_remoteTablets.any(
                (tablet) => tablet['tablet_id'] != _tabletCameraId,
              ))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 30),
              child: Text(
                'No hay cámaras registradas.',
                textAlign: TextAlign.center,
                style: TextStyle(color: colors.onSurfaceVariant),
              ),
            ),
          for (final device in _devices) ...[
            _DeviceCard(
              device: device,
              busy: _startingCamera,
              onStart: () => _startScan(device),
            ),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _startingCamera
                  ? null
                  : _opencvScanActive
                      ? _stopOpenCvScan
                      : _startOpenCvScan,
              style: ElevatedButton.styleFrom(
                backgroundColor: _opencvScanActive || remoteScanActive
                    ? Colors.red.shade700
                    : AppColors.upecGreen,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              icon: _startingCamera
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Icon(
                      _opencvScanActive || remoteScanActive
                          ? Icons.stop_circle_outlined
                          : Icons.camera_alt,
                      size: 17,
                    ),
              label: Text(
                _opencvScanActive || remoteScanActive
                    ? 'Detener escaneo'
                    : _remoteTablets.any(
                        (tablet) => tablet['tablet_id'] != _tabletCameraId,
                      )
                        ? 'Escanear con OpenCV (tablet)'
                        : 'Escanear con cámara OpenCV',
                style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: Colors.white),
              ),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _startingCamera ? null : _scanWithPhoneCamera,
              style: OutlinedButton.styleFrom(
                foregroundColor: colors.onSurface,
                side: const BorderSide(color: AppColors.upecGreen),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.all(Radius.circular(20)),
                ),
              ),
              icon:
                  Icon(Icons.phone_android, size: 17, color: colors.onSurface),
              label: Text(
                _startingCamera
                    ? 'Procesando escaneo...'
                    : 'Usar cámara de este dispositivo',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: colors.onSurface),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DeviceCard extends StatelessWidget {
  final DispositivoIoT device;
  final bool busy;
  final VoidCallback onStart;

  const _DeviceCard({
    required this.device,
    required this.busy,
    required this.onStart,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final active = device.estado == 'Transmitiendo';
    final icon = device.tipo == 'ESP32-CAM'
        ? Icons.memory
        : device.tipo == 'Webcam-USB'
            ? Icons.camera_alt
            : Icons.router;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.upecGreen, size: 18),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  device.nombre,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: colors.onSurface,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: 5),
              Text(
                '■ ${device.estado}',
                style: TextStyle(
                  color: active ? AppColors.upecGreen : colors.onSurfaceVariant,
                  fontSize: 9,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            'IP: ${device.ipAddress} • Aula: ${device.aula}',
            style: TextStyle(
              color: colors.onSurfaceVariant,
              fontSize: 10,
            ),
          ),
          const SizedBox(height: 9),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: busy ? null : onStart,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.upecGreen,
                side: const BorderSide(color: AppColors.upecGreen),
                padding: const EdgeInsets.symmetric(vertical: 8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              icon: const Icon(Icons.play_arrow, size: 16),
              label: Text(
                active ? 'Reactivar escaneo' : 'Iniciar escaneo facial',
                style: const TextStyle(fontSize: 11),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RemoteTabletCard extends StatelessWidget {
  final Map<String, dynamic> tablet;
  final bool busy;
  final ValueChanged<String> onCommand;

  const _RemoteTabletCard({
    required this.tablet,
    required this.busy,
    required this.onCommand,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final active = tablet['estado'] == 'Transmitiendo';
    final name = tablet['nombre'] as String? ?? 'Tablet Android';
    final result = tablet['resultado'];
    final resultMessage =
        result is Map<String, dynamic> ? result['mensaje']?.toString() : null;
    final resultIsWarning = result is Map<String, dynamic> &&
        {'fuera_horario', 'desconocido'}.contains(result['tipo']);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.tablet_android,
            color: AppColors.upecGreen,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: colors.onSurface,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                Text(
                  active ? 'Escaneando' : 'Conectada y lista',
                  style: TextStyle(
                    color:
                        active ? AppColors.upecGreen : colors.onSurfaceVariant,
                    fontSize: 10,
                  ),
                ),
                if (resultMessage != null && resultMessage.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      resultMessage,
                      style: TextStyle(
                        color: resultIsWarning
                            ? colors.error
                            : AppColors.upecGreen,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            onPressed:
                busy ? null : () => onCommand(active ? 'detener' : 'iniciar'),
            style: FilledButton.styleFrom(
              backgroundColor:
                  active ? Colors.red.shade700 : AppColors.upecGreen,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            ),
            child: Text(active ? 'Detener' : 'Iniciar'),
          ),
        ],
      ),
    );
  }
}
