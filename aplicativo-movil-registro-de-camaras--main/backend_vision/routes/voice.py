from flask import Blueprint, jsonify, request
from runtime import asistente, face_engine

voice_api = Blueprint('voice_api', __name__)

@voice_api.route("/api/carchito/comando", methods=["POST"])
def api_comando():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "accion": "error",
            "mensaje": "Envía el comando como un objeto JSON.",
        }), 400

    comando = data.get("comando")
    mat_id = data.get("materia_id", 1)
    if not isinstance(comando, str) or not comando.strip():
        return jsonify({
            "accion": "error",
            "mensaje": "Escribe o dicta un comando para Carchito.",
        }), 400
    if len(comando) > 500:
        return jsonify({
            "accion": "error",
            "mensaje": "El comando es demasiado largo.",
        }), 400
    if isinstance(mat_id, bool) or not isinstance(mat_id, int) or mat_id < 1:
        return jsonify({
            "accion": "error",
            "mensaje": "Selecciona una materia válida antes de hablar con Carchito.",
        }), 400

    res = asistente.procesar_comando(
        comando,
        mat_id,
        muestras_faciales=len(face_engine.label_to_student),
    )
    return jsonify(res)
