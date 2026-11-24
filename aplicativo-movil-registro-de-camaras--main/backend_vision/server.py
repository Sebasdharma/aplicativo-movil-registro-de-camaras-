from datetime import datetime
import os
import threading
import time

if os.name != "nt":
    os.environ.setdefault("TZ", "America/Guayaquil")
    if hasattr(time, "tzset"):
        time.tzset()

from flask import Flask, jsonify, render_template
from flask_cors import CORS

from app_config import FlaskConfig
from database import (
    aplicar_ausencias_programadas,
    get_db,
    init_db,
    inscribir_estudiante_en_materia,
    obtener_dispositivos_iot,
    obtener_materias_docente,
    obtener_periodos_lectivos,
    obtener_resumen_asistencia,
    registrar_asistencia_db,
)
from runtime import (
    MAX_FOTOS_ADICIONALES_POR_ESTUDIANTE,
    MAX_FOTOS_POR_SOLICITUD,
    MICROSOFT_CLIENT_ID,
    MICROSOFT_ISSUER,
    MICROSOFT_JWKS_CLIENT,
    MICROSOFT_TENANT_ID,
    TABLET_CAMERA_TIMEOUT_SECONDS,
    asistente,
    camera_thread_lock,
    face_engine,
    tablet_cameras,
    tablet_cameras_lock,
    verificar_token_microsoft,
)

_bg_worker_lock = threading.Lock()
_bg_worker_started = False


def _start_absence_worker(application):
    global _bg_worker_started
    with _bg_worker_lock:
        if _bg_worker_started:
            return
        _bg_worker_started = True

        def actualizar_ausencias_programadas():
            while True:
                try:
                    aplicar_ausencias_programadas()
                except Exception:
                    application.logger.exception(
                        "No se pudieron actualizar las faltas del horario."
                    )
                threading.Event().wait(60)

        threading.Thread(
            target=actualizar_ausencias_programadas,
            name="actualizador-asistencias",
            daemon=True,
        ).start()


def create_app():
    application = Flask(__name__)
    application.config.from_object(FlaskConfig)
    CORS(application)

    from routes.academic import academic_api
    from routes.attendance import attendance_api
    from routes.auth import auth_api
    from routes.cameras import camera_api
    from routes.devices import device_api
    from routes.enrollment import enrollment_api
    from routes.voice import voice_api

    for blueprint in (
        auth_api,
        academic_api,
        attendance_api,
        device_api,
        voice_api,
        camera_api,
        enrollment_api,
    ):
        application.register_blueprint(blueprint)

    @application.route("/", methods=["GET"])
    @application.route("/health", methods=["GET"])
    @application.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "ok",
            "service": "AsisTech UPEC API",
            "identidades_faciales": len(face_engine.label_to_student),
            "hora_servidor": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

    @application.route("/admin", methods=["GET"])
    @application.route("/dashboard", methods=["GET"])
    def admin_dashboard():
        return render_template("admin_dashboard.html")

    @application.route("/api/admin/metricas", methods=["GET"])
    def admin_metrics():
        conn = get_db()
        cursor = conn.cursor()
        try:
            total_estudiantes = cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE activo = 1").fetchone()[0]
            total_materias = cursor.execute("SELECT COUNT(*) FROM materias WHERE activo = 1").fetchone()[0]
            total_dispositivos = cursor.execute("SELECT COUNT(*) FROM dispositivos_iot").fetchone()[0]
            total_fotos = cursor.execute("SELECT COUNT(*) FROM fotos_faciales_estudiantes").fetchone()[0]
        finally:
            conn.close()

        return jsonify({
            "status": "ok",
            "estudiantes_total": total_estudiantes,
            "materias_total": total_materias,
            "dispositivos_total": total_dispositivos,
            "fotos_total": total_fotos,
            "motor_biometrico": {
                "modelo": "YuNet + SFace (128-D)",
                "clasificador": "Multi-Plantilla k-NN + Centroide",
                "umbral_coseno": face_engine.RECOGNITION_THRESHOLD,
                "margen_minimo": face_engine.MIN_RECOGNITION_MARGIN,
                "identidades_cargadas": len(face_engine.label_to_student),
            },
            "servidor": {
                "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "base_datos": "Supabase Cloud PostgreSQL" if os.environ.get("USE_SUPABASE", "true").lower() in ("true", "1", "yes") else "SQLite Local",
            }
        })

    @application.route("/api/estudiantes", methods=["GET"])
    def api_estudiantes():
        conn = get_db()
        cursor = conn.cursor()
        try:
            filas = cursor.execute("""
                SELECT e.id, e.codigo_estudiantil, e.nombre_completo, e.nivel_paralelo, e.email, e.activo,
                       (SELECT COUNT(*) FROM fotos_faciales_estudiantes WHERE estudiante_id = e.id) as total_fotos
                FROM estudiantes e
                WHERE e.activo = 1
                ORDER BY e.nombre_completo ASC
            """).fetchall()
            estudiantes = [dict(f) for f in filas]
        finally:
            conn.close()
        return jsonify({"status": "ok", "estudiantes": estudiantes})

    if os.environ.get("ASISTECH_ENABLE_BG_WORKER") == "1":
        _start_absence_worker(application)

    return application


app = create_app()


if __name__ == "__main__":
    tls_cert = os.environ.get("ASISTECH_TLS_CERT")
    tls_key = os.environ.get("ASISTECH_TLS_KEY")
    if bool(tls_cert) != bool(tls_key):
        raise RuntimeError(
            "Configura ASISTECH_TLS_CERT y ASISTECH_TLS_KEY juntos para HTTPS."
        )
    ssl_context = (tls_cert, tls_key) if tls_cert and tls_key else None
    protocol = "https" if ssl_context else "http"
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando API AsisTech UPEC en {protocol}://0.0.0.0:{port} ...")

    _start_absence_worker(app)
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        ssl_context=ssl_context,
    )
