from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
import binascii
import os
import re
import cv2
import numpy as np
import uuid
import jwt
from database import (
    init_db, get_db, registrar_asistencia_db, obtener_resumen_asistencia,
    obtener_materias_docente, obtener_dispositivos_iot,
    inscribir_estudiante_en_materia, aplicar_ausencias_programadas,
)
from carchito_voice import CarchitoVoiceAssistant
from face_engine import FaceEngine
import threading
from datetime import datetime

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024
CORS(app)

MICROSOFT_TENANT_ID = os.environ.get(
    "MICROSOFT_TENANT_ID",
    "0a42bec9-732b-45d1-977d-3b8d3ac98c2b",
)
MICROSOFT_CLIENT_ID = os.environ.get(
    "MICROSOFT_CLIENT_ID",
    "6a39d754-3c15-4599-b074-3925b7c7e77e",
)
MICROSOFT_ISSUER = (
    f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/v2.0"
)
MICROSOFT_JWKS_CLIENT = jwt.PyJWKClient(
    f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}"
    "/discovery/v2.0/keys"
)

init_db()
asistente = CarchitoVoiceAssistant()
face_engine = FaceEngine()
camera_thread = None
camera_thread_lock = threading.Lock()


def verificar_token_microsoft(id_token):
    signing_key = MICROSOFT_JWKS_CLIENT.get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=MICROSOFT_CLIENT_ID,
        issuer=MICROSOFT_ISSUER,
        options={"require": ["exp", "iss", "aud", "tid", "oid"]},
    )


@app.route("/api/auth/admin", methods=["POST"])
def api_auth_admin():
    conn = get_db()
    try:
        docente = conn.execute(
            """
            SELECT id, email_institucional, nombre_completo, cedula, facultad, carrera
            FROM docentes
            WHERE email_institucional = ?
            """,
            ("admin@upec.edu.ec",),
        ).fetchone()
    finally:
        conn.close()

    if docente is None:
        return jsonify({
            "status": "error",
            "mensaje": "No está configurada la cuenta de administrador.",
        }), 503

    return jsonify({
        "status": "ok",
        "provider": "admin_development",
        "docente": dict(docente),
    })


@app.route("/api/auth/microsoft", methods=["POST"])
def api_auth_microsoft():
    data = request.get_json(silent=True)
    id_token = data.get("id_token") if isinstance(data, dict) else None
    if not isinstance(id_token, str) or not id_token:
        return jsonify({
            "status": "error",
            "mensaje": "Microsoft no envió un token de identidad válido.",
        }), 400

    try:
        claims = verificar_token_microsoft(id_token)
    except jwt.PyJWKClientError:
        app.logger.exception("No se pudo obtener la firma pública de Microsoft.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo verificar la respuesta de Microsoft. Intenta de nuevo.",
        }), 503
    except jwt.PyJWTError:
        return jsonify({
            "status": "error",
            "mensaje": "Microsoft devolvió un token inválido o vencido.",
        }), 401

    if claims.get("tid") != MICROSOFT_TENANT_ID:
        return jsonify({
            "status": "error",
            "mensaje": "La cuenta no pertenece al directorio institucional configurado.",
        }), 403

    email = claims.get("preferred_username") or claims.get("email")
    if not isinstance(email, str) or not email:
        return jsonify({
            "status": "error",
            "mensaje": "Microsoft no proporcionó un correo para esta cuenta.",
        }), 403

    conn = get_db()
    try:
        docente = conn.execute(
            """
            SELECT id, email_institucional, nombre_completo, cedula, facultad, carrera
            FROM docentes
            WHERE LOWER(email_institucional) = LOWER(?)
            """,
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if docente is None:
        return jsonify({
            "status": "error",
            "mensaje": (
                "Tu cuenta Microsoft se autenticó, pero aún no está registrada "
                "como docente de AsisTech. Para las pruebas actuales, ingresa "
                "con el acceso temporal de Administrador."
            ),
        }), 403

    return jsonify({
        "status": "ok",
        "provider": "microsoft",
        "docente": dict(docente),
    })


@app.route("/api/materias", methods=["GET"])
def api_materias():
    docente_id = request.args.get("docente_id", 1, type=int)
    return jsonify(obtener_materias_docente(docente_id))

@app.route("/api/asistencia/resumen", methods=["GET"])
def api_resumen():
    materia_id = request.args.get("materia_id", 1, type=int)
    fecha = request.args.get("fecha")
    try:
        return jsonify(obtener_resumen_asistencia(materia_id, fecha))
    except ValueError as error:
        return jsonify({"status": "error", "mensaje": str(error)}), 400
    except Exception:
        app.logger.exception("No se pudo consultar la asistencia por periodos.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo consultar la asistencia. Intenta de nuevo.",
        }), 500

