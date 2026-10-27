class Docente {
  final int id;
  final String email;
  final String nombreCompleto;
  final String cedula;
  final String facultad;
  final String carrera;

  Docente({
    required this.id,
    required this.email,
    required this.nombreCompleto,
    required this.cedula,
    required this.facultad,
    required this.carrera,
  });

  factory Docente.fromJson(Map<String, dynamic> json) {
    return Docente(
      id: json['id'] as int,
      email: json['email_institucional'] as String? ?? '',
      nombreCompleto: json['nombre_completo'] as String? ?? '',
      cedula: json['cedula'] as String? ?? '',
      facultad: json['facultad'] as String? ?? '',
      carrera: json['carrera'] as String? ?? '',
    );
  }
}

class Materia {
  final int id;
  final String codigo;
  final String nombre;
  final String docenteNombre;
  final String horario;
  final String aula;
  final String periodo;
  final String nivelParalelo;

  Materia({
    required this.id,
    required this.codigo,
    required this.nombre,
    required this.docenteNombre,
    required this.horario,
    required this.aula,
    required this.periodo,
    required this.nivelParalelo,
  });

  factory Materia.fromJson(Map<String, dynamic> json) {
    return Materia(
      id: json['id'] as int,
      codigo: json['codigo_materia'] as String? ?? '',
      nombre: json['nombre_materia'] as String? ?? '',
      docenteNombre: json['docente_nombre'] as String? ?? '',
      horario: json['horario'] as String? ?? '',
      aula: json['aula'] as String? ?? '',
      periodo: json['periodo'] as String? ?? '',
      nivelParalelo: json['nivel_paralelo'] as String? ?? '',
    );
  }
}

class EstudianteAsistencia {
  final int id;
  final String codigo;
  final String nombreCompleto;
  final String nivelParalelo;
  final String email;
  String estado; // 'Presente', 'Ausente', 'Atrasado', 'Justificado'
  String hora;
  String metodo; // 'Facial-Carchito', 'Manual-Docente', 'Dispositivo-IoT'
  final List<PeriodoAsistencia> periodos;

  EstudianteAsistencia({
    required this.id,
    required this.codigo,
    required this.nombreCompleto,
    required this.nivelParalelo,
    required this.email,
    required this.estado,
    required this.hora,
    required this.metodo,
    required this.periodos,
  });

  factory EstudianteAsistencia.fromJson(Map<String, dynamic> json) {
    return EstudianteAsistencia(
      id: json['id'] as int,
      codigo: json['codigo_estudiantil'] as String? ?? '',
      nombreCompleto: json['nombre_completo'] as String? ?? '',
      nivelParalelo: json['nivel_paralelo'] as String? ?? '',
      email: json['email'] as String? ?? '',
      estado: json['estado'] as String? ?? 'Pendiente',
      hora: json['hora'] as String? ?? '--:--:--',
      metodo: json['metodo'] as String? ?? 'No registrado',
      periodos: (json['periodos'] as List<dynamic>? ?? const [])
          .map(
            (periodo) => PeriodoAsistencia.fromJson(
              periodo as Map<String, dynamic>,
            ),
          )
          .toList(),
    );
  }
}

class PeriodoAsistencia {
  final int indice;
  final int bloque;
  final String inicio;
  final String fin;
  String estado;
  String hora;
  final String metodo;

  PeriodoAsistencia({
    required this.indice,
    required this.bloque,
    required this.inicio,
    required this.fin,
    required this.estado,
    required this.hora,
    required this.metodo,
  });

  factory PeriodoAsistencia.fromJson(Map<String, dynamic> json) {
    return PeriodoAsistencia(
      indice: json['indice'] as int,
      bloque: json['bloque'] as int,
      inicio: json['inicio'] as String? ?? '',
      fin: json['fin'] as String? ?? '',
      estado: json['estado'] as String? ?? 'Pendiente',
      hora: json['hora'] as String? ?? '--:--:--',
      metodo: json['metodo'] as String? ?? 'No registrado',
    );
  }
}

class DispositivoIoT {
  final int id;
  final String nombre;
  final String tipo; // 'ESP32-CAM', 'Webcam-USB', 'RTSP-IP'
  final String ipAddress;
  final String aula;
  String estado; // 'Conectado', 'Desconectado', 'Transmitiendo'
  final String ultimaActividad;

  DispositivoIoT({
    required this.id,
    required this.nombre,
    required this.tipo,
    required this.ipAddress,
    required this.aula,
    required this.estado,
    required this.ultimaActividad,
  });

  factory DispositivoIoT.fromJson(Map<String, dynamic> json) {
    return DispositivoIoT(
      id: json['id'] ?? 0,
      nombre: json['nombre'] ?? '',
      tipo: json['tipo'] as String? ?? '',
      ipAddress: json['ip_address'] ?? '',
      aula: json['aula'] ?? '',
      estado: json['estado'] as String? ?? 'Desconectado',
      ultimaActividad: json['ultima_actividad'] as String? ?? '',
    );
  }
}
