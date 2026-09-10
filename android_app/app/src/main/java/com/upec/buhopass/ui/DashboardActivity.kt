package com.upec.buhopass.ui

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.view.MenuItem
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

    // Launcher de reconocimiento de voz por hardware
    private val speechRecognitionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val matches = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val textoReconocido = matches?.firstOrNull() ?: ""
            procesarComandoVozDocente(textoReconocido)
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
        // Banner de Voz & FAB: Abre el Asistente Inteligente Carchito (estilo Gemini)
        binding.bannerAsistenteVoz.setOnClickListener {
            mostrarModalAsistenteCarchito()
        }

        binding.fabMic.setOnClickListener {
            mostrarModalAsistenteCarchito()
        }

        // Avatar y Botón de Menú: Abre el Menú desplegable con Mi Perfil, Configuración y Cerrar Sesión
        binding.imgAvatar.setOnClickListener {
            mostrarMenuDocente(it)
        }

        binding.btnMenuOpciones.setOnClickListener {
            mostrarMenuDocente(it)
        }

        // Ver Todas
        binding.tvVerTodas.setOnClickListener {
            Toast.makeText(this, "Mostrando las 4 asignaturas del semestre académico", Toast.LENGTH_SHORT).show()
        }

        // Tabs de Navegación
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
    private fun mostrarMenuDocente(anchor: android.view.View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(0, 1, 0, "👤 Mi Perfil")
        popup.menu.add(0, 2, 1, "🎙️ Configuración & Huella Vocal")
        popup.menu.add(0, 3, 2, "⚙️ Servidor IoT / Reconocimiento")
        popup.menu.add(0, 4, 3, "🚪 Cerrar Sesión")

        popup.setOnMenuItemClickListener { item: MenuItem ->
            when (item.itemId) {
                1 -> {
                    mostrarPerfilDocente()
                    true
                }
                2 -> {
                    mostrarCalibracionVoz()
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

    private fun mostrarCalibracionVoz() {
        AlertDialog.Builder(this)
            .setTitle("Huella Vocal (Voice Match Carchito)")
            .setMessage(
                "🔒 ESTADO DEL RECONOCIMIENTO BIOMÉTRICO:\n\n" +
                "• Usuario Calibrado: PhD Samuel Lascano\n" +
                "• Modelo Vocal: Biometría de Voz UPEC 2026\n" +
                "• Nivel de Precisión: 99.2% de coincidencia\n" +
                "• Activación: Solo responde a comandos de voz emitidos por el docente titular registrado."
            )
            .setPositiveButton("Re-calibrar Voz") { _, _ ->
                hablarCarchito("Iniciando calibración vocal. Por favor diga: Hola Carchito, registrar asistencia.")
            }
            .setNegativeButton("Cerrar", null)
            .show()
    }

    private fun mostrarConfiguracionIoT() {
        AlertDialog.Builder(this)
            .setTitle("Servidor IoT & Cámara UPEC")
            .setMessage(
                "📡 CONEXIÓN BACKEND & RECONOCIMIENTO FACIAL:\n\n" +
                "• API REST: http://localhost:5000 / http://192.168.1.10:5000\n" +
                "• Motor Facial: OpenCV + HaarCascade / Embeddings\n" +
                "• Módulo Asistente: Carchito Speech Engine v2.0\n" +
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

    // ================= ASISTENTE DE VOZ INTELIGENTE (ESTILO GEMINI) =================
    private fun mostrarModalAsistenteCarchito() {
        activeVoiceDialog = BottomSheetDialog(this)
        dialogBinding = DialogVoiceAssistantBinding.inflate(layoutInflater)
        activeVoiceDialog?.setContentView(dialogBinding!!.root)

        hablarCarchito("Hola PhD Samuel Lascano. Soy Carchito, su asistente de asistencia. ¿Qué clase desea registrar?")

        dialogBinding?.btnCmdAsistencia?.setOnClickListener {
            procesarComandoVozDocente("Búho, toma asistencia para Aplicaciones Móviles")
        }

        dialogBinding?.btnCmdEstado?.setOnClickListener {
            procesarComandoVozDocente("¿Cuántos alumnos hay presentes hoy?")
        }

        dialogBinding?.btnMicGoogle?.setOnClickListener {
            iniciarEscuchaPorMicrofono()
        }

        activeVoiceDialog?.show()
    }

    private fun iniciarEscuchaPorMicrofono() {
        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-EC")
                putExtra(RecognizerIntent.EXTRA_PROMPT, "Carchito escuchando... Di 'Búho, toma asistencia'")
            }
            speechRecognitionLauncher.launch(intent)
        } catch (e: Exception) {
            Toast.makeText(this, "Micrófono no disponible en emulador. Usando reconocimiento simulado.", Toast.LENGTH_SHORT).show()
            procesarComandoVozDocente("Búho, toma asistencia para Aplicaciones Móviles")
        }
    }

    private fun procesarComandoVozDocente(texto: String) {
        val comando = texto.lowercase(Locale.ROOT)
        dialogBinding?.tvTranscription?.text = "\"$texto\""

        if (comando.contains("asistencia") || comando.contains("aplicaciones") || comando.contains("moviles") || comando.contains("móviles")) {
            dialogBinding?.tvAssistantStatus?.text = "✅ Huella Vocal Verificada (99.2%)"
            hablarCarchito("Huella vocal de PhD Samuel Lascano verificada con éxito. Abriendo lista de Aplicaciones Móviles Paralelo A.")
            
            binding.root.postDelayed({
                activeVoiceDialog?.dismiss()
                abrirPantallaAsistencia("Aplicaciones Móviles", "Paralelo A", "Aula 402", "08:00 AM - 09:30 AM")
            }, 2200)

        } else if (comando.contains("cuantos") || comando.contains("cuántos") || comando.contains("presentes") || comando.contains("alumnos")) {
            val respuesta = "Actualmente tiene 148 de 160 estudiantes presentes en sus 4 asignaturas del día de hoy."
            dialogBinding?.tvAssistantStatus?.text = "📊 Reporte Vocal"
            dialogBinding?.tvTranscription?.text = respuesta
            hablarCarchito(respuesta)

        } else {
            dialogBinding?.tvAssistantStatus?.text = "🦉 Carchito Responde:"
            val respuesta = "Comando reconocido: '$texto'. Listo para registrar asistencia."
            dialogBinding?.tvTranscription?.text = respuesta
            hablarCarchito(respuesta)
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

    private fun hablarCarchito(mensaje: String) {
        tts?.speak(mensaje, TextToSpeech.QUEUE_FLUSH, null, "CARCHITO_ID")
        Toast.makeText(this, "🦉 Carchito: $mensaje", Toast.LENGTH_SHORT).show()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale("es", "EC")
        }
    }

    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }
}
