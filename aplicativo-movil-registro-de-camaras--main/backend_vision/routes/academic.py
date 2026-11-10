from flask import Blueprint, jsonify, request
from database import obtener_materias_docente

academic_api = Blueprint('academic_api', __name__)

@academic_api.route("/api/materias", methods=["GET"])
def api_materias():
    docente_id = request.args.get("docente_id", 1, type=int)
    return jsonify(obtener_materias_docente(docente_id))