@app.route("/api/asistencia/manual", methods=["POST"])
def api_manual():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "mensaje": "Envía los datos de asistencia como un objeto JSON.",
        }), 400

    est_id = data.get("estudiante_id")
    mat_id = data.get("materia_id", 1)
    estado = data.get("estado", "Presente")
    metodo = data.get("metodo", "Manual-Docente")
    dispositivo_id = data.get("dispositivo_id")
    periodo_indice = data.get("periodo_indice")
    if isinstance(est_id, bool) or not isinstance(est_id, int) or est_id < 1:
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona un estudiante válido.",
        }), 400
    if isinstance(mat_id, bool) or not isinstance(mat_id, int) or mat_id < 1:
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona una materia válida.",
        }), 400
    if not isinstance(estado, str) or estado not in {
        "Presente",
        "Ausente",
        "Atrasado",
        "Justificado",
    }:
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona un estado de asistencia válido.",
        }), 400
    if not isinstance(metodo, str) or not metodo.strip() or len(metodo) > 40:
        return jsonify({
            "status": "error",
            "mensaje": "El método de registro no es válido.",
        }), 400
    if dispositivo_id is not None and (
        isinstance(dispositivo_id, bool)
        or not isinstance(dispositivo_id, int)
        or dispositivo_id < 1
    ):
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona un dispositivo válido.",
        }), 400
    if periodo_indice is not None and (
        isinstance(periodo_indice, bool)
        or not isinstance(periodo_indice, int)
        or periodo_indice < 1
    ):
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona una hora de clase válida.",
        }), 400

    try:
        res = registrar_asistencia_db(
            est_id,
            mat_id,
            estado=estado,
            metodo=metodo,
            dispositivo_id=dispositivo_id,
            periodo_indice=periodo_indice,
        )
        return jsonify(res)
    except ValueError as error:
        return jsonify({"status": "error", "mensaje": str(error)}), 400
    except Exception:
        app.logger.exception("No se pudo registrar la asistencia manual.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo guardar la asistencia. Intenta de nuevo.",
        }), 500

@app.route("/api/dispositivos", methods=["GET"])
def api_dispositivos():
    return jsonify(obtener_dispositivos_iot())

@app.route("/api/carchito/comando", methods=["POST"])
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

@app.route("/api/camara/iniciar", methods=["POST"])
def api_camara():
    global camera_thread
    data = request.json or {}
    mat_id = data.get("materia_id", 1)
    if isinstance(mat_id, bool) or not isinstance(mat_id, int) or mat_id < 1:
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona una materia válida antes de iniciar el escaneo.",
        }), 400

    with camera_thread_lock:
        if camera_thread is not None and camera_thread.is_alive():
            return jsonify({
                "status": "ok",
                "mensaje": "El escaneo OpenCV ya está activo.",
            })
        face_engine._camera_stop_event.clear()
        camera_thread = threading.Thread(
            target=face_engine.ejecutar_camara_en_vivo,
            args=(mat_id,),
            daemon=True,
        )
        camera_thread.start()
    return jsonify({
        "status": "ok",
        "mensaje": "Cámara de reconocimiento facial iniciada.",
    })


@app.route("/api/camara/detener", methods=["POST"])
def api_detener_camara():
    face_engine.detener_camara_en_vivo()
    return jsonify({
        "status": "ok",
        "mensaje": "Se solicitó terminar el escaneo OpenCV.",
    })

@app.route("/api/camara/telefono/escanear", methods=["POST"])
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

