from flask import Blueprint, jsonify
from database import obtener_dispositivos_iot

device_api = Blueprint('device_api', __name__)

@device_api.route("/api/dispositivos", methods=["GET"])
def api_dispositivos():
    return jsonify(obtener_dispositivos_iot())
