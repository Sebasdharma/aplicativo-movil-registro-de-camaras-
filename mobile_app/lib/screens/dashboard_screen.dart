import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'carchito_screen.dart';
import 'student_enroll_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<dynamic> estudiantes = [];
  bool cargando = true;
  String materiaSeleccionada = "Aplicaciones Móviles (7mo AM)";
  final String baseUrl = "http://10.0.2.2:5000"; // localhost para emulador Android

  @override
  void initState() {
    super.initState();
    cargarAsistencias();
  }

  Future<void> cargarAsistencias() async {
    setState(() => cargando = true);
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/asistencia/resumen?materia_id=1'));
      if (res.statusCode == 200) {
        setState(() {
          estudiantes = json.decode(res.body);
          cargando = false;
        });
      }
    } catch (e) {
      // Mock de datos para demostración inmediata en APK/Dispositivo
      setState(() {
        estudiantes = [
          {"id": 1, "codigo_estudiantil": "UPEC-2026-001", "nombre_completo": "Reina Gordon Jhoel Sebastian", "estado": "Presente", "hora": "07:05:12", "metodo": "Facial-Carchito"},
          {"id": 2, "codigo_estudiantil": "UPEC-2026-002", "nombre_completo": "Cadena Edelina", "estado": "Presente", "hora": "07:06:45", "metodo": "Facial-Carchito"},
          {"id": 3, "codigo_estudiantil": "UPEC-2026-003", "nombre_completo": "Lema Jordy", "estado": "Ausente", "hora": "--:--:--", "metodo": "No registrado"},
          {"id": 4, "codigo_estudiantil": "UPEC-2026-004", "nombre_completo": "Ponce Melisa", "estado": "Presente", "hora": "07:08:20", "metodo": "Facial-Carchito"},
          {"id": 5, "codigo_estudiantil": "UPEC-2026-005", "nombre_completo": "Carlosama Daniel", "estado": "Ausente", "hora": "--:--:--", "metodo": "No registrado"},
          {"id": 6, "codigo_estudiantil": "UPEC-2026-006", "nombre_completo": "Montenegro Valeria", "estado": "Presente", "hora": "07:11:05", "metodo": "Manual-Docente"}
        ];
        cargando = false;
      });
    }
  }

  Future<void> alternarEstadoManual(int index) async {
    final est = estudiantes[index];
    final nuevoEstado = est['estado'] == 'Presente' ? 'Ausente' : 'Presente';
    setState(() {
      est['estado'] = nuevoEstado;
      est['metodo'] = 'Manual-Docente';
      if (nuevoEstado == 'Presente') {
        final now = DateTime.now();
        est['hora'] = "${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}";
      } else {
        est['hora'] = "--:--:--";
      }
    });

    try {
      await http.post(
        Uri.parse('$baseUrl/api/asistencia/manual'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'estudiante_id': est['id'],
          'materia_id': 1,
          'estado': nuevoEstado,
        }),
      );
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    int presentes = estudiantes.where((e) => e['estado'] == 'Presente').length;
    int total = estudiantes.length;
    int porcentaje = total > 0 ? ((presentes / total) * 100).round() : 0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('🦉 BúhoPass - Asistencia UPEC'),
        backgroundColor: const Color(0xFF003366),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_add),
            tooltip: 'Enrolar Estudiante',
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => const StudentEnrollScreen()));
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Actualizar',
            onPressed: cargarAsistencias,
          ),
        ],
      ),
      body: cargando
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Selector de Asignatura
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  color: const Color(0xFF003366),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Icon(Icons.school, color: Colors.cyanAccent),
                      Text(
                        materiaSeleccionada,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                      ),
                      const Chip(
                        label: Text('EN VIVO', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                        backgroundColor: Colors.redAccent,
                      ),
                    ],
                  ),
                ),
                // Tarjetas de Métricas
                Container(
                  padding: const EdgeInsets.all(16),
                  color: const Color(0xFF003366).withOpacity(0.05),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildMetricCard('Total', '$total', Icons.groups, Colors.blueGrey),
                      _buildMetricCard('Presentes', '$presentes', Icons.check_circle, Colors.green),
                      _buildMetricCard('Ausentes', '${total - presentes}', Icons.cancel, Colors.red),
                      _buildMetricCard('Asistencia', '$porcentaje%', Icons.analytics, Colors.indigo),
                    ],
                  ),
                ),
                // Lista de Estudiantes
                Expanded(
                  child: ListView.builder(
                    itemCount: estudiantes.length,
                    itemBuilder: (context, index) {
                      final est = estudiantes[index];
                      final esPresente = est['estado'] == 'Presente';
                      return Card(
                        elevation: 1.5,
                        margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: ListTile(
                          leading: CircleAvatar(
                            radius: 22,
                            backgroundColor: esPresente ? Colors.green.shade100 : Colors.red.shade100,
                            child: Icon(
                              esPresente ? Icons.face : Icons.person_off,
                              color: esPresente ? Colors.green.shade800 : Colors.red.shade800,
                            ),
                          ),
                          title: Text(
                            est['nombre_completo'],
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                          subtitle: Text('${est['codigo_estudiantil']} • Hora: ${est['hora']} (${est['metodo']})'),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Chip(
                                label: Text(est['estado']),
                                backgroundColor: esPresente ? Colors.green.shade100 : Colors.red.shade100,
                                labelStyle: TextStyle(
                                  color: esPresente ? Colors.green.shade900 : Colors.red.shade900,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 12,
                                ),
                              ),
                              IconButton(
                                icon: Icon(
                                  esPresente ? Icons.toggle_on : Icons.toggle_off,
                                  color: esPresente ? Colors.green : Colors.grey,
                                  size: 32,
                                ),
                                tooltip: 'Alternar asistencia manual',
                                onPressed: () => alternarEstadoManual(index),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
      bottomNavigationBar: BottomAppBar(
        color: const Color(0xFF003366),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            TextButton.icon(
              style: TextButton.styleFrom(foregroundColor: Colors.white),
              icon: const Icon(Icons.mic, color: Colors.cyanAccent),
              label: const Text('Asistente Carchito'),
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const CarchitoScreen()));
              },
            ),
            TextButton.icon(
              style: TextButton.styleFrom(foregroundColor: Colors.white),
              icon: const Icon(Icons.person_add_alt_1),
              label: const Text('Enrolar'),
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const StudentEnrollScreen()));
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        Text(label, style: TextStyle(color: Colors.grey.shade700, fontSize: 11)),
      ],
    );
  }
}
