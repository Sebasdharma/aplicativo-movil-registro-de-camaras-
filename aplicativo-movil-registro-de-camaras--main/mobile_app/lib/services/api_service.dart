import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/models.dart';

class ApiService {
  static const _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  static final String baseUrl = _configuredBaseUrl.isNotEmpty
      ? _configuredBaseUrl
      : defaultTargetPlatform == TargetPlatform.android
          ? 'http://10.0.2.2:5000'
          : 'http://127.0.0.1:5000';

  static Future<Docente> loginMicrosoft(String idToken) async {
    final http.Response response;
    try {
      response = await http
          .post(
            Uri.parse('$baseUrl/api/auth/microsoft'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'id_token': idToken}),
          )
          .timeout(const Duration(seconds: 10));
    } catch (error) {
      throw Exception('No se pudo verificar la cuenta con el servidor: $error');
    }

    final Map<String, dynamic> data;
    try {
      data = json.decode(response.body) as Map<String, dynamic>;
    } catch (error) {
      throw Exception('El servidor devolvió una respuesta inválida: $error');
    }

    if (response.statusCode != 200) {
      throw Exception(
        data['mensaje']?.toString() ??
            'No se pudo completar el inicio de sesión con Microsoft.',
      );
    }
    return Docente.fromJson(data['docente'] as Map<String, dynamic>);
  }

  // Acceso temporal de administrador mientras se configura Microsoft 365.
  static Future<Docente> loginAdministrador() async {
    final http.Response res;
    try {
      res = await http
          .post(Uri.parse('$baseUrl/api/auth/admin'))
          .timeout(const Duration(seconds: 4));
    } catch (error) {
      throw Exception('No se pudo conectar con el servidor: $error');
    }

    final Map<String, dynamic> data;
    try {
      data = json.decode(res.body) as Map<String, dynamic>;
    } catch (error) {
      throw Exception('El servidor devolvió una respuesta inválida: $error');
    }

    if (res.statusCode != 200) {
      throw Exception(
        data['mensaje']?.toString() ?? 'El servidor rechazó el acceso.',
      );
    }
    return Docente.fromJson(data['docente'] as Map<String, dynamic>);
  }

  // Obtener lista de materias asignadas al docente
  static Future<List<Materia>> getMaterias({int docenteId = 1}) async {
    try {
      final res = await http
          .get(Uri.parse('$baseUrl/api/materias?docente_id=$docenteId'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final List<dynamic> list = json.decode(res.body);
        return list.map((m) => Materia.fromJson(m)).toList();
      }
      throw Exception(
          'No se pudieron cargar las materias (${res.statusCode}).');
    } on Exception {
      rethrow;
    } catch (error) {
      throw Exception('No se pudo conectar con el servidor: $error');
    }
  }

  // Obtener lista de estudiantes y estado de asistencia del día
  static Future<List<EstudianteAsistencia>> getAsistencias(
      {int materiaId = 1}) async {
    try {
      final res = await http
          .get(Uri.parse(
              '$baseUrl/api/asistencia/resumen?materia_id=$materiaId'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final List<dynamic> list = json.decode(res.body);
        return list.map((e) => EstudianteAsistencia.fromJson(e)).toList();
      }
      throw Exception('No se pudo cargar la asistencia (${res.statusCode}).');
    } on Exception {
      rethrow;
    } catch (error) {
      throw Exception('No se pudo conectar con el servidor: $error');
    }
  }

  static Future<Uint8List> descargarReporteAsistencia({
    required int materiaId,
    required int docenteId,
    required DateTime fecha,
  }) async {
    final fechaFormateada = '${fecha.year.toString().padLeft(4, '0')}-'
        '${fecha.month.toString().padLeft(2, '0')}-'
        '${fecha.day.toString().padLeft(2, '0')}';
    final uri = Uri.parse('$baseUrl/api/asistencia/reporte/excel').replace(
      queryParameters: {
        'materia_id': '$materiaId',
        'docente_id': '$docenteId',
        'fecha': fechaFormateada,
      },
    );
    final response = await http.get(uri).timeout(const Duration(seconds: 30));
    if (response.statusCode != 200) {
      var mensaje = 'No se pudo generar el reporte '
          '(${response.statusCode}).';
      try {
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (data is Map<String, dynamic> && data['mensaje'] is String) {
          mensaje = data['mensaje'] as String;
        }
      } on FormatException {
        // Keep the HTTP status message when the server does not return JSON.
      }
      throw Exception(mensaje);
    }
    if (response.bodyBytes.isEmpty) {
      throw Exception('El servidor devolvió un reporte vacío.');
    }
    return response.bodyBytes;
  }

  // Alternar o marcar asistencia manual (Presente, Ausente, Atrasado, Justificado)
  static Future<bool> registrarAsistenciaManual({
    required int estudianteId,
    required int materiaId,
    required String nuevoEstado,
    int? periodoIndice,
    String metodo = 'Manual-Docente',
  }) async {
    final http.Response response;
    try {
      response = await http
          .post(
            Uri.parse('$baseUrl/api/asistencia/manual'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'estudiante_id': estudianteId,
              'materia_id': materiaId,
              'estado': nuevoEstado,
              'metodo': metodo,
              'periodo_indice': periodoIndice,
            }),
          )
          .timeout(const Duration(seconds: 15));
    } catch (error) {
      throw Exception('No se pudo conectar con el servidor: $error');
    }

    final Map<String, dynamic> data;
    try {
      data = json.decode(response.body) as Map<String, dynamic>;
    } catch (error) {
      throw Exception('El servidor devolvió una respuesta inválida: $error');
    }

    if (response.statusCode != 200 || data['status'] != 'ok') {
      throw Exception(
        data['mensaje']?.toString() ?? 'No se pudo guardar la asistencia.',
      );
    }
    return true;
  }

  // Obtener dispositivos IoT / cámaras del aula
  static Future<List<DispositivoIoT>> getDispositivosIoT() async {
    try {
      final res = await http
          .get(Uri.parse('$baseUrl/api/dispositivos'))
          .timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        final List<dynamic> list = json.decode(res.body);
        return list.map((d) => DispositivoIoT.fromJson(d)).toList();
      }
      throw Exception('No se pudieron cargar las cámaras (${res.statusCode}).');
    } on Exception {
      rethrow;
    } catch (error) {
      throw Exception('No se pudo conectar con el servidor: $error');
    }
  }

  static Future<List<Map<String, dynamic>>> getTabletCameras() async {
    final response = await http
        .get(Uri.parse('$baseUrl/api/camara/tablet/dispositivos'))
        .timeout(const Duration(seconds: 4));
    if (response.statusCode != 200) {
      throw Exception('No se pudieron consultar las tablets conectadas.');
    }
    return (json.decode(response.body) as List<dynamic>)
        .cast<Map<String, dynamic>>();
  }

  static Future<Map<String, dynamic>> heartbeatTabletCamera({
    required String tabletId,
    required String name,
    required bool active,
    bool enabled = true,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/camara/tablet/heartbeat'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'tablet_id': tabletId,
            'nombre': name,
            'activa': active,
            'habilitada': enabled,
          }),
        )
        .timeout(const Duration(seconds: 4));
    final Map<String, dynamic> result =
        json.decode(response.body) as Map<String, dynamic>;
    if (response.statusCode == 200 && result['status'] == 'ok') return result;
    throw Exception(result['mensaje'] ?? 'No se pudo conectar la tablet.');
  }

  static Future<Map<String, dynamic>> commandTabletCamera({
    required String tabletId,
    required String action,
    required int materiaId,
  }) async {
    final response = await http
        .post(
          Uri.parse('$baseUrl/api/camara/tablet/comando'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'tablet_id': tabletId,
            'action': action,
            'materia_id': materiaId,
          }),
        )
        .timeout(const Duration(seconds: 4));
    final Map<String, dynamic> result =
        json.decode(response.body) as Map<String, dynamic>;
    if (response.statusCode == 200 && result['status'] == 'ok') return result;
    throw Exception(result['mensaje'] ?? 'No se pudo enviar la orden.');
  }

  // Iniciar escaneo de cámara / dispositivo de hardware
  static Future<Map<String, dynamic>> iniciarEscaneoCamara(
      {int materiaId = 1, int? dispositivoId}) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/api/camara/iniciar'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'materia_id': materiaId,
            'dispositivo_id': dispositivoId,
          }),
        )
        .timeout(const Duration(seconds: 4));
    final Map<String, dynamic> result = json.decode(res.body);
    if (res.statusCode == 200 && result['status'] == 'ok') return result;
    throw Exception(result['mensaje'] ?? 'No se pudo iniciar la cámara.');
  }

  static Future<Map<String, dynamic>> detenerEscaneoCamara() async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/camara/detener'),
      headers: {'Content-Type': 'application/json'},
    ).timeout(const Duration(seconds: 5));
    final Map<String, dynamic> result = json.decode(res.body);
    if (res.statusCode == 200 && result['status'] == 'ok') return result;
    throw Exception(result['mensaje'] ?? 'No se pudo detener la cámara.');
  }

  // Escanear rostro usando la cámara del teléfono móvil
  static Future<Map<String, dynamic>> escanearRostroTelefono({
    required int materiaId,
    required String fotoBase64,
    int rotacion = 0,
  }) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/api/camara/telefono/escanear'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'foto': fotoBase64,
            'materia_id': materiaId,
            'rotacion': rotacion,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final Map<String, dynamic> result = json.decode(res.body);
    if (res.statusCode == 200 && result['status'] == 'ok') return result;
    throw Exception(result['mensaje'] ?? 'No se pudo escanear la imagen.');
  }

  // Enviar comando por voz a Carchito
  static Future<Map<String, dynamic>> enviarComandoCarchito(String comando,
      {int materiaId = 1}) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/api/carchito/comando'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'comando': comando,
            'materia_id': materiaId,
          }),
        )
        .timeout(const Duration(seconds: 15));
    final Map<String, dynamic> result = json.decode(res.body);
    if (res.statusCode == 200) return result;
    throw Exception(
        result['mensaje'] ?? 'Carchito no pudo procesar el comando.');
  }

  // Enrolar nuevo estudiante con validación universitaria
  static Future<Map<String, dynamic>> enrolarEstudiante({
    required String codigo,
    required String nombre,
    required String paralelo,
    required String email,
    required int materiaId,
    List<String>? fotosBase64,
    String? fotoBase64,
    bool consentimientoBiometrico = false,
  }) async {
    final res = await http
        .post(
          Uri.parse('$baseUrl/api/estudiantes/enrolar'),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'codigo': codigo,
            'nombre': nombre,
            'paralelo': paralelo,
            'email': email,
            'materia_id': materiaId,
            if (fotosBase64 != null)
              'fotos': fotosBase64
            else if (fotoBase64 != null)
              'foto': fotoBase64,
            'consentimiento_biometrico': consentimientoBiometrico,
          }),
        )
        .timeout(const Duration(seconds: 20));
    final Map<String, dynamic> result = json.decode(res.body);
    if (res.statusCode == 200 && result['status'] == 'ok') return result;
    throw Exception(result['mensaje'] ?? 'No se pudo enrolar al estudiante.');
  }
}
