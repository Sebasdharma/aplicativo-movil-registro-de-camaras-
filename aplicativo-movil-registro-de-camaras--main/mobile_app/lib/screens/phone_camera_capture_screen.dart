import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../core/constants/app_colors.dart';

class PhoneCameraCaptureScreen extends StatefulWidget {
  final String title;

  const PhoneCameraCaptureScreen({
    super.key,
    required this.title,
  });

  @override
  State<PhoneCameraCaptureScreen> createState() =>
      _PhoneCameraCaptureScreenState();
}

class _PhoneCameraCaptureScreenState extends State<PhoneCameraCaptureScreen> {
  CameraController? _controller;
  String? _error;
  bool _capturing = false;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw StateError('El teléfono no informa ninguna cámara disponible.');
      }
      final camera = cameras.firstWhere(
        (item) => item.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      final controller = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      setState(() => _controller = controller);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    }
  }

  Future<void> _capture() async {
    final controller = _controller;
    if (controller == null || _capturing || !controller.value.isInitialized) {
      return;
    }
    setState(() => _capturing = true);
    try {
      final image = await controller.takePicture();
      final bytes = await image.readAsBytes();
      if (mounted) Navigator.of(context).pop<Uint8List>(bytes);
    } catch (error) {
      if (mounted) {
        setState(() {
          _capturing = false;
          _error = 'No se pudo capturar la foto: $error';
        });
      }
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        backgroundColor: AppColors.upecGreen,
        foregroundColor: Colors.white,
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
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              child: Text(
                'Centra un solo rostro, con buena iluminación y sin cubrir la cara.',
                textAlign: TextAlign.center,
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: controller == null || _capturing || _error != null
                      ? null
                      : _capture,
                  icon: _capturing
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.camera_alt),
                  label: Text(
                    _capturing ? 'Capturando...' : 'Capturar foto',
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