@app.route("/api/estudiantes/enrolar", methods=["POST"])
def api_enrolar():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "mensaje": "Envía los datos del estudiante como JSON."}), 400
    codigo = data.get("codigo")
    nombre = data.get("nombre")
    paralelo = data.get("paralelo", "7mo Semestre - Paralelo AM")
    email = data.get("email")
    materia_id = data.get("materia_id")
    fotos = data.get("fotos")
    if fotos is None and data.get("foto") is not None:
        fotos = [data["foto"]]

    if not codigo or not nombre:
        return jsonify({"status": "error", "mensaje": "Código y nombre requeridos"}), 400
    if not isinstance(codigo, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", codigo):
        return jsonify({"status": "error", "mensaje": "El código estudiantil contiene caracteres no válidos."}), 400
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > 160:
        return jsonify({"status": "error", "mensaje": "Ingresa un nombre válido para el estudiante."}), 400
    if isinstance(materia_id, bool) or not isinstance(materia_id, int) or materia_id < 1:
        return jsonify({"status": "error", "mensaje": "Selecciona una materia válida."}), 400
    images = []
    if fotos is not None:
        if (
            not isinstance(fotos, list)
            or not fotos
            or len(fotos) > 5
            or any(not isinstance(foto, str) or not foto for foto in fotos)
        ):
            return jsonify({
                "status": "error",
                "mensaje": "Envía de 1 a 5 fotos faciales válidas.",
            }), 400
        if data.get("consentimiento_biometrico") is not True:
            return jsonify({"status": "error", "mensaje": "Se requiere confirmar la autorización antes de guardar las fotos faciales."}), 400
        total_image_bytes = 0
        for foto in fotos:
            try:
                image_bytes = base64.b64decode(foto, validate=True)
            except (ValueError, binascii.Error):
                return jsonify({"status": "error", "mensaje": "Una de las fotos enviadas no tiene un formato válido."}), 400
            total_image_bytes += len(image_bytes)
            if len(image_bytes) > 6 * 1024 * 1024:
                return jsonify({"status": "error", "mensaje": "Cada foto debe pesar menos de 6 MB."}), 413
            if total_image_bytes > 8 * 1024 * 1024:
                return jsonify({"status": "error", "mensaje": "El conjunto de fotos supera el límite total de 8 MB."}), 413
            valido, mensaje = face_engine.validar_foto_enrolamiento(image_bytes)
            if not valido:
                return jsonify({"status": "error", "mensaje": mensaje}), 400
            image = cv2.imdecode(
                np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
            )
            if image is None:
                return jsonify({"status": "error", "mensaje": "No se pudo leer una de las fotos enviadas."}), 400
            images.append(image)

    conn = get_db()
    cursor = conn.cursor()
    saved_photo_paths = []
    try:
        if cursor.execute("SELECT 1 FROM materias WHERE id = ?", (materia_id,)).fetchone() is None:
            return jsonify({"status": "error", "mensaje": "La materia seleccionada no existe."}), 404

        cursor.execute("SELECT id FROM estudiantes WHERE codigo_estudiantil = ?", (codigo,))
        existente = cursor.fetchone()
        if existente:
            estudiante_id = existente["id"]
            cursor.execute("""
            UPDATE estudiantes
            SET nombre_completo = ?, nivel_paralelo = ?, email = ?, activo = 1
            WHERE id = ?
            """, (nombre.strip(), paralelo, email, estudiante_id))
        else:
            cursor.execute("""
            INSERT INTO estudiantes (codigo_estudiantil, nombre_completo, nivel_paralelo, email, foto_path)
            VALUES (?, ?, ?, ?, ?)
            """, (codigo, nombre.strip(), paralelo, email, None))
            estudiante_id = cursor.lastrowid

        if images:
            fotos_adicionales_anteriores = cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM fotos_faciales_estudiantes
                WHERE estudiante_id = ?
                """,
                (estudiante_id,),
            ).fetchone()["total"]
            if fotos_adicionales_anteriores + len(images) > 5:
                return jsonify({
                    "status": "error",
                    "mensaje": (
                        f"Este estudiante ya tiene {fotos_adicionales_anteriores} "
                        "fotos adicionales; puede agregar hasta 5 sin contar "
                        "la foto de referencia anterior."
                    ),
                }), 409

        inscribir_estudiante_en_materia(cursor, estudiante_id, materia_id)
        for image in images:
            foto_filename = f"{codigo}-{uuid.uuid4().hex}.jpg"
            foto_path = os.path.join(face_engine.dataset_dir, foto_filename)
            if not cv2.imwrite(foto_path, image):
                raise OSError("No se pudo guardar una de las fotos faciales.")
            saved_photo_paths.append(foto_path)
            cursor.execute(
                """
                INSERT INTO fotos_faciales_estudiantes (estudiante_id, foto_path)
                VALUES (?, ?)
                """,
                (estudiante_id, foto_filename),
            )
        conn.commit()
        face_engine.cargar_dataset_fotos()
        mensaje = (
            f"Estudiante inscrito y {len(images)} foto(s) facial(es) enrolada(s). "
            "Las referencias anteriores se conservaron."
            if images
            else "Estudiante inscrito en la materia. La referencia facial se puede agregar después."
        )
        return jsonify({"status": "ok", "mensaje": mensaje})
    except Exception:
        conn.rollback()
        for foto_path in saved_photo_paths:
            if os.path.exists(foto_path):
                os.remove(foto_path)
        app.logger.exception("No se pudo guardar el enrolamiento facial.")
        return jsonify({"status": "error", "mensaje": "No se pudo completar el enrolamiento."}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    print("Iniciando API AsisTech UPEC en http://localhost:5000 ...")

    def actualizar_ausencias_programadas():
        while True:
            try:
                aplicar_ausencias_programadas()
            except Exception:
                app.logger.exception(
                    "No se pudieron actualizar las faltas del horario."
                )
            threading.Event().wait(10)

    threading.Thread(
        target=actualizar_ausencias_programadas,
        name="actualizador-asistencias",
        daemon=True,
    ).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
