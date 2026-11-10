import os
import threading

from flask import Flask
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
    print(f"Iniciando API AsisTech UPEC en {protocol}://0.0.0.0:5000 ...")

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
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        ssl_context=ssl_context,
    )
