import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class StudentEnrollScreen extends StatefulWidget {
  const StudentEnrollScreen({super.key});

  @override
  State<StudentEnrollScreen> createState() => _StudentEnrollScreenState();
}

class _StudentEnrollScreenState extends State<StudentEnrollScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nombreCtrl = TextEditingController();
  final _codigoCtrl = TextEditingController();
  final _paraleloCtrl = TextEditingController(text: "7mo Semestre - Paralelo AM");
  bool _enrolando = false;

  Future<void> _iniciarEnrolamiento() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() => _enrolando = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Abriendo cámara para captura biométrica...')),
    );

    try {
      final res = await http.post(
        Uri.parse('http://10.0.2.2:5000/api/camara/iniciar'),
      );
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: Colors.green,
            content: Text('Estudiante enrolado y registrado en la base de datos.'),
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Nota de conexión: $e')),
      );
    } finally {
      setState(() => _enrolando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Registro y Enrolamiento Facial'),
        backgroundColor: const Color(0xFF003366),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: ListView(
            children: [
              const Icon(Icons.badge, size: 70, color: Color(0xFF003366)),
              const SizedBox(height: 10),
              const Text(
                'Nuevo Estudiante UPEC',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const Text(
                'Registre los datos del estudiante para calibrar su vector facial.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _codigoCtrl,
                decoration: const InputDecoration(
                  labelText: 'Código Estudiantil',
                  prefixIcon: Icon(Icons.qr_code),
                  border: OutlineInputBorder(),
                ),
                validator: (v) => v!.isEmpty ? 'Ingrese el código' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _nombreCtrl,
                decoration: const InputDecoration(
                  labelText: 'Nombres y Apellidos Completos',
                  prefixIcon: Icon(Icons.person),
                  border: OutlineInputBorder(),
                ),
                validator: (v) => v!.isEmpty ? 'Ingrese los nombres' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _paraleloCtrl,
                decoration: const InputDecoration(
                  labelText: 'Nivel y Paralelo',
                  prefixIcon: Icon(Icons.school),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF003366),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                onPressed: _enrolando ? null : _iniciarEnrolamiento,
                icon: const Icon(Icons.camera_alt),
                label: Text(_enrolando ? 'Procesando...' : 'Capturar Foto y Enrolar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
