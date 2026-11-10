import base64
import binascii
import re
import threading
import time
from flask import Blueprint, jsonify, render_template, request
import runtime
from runtime import (
    TABLET_CAMERA_TIMEOUT_SECONDS, face_engine, tablet_cameras,
    tablet_cameras_lock,
)

camera_api = Blueprint('camera_api', __name__)

@camera_api.route("/api/camara/iniciar", methods=["POST"])
def api_camara():
    data = request.json or {}
    mat_id = data.get("materia_id", 1)
    if isinstance(mat_id, bool) or not isinstance(mat_id, int) or mat_id < 1:
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona una materia válida antes de iniciar el escaneo.",
        }), 400

    with runtime.camera_thread_lock:
        if runtime.camera_thread is not None and runtime.camera_thread.is_alive():
            return jsonify({
                "status": "ok",
                "mensaje": "El escaneo OpenCV ya está activo.",
            })
        face_engine._camera_stop_event.clear()
        runtime.camera_thread = threading.Thread(
            target=face_engine.ejecutar_camara_en_vivo,
            args=(mat_id,),
            daemon=True,
        )
        runtime.camera_thread.start()
    return jsonify({
        "status": "ok",
        "mensaje": "Cámara de reconocimiento facial iniciada.",
    })


@camera_api.route("/api/camara/detener", methods=["POST"])
def api_detener_camara():
    face_engine.detener_camara_en_vivo()
    return jsonify({
        "status": "ok",
        "mensaje": "Se solicitó terminar el escaneo OpenCV.",
    })


@camera_api.route("/api/camara/tablet/dispositivos", methods=["GET"])
def api_tablet_cameras():
    now = time.monotonic()
    with tablet_cameras_lock:
        connected = [
            {
                "tablet_id": tablet_id,
                "nombre": camera["nombre"],
                "estado": "Transmitiendo" if camera["activa"] else "Conectada",
                "resultado": camera["resultado"],
            }
            for tablet_id, camera in tablet_cameras.items()
            if now - camera["ultima_actividad"] <= TABLET_CAMERA_TIMEOUT_SECONDS
        ]
    return jsonify(connected)


@camera_api.route("/tablet-camera", methods=["GET"])
def tablet_camera_page():
    return render_template("tablet_camera.html")


@camera_api.route("/api/camara/tablet/heartbeat", methods=["POST"])
def api_tablet_camera_heartbeat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "mensaje": "Envía datos válidos."}), 400

    tablet_id = data.get("tablet_id")
    nombre = data.get("nombre", "Tablet Android")
    activa = data.get("activa", False)
    if not isinstance(tablet_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}", tablet_id
    ):
        return jsonify({
            "status": "error",
            "mensaje": "El identificador de la tablet no es válido.",
        }), 400
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 80:
        return jsonify({"status": "error", "mensaje": "El nombre no es válido."}), 400
    if not isinstance(activa, bool):
        return jsonify({"status": "error", "mensaje": "El estado no es válido."}), 400

    if data.get("habilitada") is False:
        with tablet_cameras_lock:
            tablet_cameras.pop(tablet_id, None)
        return jsonify({"status": "ok", "command": None})

    now = time.monotonic()
    with tablet_cameras_lock:
        camera = tablet_cameras.get(tablet_id)
        if camera is None:
            camera = {
                "nombre": nombre.strip(),
                "ultima_actividad": now,
                "activa": activa,
                "command": None,
                "resultado": None,
            }
            tablet_cameras[tablet_id] = camera
        camera["nombre"] = nombre.strip()
        camera["ultima_actividad"] = now
        camera["activa"] = activa
        command = camera["command"]
        camera["command"] = None

    return jsonify({"status": "ok", "command": command})


