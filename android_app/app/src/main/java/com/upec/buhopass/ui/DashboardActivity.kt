package com.upec.buhopass.ui

import android.content.Intent
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.upec.buhopass.adapter.ClaseAdapter
import com.upec.buhopass.databinding.ActivityDashboardBinding
import com.upec.buhopass.model.Clase
import java.util.Locale

class DashboardActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var binding: ActivityDashboardBinding
    private var tts: TextToSpeech? = null

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
            val intent = Intent(this, AsistenciaActivity::class.java).apply {
                putExtra("MATERIA", clase.materia)
                putExtra("PARALELO", clase.paralelo)
                putExtra("AULA", clase.aula)
                putExtra("HORARIO", clase.horario)
            }
            startActivity(intent)
        }
        binding.rvClases.layoutManager = LinearLayoutManager(this)
        binding.rvClases.adapter = adapter
    }

    private fun setupListeners() {
        // Banner Voz
        binding.bannerAsistenteVoz.setOnClickListener {
            hablarCarchito("Hola estimado docente Samuel Lascano. Por favor indique la materia para iniciar el reconocimiento facial.")
        }

        // FAB Micrófono
        binding.fabMic.setOnClickListener {
            hablarCarchito("Asistente Carchito activo. Iniciando registro biométrico para Aplicaciones Móviles.")
            Toast.makeText(this, "🎙️ Escuchando: 'Hola Carchito...'", Toast.LENGTH_SHORT).show()
        }

        // Avatar Click
        binding.imgAvatar.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("Perfil del Docente")
                .setMessage("PhD Samuel Lascano\nDocente Titular - Carrera de Computación\nUniversidad Politécnica Estatal del Carchi")
                .setPositiveButton("Cerrar", null)
                .show()
        }

        // Ver Todas
        binding.tvVerTodas.setOnClickListener {
            Toast.makeText(this, "Mostrando todas las 4 asignaturas activas del semestre", Toast.LENGTH_SHORT).show()
        }

        // Bottom Navigation Tabs
        binding.tabInicio.setOnClickListener {
            Toast.makeText(this, "Estás en la pantalla de Inicio", Toast.LENGTH_SHORT).show()
        }
        binding.tabClases.setOnClickListener {
            Toast.makeText(this, "Gestión de Asignaturas y Horarios", Toast.LENGTH_SHORT).show()
        }
        binding.tabAsistencia.setOnClickListener {
            val intent = Intent(this, AsistenciaActivity::class.java).apply {
                putExtra("MATERIA", "Aplicaciones Móviles")
                putExtra("PARALELO", "Paralelo A")
                putExtra("AULA", "Aula 402")
                putExtra("HORARIO", "08:00 AM - 09:30 AM")
            }
            startActivity(intent)
        }
        binding.tabReportes.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("Reporte de Asistencia UPEC")
                .setMessage("Resumen General:\n• Asistencia Promedio: 92.4%\n• Estudiantes Presentes: 148/160\n• Reporte exportable en formato APA / Excel.")
                .setPositiveButton("Descargar PDF", null)
                .show()
        }
    }

    private fun hablarCarchito(mensaje: String) {
        tts?.speak(mensaje, TextToSpeech.QUEUE_FLUSH, null, "CARCHITO_ID")
        Toast.makeText(this, "🦉 Carchito: $mensaje", Toast.LENGTH_LONG).show()
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
