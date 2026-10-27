import 'dart:async';

import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

import '../core/constants/app_colors.dart';
import '../core/utils/carchito_command.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'login_screen.dart';
import 'institutional_camera_view.dart';
import 'institutional_settings_view.dart';
import 'student_enroll_screen.dart';

class InstitutionalDashboardScreen extends StatefulWidget {
  final Docente docente;
  final Future<void> Function(bool enabled) onThemeModeChanged;

  const InstitutionalDashboardScreen({
    super.key,
    required this.docente,
    required this.onThemeModeChanged,
  });

  @override
  State<InstitutionalDashboardScreen> createState() =>
      _InstitutionalDashboardScreenState();
}

class _InstitutionalDashboardScreenState
    extends State<InstitutionalDashboardScreen> {
  final TextEditingController _searchController = TextEditingController();
  List<Materia> _materias = [];
  List<EstudianteAsistencia> _estudiantes = [];
  Materia? _materiaSeleccionada;
  String _filtro = '';
  bool _cargando = true;
  bool _errorCarga = false;
  bool _autoStartPhoneCamera = false;
  int _selectedTab = 0;
  Timer? _actualizador;

  @override
  void initState() {
    super.initState();
    _cargarDatos();
    _actualizador = Timer.periodic(
      const Duration(seconds: 4),
      (_) {
        if (_materiaSeleccionada != null) {
          _cargarAsistencias(silencioso: true);
        }
      },
    );
  }

  @override
  void dispose() {
    _actualizador?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _cargarDatos() async {
    setState(() {
      _cargando = true;
      _errorCarga = false;
    });
    try {
      final materias = await ApiService.getMaterias(
        docenteId: widget.docente.id,
      );
      if (!mounted) return;
      setState(() {
        _materias = materias;
        _materiaSeleccionada = null;
        _estudiantes = [];
        _cargando = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _cargando = false;
        _errorCarga = true;
      });
    }
  }

  Future<void> _cargarAsistencias({bool silencioso = false}) async {
    final materia = _materiaSeleccionada;
    if (materia == null) {
      if (mounted) {
        setState(() {
          _estudiantes = [];
          _cargando = false;
        });
      }
      return;
    }

    if (!silencioso && mounted) setState(() => _cargando = true);
    try {
      final estudiantes = await ApiService.getAsistencias(
        materiaId: materia.id,
      );
      if (!mounted) return;
      setState(() {
        _estudiantes = estudiantes;
        _cargando = false;
        _errorCarga = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _cargando = false;
        _errorCarga = true;
      });
    }
  }

  List<EstudianteAsistencia> get _estudiantesFiltrados {
    final filtro = _filtro.trim().toLowerCase();
    if (filtro.isEmpty) return _estudiantes;
    return _estudiantes.where((estudiante) {
      return estudiante.nombreCompleto.toLowerCase().contains(filtro) ||
          estudiante.codigo.toLowerCase().contains(filtro);
    }).toList();
  }

  Future<void> _cambiarEstado(
      EstudianteAsistencia estudiante, String nuevoEstado,
      {int? periodoIndice}) async {
    final estadoAnterior = estudiante.estado;
    final horaAnterior = estudiante.hora;
    final metodoAnterior = estudiante.metodo;
    PeriodoAsistencia? periodo;
    String? estadoPeriodoAnterior;
    String? horaPeriodoAnterior;
    if (periodoIndice != null) {
      for (final candidato in estudiante.periodos) {
        if (candidato.indice == periodoIndice) {
          periodo = candidato;
          break;
        }
      }
      estadoPeriodoAnterior = periodo?.estado;
      horaPeriodoAnterior = periodo?.hora;
    }
    final ahora = DateTime.now();
    setState(() {
      estudiante.estado = nuevoEstado;
      estudiante.metodo = 'Manual-Docente';
      estudiante.hora = nuevoEstado == 'Ausente'
          ? '--:--:--'
          : '${ahora.hour.toString().padLeft(2, '0')}:'
              '${ahora.minute.toString().padLeft(2, '0')}:'
              '${ahora.second.toString().padLeft(2, '0')}';
      if (periodo != null) {
        periodo.estado = nuevoEstado;
        periodo.hora = estudiante.hora;
      }
    });

    try {
      await ApiService.registrarAsistenciaManual(
        estudianteId: estudiante.id,
        materiaId: _materiaSeleccionada?.id ?? 1,
        nuevoEstado: nuevoEstado,
        periodoIndice: periodoIndice,
      );
      if (mounted) await _cargarAsistencias(silencioso: true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        estudiante.estado = estadoAnterior;
        estudiante.hora = horaAnterior;
        estudiante.metodo = metodoAnterior;
        if (periodo != null) {
          periodo.estado = estadoPeriodoAnterior ?? 'Pendiente';
          periodo.hora = horaPeriodoAnterior ?? '--:--:--';
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'No se guardó: ${error.toString().replaceFirst('Exception: ', '')}',
          ),
        ),
      );
    }
  }

  void _mostrarEstados(
    EstudianteAsistencia estudiante, {
    int? periodoIndice,
  }) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
      ),
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                estudiante.nombreCompleto,
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurface,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${estudiante.codigo} • ${estudiante.nivelParalelo}',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final estado in [
                    'Presente',
                    'Atrasado',
                    'Justificado',
                    'Ausente',
                  ])
                    OutlinedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _cambiarEstado(
                          estudiante,
                          estado,
                          periodoIndice: periodoIndice,
                        );
                      },
                      child: Text(estado),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _cerrarSesion() async {
    await Navigator.pushReplacement<void, void>(
      context,
      MaterialPageRoute(
        builder: (_) => LoginScreen(
          onThemeModeChanged: widget.onThemeModeChanged,
        ),
      ),
    );
  }

  void _mostrarAsistenteCarchito() {
    final materia = _materiaSeleccionada;
    if (materia == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Primero selecciona una materia.')),
      );
      return;
    }

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => _CarchitoVoiceAssistantSheet(
        materiaId: materia.id,
        materiaNombre: materia.nombre,
        onCommandCompleted: () => _cargarAsistencias(silencioso: true),
        onStartScan: () {
          Navigator.of(context).pop();
          setState(() {
            _selectedTab = 1;
            _autoStartPhoneCamera = true;
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final total = _estudiantes.length;
    final periodos = _estudiantes.expand((estudiante) => estudiante.periodos);
    final periodosActivos = periodos.isNotEmpty;
    final presentes = periodosActivos
        ? periodos
            .where((periodo) => {
                  'Presente',
                  'Atrasado',
                  'Justificado',
                }.contains(periodo.estado))
            .length
        : _estudiantes
            .where((estudiante) =>
                estudiante.estado == 'Presente' ||
                estudiante.estado == 'Atrasado' ||
                estudiante.estado == 'Parcial')
            .length;
    final ausentes = periodosActivos
        ? periodos.where((periodo) => periodo.estado == 'Ausente').length
        : _estudiantes
            .where((estudiante) => estudiante.estado == 'Ausente')
            .length;
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      floatingActionButton: _selectedTab == 2
          ? null
          : FloatingActionButton(
              onPressed: _mostrarAsistenteCarchito,
              backgroundColor: Colors.transparent,
              elevation: 4,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.upecYellow, width: 3),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.25),
                      blurRadius: 6,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: ClipOval(
                  child: Image.asset(
                    'assets/images/carchito.png',
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const Icon(
                      Icons.support_agent,
                      color: AppColors.upecGreen,
                    ),
                  ),
                ),
              ),
            ),
      appBar: AppBar(
        backgroundColor: AppColors.upecGreen,
        foregroundColor: Colors.white,
        toolbarHeight: 60,
        titleSpacing: 14,
        title: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: AppColors.upecYellow, width: 1.5),
                borderRadius: BorderRadius.circular(7),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: Image.asset(
                  'assets/images/asistech_logo_cropped.png',
                  fit: BoxFit.cover,
                  filterQuality: FilterQuality.high,
                  errorBuilder: (_, __, ___) =>
                      const Icon(Icons.school, color: AppColors.upecGreen),
                ),
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    'AsisTech',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w900),
                  ),
                  Text(
                    widget.docente.nombreCompleto,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: AppColors.upecYellow,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          if (_selectedTab != 2)
            IconButton(
              tooltip: 'Actualizar asistencia',
              onPressed: _cargarAsistencias,
              icon: const Icon(Icons.refresh),
            ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'logout') _cerrarSesion();
              if (value == 'enroll') {
                final materia = _materiaSeleccionada;
                if (materia == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Primero selecciona una materia.'),
                    ),
                  );
                  return;
                }
                Navigator.push<void>(
                  context,
                  MaterialPageRoute(
                    builder: (_) => StudentEnrollScreen(
                      materiaId: materia.id,
                      materiaNombre: materia.nombre,
                    ),
                  ),
                ).then((_) {
                  if (mounted) _cargarAsistencias(silencioso: true);
                });
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'enroll',
                child: Text('Enrolar estudiante'),
              ),
              PopupMenuItem(
                value: 'logout',
                child: Text('Cerrar sesión'),
              ),
            ],
          ),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(3),
          child: ColoredBox(
              color: AppColors.upecYellow, child: SizedBox(height: 3)),
        ),
      ),
      body: Column(
        children: [
          if (_selectedTab != 2) _buildMateriaStrip(),
          Expanded(
            child: _buildSelectedTab(
              total,
              presentes,
              ausentes,
              periodosActivos,
            ),
          ),
        ],
      ),
      bottomNavigationBar: _buildBottomNavigation(),
    );
  }

  Widget _buildMateriaStrip() {
    final aula = _materiaSeleccionada?.aula;
    return Container(
      color: AppColors.upecYellow,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 40,
            child: Row(
              children: [
                const Icon(Icons.menu_book, size: 17, color: Color(0xFF2B1F00)),
                const SizedBox(width: 7),
                Expanded(
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<Materia>(
                      value: _materiaSeleccionada,
                      hint: const Text(
                        'Seleccionar materia',
                        style: TextStyle(
                          color: Color(0xFF2B1F00),
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      isExpanded: true,
                      dropdownColor: Colors.white,
                      icon: const Icon(Icons.arrow_drop_down,
                          color: Colors.black87),
                      style: const TextStyle(
                        color: Colors.black,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                      items: _materias
                          .map(
                            (materia) => DropdownMenuItem(
                              value: materia,
                              child: Text(
                                '${materia.codigo}: ${materia.nombre}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          )
                          .toList(),
                      onChanged: (materia) {
                        if (materia == null) return;
                        setState(() {
                          _materiaSeleccionada = materia;
                          _estudiantes = [];
                          _cargando = true;
                        });
                        _cargarAsistencias();
                      },
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.upecGreen,
                    border: Border.all(color: AppColors.upecGreenDark),
                    borderRadius: BorderRadius.circular(5),
                  ),
                  child: Text(
                    aula == null || aula == 'No indicado'
                        ? 'AULA N/D'
                        : aula.toUpperCase(),
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
          if (_materiaSeleccionada case final materia?)
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 4, 3),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.schedule, size: 13, color: Colors.black87),
                  const SizedBox(width: 5),
                  Expanded(
                    child: Text(
                      '${materia.nivelParalelo} · '
                      '${materia.horario.replaceAll('\n', ' · ')}',
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Color(0xFF2B1F00),
                        fontSize: 9,
                        height: 1.2,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSearchAndMetrics(
    int total,
    int presentes,
    int ausentes,
    bool periodosActivos,
  ) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      color: colors.surface,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 9),
      child: Column(
        children: [
          SizedBox(
            height: 36,
            child: TextField(
              controller: _searchController,
              onChanged: (value) => setState(() => _filtro = value),
              style: TextStyle(fontSize: 12, color: colors.onSurface),
              decoration: InputDecoration(
                hintText: 'Buscar por nombre o cédula...',
                hintStyle: TextStyle(
                  fontSize: 12,
                  color: colors.onSurfaceVariant,
                ),
                prefixIcon: const Icon(
                  Icons.search,
                  size: 17,
                  color: AppColors.upecGreen,
                ),
                prefixIconConstraints:
                    const BoxConstraints(minWidth: 36, minHeight: 36),
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
                filled: true,
                fillColor: colors.surfaceContainerHighest,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colors.outlineVariant),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide(color: colors.outlineVariant),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _MetricCard(
                  label: 'TOTAL', value: '$total', color: AppColors.upecGreen),
              const SizedBox(width: 5),
              _MetricCard(
                  label: periodosActivos ? 'HORAS PRESENTES' : 'PRESENTES',
                  value: '$presentes',
                  color: AppColors.statePresent),
              const SizedBox(width: 5),
              _MetricCard(
                  label: periodosActivos ? 'HORAS AUSENTES' : 'AUSENTES',
                  value: '$ausentes',
                  color: AppColors.stateAbsent),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'ALUMNOS REGISTRADOS (${_materiaSeleccionada?.codigo ?? 'UPEC'})',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  color: colors.onSurface,
                ),
              ),
              Row(
                children: [
                  const Icon(Icons.circle, color: AppColors.upecGreen, size: 7),
                  const SizedBox(width: 4),
                  Text(
                    'TIEMPO REAL',
                    style: TextStyle(
                      fontSize: 8,
                      fontWeight: FontWeight.w800,
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSelectedTab(
    int total,
    int presentes,
    int ausentes,
    bool periodosActivos,
  ) {
    final colors = Theme.of(context).colorScheme;
    if (_selectedTab != 2 && _materiaSeleccionada == null) {
      if (_cargando && !_errorCarga) {
        return const Center(
          child: CircularProgressIndicator(color: AppColors.upecGreen),
        );
      }
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.menu_book_outlined,
                size: 44,
                color: AppColors.upecGreen,
              ),
              const SizedBox(height: 12),
              Text(
                _materias.isEmpty
                    ? _errorCarga
                        ? 'No se pudieron cargar las materias. Revisa la conexión y vuelve a iniciar.'
                        : 'No hay materias disponibles para esta cuenta.'
                    : 'Selecciona una materia arriba para ver su asistencia y horario.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: colors.onSurfaceVariant,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      );
    }

    switch (_selectedTab) {
      case 1:
        final autoStartPhoneCamera = _autoStartPhoneCamera;
        _autoStartPhoneCamera = false;
        return InstitutionalCameraView(
          key: const ValueKey('camera-tab'),
          materiaId: _materiaSeleccionada!.id,
          autoStartPhoneCamera: autoStartPhoneCamera,
          onAttendanceRegistered: () => _cargarAsistencias(silencioso: true),
        );
      case 2:
        return InstitutionalSettingsView(
          key: const ValueKey('settings-tab'),
          docente: widget.docente,
          isDarkMode: Theme.of(context).brightness == Brightness.dark,
          onThemeModeChanged: widget.onThemeModeChanged,
          onChangeAccount: _cerrarSesion,
          onLogout: _cerrarSesion,
        );
      default:
        return Column(
          children: [
            _buildSearchAndMetrics(
              total,
              presentes,
              ausentes,
              periodosActivos,
            ),
            Expanded(child: _buildStudentList()),
          ],
        );
    }
  }

  Widget _buildStudentList() {
    final colors = Theme.of(context).colorScheme;
    if (_cargando && _estudiantes.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.upecGreen),
      );
    }
    if (_errorCarga && _estudiantes.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'No se pudo cargar la asistencia.',
                style: TextStyle(color: colors.onSurface),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _cargarDatos,
                icon: const Icon(Icons.refresh),
                label: const Text('Reintentar'),
              ),
            ],
          ),
        ),
      );
    }
    final estudiantes = _estudiantesFiltrados;
    if (estudiantes.isEmpty) {
      return Center(
        child: Text(
          'Aún no hay estudiantes inscritos en esta materia.',
          style: TextStyle(color: colors.onSurfaceVariant),
        ),
      );
    }

    return RefreshIndicator(
      color: AppColors.upecGreen,
      onRefresh: _cargarAsistencias,
      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        itemCount: estudiantes.length,
        itemBuilder: (context, index) {
          final estudiante = estudiantes[index];
          return _StudentAttendanceCard(
            estudiante: estudiante,
            onTap: estudiante.periodos.isEmpty
                ? () => _mostrarEstados(estudiante)
                : null,
            onToggle: () => _cambiarEstado(
              estudiante,
              estudiante.estado == 'Presente' ? 'Ausente' : 'Presente',
            ),
            onPeriodChanged: (periodo, seleccionado) => _cambiarEstado(
              estudiante,
              seleccionado ? 'Presente' : 'Ausente',
              periodoIndice: periodo.indice,
            ),
            onPeriodTap: (periodo) => _mostrarEstados(
              estudiante,
              periodoIndice: periodo.indice,
            ),
          );
        },
      ),
    );
  }

  Widget _buildBottomNavigation() {
    return SafeArea(
      top: false,
      child: Container(
        height: 58,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          border: Border(
            top:
                BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
          ),
        ),
        child: Row(
          children: [
            _NavItem(
              icon: FontAwesomeIcons.listCheck,
              label: 'Asistencia',
              selected: _selectedTab == 0,
              onTap: () => setState(() => _selectedTab = 0),
            ),
            _NavItem(
              icon: FontAwesomeIcons.video,
              label: 'Cámaras',
              selected: _selectedTab == 1,
              onTap: () => setState(() => _selectedTab = 1),
            ),
            _NavItem(
              icon: FontAwesomeIcons.gear,
              label: 'Configuración',
              selected: _selectedTab == 2,
              onTap: () => setState(() => _selectedTab = 2),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _MetricCard({
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Expanded(
      child: Container(
        height: 47,
        decoration: BoxDecoration(
          color: colors.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: colors.outlineVariant),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              value,
              style: TextStyle(
                color: colors.onSurface,
                fontFamily: 'Roboto',
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
            Text(
              label,
              style: TextStyle(
                color: colors.onSurface,
                fontFamily: 'Roboto',
                fontSize: 7,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StudentAttendanceCard extends StatelessWidget {
  final EstudianteAsistencia estudiante;
  final VoidCallback? onTap;
  final VoidCallback onToggle;
  final void Function(PeriodoAsistencia periodo, bool seleccionado)
      onPeriodChanged;
  final ValueChanged<PeriodoAsistencia> onPeriodTap;

  const _StudentAttendanceCard({
    required this.estudiante,
    required this.onTap,
    required this.onToggle,
    required this.onPeriodChanged,
    required this.onPeriodTap,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final presente = estudiante.estado == 'Presente';
    final atrasado = estudiante.estado == 'Atrasado';
    final parcial = estudiante.estado == 'Parcial';
    final color = presente
        ? AppColors.statePresent
        : atrasado
            ? AppColors.stateLate
            : parcial
                ? AppColors.upecYellow
                : AppColors.stateAbsent;
    final initial = estudiante.nombreCompleto.trim().isEmpty
        ? '?'
        : estudiante.nombreCompleto.trim()[0].toUpperCase();

    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      decoration: BoxDecoration(
        color: colors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.outlineVariant),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 15,
                      backgroundColor: colors.surfaceContainerHighest,
                      child: Text(
                        initial,
                        style: TextStyle(
                          color: colors.primary,
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            estudiante.nombreCompleto,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: colors.onSurface,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${estudiante.codigo} • ${estudiante.hora}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: colors.onSurfaceVariant,
                              fontSize: 8,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 4),
                      decoration: BoxDecoration(
                        color: presente
                            ? AppColors.statePresentBg
                            : atrasado
                                ? AppColors.stateLateBg
                                : parcial
                                    ? AppColors.upecYellow
                                    : AppColors.stateAbsentBg,
                        border: Border.all(color: color.withOpacity(0.45)),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Text(
                        estudiante.estado.toUpperCase(),
                        style: const TextStyle(
                          color: Colors.black,
                          fontSize: 8,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                    if (estudiante.periodos.isEmpty)
                      IconButton(
                        onPressed: onToggle,
                        visualDensity: VisualDensity.compact,
                        constraints: const BoxConstraints.tightFor(
                            width: 34, height: 34),
                        padding: EdgeInsets.zero,
                        icon: Icon(
                          presente
                              ? Icons.check_circle
                              : Icons.radio_button_unchecked,
                          color: presente
                              ? AppColors.upecGreen
                              : AppColors.borderDark,
                          size: 20,
                        ),
                      ),
                  ],
                ),
                if (estudiante.periodos.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 6,
                    runSpacing: 0,
                    children: estudiante.periodos.map((periodo) {
                      final marcado = {
                        'Presente',
                        'Atrasado',
                        'Justificado',
                      }.contains(periodo.estado);
                      return Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(
                            width: 34,
                            height: 34,
                            child: Checkbox(
                              value: marcado,
                              visualDensity: VisualDensity.compact,
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              onChanged: (value) => onPeriodChanged(
                                periodo,
                                value ?? false,
                              ),
                            ),
                          ),
                          GestureDetector(
                            onTap: () => onPeriodTap(periodo),
                            child: Padding(
                              padding: const EdgeInsets.only(right: 4),
                              child: Text(
                                '${periodo.indice} ${periodo.inicio}-${periodo.fin}',
                                style: TextStyle(
                                  color: colors.onSurfaceVariant,
                                  fontSize: 9,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final FaIconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.onTap,
    this.selected = false,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final color = selected ? colors.primary : colors.onSurfaceVariant;
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            FaIcon(icon, color: color, size: 18),
            const SizedBox(height: 2),
            Text(
              label,
              maxLines: 1,
              style: TextStyle(
                color: color,
                fontSize: 9,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CarchitoVoiceAssistantSheet extends StatefulWidget {
  final int materiaId;
  final String materiaNombre;
  final VoidCallback onCommandCompleted;
  final VoidCallback onStartScan;

  const _CarchitoVoiceAssistantSheet({
    required this.materiaId,
    required this.materiaNombre,
    required this.onCommandCompleted,
    required this.onStartScan,
  });

  @override
  State<_CarchitoVoiceAssistantSheet> createState() =>
      _CarchitoVoiceAssistantSheetState();
}

class _CarchitoVoiceAssistantSheetState
    extends State<_CarchitoVoiceAssistantSheet> {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();
  bool _speechReady = false;
  bool _listening = false;
  bool _processing = false;
  bool _wakeWordActivated = false;
  String _speechLocaleId = 'es_ES';
  String _lastTranscript = '';
  Timer? _wakeWordTimer;
  Timer? _listenRestartTimer;
  String _statusText = 'Iniciando asistente de voz...';
  String _responseMessage = '¿Qué deseas hacer hoy colega?';

  @override
  void initState() {
    super.initState();
    _initAssistant();
  }

  Future<void> _initAssistant() async {
    try {
      await _tts.setLanguage("es-ES");
      await _tts.setSpeechRate(0.5);
      await _tts.setVolume(1.0);
    } catch (error) {
      if (mounted) {
        setState(() => _statusText =
            'La voz no está disponible; puedes usar los comandos rápidos.');
      }
    }
    if (!mounted) return;

    try {
      final available = await _speech.initialize(
        onStatus: (status) {
          if (mounted && status == 'notListening') {
            setState(() => _listening = false);
            _restartListeningAfterPause();
          }
        },
        onError: (error) {
          if (!mounted) return;
          setState(() {
            _speechReady = !error.permanent;
            _listening = false;
            _statusText = error.permanent
                ? 'No se pudo usar el micrófono (${error.errorMsg}). Revisa los permisos.'
                : 'No escuché un comando (${error.errorMsg}); sigo escuchando.';
          });
          if (!error.permanent) _restartListeningAfterPause();
        },
      );
      if (!mounted) return;
      _speechReady = available;
      if (available) {
        try {
          final locales = await _speech.locales();
          _speechLocaleId = selectSpanishSpeechLocale(
            locales.map((locale) => locale.localeId),
          );
        } catch (error) {
          _speechLocaleId = 'es_ES';
          if (mounted) {
            setState(() => _statusText =
                'Usaré reconocimiento de voz en español ($error).');
          }
        }
        await _speak(
            "¡Hola! Soy tu asistente Carchito. ¿Qué deseas hacer hoy?");
        if (mounted && _speechReady) _startListening();
      } else {
        setState(() =>
            _statusText = 'Micrófono no disponible; usa los comandos rápidos.');
        await _speak("Hola, soy Carchito. Puedes usar los comandos rápidos.");
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _speechReady = false;
          _listening = false;
          _statusText =
              'No pude iniciar el micrófono ($error); usa los comandos rápidos.';
        });
      }
    }
  }

  void _restartListeningAfterPause() {
    if (!mounted || !_speechReady || _processing) return;
    _listenRestartTimer?.cancel();
    _listenRestartTimer = Timer(const Duration(milliseconds: 600), () {
      if (mounted && _speechReady && !_processing && !_listening) {
        unawaited(_startListening());
      }
    });
  }

  Future<void> _speak(String text) async {
    try {
      await _tts.speak(text);
    } catch (error) {
      if (mounted) {
        setState(() => _statusText =
            'Respuesta visible; no se pudo reproducir la voz ($error).');
      }
    }
  }

  Future<void> _startListening() async {
    if (!mounted || !_speechReady || _listening || _processing) return;
    setState(() {
      _listening = true;
      _statusText = _wakeWordActivated
          ? 'Escuchando tu comando...'
          : 'Escuchando "Hola Carchito"...';
    });
    try {
      await _speech.listen(
        listenOptions: stt.SpeechListenOptions(
          localeId: _speechLocaleId,
          listenFor: const Duration(minutes: 1),
          pauseFor: const Duration(seconds: 5),
        ),
        onResult: (result) {
          final words = result.recognizedWords.trim();
          if (words.isNotEmpty && mounted) {
            setState(() => _lastTranscript = words);
          }
          if (result.finalResult && words.isNotEmpty) {
            unawaited(_handleVoiceInput(words));
          }
        },
      );
    } catch (error) {
      if (mounted) {
        setState(() {
          _speechReady = false;
          _listening = false;
          _statusText = 'No se pudo iniciar la escucha ($error).';
        });
      }
    }
  }

  Future<void> _handleVoiceInput(String rawWords) async {
    if (!mounted) return;
    if (_processing) return;
    final command = normalizeCarchitoCommand(
      rawWords,
      wakeWordActivated: _wakeWordActivated,
    );
    if (command == null) {
      setState(() {
        _wakeWordActivated = false;
        _statusText = 'Di "Hola Carchito" para activar un comando';
      });
      return;
    }
    if (command == 'hola carchito') {
      _wakeWordTimer?.cancel();
      _wakeWordActivated = true;
      _wakeWordTimer = Timer(const Duration(seconds: 12), () {
        _wakeWordActivated = false;
      });
      setState(() => _statusText = 'Te escucho; di ahora el comando.');
      return;
    }
    _wakeWordTimer?.cancel();
    _wakeWordActivated = false;
    await _processCommand(command);
  }

  Future<void> _processCommand(String command) async {
    if (!mounted) return;
    setState(() {
      _listening = false;
      _processing = true;
      _statusText = 'Procesando comando...';
      _responseMessage = 'Procesando: "$command"';
    });

    var scanStarted = false;
    try {
      final res = await ApiService.enviarComandoCarchito(
        command,
        materiaId: widget.materiaId,
      );
      if (!mounted) return;
      final msg = res['mensaje']?.toString() ?? 'Carchito procesó el comando.';
      final accion = res['accion']?.toString();
      final commandSucceeded = ![
        'error',
        'materia_no_coincide',
        'desconocido',
      ].contains(accion);
      setState(() {
        _responseMessage = msg;
        _statusText = commandSucceeded
            ? '¡Comando completado!'
            : 'Revisa el comando e inténtalo de nuevo.';
      });
      await _speak(msg);
      if (!mounted) return;
      if (accion == 'iniciar_escaneo') {
        scanStarted = true;
        widget.onStartScan();
      } else if (accion == 'consultar_reporte') {
        widget.onCommandCompleted();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _responseMessage = 'Error al procesar comando: $e';
          _statusText = 'Error de conexión';
        });
        await _speak('Lo siento, ocurrió un error.');
      }
    } finally {
      if (mounted) {
        setState(() => _processing = false);
        if (!scanStarted) _startListening();
      }
    }
  }

  @override
  void dispose() {
    _wakeWordTimer?.cancel();
    _listenRestartTimer?.cancel();
    _speech.stop();
    _tts.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          20,
          20,
          20 + MediaQuery.of(context).viewInsets.bottom,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border:
                          Border.all(color: AppColors.upecYellow, width: 2.5),
                    ),
                    child: ClipOval(
                      child: Image.asset(
                        'assets/images/carchito.png',
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const Icon(
                            Icons.support_agent,
                            color: AppColors.upecGreen),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Soy tu asistente Carchito',
                          style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              color: colors.onSurface),
                        ),
                        Text(
                          _statusText,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: _listening
                                ? AppColors.upecGreen
                                : colors.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (_listening)
                    const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: AppColors.upecGreen),
                    ),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: colors.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: colors.outlineVariant),
                ),
                child: Text(
                  _lastTranscript.isEmpty
                      ? _responseMessage
                      : 'Escuché: "$_lastTranscript"\n$_responseMessage',
                  style: TextStyle(
                      fontSize: 13,
                      color: colors.onSurface,
                      fontWeight: FontWeight.w600),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _processing || _listening
                    ? null
                    : () async {
                        if (_speechReady) {
                          await _startListening();
                        } else {
                          await _initAssistant();
                        }
                      },
                icon: const Icon(Icons.mic),
                label: Text(
                  _listening
                      ? 'Escuchando: di «Hola Carchito» y tu comando'
                      : _speechReady
                          ? 'Reintentar micrófono'
                          : 'Activar micrófono para hablar',
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'COMANDOS RÁPIDOS:',
                style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    color: colors.onSurfaceVariant),
              ),
              const SizedBox(height: 8),
              ElevatedButton.icon(
                onPressed: _processing
                    ? null
                    : () => _processCommand(
                          'Hola Carchito, toma lista de la materia de ${widget.materiaNombre}',
                        ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.upecGreen,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20)),
                ),
                icon: const Icon(Icons.mic, color: Colors.white),
                label: Text(
                  'Hola Carchito, toma lista de ${widget.materiaNombre}',
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(height: 10),
              ElevatedButton.icon(
                onPressed: _processing
                    ? null
                    : () => _processCommand(
                          'Hola Carchito, reporte de asistencia',
                        ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.upecYellow,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20)),
                ),
                icon: const Icon(Icons.bar_chart, color: Colors.black),
                label: const Text('Carchito, dame el reporte de ausencias',
                    style: TextStyle(
                        color: Colors.black, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: _processing
                    ? null
                    : () => _processCommand('Hola Carchito, ayuda'),
                icon: const Icon(Icons.help_outline),
                label: const Text('¿Qué puedes hacer?'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
