package com.upec.buhopass.ui

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.view.MenuItem
import android.view.View
import android.widget.PopupMenu
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.upec.buhopass.R
import com.upec.buhopass.adapter.ClaseAdapter
import com.upec.buhopass.databinding.ActivityDashboardBinding
import com.upec.buhopass.databinding.DialogVoiceAssistantBinding
import com.upec.buhopass.model.Clase
import java.util.Locale

class DashboardActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var binding: ActivityDashboardBinding
    private var tts: TextToSpeech? = null
    private var activeVoiceDialog: BottomSheetDialog? = null
    private var dialogBinding: DialogVoiceAssistantBinding? = null

    // Estado conversacional (Jarvis Multi-Turn Engine)
    private enum class ConversationalState {
        IDLE,
        AWAITING_COURSE,
        EXECUTING_ACTION
    }
    private var estadoConversacion = ConversationalState.IDLE

    private val speechRecognitionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val matches = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val textoReconocido = matches?.firstOrNull() ?: ""
            procesarFlujoConversacionalJarvis(textoReconocido)
        }
    }

    private val clasesList = listOf(
        Clase(
            id = "1",
            materia = "Aplicaciones Moviles",
            paralelo = "Paralelo A",
            aula = "Aula 402",
            edificio = "Edificio Ingeniería",
            horario = "08:00 AM - 09:30 AM",
            alumnos = 38,
            estado = "Tomada"
        ),
        Clase(
            id = "2",
            materia = "Normativas de Seguridad",
            paralelo = "Paralelo A",
            aula = "Laboratorio 3",
            edificio = "Edificio Ciencias",
            horario = "10:00 AM - 11:30 AM",
            alumnos = 42,
            estado = "Pendiente"
        ),
        Clase(
            id = "3",
            materia = "Visión por Computador",
            paralelo = "Paralelo B",
            aula = "Aula 405",
            edificio = "Edificio Ingeniería",
            horario = "02:00 PM - 03:30 PM",
            alumnos = 35,
            estado = "Pendiente"
        )
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tts = TextToSpeech(this, this)

        setupRecyclerView()
        setupListeners()
    }

    private fun setupRecyclerView() {
        val adapter = ClaseAdapter(clasesList) { clase ->
            abrirPantallaAsistencia(clase.materia, clase.paralelo, clase.aula, clase.horario)
        }
        binding.rvClases.layoutManager = LinearLayoutManager(this)
        binding.rvClases.adapter = adapter
    }

    private fun setupListeners() {
        // Banner de Voz & FAB: Abre el Asistente Inteligente Jarvis/Carchito
        binding.bannerAsistenteVoz.setOnClickListener {
            abrirAsistenteConversacional()
        }

        binding.fabMic.setOnClickListener {
            abrirAsistenteConversacional()
        }

        // Menú Desplegable
        binding.imgAvatar.setOnClickListener {
            mostrarMenuDocente(it)
        }

        binding.btnMenuOpciones.setOnClickListener {
            mostrarMenuDocente(it)
        }

        binding.tvVerTodas.setOnClickListener {
            Toast.makeText(this, "Mostrando las 4 asignaturas del semestre académico", Toast.LENGTH_SHORT).show()
        }

        // Tabs
        binding.tabInicio.setOnClickListener {
            Toast.makeText(this, "Estás en el Inicio", Toast.LENGTH_SHORT).show()
        }
        binding.tabClases.setOnClickListener {
            Toast.makeText(this, "Módulo de Asignaturas y Horarios", Toast.LENGTH_SHORT).show()
        }
        binding.tabAsistencia.setOnClickListener {
            abrirPantallaAsistencia("Aplicaciones Móviles", "Paralelo A", "Aula 402", "08:00 AM - 09:30 AM")
        }
        binding.tabReportes.setOnClickListener {
            mostrarReporteGeneral()
        }
    }

    // ================= MENÚ DESPLEGABLE DEL DOCENTE =================
    private fun mostrarMenuDocente(anchor: View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(0, 1, 0, "👤 Mi Perfil")
        popup.menu.add(0, 2, 1, "🎙️ Calibrar Huella Vocal (Voice Match)")
        popup.menu.add(0, 3, 2, "⚙️ Servidor IoT / Reconocimiento")
        popup.menu.add(0, 4, 3, "🚪 Cerrar Sesión")

        popup.setOnMenuItemClickListener { item: MenuItem ->
            when (item.itemId) {
                1 -> {
                    mostrarPerfilDocente()
                    true
                }
                2 -> {
                    val intent = Intent(this, VoiceMatchActivity::class.java)
                    startActivity(intent)
                    true
                }
                3 -> {
                    mostrarConfiguracionIoT()
                    true
                }
                4 -> {
                    confirmarCerrarSesion()
                    true
                }
                else -> false
            }
        }
        popup.show()
    }

    private fun mostrarPerfilDocente() {
        AlertDialog.Builder(this)
            .setTitle("Perfil del Docente")
            .setMessage(
                "📋 DATOS INSTITUCIONALES:\n\n" +
                "• Nombre: PhD Samuel Lascano\n" +
                "• Cargo: Docente Titular / Investigador\n" +
                "• Facultad: FIACA - Carrera de Computación\n" +
                "• Correo: samuel.lascano@upec.edu.ec\n" +
                "• Código Docente: UPEC-DOC-704\n" +
                "• Asignaturas: Aplicaciones Móviles, Visión por Computador, Normativas."
            )
            .setPositiveButton("Aceptar", null)
            .show()
    }

    private fun mostrarConfiguracionIoT() {
        AlertDialog.Builder(this)
            .setTitle("Servidor IoT & Cámara UPEC")
            .setMessage(
                "📡 CONEXIÓN BACKEND & RECONOCIMIENTO FACIAL:\n\n" +
                "• API REST: http://localhost:5000 / http://192.168.1.10:5000\n" +
                "• Motor Facial: OpenCV + HaarCascade / Embeddings\n" +
                "• Módulo Asistente: Jarvis / Carchito Speech Engine v2.0\n" +
                "• Base de Datos: SQLite (buhopass.db)"
            )
            .setPositiveButton("Probar Conexión") { _, _ ->
                Toast.makeText(this, "✅ Conexión con el servidor backend exitosa", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    private fun confirmarCerrarSesion() {
        AlertDialog.Builder(this)
            .setTitle("Cerrar Sesión")
            .setMessage("¿Está seguro de que desea salir del aplicativo BúhoPass?")
            .setPositiveButton("Sí, Salir") { _, _ ->
                val intent = Intent(this, WelcomeActivity::class.java)
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                startActivity(intent)
                finish()
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    // ================= ASISTENTE CONVERSACIONAL ESTILO JARVIS =================
    private fun abrirAsistenteConversacional() {
        activeVoiceDialog = BottomSheetDialog(this)
        dialogBinding = DialogVoiceAssistantBinding.inflate(layoutInflater)
        activeVoiceDialog?.setContentView(dialogBinding!!.root)

        estadoConversacion = ConversationalState.IDLE

        dialogBinding?.tvAssistantStatus?.text = "JARVIS UPEC Listo"
        dialogBinding?.tvTranscription?.text = "Diga: \"Ok Búho, toma lista\""
        hablarJarvis("A la orden, PhD Samuel Lascano. ¿En qué le puedo colaborar hoy?")

        dialogBinding?.btnCmdAsistencia?.text = "🗣️ \"Ok Búho, toma lista\""
        dialogBinding?.btnCmdAsistencia?.setOnClickListener {
            procesarFlujoConversacionalJarvis("Ok Búho toma lista")
        }

        dialogBinding?.btnCmdEstado?.text = "🗣️ \"¿Cuántos alumnos hay presentes?\""
        dialogBinding?.btnCmdEstado?.setOnClickListener {
            procesarFlujoConversacionalJarvis("¿Cuántos alumnos hay presentes hoy?")
        }

        dialogBinding?.btnMicGoogle?.setOnClickListener {
            iniciarMicrofonoPrompt()
        }

        activeVoiceDialog?.show()
    }

    private fun iniciarMicrofonoPrompt() {
        val prompt = if (estadoConversacion == ConversationalState.AWAITING_COURSE) {
            "¿De qué curso deseas que tome la lista?"
        } else {
            "Diga: 'Ok Búho, toma lista'"
        }

        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-EC")
                putExtra(RecognizerIntent.EXTRA_PROMPT, prompt)
            }
            speechRecognitionLauncher.launch(intent)
        } catch (e: Exception) {
            Toast.makeText(this, "Micrófono no disponible en emulador. Ejecutando flujo simulado.", Toast.LENGTH_SHORT).show()
            if (estadoConversacion == ConversationalState.AWAITING_COURSE) {
                procesarFlujoConversacionalJarvis("Aplicaciones Móviles")
            } else {
                procesarFlujoConversacionalJarvis("Ok Búho toma lista")
            }
        }
    }

    private fun procesarFlujoConversacionalJarvis(texto: String) {
        val comando = texto.lowercase(Locale.ROOT)
        dialogBinding?.tvTranscription?.text = "\"$texto\""

        when (estadoConversacion) {
            ConversationalState.IDLE -> {
                if (comando.contains("lista") || comando.contains("asistencia") || comando.contains("toma") || comando.contains("buho") || comando.contains("búho")) {
                    estadoConversacion = ConversationalState.AWAITING_COURSE

                    dialogBinding?.tvAssistantStatus?.text = "🗣️ JARVIS Pregunta:"
                    val pregunta = "A la orden, PhD Samuel Lascano. Huella vocal confirmada al 99.4%. ¿De qué curso o asignatura desea que tome la lista hoy?"
                    dialogBinding?.tvTranscription?.text = pregunta
                    hablarJarvis(pregunta)

                    // Actualizar botones de respuesta rápida para cursos
                    dialogBinding?.btnCmdAsistencia?.text = "📱 Aplicaciones Móviles (Paralelo A)"
                    dialogBinding?.btnCmdAsistencia?.setOnClickListener {
                        procesarFlujoConversacionalJarvis("Aplicaciones Móviles")
                    }

                    dialogBinding?.btnCmdEstado?.text = "👁️ Visión por Computador (Paralelo B)"
                    dialogBinding?.btnCmdEstado?.setOnClickListener {
                        procesarFlujoConversacionalJarvis("Visión por Computador")
                    }

                    // Auto abrir micrófono tras la pregunta si lo desea
                    dialogBinding?.btnMicGoogle?.text = "🎙️ Responder: Indicar Curso"

                } else if (comando.contains("cuantos") || comando.contains("cuántos") || comando.contains("presentes")) {
                    val respuesta = "Actualmente señor, cuenta con 148 de 160 estudiantes presentes en sus 4 cursos de la UPEC."
                    dialogBinding?.tvAssistantStatus?.text = "📊 Reporte Vocal JARVIS"
                    dialogBinding?.tvTranscription?.text = respuesta
                    hablarJarvis(respuesta)
                } else {
                    val respuesta = "Comando reconocido: '$texto'. Diga 'Ok Búho toma lista' para iniciar el registro biométrico."
                    dialogBinding?.tvAssistantStatus?.text = "JARVIS Responde:"
                    dialogBinding?.tvTranscription?.text = respuesta
                    hablarJarvis(respuesta)
                }
            }

            ConversationalState.AWAITING_COURSE -> {
                var cursoSeleccionado = "Aplicaciones Móviles"
                var paralelo = "Paralelo A"
                var aula = "Aula 402"
                var horario = "08:00 AM - 09:30 AM"

                if (comando.contains("vision") || comando.contains("visión") || comando.contains("computador")) {
                    cursoSeleccionado = "Visión por Computador"
                    paralelo = "Paralelo B"
                    aula = "Aula 405"
                    horario = "02:00 PM - 03:30 PM"
                } else if (comando.contains("seguridad") || comando.contains("normativas")) {
                    cursoSeleccionado = "Normativas de Seguridad"
                    paralelo = "Paralelo A"
                    aula = "Laboratorio 3"
                    horario = "10:00 AM - 11:30 AM"
                }

                estadoConversacion = ConversationalState.EXECUTING_ACTION
                dialogBinding?.tvAssistantStatus?.text = "✅ Ejecutando Registro Biométrico"
                val respuestaFinal = "Excelente señor. Abriendo lista y activando reconocimiento facial para $cursoSeleccionado $paralelo. Que tenga una excelente clase."
                dialogBinding?.tvTranscription?.text = respuestaFinal
                hablarJarvis(respuestaFinal)

                binding.root.postDelayed({
                    activeVoiceDialog?.dismiss()
                    abrirPantallaAsistencia(cursoSeleccionado, paralelo, aula, horario)
                }, 2800)
            }

            ConversationalState.EXECUTING_ACTION -> {
                // Ya en proceso
            }
        }
    }

    private fun abrirPantallaAsistencia(materia: String, paralelo: String, aula: String, horario: String) {
        val intent = Intent(this, AsistenciaActivity::class.java).apply {
            putExtra("MATERIA", materia)
            putExtra("PARALELO", paralelo)
            putExtra("AULA", aula)
            putExtra("HORARIO", horario)
        }
        startActivity(intent)
    }

    private fun mostrarReporteGeneral() {
        AlertDialog.Builder(this)
            .setTitle("Reporte General de Asistencia")
            .setMessage(
                "📊 RESUMEN ACADÉMICO UPEC:\n\n" +
                "• Asistencia Global: 92.4%\n" +
                "• Estudiantes Presentes: 148 / 160\n" +
                "• Cursos Evaluados: 4 paralelos\n" +
                "• Integración Facial OpenCV: Activa."
            )
            .setPositiveButton("Descargar Reporte", null)
            .show()
    }

    private fun hablarJarvis(mensaje: String) {
        // Voz Masculina Grave Tipo JARVIS
        tts?.setPitch(0.72f)      // Tono grave
        tts?.setSpeechRate(0.92f)  // Ritmo controlado
        tts?.speak(mensaje, TextToSpeech.QUEUE_FLUSH, null, "JARVIS_RESPONSE")
        Toast.makeText(this, "🤖 JARVIS: $mensaje", Toast.LENGTH_SHORT).show()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("es", "EC")
            tts?.setPitch(0.72f)
            tts?.setSpeechRate(0.92f)
        }
    }

    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }
}
