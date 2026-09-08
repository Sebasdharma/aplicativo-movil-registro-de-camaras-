import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<dynamic> estudiantes = [];
  bool cargando = true;
  final String baseUrl = "http://10.0.2.2:5000"; // O IP local de la computadora

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
      // Mock de datos para demostración inmediata
      setState(() {
        estudiantes = [
          {"id": 1, "codigo_estudiantil": "UPEC-2026-001", "nombre_completo": "Reina Gordon Jhoel Sebastian", "estado": "Presente", "hora": "07:05:12", "metodo": "Facial-Carchito"},
          {"id": 2, "codigo_estudiantil": "UPEC-2026-002", "nombre_completo": "Cadena Edelina", "estado": "Presente", "hora": "07:06:45", "metodo": "Facial-Carchito"},
          {"id": 3, "codigo_estudiantil": "UPEC-2026-003", "nombre_completo": "Lema Jordy", "estado": "Ausente", "hora": "--:--:--", "metodo": "No registrado"},
          {"id": 4, "codigo_estudiantil": "UPEC-2026-004", "nombre_completo": "Ponce Melisa", "estado": "Presente", "hora": "07:08:20", "metodo": "Facial-Carchito"}
        ];
        cargando = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    int presentes = estudiantes.where((e) => e['estado'] == 'Presente').length;
    int total = estudiantes.length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('🦉 BúhoPass - Asistencia UPEC'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: cargarAsistencias,
          ),
        ],
      ),
      body: cargando
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Cabecera Informativa
                Container(
                  padding: const EdgeInsets.all(16),
                  color: const Color(0xFF003366).withOpacity(0.06),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildStatCard('Materia', 'Aplicaciones Móviles', Icons.book, Colors.blue),
                      _buildStatCard('Presentes', '$presentes / $total', Icons.check_circle, Colors.green),
                      _buildStatCard('Porcentaje', total > 0 ? '${((presentes/total)*100).round()}%' : '0%', Icons.percent, Colors.orange),
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
                        margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: esPresente ? Colors.green.shade100 : Colors.red.shade100,
                            child: Icon(
                              esPresente ? Icons.face : Icons.person_off,
                              color: esPresente ? Colors.green.shade800 : Colors.red.shade800,
                            ),
                          ),
                          title: Text(est['nombre_completo'], style: const TextStyle(fontWeight: FontWeight.bold)),
                          subtitle: Text('${est['codigo_estudiantil']} • Hora: ${est['hora']}'),
                          trailing: Chip(
                            label: Text(est['estado']),
                            backgroundColor: esPresente ? Colors.green.shade100 : Colors.red.shade100,
                            labelStyle: TextStyle(
                              color: esPresente ? Colors.green.shade900 : Colors.red.shade900,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF0066CC),
        foregroundColor: Colors.white,
        icon: const Icon(Icons.mic),
        label: const Text('Asistente Carchito'),
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Comando de voz: Di "Hola Carchito, toma asistencia"')),
          );
        },
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 24),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
      ],
    );
  }
}
