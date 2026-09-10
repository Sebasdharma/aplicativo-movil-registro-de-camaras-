package com.upec.buhopass.ui

import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.upec.buhopass.adapter.EstudianteAdapter
import com.upec.buhopass.databinding.ActivityDashboardBinding
import com.upec.buhopass.model.Estudiante
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class DashboardActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var binding: ActivityDashboardBinding
    private lateinit var adapter: EstudianteAdapter
    private val listaEstudiantes = mutableListOf<Estudiante>()
    private var tts: TextToSpeech? = null
    private var speechRecognizer: SpeechRecognizer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tts = TextToSpeech(this, this)
        configurarRecyclerView()
        cargarDatosSemilla()

        binding.swipeRefresh.setOnRefreshListener {
            cargarDatosSemilla()
            binding.swipeRefresh.isRefreshing = false
        }

        binding.fabCarchito.setOnClickListener {
            activarComandoVozCarchito()
        }

        // Bucle de actualización reactiva
        lifecycleScope.launch {
            while (true) {
                delay(4000)
                actualizarMetricas()
            }
        }
    }

    private fun configurarRecyclerView() {
        adapter = EstudianteAdapter(listaEstudiantes) { est ->
            // Alternar estado manual
            val nuevoEstado = if (est.estado == "Presente") "Ausente" else "Presente"
            est.estado = nuevoEstado
            est.metodo = "Manual-Docente"
            if (nuevoEstado == "Presente") {
                est.hora = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
            } else {
                est.hora = "--:--:--"
            }
            adapter.notifyDataSetChanged()
            actualizarMetricas()
            Toast.makeText(this, "${est.nombre_completo}: $nuevoEstado", Toast.LENGTH_SHORT).show()
        }
        binding.rvEstudiantes.layoutManager = LinearLayoutManager(this)
        binding.rvEstudiantes.adapter = adapter
    }

    private fun cargarDatosSemilla() {
        val mock = listOf(
            Estudiante(1, "UPEC-2026-001", "Reina Gordon Jhoel Sebastian", "Presente", "07:05:12", "Facial-Carchito"),
            Estudiante(2, "UPEC-2026-002", "Cadena Edelina", "Presente", "07:06:45", "Facial-Carchito"),
            Estudiante(3, "UPEC-2026-003", "Lema Jordy", "Ausente", "--:--:--", "No registrado"),
            Estudiante(4, "UPEC-2026-004", "Ponce Melisa", "Presente", "07:08:20", "Facial-Carchito"),
            Estudiante(5, "UPEC-2026-005", "Carlosama Daniel", "Ausente", "--:--:--", "No registrado"),
            Estudiante(6, "UPEC-2026-006", "Montenegro Valeria", "Presente", "07:12:00", "Manual-Docente")
        )
        listaEstudiantes.clear()
        listaEstudiantes.addAll(mock)
        adapter.notifyDataSetChanged()
        actualizarMetricas()
    }

    private fun actualizarMetricas() {
        val total = listaEstudiantes.size
        val presentes = listaEstudiantes.count { it.estado == "Presente" }
        val ausentes = total - presentes
        val porcentaje = if (total > 0) ((presentes.toDouble() / total) * 100).toInt() else 0

        binding.tvTotalCount.text = total.toString()
        binding.tvPresentesCount.text = presentes.toString()
        binding.tvAusentesCount.text = ausentes.toString()
        binding.tvPorcentajeAsist.text = "$porcentaje%"
    }

    private fun activarComandoVozCarchito() {
        hablarCarchito("Hola docente. ¿Desea iniciar la toma de asistencia para el aula de Aplicaciones Móviles?")
        Toast.makeText(this, "🦉 Carchito: Di 'Hola Carchito, toma asistencia'", Toast.LENGTH_LONG).show()
    }

    private fun hablarCarchito(mensaje: String) {
        tts?.speak(mensaje, TextToSpeech.QUEUE_FLUSH, null, "CarchitoVoice")
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
