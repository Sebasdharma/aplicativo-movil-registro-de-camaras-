package com.upec.buhopass.adapter

import android.graphics.Color
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.upec.buhopass.R
import com.upec.buhopass.databinding.ItemEstudianteBinding
import com.upec.buhopass.model.Estudiante

class EstudianteAdapter(
    private val lista: MutableList<Estudiante>,
    private val onToggleClick: (Estudiante) -> Unit
) : RecyclerView.Adapter<EstudianteAdapter.ViewHolder>() {

    class ViewHolder(val binding: ItemEstudianteBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemEstudianteBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val est = lista[position]
        holder.binding.tvNombre.text = est.nombre_completo
        holder.binding.tvDetalle.text = "${est.codigo_estudiantil} • Hora: ${est.hora} (${est.metodo})"
        holder.binding.tvEstadoBadge.text = est.estado

        if (est.estado == "Presente") {
            holder.binding.tvEstadoBadge.setTextColor(Color.parseColor("#10B981"))
            holder.binding.tvEstadoBadge.setBackgroundResource(R.drawable.bg_badge_present)
            holder.binding.ivAvatar.setColorFilter(Color.parseColor("#003366"))
        } else {
            holder.binding.tvEstadoBadge.setTextColor(Color.parseColor("#EF4444"))
            holder.binding.tvEstadoBadge.setBackgroundColor(Color.parseColor("#FCE8E6"))
            holder.binding.ivAvatar.setColorFilter(Color.parseColor("#EF4444"))
        }

        holder.binding.btnToggleManual.setOnClickListener {
            onToggleClick(est)
        }
    }

    override fun getItemCount(): Int = lista.size

    fun actualizarLista(nuevaLista: List<Estudiante>) {
        lista.clear()
        lista.addAll(nuevaLista)
        notifyDataSetChanged()
    }
}
