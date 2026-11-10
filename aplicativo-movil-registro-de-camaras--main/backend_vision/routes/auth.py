import os

from flask import Blueprint, current_app, jsonify, request
import jwt
from database import get_db, insertar_y_obtener_id
from runtime import MICROSOFT_TENANT_ID, verificar_token_microsoft

auth_api = Blueprint('auth_api', __name__)


def docentes_autorizados():
    """Correos que pueden registrarse solos como docentes (ASISTECH_DOCENTES en .env)."""
    return {
        correo.strip().lower()
        for correo in os.environ.get("ASISTECH_DOCENTES", "").split(",")
        if correo.strip()
    }

@auth_api.route("/api/auth/admin", methods=["POST"])
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


@auth_api.route("/api/auth/microsoft", methods=["POST"])
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
        current_app.logger.exception("No se pudo obtener la firma pública de Microsoft.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo verificar la respuesta de Microsoft. Intenta de nuevo.",
        }), 503
    except jwt.PyJWTError as error:
        current_app.logger.warning(
            "Token de Microsoft rechazado (%s).",
            type(error).__name__,
        )
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

    if docente is None and email.strip().lower() in docentes_autorizados():
        # Solo los correos autorizados se registran solos como docentes; las
        # cuentas de estudiantes de @upec.edu.ec siguen sin acceso. Las materias
        # se asignan después (columna docente_id de la tabla materias).
        nombre = claims.get("name") or email.split("@")[0].replace(".", " ").title()
        conn = get_db()
        try:
            cursor = conn.cursor()
            nuevo_id = insertar_y_obtener_id(
                cursor,
                """
                INSERT INTO docentes (email_institucional, nombre_completo, facultad, carrera, auth_provider)
                VALUES (?, ?, ?, ?, 'microsoft')
                """,
                (
                    email.strip(),
                    nombre,
                    "Facultad de Industrias Agropecuarias y Ciencias Ambientales (FIACA)",
                    "Carrera de Computación",
                ),
            )
            docente = cursor.execute(
                """
                SELECT id, email_institucional, nombre_completo, cedula, facultad, carrera
                FROM docentes
                WHERE id = ?
                """,
                (nuevo_id,),
            ).fetchone()
            conn.commit()
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
