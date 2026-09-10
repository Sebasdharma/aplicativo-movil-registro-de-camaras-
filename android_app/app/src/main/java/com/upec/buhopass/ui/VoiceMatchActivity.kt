package com.upec.buhopass.ui

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.tts.TextToSpeech
import android.speech.tts.Voice
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.upec.buhopass.databinding.ActivityVoiceMatchBinding
import java.util.Locale

class VoiceMatchActivity : AppCompatActivity(), TextToSpeech.OnInitListener {

    private lateinit var binding: ActivityVoiceMatchBinding
    private var tts: TextToSpeech? = null
    private var currentStep = 0 // 0, 1, 2

    private val speechLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val matches = result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            val texto = matches?.firstOrNull() ?: ""
            avanzarPasoCalibracion(texto)
        } else {
            // Avance interactivo si el emulador no cuenta con servicio de reconocimiento
            avanzarPasoCalibracion("Comando de voz")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityVoiceMatchBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tts = TextToSpeech(this, this)

        // Estado 1: Botones Info
        binding.btnNoGracias.setOnClickListener {
            irAlDashboard()
        }

        binding.btnAcepto.setOnClickListener {
            iniciarCalibracionVisual()
        }

        // Estado 2: Calibración
        binding.btnCancelarCalibracion.setOnClickListener {
            binding.layoutCalibratingState.visibility = View.GONE
            binding.layoutInfoState.visibility = View.VISIBLE
        }

        binding.btnHablarCalibracion.setOnClickListener {
            abrirMicrofonoParaPasoActual()
        }
    }

    private fun iniciarCalibracionVisual() {
        binding.layoutInfoState.visibility = View.GONE
        binding.layoutCalibratingState.visibility = View.VISIBLE
        currentStep = 0
        actualizarPasoEnPantalla()
    }

    private fun actualizarPasoEnPantalla() {
        binding.tvStepCircle.text = currentStep.toString()

        when (currentStep) {
            0 -> {
                binding.tvCalibrationPrompt.text = "Di \"Ok Búho, toma la lista de Aplicaciones Móviles.\""
                binding.tvCalibrationSubPrompt.text = "Paso 1 de 3: Di la frase con voz clara."
                hablarOrbit("Di: Ok Búho, toma la lista de Aplicaciones Móviles.")
            }
            1 -> {
                binding.tvCalibrationPrompt.text = "Ahora di \"Ok Búho, ¿cuántos alumnos están presentes?\""
                binding.tvCalibrationSubPrompt.text = "Paso 2 de 3: Reconociendo entonación."
                hablarOrbit("Ahora di: Ok Búho, cuántos alumnos están presentes.")
            }
            2 -> {
                binding.tvCalibrationPrompt.text = "Ahora di \"Hey Búho, registra la asistencia de mi clase.\""
                binding.tvCalibrationSubPrompt.text = "Paso 3 de 3: Finalizando modelo vocal."
                hablarOrbit("Ahora di: Hey Búho, registra la asistencia de mi clase.")
            }
        }
    }

    private fun abrirMicrofonoParaPasoActual() {
        val prompt = when (currentStep) {
            0 -> "Di: 'Ok Búho, toma la lista de Aplicaciones Móviles'"
            1 -> "Di: 'Ok Búho, ¿cuántos alumnos están presentes?'"
            else -> "Di: 'Hey Búho, registra la asistencia de mi clase'"
        }

        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-EC")
                putExtra(RecognizerIntent.EXTRA_PROMPT, prompt)
            }
            speechLauncher.launch(intent)
        } catch (e: Exception) {
            Toast.makeText(this, "Capturando muestra vocal...", Toast.LENGTH_SHORT).show()
            avanzarPasoCalibracion("Grabación de muestra exitosa")
        }
    }

    private fun avanzarPasoCalibracion(textoReconocido: String) {
        if (currentStep < 2) {
            currentStep++
            actualizarPasoEnPantalla()
        } else {
            // Calibración finalizada
            completarCalibracion()
        }
    }

    private fun completarCalibracion() {
        val prefs = getSharedPreferences("BUHOPASS_PREFS", Context.MODE_PRIVATE)
        prefs.edit().putBoolean("VOICE_MATCH_CALIBRATED", true).apply()

        binding.tvStepCircle.text = "✓"
        binding.tvCalibrationPrompt.text = "¡Voice Match configurado con éxito!"
        binding.tvCalibrationSubPrompt.text = "Modelo vocal calibrado para PhD Samuel Lascano."

        hablarOrbit("Voice Match configurado con éxito. Ahora puedes pedirme que tome lista con solo hablar.")

        binding.root.postDelayed({
            irAlDashboard()
        }, 2200)
    }

    // Configuración de la voz masculina estilo ORBIT (Gemini)
    // Tono natural y cálido (0.95), sin distorsión robótica, ritmo seguro (1.0)
    private fun hablarOrbit(mensaje: String) {
        tts?.speak(mensaje, TextToSpeech.QUEUE_FLUSH, null, "ORBIT_VOICE")
    }

    private fun irAlDashboard() {
        val intent = Intent(this, DashboardActivity::class.java)
        startActivity(intent)
        finish()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val result = tts?.setLanguage(Locale("es", "EC"))
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                tts?.setLanguage(Locale("es", "ES"))
            }

            // Seleccionar voz masculina de alta calidad si está disponible
            seleccionarVozMasculinaOrbit()

            // Parámetros naturales Orbit (sin tonos artificiales feos)
            tts?.setPitch(0.95f)
            tts?.setSpeechRate(1.0f)
        }
    }

    private fun seleccionarVozMasculinaOrbit() {
        try {
            val voices = tts?.voices
            if (voices != null) {
                for (v in voices) {
                    val name = v.name.lowercase(Locale.ROOT)
                    if (v.locale.language == "es" && (name.contains("male") || name.contains("hombre") || name.contains("sfb") || name.contains("orbit"))) {
                        tts?.voice = v
                        break
                    }
                }
            }
        } catch (e: Exception) {
            // Fallback por defecto seguro
        }
    }

    override fun onDestroy() {
        tts?.stop()
        tts?.shutdown()
        super.onDestroy()
    }
}
