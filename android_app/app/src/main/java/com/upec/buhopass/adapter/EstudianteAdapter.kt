package com.upec.buhopass.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.upec.buhopass.R
import com.upec.buhopass.databinding.ItemEstudianteBinding
import com.upec.buhopass.model.Estudiante

class EstudianteAdapter(
    private val estudiantes: List<Estudiante>,
    private val onToggleClick: (Estudiante) -> Unit
) : RecyclerView.Adapter<EstudianteAdapter.EstudianteViewHolder>() {

    inner class EstudianteViewHolder(private val binding: ItemEstudianteBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(estudiante: Estudiante) {
            val initials = estudiante.nombre.split(" ")
                .filter { it.isNotEmpty() }
                .take(2)
                .map { it.first() }
                .joinToString("")

            binding.tvAvatarInitials.text = if (initials.isNotEmpty()) initials else "U"
            binding.tvNombreEstudiante.text = estudiante.nombre
            binding.tvCodigoEstudiante.text = "${estudiante.codigo} • ${estudiante.carrera}"

            if (estudiante.presente) {
                binding.tvEstadoAsistencia.text = "PRESENTE"
                binding.tvEstadoAsistencia.setBackgroundResource(R.drawable.bg_badge_tomada)
                binding.tvEstadoAsistencia.setTextColor(
                    ContextCompat.getColor(binding.root.context, R.color.upec_green_badge_text)
                )
            } else {
                binding.tvEstadoAsistencia.text = "AUSENTE"
                binding.tvEstadoAsistencia.setBackgroundResource(R.drawable.bg_badge_pendiente)
                binding.tvEstadoAsistencia.setTextColor(
                    ContextCompat.getColor(binding.root.context, R.color.upec_gold_text)
                )
            }

            binding.root.setOnClickListener {
                onToggleClick(estudiante)
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): EstudianteViewHolder {
        val binding = ItemEstudianteBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return EstudianteViewHolder(binding)
    }

    override fun onBindViewHolder(holder: EstudianteViewHolder, position: Int) {
        holder.bind(estudiantes[position])
    }

    override fun getItemCount(): Int = estudiantes.size
}