@camera_api.route("/api/camara/tablet/resultado", methods=["POST"])
def api_tablet_camera_result():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "mensaje": "Envía datos válidos."}), 400

    tablet_id = data.get("tablet_id")
    event_id = data.get("evento_id")
    message = data.get("mensaje")
    result_type = data.get("tipo")
    if not isinstance(tablet_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}", tablet_id
    ):
        return jsonify({"status": "error", "mensaje": "La tablet no es válida."}), 400
    if not isinstance(event_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}", event_id
    ):
        return jsonify({"status": "error", "mensaje": "El evento no es válido."}), 400
    if not isinstance(message, str) or not message.strip() or len(message) > 500:
        return jsonify({"status": "error", "mensaje": "El resultado no es válido."}), 400
    if not isinstance(result_type, str) or result_type not in {
        "reconocido",
        "fuera_horario",
        "desconocido",
    }:
        return jsonify({"status": "error", "mensaje": "El tipo de resultado no es válido."}), 400

    now = time.monotonic()
    with tablet_cameras_lock:
        camera = tablet_cameras.get(tablet_id)
        if (
            camera is None
            or now - camera["ultima_actividad"] > TABLET_CAMERA_TIMEOUT_SECONDS
        ):
            return jsonify({
                "status": "error",
                "mensaje": "La tablet no está conectada.",
            }), 404
        camera["resultado"] = {
            "evento_id": event_id,
            "mensaje": message.strip(),
            "tipo": result_type,
        }

    return jsonify({"status": "ok"})


@camera_api.route("/api/camara/tablet/comando", methods=["POST"])
def api_tablet_camera_command():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "mensaje": "Envía datos válidos."}), 400

    tablet_id = data.get("tablet_id")
    action = data.get("action")
    materia_id = data.get("materia_id")
    if not isinstance(tablet_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}", tablet_id
    ):
        return jsonify({"status": "error", "mensaje": "Selecciona una tablet válida."}), 400
    if action not in ("iniciar", "detener"):
        return jsonify({"status": "error", "mensaje": "La orden no es válida."}), 400
    if action == "iniciar" and (
        isinstance(materia_id, bool)
        or not isinstance(materia_id, int)
        or materia_id < 1
    ):
        return jsonify({"status": "error", "mensaje": "Selecciona una materia válida."}), 400

    now = time.monotonic()
    with tablet_cameras_lock:
        camera = tablet_cameras.get(tablet_id)
        if (
            camera is None
            or now - camera["ultima_actividad"] > TABLET_CAMERA_TIMEOUT_SECONDS
        ):
            return jsonify({
                "status": "error",
                "mensaje": (
                    "La tablet no está conectada. Abre la página de cámara "
                    "en Chrome y concede permiso para usar la cámara."
                ),
            }), 404
        camera["command"] = {
            "action": action,
            "materia_id": materia_id,
        }

    return jsonify({
        "status": "ok",
        "mensaje": (
            "Se envió la orden a la tablet."
            if action == "iniciar"
            else "Se solicitó detener la cámara de la tablet."
        ),
    })


@camera_api.route("/api/camara/telefono/escanear", methods=["POST"])
def api_escanear_camara_telefono():
    data = request.json or {}
    foto = data.get("foto")
    materia_id = data.get("materia_id", 1)
    rotacion = data.get("rotacion", 0)
    if rotacion not in (0, 90, 180, 270):
        return jsonify({"status": "error", "mensaje": "La rotación de cámara no es válida."}), 400
    if not isinstance(foto, str) or not foto:
        return jsonify({"status": "error", "mensaje": "Se requiere una foto capturada por la cámara."}), 400
    try:
        image_bytes = base64.b64decode(foto, validate=True)
    except (ValueError, binascii.Error):
        return jsonify({"status": "error", "mensaje": "La foto enviada no tiene un formato válido."}), 400
    if len(image_bytes) > 6 * 1024 * 1024:
        return jsonify({"status": "error", "mensaje": "La foto supera el tamaño máximo permitido de 6 MB."}), 413

    result, status_code = face_engine.reconocer_imagen(
        image_bytes,
        materia_id,
        rotacion,
        session_key=f"{request.remote_addr or 'unknown'}:{materia_id}",
    )
    return jsonify(result), status_code
