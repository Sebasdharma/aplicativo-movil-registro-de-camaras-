import 'package:flutter/material.dart';

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
  List<DispositivoIoT> _devices = [];
  bool _loading = true;
  bool _startingCamera = false;
  bool _opencvScanActive = false;
  bool _autoStartHandled = false;

  @override
  void initState() {
    super.initState();
    _loadDevices();
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

  Future<void> _scanWithPhoneCamera() async {
    if (_startingCamera) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => LiveFaceScanScreen(
          materiaId: widget.materiaId,
          onAttendanceRegistered: () => widget.onAttendanceRegistered?.call(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
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
                    style: TextStyle(
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
          if (_devices.isEmpty)
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
                      : () => _startScan(),
              style: ElevatedButton.styleFrom(
                backgroundColor: _opencvScanActive
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
                      _opencvScanActive
                          ? Icons.stop_circle_outlined
                          : Icons.camera_alt,
                      size: 17,
                    ),
              label: Text(
                _opencvScanActive
                    ? 'Detener escaneo'
                    : 'Escanear con Cámara OpenCV en Vivo',
                style: TextStyle(
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
                    : 'Usar Cámara de mi Teléfono',
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
