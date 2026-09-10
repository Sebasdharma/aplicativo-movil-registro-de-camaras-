package com.upec.buhopass.ui

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.upec.buhopass.databinding.ActivityWelcomeBinding

class WelcomeActivity : AppCompatActivity() {

    private lateinit var binding: ActivityWelcomeBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWelcomeBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Acción: Ingresar con Cuenta Institucional
        binding.btnIngresar.setOnClickListener {
            val prefs = getSharedPreferences("BUHOPASS_PREFS", Context.MODE_PRIVATE)
            val yaCalibrado = prefs.getBoolean("VOICE_MATCH_CALIBRATED", false)

            if (!yaCalibrado) {
                // Si es la primera vez, abre la pantalla de prueba y calibración de voz (estilo Gemini)
                val intent = Intent(this, VoiceMatchActivity::class.java)
                startActivity(intent)
            } else {
                val intent = Intent(this, DashboardActivity::class.java)
                startActivity(intent)
            }
            finish()
        }

        // Acción: Ver Guía del Docente
        binding.btnGuiaDocente.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("Guía del Docente - BúhoPass UPEC")
                .setMessage(
                    "¡Bienvenido a BúhoPass!\n\n" +
                    "1. Control de Asistencia Inteligente: Utiliza el reconocimiento facial integrado con la cámara del aula.\n\n" +
                    "2. Asistente de Voz 'Carchito' (Motor Jarvis): Se activa diciendo 'Ok Búho toma lista' y dialoga contigo para saber el curso a registrar.\n\n" +
                    "3. Corrección Manual: Puedes ajustar el estado de cualquier estudiante tocando directamente sobre su nombre.\n\n" +
                    "Desarrollado para la Carrera de Computación - 7mo Semestre."
                )
                .setPositiveButton("Entendido", null)
                .show()
        }
    }
}
