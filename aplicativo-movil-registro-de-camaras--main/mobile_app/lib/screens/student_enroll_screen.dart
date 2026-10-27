import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../services/api_service.dart';
import 'phone_camera_capture_screen.dart';

class StudentEnrollScreen extends StatefulWidget {
  final int materiaId;
  final String materiaNombre;

  const StudentEnrollScreen({
    super.key,
    required this.materiaId,
    required this.materiaNombre,
  });

  @override
  State<StudentEnrollScreen> createState() => _StudentEnrollScreenState();
}

class _StudentEnrollScreenState extends State<StudentEnrollScreen> {
  final _formKey = GlobalKey<FormState>();
  final _codigoCtrl = TextEditingController();
  final _nombreCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _paraleloCtrl = TextEditingController();
  bool _enrolando = false;
  bool _consentimientoBiometrico = false;
  final List<Uint8List> _fotosCapturadas = [];

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    _codigoCtrl.dispose();
    _nombreCtrl.dispose();
    _emailCtrl.dispose();
    _paraleloCtrl.dispose();
    super.dispose();
  }

  Future<void> _capturarFoto() async {
    if (_fotosCapturadas.length >= 5) return;
    final foto = await Navigator.of(context).push<Uint8List>(
      MaterialPageRoute(
        builder: (_) => const PhoneCameraCaptureScreen(
          title: 'Capturar foto facial',
        ),
      ),
    );
    if (mounted && foto != null) {
      setState(() => _fotosCapturadas.add(foto));
    }
  }

  Future<void> _iniciarEnrolamiento() async {
    if (!_formKey.currentState!.validate()) return;
    if (_fotosCapturadas.isNotEmpty && !_consentimientoBiometrico) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content:
              Text('Confirma la autorización para guardar la foto facial.'),
        ),
      );
      return;
    }
    setState(() => _enrolando = true);

    try {
      final resultado = await ApiService.enrolarEstudiante(
        codigo: _codigoCtrl.text.trim(),
        nombre: _nombreCtrl.text.trim(),
        paralelo: _paraleloCtrl.text.trim(),
        email: _emailCtrl.text.trim(),
        materiaId: widget.materiaId,
        fotosBase64: _fotosCapturadas.isEmpty
            ? null
            : _fotosCapturadas.map(base64Encode).toList(),
        consentimientoBiometrico: _consentimientoBiometrico,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(resultado['mensaje'].toString())),
        );
        Navigator.pop(context);
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('No se pudo enrolar al estudiante: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _enrolando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF070F26),
      appBar: AppBar(
        title: const Text('Inscribir estudiante'),
        backgroundColor: const Color(0xFF003366),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Icono e Información
                Center(
                  child: Container(
                    width: 90,
                    height: 90,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: const Color(0xFF003366),
                      border:
                          Border.all(color: const Color(0xFF00D2FF), width: 2),
                    ),
                    child: const Icon(Icons.person_add_alt_1,
                        color: Color(0xFF00D2FF), size: 48),
                  ),
                ),
                const SizedBox(height: 14),
                const Text(
                  'Registro de Alumno UPEC',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Registra al estudiante en la materia seleccionada. La foto facial se puede agregar después.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                ),
                const SizedBox(height: 8),
                Text(
                  widget.materiaNombre,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFF00D2FF),
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 24),

                // Formulario
                _buildTextField(
                  controller: _codigoCtrl,
                  label: 'Código Estudiantil',
                  icon: Icons.badge,
                  validator: (v) => v!.isEmpty ? 'Requerido' : null,
                ),
                const SizedBox(height: 14),

                _buildTextField(
                  controller: _nombreCtrl,
                  label: 'Nombres y Apellidos Completos',
                  icon: Icons.person,
                  validator: (v) =>
                      v!.isEmpty ? 'Ingrese nombres completos' : null,
                ),
                const SizedBox(height: 14),

                _buildTextField(
                  controller: _emailCtrl,
                  label: 'Correo Institucional (@upec.edu.ec)',
                  icon: Icons.email,
                ),
                const SizedBox(height: 14),

                _buildTextField(
                  controller: _paraleloCtrl,
                  label: 'Nivel y Paralelo',
                  icon: Icons.school,
                ),
                const SizedBox(height: 20),

                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          const Icon(
                            Icons.camera_alt,
                            color: Color(0xFF00D2FF),
                            size: 36,
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Fotos nuevas: ${_fotosCapturadas.length}/5',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                const Text(
                                  'Usa varias fotos claras con leves cambios de ángulo e iluminación.',
                                  style: TextStyle(
                                    color: Color(0xFF94A3B8),
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      if (_fotosCapturadas.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        SizedBox(
                          height: 68,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: _fotosCapturadas.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(width: 8),
                            itemBuilder: (context, index) => Stack(
                              children: [
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: Image.memory(
                                    _fotosCapturadas[index],
                                    width: 68,
                                    height: 68,
                                    fit: BoxFit.cover,
                                  ),
                                ),
                                Positioned(
                                  top: 0,
                                  right: 0,
                                  child: InkWell(
                                    onTap: () => setState(
                                      () => _fotosCapturadas.removeAt(index),
                                    ),
                                    child: const CircleAvatar(
                                      radius: 11,
                                      backgroundColor: Colors.black87,
                                      child: Icon(
                                        Icons.close,
                                        size: 14,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed:
                            _fotosCapturadas.length >= 5 ? null : _capturarFoto,
                        icon: const Icon(Icons.add_a_photo_outlined),
                        label: Text(
                          _fotosCapturadas.length >= 5
                              ? 'Límite de 5 fotos alcanzado'
                              : 'Agregar foto (${_fotosCapturadas.length}/5)',
                        ),
                      ),
                    ],
                  ),
                ),

                if (_fotosCapturadas.isNotEmpty)
                  CheckboxListTile(
                    value: _consentimientoBiometrico,
                    onChanged: (value) => setState(
                      () => _consentimientoBiometrico = value ?? false,
                    ),
                    activeColor: const Color(0xFF10B981),
                    contentPadding: EdgeInsets.zero,
                    title: const Text(
                      'Confirmo que el estudiante (o su representante legal, cuando corresponda) autorizó expresamente guardar y usar estas fotos para comparar rostros y registrar asistencia.',
                      style: TextStyle(color: Color(0xFFCBD5E1), fontSize: 12),
                    ),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                const SizedBox(height: 26),

                // Botón Guardar
                ElevatedButton(
                  onPressed: _enrolando ? null : _iniciarEnrolamiento,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    elevation: 3,
                  ),
                  child: _enrolando
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2),
                        )
                      : const Text(
                          'Inscribir en la materia',
                          style: TextStyle(
                              fontSize: 15, fontWeight: FontWeight.bold),
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      validator: validator,
      style: const TextStyle(color: Colors.white, fontSize: 14),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
        prefixIcon: Icon(icon, color: const Color(0xFF00D2FF), size: 20),
        filled: true,
        fillColor: Colors.white.withOpacity(0.04),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: Colors.white.withOpacity(0.08)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Color(0xFF00D2FF), width: 1.5),
        ),
      ),
    );
  }
}
