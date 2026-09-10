package com.upec.buhopass.model

data class Estudiante(
    val codigo: String,
    val nombre: String,
    val carrera: String,
    var presente: Boolean = false,
    var horaRegistro: String = "--:--",
    var metodo: String = "Manual"
)
