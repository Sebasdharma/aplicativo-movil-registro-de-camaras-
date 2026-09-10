package com.upec.buhopass.model

data class Estudiante(
    val id: Int,
    val codigo_estudiantil: String,
    val nombre_completo: String,
    var estado: String,
    var hora: String,
    var metodo: String
)
