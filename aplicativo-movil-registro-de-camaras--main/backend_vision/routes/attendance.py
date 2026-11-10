from datetime import datetime
from io import BytesIO
import re
from flask import Blueprint, current_app, jsonify, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from database import (
    obtener_materias_docente, obtener_periodos_lectivos,
    obtener_resumen_asistencia, registrar_asistencia_db,
)

attendance_api = Blueprint('attendance_api', __name__)

@attendance_api.route("/api/asistencia/resumen", methods=["GET"])
def api_resumen():
    materia_id = request.args.get("materia_id", 1, type=int)
    fecha = request.args.get("fecha")
    try:
        return jsonify(obtener_resumen_asistencia(materia_id, fecha))
    except ValueError as error:
        return jsonify({"status": "error", "mensaje": str(error)}), 400
    except Exception:
        current_app.logger.exception("No se pudo consultar la asistencia por periodos.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo consultar la asistencia. Intenta de nuevo.",
        }), 500


@attendance_api.route("/api/asistencia/reporte/excel", methods=["GET"])
def api_reporte_excel():
    materia_id = request.args.get("materia_id", type=int)
    docente_id = request.args.get("docente_id", type=int)
    fecha = request.args.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    if not materia_id or not docente_id:
        return jsonify({
            "status": "error",
            "mensaje": "Selecciona la materia y el docente del reporte.",
        }), 400

    materias_docente = obtener_materias_docente(docente_id)
    materia = next(
        (item for item in materias_docente if item["id"] == materia_id),
        None,
    )
    if materia is None:
        return jsonify({
            "status": "error",
            "mensaje": "La materia no pertenece a la cuenta seleccionada.",
        }), 404

    try:
        registros = obtener_resumen_asistencia(materia_id, fecha)
        periodos = (
            registros[0]["periodos"]
            if registros
            else obtener_periodos_lectivos(materia["horario"], fecha)
        )
        total_con_falta = sum(
            any(periodo["estado"] == "Ausente" for periodo in estudiante["periodos"])
            for estudiante in registros
        )

        libro = Workbook()
        hoja = libro.active
        hoja.title = "Asistencia diaria"
        hoja.cell(1, 1, "Reporte diario de asistencia")
        hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4 + len(periodos))
        hoja.cell(1, 1).font = Font(bold=True, size=14, color="FFFFFF")
        hoja.cell(1, 1).fill = PatternFill("solid", fgColor="006B3F")
        hoja.cell(2, 1, "Materia")
        hoja.cell(2, 2, materia["nombre_materia"])
        hoja.cell(3, 1, "Código")
        hoja.cell(3, 2, materia["codigo_materia"])
        hoja.cell(4, 1, "Fecha")
        hoja.cell(4, 2, fecha)
        hoja.cell(5, 1, "Total de estudiantes")
        hoja.cell(5, 2, len(registros))
        hoja.cell(5, 3, "Estudiantes con falta (únicos)")
        hoja.cell(5, 4, total_con_falta)

        encabezados = [
            "Código estudiantil",
            "Estudiante",
            "Nivel / paralelo",
            *[
                f"{periodo['inicio']}-{periodo['fin']}"
                for periodo in periodos
            ],
            "Falta del día",
        ]
        fila_encabezado = 7
        for columna, encabezado in enumerate(encabezados, start=1):
            celda = hoja.cell(fila_encabezado, columna, encabezado)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="006B3F")
            celda.alignment = Alignment(horizontal="center", wrap_text=True)

        for numero_fila, estudiante in enumerate(registros, start=fila_encabezado + 1):
            detalle = {
                periodo["indice"]: periodo
                for periodo in estudiante["periodos"]
            }
            tiene_falta = any(
                periodo["estado"] == "Ausente"
                for periodo in estudiante["periodos"]
            )
            valores = [
                estudiante["codigo_estudiantil"],
                estudiante["nombre_completo"],
                estudiante["nivel_paralelo"],
                *[
                    (
                        f"{detalle[periodo['indice']]['estado']} "
                        f"{detalle[periodo['indice']]['hora']}"
                        if detalle[periodo["indice"]]["hora"] != "--:--:--"
                        else detalle[periodo["indice"]]["estado"]
                    )
                    for periodo in periodos
                ],
                "Sí" if tiene_falta else "No",
            ]
            for columna, valor in enumerate(valores, start=1):
                celda = hoja.cell(numero_fila, columna, valor)
                if valor == "Sí":
                    celda.fill = PatternFill("solid", fgColor="FCE4D6")
                elif valor == "Presente":
                    celda.fill = PatternFill("solid", fgColor="E2F0D9")

        hoja.freeze_panes = "A8"
        hoja.auto_filter.ref = (
            f"A7:{hoja.cell(fila_encabezado, len(encabezados)).column_letter}"
            f"{max(fila_encabezado, hoja.max_row)}"
        )
        anchos = [20, 34, 22] + [18] * len(periodos) + [16]
        for columna, ancho in enumerate(anchos, start=1):
            hoja.column_dimensions[
                hoja.cell(fila_encabezado, columna).column_letter
            ].width = ancho

        archivo = BytesIO()
        libro.save(archivo)
        archivo.seek(0)
        codigo_seguro = re.sub(
            r"[^A-Za-z0-9_-]+", "-", materia["codigo_materia"]
        ).strip("-")
        return send_file(
            archivo,
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            as_attachment=True,
            download_name=f"asistencia-{codigo_seguro}-{fecha}.xlsx",
        )
    except ValueError as error:
        return jsonify({"status": "error", "mensaje": str(error)}), 400
    except Exception:
        current_app.logger.exception("No se pudo generar el reporte diario de Excel.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo generar el reporte. Intenta de nuevo.",
        }), 500


@attendance_api.route("/api/asistencia/manual", methods=["POST"])
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
        current_app.logger.exception("No se pudo registrar la asistencia manual.")
        return jsonify({
            "status": "error",
            "mensaje": "No se pudo guardar la asistencia. Intenta de nuevo.",
        }), 500
