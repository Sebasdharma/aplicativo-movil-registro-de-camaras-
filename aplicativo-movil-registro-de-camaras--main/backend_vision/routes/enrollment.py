import base64
import binascii
import os
import re
import uuid
import cv2
import numpy as np
from flask import Blueprint, current_app, jsonify, request
from database import get_db, inscribir_estudiante_en_materia
from runtime import (
    MAX_FOTOS_ADICIONALES_POR_ESTUDIANTE, MAX_FOTOS_POR_SOLICITUD,
    face_engine,
)

enrollment_api = Blueprint('enrollment_api', __name__)

@enrollment_api.route("/api/estudiantes/enrolar", methods=["POST"])
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
            or len(fotos) > MAX_FOTOS_POR_SOLICITUD
            or any(not isinstance(foto, str) or not foto for foto in fotos)
        ):
            return jsonify({
                "status": "error",
                "mensaje": (
                    "Envía de 1 a "
                    f"{MAX_FOTOS_POR_SOLICITUD} fotos faciales por solicitud."
                ),
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
            encoded_ok, encoded_image = cv2.imencode(".jpg", image)
            if not encoded_ok:
                return jsonify({"status": "error", "mensaje": "No se pudo preparar una de las fotos faciales."}), 400
            stored_image_bytes = encoded_image.tobytes()
            valido, mensaje = face_engine.validar_foto_enrolamiento(
                stored_image_bytes
            )
            if not valido:
                return jsonify({"status": "error", "mensaje": mensaje}), 400
            images.append(stored_image_bytes)

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
            if (
                fotos_adicionales_anteriores + len(images)
                > MAX_FOTOS_ADICIONALES_POR_ESTUDIANTE
            ):
                return jsonify({
                    "status": "error",
                    "mensaje": (
                        f"Este estudiante ya tiene {fotos_adicionales_anteriores} "
                        f"fotos adicionales; puede agregar hasta "
                        f"{MAX_FOTOS_ADICIONALES_POR_ESTUDIANTE} sin contar "
                        "la foto de referencia anterior."
                    ),
                }), 409

        # Inscribir al estudiante en la materia y en todas las materias activas del semestre
        inscribir_estudiante_en_materia(cursor, estudiante_id, materia_id)
        for row in cursor.execute("SELECT id FROM materias WHERE activo = 1").fetchall():
            inscribir_estudiante_en_materia(cursor, estudiante_id, row["id"])

        for image_bytes in images:
            foto_filename = f"{codigo}-{uuid.uuid4().hex}.jpg"
            foto_path = os.path.join(face_engine.dataset_dir, foto_filename)
            with open(foto_path, "wb") as photo_file:
                photo_file.write(image_bytes)
            saved_photo_paths.append(foto_path)
            cursor.execute(
                """
                INSERT INTO fotos_faciales_estudiantes (estudiante_id, foto_path, imagen_bytes)
                VALUES (?, ?, ?)
                """,
                (estudiante_id, foto_filename, image_bytes),
            )
            # Asegurar foto principal en tabla estudiantes si no tiene
            cursor.execute(
                """
                UPDATE estudiantes
                SET foto_path = ?
                WHERE id = ? AND (foto_path IS NULL OR foto_path = '')
                """,
                (foto_filename, estudiante_id),
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
        current_app.logger.exception("No se pudo guardar el enrolamiento facial.")
        return jsonify({"status": "error", "mensaje": "No se pudo completar el enrolamiento."}), 500
    finally:
        conn.close()
