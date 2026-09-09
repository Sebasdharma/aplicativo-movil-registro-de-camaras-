import 'package:flutter/material.dart';

class CarchitoScreen extends StatefulWidget {
  const CarchitoScreen({super.key});

  @override
  State<CarchitoScreen> createState() => _CarchitoScreenState();
}

class _CarchitoScreenState extends State<CarchitoScreen> with SingleTickerProviderStateMixin {
  late AnimationController _animCtrl;
  bool _escuchando = false;
  String _mensajeAsistente = "Hola docente. Soy Carchito, su asistente de asistencia en el aula. ¿Qué desea hacer hoy?";

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    super.dispose();
  }

  void _toggleEscucha() {
    setState(() {
      _escuchando = !_escuchando;
      if (_escuchando) {
        _mensajeAsistente = "Escuchando... Di: \"Hola Carchito, toma la asistencia del aula\"";
      } else {
        _mensajeAsistente = "Comando procesado: \"Iniciando escaneo facial para 7mo AM\"";
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B132B),
      appBar: AppBar(
        title: const Text('Asistente Virtual Carchito'),
        backgroundColor: const Color(0xFF003366),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Avatar de Carchito
              Container(
                width: 130,
                height: 130,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFF003366),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF00D2FF).withOpacity(_escuchando ? 0.8 : 0.2),
                      blurRadius: _escuchando ? 40 : 15,
                      spreadRadius: _escuchando ? 10 : 2,
                    ),
                  ],
                ),
                child: const Center(
                  child: Text('🦉', style: TextStyle(fontSize: 60)),
                ),
              ),
              const SizedBox(height: 30),
              Text(
                'Carchito UPEC',
                style: TextStyle(
                  color: Colors.cyanAccent.shade200,
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.15)),
                ),
                child: Text(
                  _mensajeAsistente,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 15),
                ),
              ),
              const SizedBox(height: 40),
              GestureDetector(
                onTap: _toggleEscucha,
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _escuchando ? Colors.redAccent : const Color(0xFF0066CC),
                    boxShadow: [
                      BoxShadow(
                        color: (_escuchando ? Colors.red : const Color(0xFF0066CC)).withOpacity(0.5),
                        blurRadius: 20,
                      ),
                    ],
                  ),
                  child: Icon(
                    _escuchando ? Icons.stop : Icons.mic,
                    color: Colors.white,
                    size: 38,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                _escuchando ? 'Toca para detener' : 'Toca para hablar',
                style: const TextStyle(color: Colors.grey, fontSize: 13),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
