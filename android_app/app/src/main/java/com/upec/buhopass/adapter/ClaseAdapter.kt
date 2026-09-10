package com.upec.buhopass.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.upec.buhopass.R
import com.upec.buhopass.databinding.ItemClaseBinding
import com.upec.buhopass.model.Clase

class ClaseAdapter(
    private val clases: List<Clase>,
    private val onClaseClick: (Clase) -> Unit
) : RecyclerView.Adapter<ClaseAdapter.ClaseViewHolder>() {

    inner class ClaseViewHolder(private val binding: ItemClaseBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(clase: Clase) {
            binding.tvNombreMateria.text = "${clase.materia} - ${clase.paralelo}"
            binding.tvUbicacion.text = "${clase.aula} • ${clase.edificio}"
            binding.tvHorario.text = clase.horario
            binding.tvAlumnos.text = "${clase.alumnos} Alumnos"
            binding.tvBadgeEstado.text = clase.estado

            if (clase.estado.equals("Tomada", ignoreCase = true)) {
                binding.tvBadgeEstado.setBackgroundResource(R.drawable.bg_badge_tomada)
                binding.tvBadgeEstado.setTextColor(
                    ContextCompat.getColor(binding.root.context, R.color.upec_green_badge_text)
                )
            } else {
                binding.tvBadgeEstado.setBackgroundResource(R.drawable.bg_badge_pendiente)
                binding.tvBadgeEstado.setTextColor(
                    ContextCompat.getColor(binding.root.context, R.color.upec_gold_text)
                )
            }

            binding.root.setOnClickListener {
                onClaseClick(clase)
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ClaseViewHolder {
        val binding = ItemClaseBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ClaseViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ClaseViewHolder, position: Int) {
        holder.bind(clases[position])
    }

    override fun getItemCount(): Int = clases.size
}
