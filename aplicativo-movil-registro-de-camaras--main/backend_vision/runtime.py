import threading

import jwt

from app_config import FlaskConfig
from carchito_voice import CarchitoVoiceAssistant
from database import init_db
from face_engine import FaceEngine

MICROSOFT_TENANT_ID = FlaskConfig.MICROSOFT_TENANT_ID
MICROSOFT_CLIENT_ID = FlaskConfig.MICROSOFT_CLIENT_ID
MICROSOFT_ISSUER = (
    f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/v2.0"
)
MICROSOFT_JWKS_CLIENT = jwt.PyJWKClient(
    f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}"
    "/discovery/v2.0/keys"
)

MAX_FOTOS_POR_SOLICITUD = 5
MAX_FOTOS_ADICIONALES_POR_ESTUDIANTE = 10
TABLET_CAMERA_TIMEOUT_SECONDS = 12

init_db()
asistente = CarchitoVoiceAssistant()
face_engine = FaceEngine()
camera_thread = None
camera_thread_lock = threading.Lock()
tablet_cameras = {}
tablet_cameras_lock = threading.Lock()


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
