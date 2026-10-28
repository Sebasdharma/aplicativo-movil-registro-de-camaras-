import re
import unicodedata
from datetime import datetime

from database import get_db


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"[^a-z0-9 ]", " ", texto)


class CarchitoVoiceAssistant:
    def __init__(self):
        self.nombre = "Carchito"

    def _crear_reporte(self, materia_id, materia_nombre):
        fecha = datetime.now().strftime("%Y-%m-%d")
        conn = get_db()
        try:
            resumen_periodos = conn.execute(
                """
                SELECT COUNT(DISTINCT p.estudiante_id)
                    AS estudiantes_con_registro,
                       COUNT(DISTINCT CASE WHEN p.estado = 'Ausente'
                                           THEN p.estudiante_id END)
                    AS estudiantes_ausentes
                FROM asistencia_periodos p
                JOIN estudiantes e ON e.id = p.estudiante_id
                JOIN materia_estudiantes me
                  ON me.estudiante_id = p.estudiante_id
                 AND me.materia_id = p.materia_id
                WHERE p.materia_id = ?
                  AND p.fecha = ?
                  AND e.activo = 1
                """,
                (materia_id, fecha),
            ).fetchone()
            periodos_registrados = (
                conn.execute(
                    """
                    SELECT p.periodo_indice,
                           SUM(CASE WHEN p.estado IN ('Presente', 'Atrasado')
                                    THEN 1 ELSE 0 END) AS presentes,
                           SUM(CASE WHEN p.estado = 'Ausente'
                                    THEN 1 ELSE 0 END) AS ausentes
                    FROM asistencia_periodos p
                    JOIN estudiantes e ON e.id = p.estudiante_id
                    JOIN materia_estudiantes me
                      ON me.estudiante_id = p.estudiante_id
                     AND me.materia_id = p.materia_id
                    WHERE p.materia_id = ?
                      AND p.fecha = ?
                      AND e.activo = 1
                    GROUP BY p.periodo_indice
                    ORDER BY p.periodo_indice
                    """,
                    (materia_id, fecha),
                ).fetchall()
                if resumen_periodos["estudiantes_con_registro"]
                else []
            )
            resumen_legacy = conn.execute(
                """
                SELECT
                    COUNT(DISTINCT e.id) AS estudiantes_con_registro,
                    SUM(CASE WHEN a.hora_1_estado IN ('Presente', 'Atrasado')
                             THEN 1 ELSE 0 END) AS h1_presentes,
                    SUM(CASE WHEN a.hora_1_estado = 'Ausente'
                             THEN 1 ELSE 0 END) AS h1_ausentes,
                    SUM(CASE WHEN a.hora_2_estado IN ('Presente', 'Atrasado')
                             THEN 1 ELSE 0 END) AS h2_presentes,
                    SUM(CASE WHEN a.hora_2_estado = 'Ausente'
                             THEN 1 ELSE 0 END) AS h2_ausentes,
                    COUNT(DISTINCT CASE
                        WHEN a.hora_1_estado = 'Ausente'
                          OR a.hora_2_estado = 'Ausente'
                        THEN e.id END) AS estudiantes_ausentes
                FROM asistencias a
                JOIN estudiantes e ON e.id = a.estudiante_id
                JOIN materia_estudiantes me
                    ON me.estudiante_id = e.id
                    AND me.materia_id = a.materia_id
                WHERE a.materia_id = ?
                    AND a.fecha = ?
                    AND e.activo = 1
                """,
                (materia_id, fecha),
            ).fetchone()
        finally:
            conn.close()

        if periodos_registrados:
            estudiantes_con_registro = resumen_periodos[
                "estudiantes_con_registro"
            ] or 0
            estudiantes_ausentes = resumen_periodos["estudiantes_ausentes"] or 0
            reporte = {
                f"hora_{row['periodo_indice']}": {
                    "presentes": row["presentes"] or 0,
                    "ausentes": row["ausentes"] or 0,
                }
                for row in periodos_registrados
            }
        else:
            estudiantes_con_registro = (
                resumen_legacy["estudiantes_con_registro"] or 0
            )
            estudiantes_ausentes = resumen_legacy["estudiantes_ausentes"] or 0
            h1_presentes = resumen_legacy["h1_presentes"] or 0
            h1_ausentes = resumen_legacy["h1_ausentes"] or 0
            h2_presentes = resumen_legacy["h2_presentes"] or 0
            h2_ausentes = resumen_legacy["h2_ausentes"] or 0
            reporte = {
                "hora_1": {
                    "presentes": h1_presentes,
                    "ausentes": h1_ausentes,
                },
                "hora_2": {
                    "presentes": h2_presentes,
                    "ausentes": h2_ausentes,
                },
            }
        if estudiantes_con_registro == 0:
            mensaje = (
                f"Hoy no hay registros de asistencia para {materia_nombre}. "
                "Aún no puedo calcular estudiantes pendientes sin la lista del curso."
            )
        else:
            resumen_horas = " ".join(
                f"Hora {indice}: {datos['presentes']} presentes y "
                f"{datos['ausentes']} ausentes registrados."
                for indice, datos in (
                    (
                        int(nombre.split("_", 1)[1]),
                        datos,
                    )
                    for nombre, datos in reporte.items()
                )
            )
            mensaje = (
                f"Reporte de {materia_nombre} para hoy: "
                f"{estudiantes_con_registro} estudiantes tienen registros. "
                f"{estudiantes_ausentes} estudiantes tienen al menos una falta, "
                "contados una sola vez por materia y día. "
                f"Detalle por hora: {resumen_horas}"
            )
        return {
            "accion": "consultar_reporte",
            "materia_id": materia_id,
            "materia": materia_nombre,
            "fecha": fecha,
            "estudiantes_con_registro": estudiantes_con_registro,
            "estudiantes_ausentes": estudiantes_ausentes,
            "reporte": reporte,
            "mensaje": mensaje,
        }

    def procesar_comando(self, texto_comando, materia_id=1, muestras_faciales=0):
        texto = _normalizar(texto_comando).strip()
        palabras = f" {texto} "
        if " hola carchito " not in palabras:
            return {
                "accion": "desconocido",
                "mensaje": 'Para activarme, di "Hola Carchito" y luego tu instrucción.',
            }

        if any(
            frase in texto
            for frase in (
                "ayuda",
                "que puedes hacer",
                "que comandos",
                "comandos disponibles",
                "como te uso",
                "como puedo usar",
            )
        ):
            return {
                "accion": "ayuda",
                "mensaje": (
                    "Puedo abrir el escaneo en vivo, consultar el reporte de "
                    "asistencia y ayudarte con comandos. Prueba: «Hola Carchito, "
                    "toma lista», «Hola Carchito, dame el reporte» o "
                    "«Hola Carchito, ayuda»."
                ),
            }

        if any(frase in texto for frase in ("reporte", "resumen", "cuantos", "cuantas")):
            conn = get_db()
            try:
                materia = conn.execute(
                    "SELECT nombre_materia FROM materias WHERE id = ?", (materia_id,)
                ).fetchone()
                materias = conn.execute(
                    "SELECT id, nombre_materia FROM materias"
                ).fetchall()
            finally:
                conn.close()
            return self._reporte_para_materia(
                materia_id, materia, materias, texto
            )

        es_lista = any(
            frase in texto
            for frase in ("toma lista", "tomar lista", "pasa lista", "asistencia", "inicia")
        )
        if not es_lista:
            return {
                "accion": "ayuda",
                "mensaje": (
                    "Hola, soy Carchito. Puedo iniciar el escaneo en vivo o "
                    "consultar el reporte. Di «Hola Carchito, ayuda» para ver ejemplos."
                ),
            }

        conn = get_db()
        try:
            materia = conn.execute(
                "SELECT nombre_materia FROM materias WHERE id = ?", (materia_id,)
            ).fetchone()
            materias = conn.execute(
                "SELECT id, nombre_materia FROM materias"
            ).fetchall()
        finally:
            conn.close()

        error_materia = self._validar_materia(materia, materias, texto)
        if error_materia:
            return error_materia

        nombre_materia = materia["nombre_materia"]
        if muestras_faciales <= 0:
            mensaje = (
                f"Abriendo la cámara en vivo para {nombre_materia}. Aún no hay "
                "fotos de referencia enroladas: podrás probar la cámara, pero "
                "no identificaré estudiantes ni registraré asistencias hasta "
                "que cargues referencias autorizadas."
            )
        else:
            mensaje = (
                f"Abriendo la cámara en vivo para tomar lista de {nombre_materia}. "
                "Solo registraré rostros que coincidan con las referencias enroladas."
            )
        return {
            "accion": "iniciar_escaneo",
            "materia_id": materia_id,
            "materia": nombre_materia,
            "muestras_faciales": muestras_faciales,
            "mensaje": mensaje,
        }

    def _reporte_para_materia(self, materia_id, materia, materias, texto):
        error_materia = self._validar_materia(materia, materias, texto)
        if error_materia:
            return error_materia
        return self._crear_reporte(materia_id, materia["nombre_materia"])

    @staticmethod
    def _validar_materia(materia, materias, texto):
        if materia is None:
            return {
                "accion": "error",
                "mensaje": (
                    "No encontré la materia seleccionada. Elige una materia "
                    "e inténtalo de nuevo."
                ),
            }

        nombre_materia = materia["nombre_materia"]
        materia_mencionada = next(
            (
                otra["nombre_materia"]
                for otra in materias
                if _normalizar(otra["nombre_materia"]) in texto
            ),
            None,
        )
        if materia_mencionada and _normalizar(materia_mencionada) != _normalizar(nombre_materia):
            return {
                "accion": "materia_no_coincide",
                "mensaje": (
                    f"Seleccionaste {nombre_materia}, pero pediste {materia_mencionada}. "
                    "Selecciona esa materia antes de continuar."
                ),
            }
        return None
