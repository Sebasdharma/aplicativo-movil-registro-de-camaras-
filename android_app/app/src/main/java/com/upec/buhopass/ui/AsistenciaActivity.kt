package com.upec.buhopass.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.upec.buhopass.adapter.EstudianteAdapter
import com.upec.buhopass.databinding.ActivityAsistenciaBinding
import com.upec.buhopass.model.Estudiante

class AsistenciaActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAsistenciaBinding
    private lateinit var adapter: EstudianteAdapter

    private val estudiantes = mutableListOf(
        Estudiante("UPEC-001", "Sebastián Reina", "Ing. Computación", true, "08:02 AM", "Facial"),
        Estudiante("UPEC-002", "Edelina Cadena", "Ing. Computación", true, "08:05 AM", "Facial"),
        Estudiante("UPEC-003", "Jordy Lema", "Ing. Computación", true, "08:06 AM", "Facial"),
        Estudiante("UPEC-004", "Melisa Ponce", "Ing. Computación", true, "08:10 AM", "Facial")
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAsistenciaBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val materia = intent.getStringExtra("MATERIA") ?: "Aplicaciones Móviles"
        val paralelo = intent.getStringExtra("PARALELO") ?: "Paralelo A"
        val aula = intent.getStringExtra("AULA") ?: "Aula 402"
        val horario = intent.getStringExtra("HORARIO") ?: "08:00 AM - 09:30 AM"

        binding.toolbarAsistencia.title = "Toma de Asistencia"
        binding.toolbarAsistencia.setNavigationOnClickListener { finish() }

        binding.tvClaseTitulo.text = "$materia - $paralelo"
        binding.tvClaseInfo.text = "$aula • $horario"

        setupRecyclerView()
        actualizarContador()

        binding.btnSincronizarCamara.setOnClickListener {
            Toast.makeText(this, "📸 Escaneando cámara facial UPEC en tiempo real...", Toast.LENGTH_SHORT).show()
        }
    }

    private fun setupRecyclerView() {
        adapter = EstudianteAdapter(estudiantes) { estudiante ->
            estudiante.presente = !estudiante.presente
            adapter.notifyDataSetChanged()
            actualizarContador()
            val estado = if (estudiante.presente) "PRESENTE" else "AUSENTE"
            Toast.makeText(this, "${estudiante.nombre}: $estado", Toast.LENGTH_SHORT).show()
        }
        binding.rvEstudiantesAsistencia.layoutManager = LinearLayoutManager(this)
        binding.rvEstudiantesAsistencia.adapter = adapter
    }

    private fun actualizarContador() {
        val presentes = estudiantes.count { it.presente }
        val total = estudiantes.size
        binding.tvContadorAsistencia.text = "Presentes: $presentes / $total Estudiantes Registrados"
    }
}
