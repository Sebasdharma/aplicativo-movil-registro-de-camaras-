package com.upec.buhopass.model

data class Clase(
    val id: String,
    val materia: String,
    val paralelo: String,
    val aula: String,
    val edificio: String,
    val horario: String,
    val alumnos: Int,
    val estado: String // "Tomada" o "Pendiente"
)
