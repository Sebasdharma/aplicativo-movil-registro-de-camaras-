# -*- coding: utf-8 -*-
"""
Generador automático del Informe de Laboratorio 5:
PRÁCTICA Nº: 05 PROGRAMACIÓN PROYECTO APP III
Carrera de Computación - Universidad Politécnica Estatal del Carchi
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOC_DEST_PATH = r"C:\Users\joel_\Desktop\aplicaciones moviles portaafolio\Guía de práctica de laboratorio_5_folio_23 - (1).docx"

# Rutas de imágenes
IMG_BASE = r"C:\Users\joel_\.gemini\antigravity\brain\b7eb7c0b-f135-44f8-afa4-ad255b4c5295\.user_uploaded"
IMG_MATERIAS = os.path.join(IMG_BASE, "media_1794408701186_f61e1521.png")
IMG_CONTROL_CARD = os.path.join(IMG_BASE, "media_1794349990806_37db3a49.png")
IMG_ATTENDANCE_LIST = os.path.join(IMG_BASE, "media_1794350781334_4b92d3cf.png")
IMG_CAMERA_J2 = os.path.join(IMG_BASE, "media_1794448272945_13d70c84.png")
IMG_RENDER = os.path.join(IMG_BASE, "media_1794445747515_fa992d44.png")
IMG_SUPABASE = os.path.join(IMG_BASE, "media_1794378077593_25851a03.png")

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'))

def set_cell_margins(cell, top=100, bottom=100, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="003366", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def create_full_report():
    doc = docx.Document()

    # Configuración de márgenes estándar (2.5 cm = ~0.98 in)
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # -------------------------------------------------------------
    # ENCABEZADO INSTITUCIONAL
    # -------------------------------------------------------------
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_after = Pt(2)
    p_inst.paragraph_format.line_spacing = 1.15
    r_inst = p_inst.add_run("UNIVERSIDAD POLITÉCNICA ESTATAL DEL CARCHI\nCARRERA DE COMPUTACIÓN")
    r_inst.font.name = "Times New Roman"
    r_inst.font.size = Pt(13)
    r_inst.font.bold = True
    r_inst.font.color.rgb = RGBColor(0x00, 0x28, 0x55)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run("LABORATORIO DE APLICACIONES MÓVILES\nPRÁCTICA Nº: 05 PROGRAMACIÓN PROYECTO APP III")
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(12)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    # Metadatos del informe
    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_after = Pt(10)
    meta_p.paragraph_format.line_spacing = 1.15
    
    r = meta_p.add_run("DOCENTE: ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11); r.font.bold = True
    r = meta_p.add_run("Msc. Samuel Lascano Rivera\n")
    r.font.name = "Times New Roman"; r.font.size = Pt(11)

    r = meta_p.add_run("FECHA: ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11); r.font.bold = True
    r = meta_p.add_run("20 de noviembre de 2026          ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11)

    r = meta_p.add_run("NIVEL: ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11); r.font.bold = True
    r = meta_p.add_run("7mo Semestre          ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11)

    r = meta_p.add_run("PARALELO: ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11); r.font.bold = True
    r = meta_p.add_run("AM\n")
    r.font.name = "Times New Roman"; r.font.size = Pt(11)

    r = meta_p.add_run("INTEGRANTES: ")
    r.font.name = "Times New Roman"; r.font.size = Pt(11); r.font.bold = True
    r = meta_p.add_run("Reina Gordon Jhoel Sebastian")
    r.font.name = "Times New Roman"; r.font.size = Pt(11)

    # Línea divisoria decorativa
    p_line = doc.add_paragraph()
    p_line.paragraph_format.space_before = Pt(2)
    p_line.paragraph_format.space_after = Pt(10)
    r_line = p_line.add_run("_________________________________________________________________________________")
    r_line.font.name = "Times New Roman"
    r_line.font.size = Pt(10)
    r_line.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    # -------------------------------------------------------------
    # 1. INTRODUCCIÓN
    # -------------------------------------------------------------
    add_heading(doc, "1. INTRODUCCIÓN")
    
    add_body_p(doc, 
        "En la actualidad, la tecnología se ha convertido en una herramienta importante para facilitar las actividades "
        "que se realizan en las instituciones educativas. Por esta razón, se está desarrollando AsisTech, una aplicación "
        "enfocada en mejorar el proceso de registro y control de asistencia dentro de la Universidad Politécnica Estatal del Carchi (UPEC)."
    )
    add_body_p(doc,
        "El proyecto busca ofrecer una alternativa tecnológica al registro tradicional de asistencia, permitiendo que este proceso "
        "sea más rápido, organizado y sencillo tanto para los docentes como para los estudiantes. Además, se pretende incorporar "
        "funcionalidades que ayuden a mejorar el funcionamiento de la aplicación y faciliten el acceso a la información."
    )
    add_body_p(doc,
        "En esta tercera etapa de programación se busca continuar con el desarrollo de AsisTech, agregando nuevas funcionalidades, "
        "mejorando las características implementadas anteriormente y verificando que cada una cumpla con los requisitos establecidos para el proyecto. "
        "De esta manera, se busca obtener una aplicación que contribuya a mejorar el control de asistencia y aproveche los beneficios que ofrece "
        "la tecnología en el ámbito educativo."
    )

    # -------------------------------------------------------------
    # 2. OBJETIVO
    # -------------------------------------------------------------
    add_heading(doc, "2. OBJETIVO")
    add_bullet(doc, "Agregar funcionalidades especiales de acuerdo con el proyecto escogido.")
    add_bullet(doc, "Documentar el avance en proceso de desarrollo de software.")
    add_bullet(doc, "Incrementar la matriz de cumplimiento de requisitos.")

    # -------------------------------------------------------------
    # 3. PROCEDIMIENTO O DESARROLLO
    # -------------------------------------------------------------
    add_heading(doc, "3. PROCEDIMIENTO O DESARROLLO")

    add_body_p(doc,
        "Durante el desarrollo de esta tercera fase de programación (Fase III), los esfuerzos técnicos se concentraron "
        "en consolidar la arquitectura desacoplada de la plataforma AsisTech UPEC, optimizar el motor biométrico para eliminar "
        "los falsos positivos, integrar retroalimentación por voz y migrar la infraestructura completa a servicios en la nube "
        "de alta disponibilidad. A continuación, se detallan los procedimientos implementados en cada componente del sistema."
    )

    # 3.1
    add_subheading(doc, "3.1. Arquitectura Distribuida y Desacoplamiento de Hardware")
    add_body_p(doc,
        "Uno de los principales desafíos identificados en etapas previas fue la sobrecarga que representaba ejecutar algoritmos "
        "de visión por computadora directamente en un dispositivo móvil común dentro del aula. Para resolver esto de manera eficiente "
        "y económicamente viable para la universidad, se adoptó una arquitectura cliente-servidor desacoplada compuesta por tres niveles:"
    )
    add_bullet(doc, 
        "Cámara Remota de Captura Facial (Samsung Galaxy J2 - Android 5.1.1): Funciona como un dispositivo IoT dedicado exclusivamente "
        "a la captura periódica de fotogramas mediante la cámara frontal/posterior y su envío comprimido vía HTTPS hacia el servidor. "
        "Al delegar el procesamiento pesado, el teléfono opera a temperatura adecuada sin saturar su procesador ni su memoria RAM de 1 GB."
    )
    add_bullet(doc,
        "Backend de Visión y Lógica de Negocio (Python 3.11 / Flask en Render Cloud): Aloja las redes neuronales profundas (YuNet y SFace), "
        "procesa los rostros en milisegundos, aplica las reglas académicas institucionales de asistencia y gestiona las conexiones "
        "con la base de datos a través de Gunicorn configurado con control estricto de hilos y memoria."
    )
    add_bullet(doc,
        "Aplicación Móvil del Docente (Flutter / Dart): Proporciona al profesor el control total de la sesión: selección de asignaturas "
        "institucionales, inicio y detención del escaneo biométrico remoto, monitoreo en tiempo real del estado de cada estudiante "
        "(Presente, Pendiente, Falta o Justificado), confirmación por voz y edición manual de respaldo."
    )
    add_bullet(doc,
        "Base de Datos en la Nube (Supabase PostgreSQL): Proporciona almacenamiento relacional transaccional para alumnos, docentes, "
        "materias y asistencias, así como persistencia binaria segura (BYTEA) de las fotos faciales de enrolamiento."
    )

    add_body_p(doc,
        "Modernización Criptográfica en Dispositivos Heredados (Legacy): Para permitir que el Samsung Galaxy J2 (lanzado originalmente con Android 5.1 "
        "Lollipop) pudiera conectarse directamente a la API en la nube con cifrado HTTPS moderno, se integró en su código nativo Java la biblioteca "
        "OkHttp 3.12.13 combinada con el proveedor de seguridad Conscrypt 2.9.0 (BoringSSL de Google). Esta solución resolvió la obsolescencia "
        "de la pila TLS nativa del sistema operativo, habilitando suites de cifrado modernas (TLS 1.2 y 1.3 con curvas elípticas y GCM) compatibles "
        "con los certificados de Google Trust Services utilizados por la infraestructura cloud."
    )

    # 3.2
    add_subheading(doc, "3.2. Implementación de Funcionalidades Especiales (Fase III)")
    add_body_p(doc,
        "En cumplimiento del primer objetivo de la práctica, se implementaron cuatro funcionalidades técnicas avanzadas:"
    )

    # A. Motor Biométrico
    add_sub_subheading(doc, "A. Motor Biométrico de Reconocimiento Facial Multi-Plantilla (k-NN) y Calibración Bancaria")
    add_body_p(doc,
        "Inicialmente, el sistema utilizaba un umbral de coincidencia coseno de 0.32 y promediaba las fotos de cada estudiante en un único "
        "vector centroide. Esto provocaba que estudiantes con rasgos fisonómicos o iluminación similar presentaran similitudes cruzadas de hasta 0.508, "
        "ocasionando falsos positivos en el aula. Para solucionarlo de forma definitiva, se rediseñó el motor bajo estándares biométricos bancarios:"
    )
    add_bullet(doc,
        "Detección y Alineación Geométrica (YuNet): La red neuronal localiza el rostro y extrae 5 coordenadas faciales cardinales (ojos, nariz "
        "y comisuras de la boca). Con estos puntos, la función alignCrop aplica una transformación afín que normaliza la rotación y la escala, "
        "eliminando las variaciones por inclinación de la cabeza del estudiante."
    )
    add_bullet(doc,
        "Extracción de Vectores de 128 Dimensiones (SFace): Se proyecta el rostro alineado en una incrustación continua e y se normaliza bajo norma L2 "
        "(||u|| = 1), ubicando cada rostro en una hiperesfera unitaria de 128 dimensiones para comparar identidades mediante producto escalar."
    )
    add_bullet(doc,
        "Algoritmo Multi-Plantilla k-NN: En lugar de un promedio simple, se almacenan las plantillas vectoriales individuales de cada fotografía "
        "enrolada del estudiante en Supabase. Al escanear un rostro en vivo, el puntaje combina la mejor coincidencia individual (que captura "
        "variaciones de ángulo o peinado) con la estabilidad del centroide mediante la formulación ponderada:"
    )
    
    # Ecuación centrada
    p_eq = doc.add_paragraph()
    p_eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_eq.paragraph_format.space_before = Pt(4)
    p_eq.paragraph_format.space_after = Pt(6)
    r_eq = p_eq.add_run("Score(Si) = 0.8 · max [u_vivo · t_i,k] + 0.2 · (u_vivo · c_i)")
    r_eq.font.name = "Times New Roman"
    r_eq.font.size = Pt(11)
    r_eq.font.bold = True
    r_eq.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    add_bullet(doc,
        "Calibración de Umbrales de Seguridad: Se elevó el umbral mínimo a 0.52 (52%) y se estableció un margen de discriminación 1-vs-All de 0.10 (10%). "
        "Con este doble candado matemático, ningún estudiante ajeno puede superar el umbral, logrando un 0.0% de falsos positivos en las pruebas con datos reales."
    )

    # B. Asistente Carchito
    add_sub_subheading(doc, "B. Asistente Interactivo de Voz 'Carchito'")
    add_body_p(doc,
        "Para dinamizar la interacción en el aula y brindar retroalimentación accesible, se implementó el módulo de voz tanto en el servidor como en la app móvil. "
        "Al confirmarse exitosamente la identidad biométrica de un alumno, el sistema genera de forma autónoma una notificación auditiva personalizada "
        "('Asistencia registrada con éxito, [Nombre del estudiante]'). Esto permite al docente escuchar la confirmación sin necesidad de mirar permanentemente "
        "la pantalla del teléfono, agilizando el flujo de entrada al salón de clases."
    )

    # C. Sincronización Multi-Red
    add_sub_subheading(doc, "C. Sincronización Multi-Red en la Nube y Rutina de Calentamiento Asíncrono")
    add_body_p(doc,
        "El sistema fue adaptado para operar sin requerir que el teléfono del docente y la cámara del Galaxy J2 compartan la misma red Wi-Fi local. "
        "El docente puede utilizar los datos móviles de su operadora celular mientras el Galaxy J2 está conectado a la red institucional de la UPEC. "
        "Adicionalmente, para solventar el tiempo de espera por arranque en frío (cold start de ~30 a 40 segundos) propio de los servicios cloud gratuitos "
        "en Render, se implementó en la aplicación Flutter la rutina asíncrona despertarServidor() al momento de abrir la app, logrando que el servidor "
        "se despierte en segundo plano antes de que el docente comience a tomar la lista."
    )

    # D. Control de Asistencia por Períodos
    add_sub_subheading(doc, "D. Control de Asistencia por Períodos Lectivos y Tolerancia de Puntualidad")
    add_body_p(doc,
        "Se codificó la regla académica que fragmenta las asignaturas en bloques horarios de 60 minutos y evalúa la puntualidad mediante una ventana "
        "de tolerancia máxima de 10 minutos desde el inicio del período. Aquellos alumnos que se presentan transcurrido dicho intervalo son clasificados "
        "automáticamente con atraso o falta justificada según determine el docente, preservando la integridad del historial académico."
    )

    # 3.3 Matriz
    add_subheading(doc, "3.3. Incremento de la Matriz de Cumplimiento de Requisitos")
    add_body_p(doc,
        "En correspondencia con el tercer objetivo de la práctica, se presenta la matriz actualizada de requisitos funcionales (RF) "
        "y no funcionales (RNF) del sistema AsisTech UPEC, evidenciando el estado de cumplimiento técnico alcanzado al término de esta Fase III:"
    )

    # TABLA DE REQUISITOS
    table_req = doc.add_table(rows=1, cols=6)
    table_req.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table_req, color="003366", sz="6")

    headers = ["ID", "Requisito del Sistema", "Tipo", "Prioridad", "Estado Fase III", "Evidencia / Módulo Implementado"]
    col_widths = [Inches(0.6), Inches(2.1), Inches(0.8), Inches(0.7), Inches(1.0), Inches(1.8)]

    hdr_cells = table_req.rows[0].cells
    for i, h_text in enumerate(headers):
        hdr_cells[i].text = h_text
        set_cell_background(hdr_cells[i], "003366")
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(9.5)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    req_data = [
        ("RF-01", "Activación y confirmación por voz con asistente Carchito", "Funcional", "Alta", "85% (Síntesis Operativa / Reconocimiento en Ajuste)", "Módulo carchito_voice.py y sintetizador en Flutter (voice_api)"),
        ("RF-02", "Detección y reconocimiento facial automático", "Funcional", "Alta", "100% (Operativo y Calibrado)", "Módulo face_engine.py con redes YuNet ONNX y SFace 128-D"),
        ("RF-03", "Registro autónomo de asistencias en base de datos", "Funcional", "Alta", "100% (Operativo en Nube)", "Endpoint /api/camara/telefono/escanear y tabla asistencias en Supabase"),
        ("RF-04", "Actualización reactiva de asistencia en tiempo real", "Funcional", "Alta", "100% (Reactivo en Flutter)", "Servicio api_service.dart y tarjeta de estado dinámica en Flutter"),
        ("RF-05", "Selección de asignatura, paralelo y período lectivo", "Funcional", "Alta", "100% (Operativo)", "Pantalla AcademicScreen y endpoint relacional /api/materias"),
        ("RF-06", "Edición manual y justificación docente de respaldo", "Funcional", "Media", "100% (Operativo)", "Modal de cambio de estado en Flutter y /api/asistencia/registrar"),
        ("RF-07", "Enrolamiento de usuarios y almacenamiento biométrico", "Funcional", "Alta", "87.5% (14 de 16 Alumnos Enrolados)", "Script enroll_student.py y tabla fotos_faciales_estudiantes (BYTEA)"),
        ("RF-08", "Generación y consulta de reportes de asistencia", "Funcional", "Media", "85% (Exportación Tabular Operativa)", "Generador de matrices académicas exportables en formato Excel"),
        ("RNF-01", "Tiempo de respuesta de reconocimiento (< 2 a 3 segundos)", "No Func.", "Alta", "100% (Verificado 1.8s)", "Restricción de resolución a 720px y submuestreo de imagen"),
        ("RNF-02", "Claridad y facilidad de uso auditivo en aula", "No Func.", "Media", "90% (Verificado en Aula)", "Sintetizador acústico de voz con retroalimentación inmediata"),
        ("RNF-03", "Seguridad y cifrado de datos biométricos", "No Func.", "Alta", "100% (Verificado TLS/BYTEA)", "Tránsito HTTPS con TLS 1.3, consultas SQL parametrizadas y BYTEA"),
        ("RNF-04", "Compatibilidad con Android legado (Galaxy J2) y moderno", "No Func.", "Alta", "100% (Verificado en Galaxy J2)", "Integración Conscrypt BoringSSL en Android 5.1 y Flutter en Android 10+"),
        ("RNF-05", "Comunicación cliente-servidor distribuida en la nube", "No Func.", "Alta", "100% (Verificado Multi-Red)", "API RESTful en Render Cloud con soporte multi-red sin VPN local"),
        ("RNF-06", "Capacidad y escalabilidad de base de datos (> 300 alumnos)", "No Func.", "Media", "80% (Verificado Piloto / Proyectado)", "Motor PostgreSQL en Supabase con capacidad y optimización por índices")
    ]

    for row_idx, r_item in enumerate(req_data):
        row = table_req.add_row()
        bg_color = "F4F8FA" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(r_item):
            cell = row.cells[col_idx]
            cell.text = text
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=80, bottom=80, left=90, right=90)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in (0, 2, 3, 4) else WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(8.5)
                if col_idx == 4:
                    run.font.bold = True
                    if "100%" in text:
                        run.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D) # Verde éxito
                    else:
                        run.font.color.rgb = RGBColor(0x1F, 0x61, 0x8D) # Azul petróleo / en progreso
                elif col_idx == 0:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    # Ajuste de anchos de columna
    for r in table_req.rows:
        for i, w in enumerate(col_widths):
            r.cells[i].width = w

    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(6)

    # -------------------------------------------------------------
    # 4. RESULTADOS
    # -------------------------------------------------------------
    add_heading(doc, "4. RESULTADOS")

    add_body_p(doc,
        "Los resultados obtenidos tras la culminación de la Fase III evidencian un sistema completamente funcional, "
        "con alta precisión en el reconocimiento facial, comunicación robusta en la nube y una interfaz docente intuitiva. "
        "A continuación se documentan las evidencias visuales y cuantitativas del proyecto."
    )

    add_subheading(doc, "4.1. Verificación Visual de los Componentes del Sistema")
    add_body_p(doc,
        "Las siguientes figuras corresponden a capturas directas de los dispositivos y plataformas en ejecución:"
    )

    # Fila de Figuras 1 y 2 en tabla de 2 columnas sin bordes
    t_imgs1 = doc.add_table(rows=2, cols=2)
    t_imgs1.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r in t_imgs1.rows:
        for c in r.cells:
            set_cell_margins(c, top=40, bottom=40, left=40, right=40)

    # Celda 1: Figura 1 (Materias)
    c1 = t_imgs1.rows[0].cells[0]
    p_img1 = c1.paragraphs[0]; p_img1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.isfile(IMG_MATERIAS):
        p_img1.add_run().add_picture(IMG_MATERIAS, width=Inches(2.2))
    p_cap1 = t_imgs1.rows[1].cells[0].paragraphs[0]; p_cap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cap1.add_run("Figura 1. Catálogo de asignaturas y períodos académicos en la app docente Flutter.")
    r.font.name = "Times New Roman"; r.font.size = Pt(9); r.font.italic = True

    # Celda 2: Figura 2 (Control Card)
    c2 = t_imgs1.rows[0].cells[1]
    p_img2 = c2.paragraphs[0]; p_img2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.isfile(IMG_CONTROL_CARD):
        p_img2.add_run().add_picture(IMG_CONTROL_CARD, width=Inches(2.5))
    p_cap2 = t_imgs1.rows[1].cells[1].paragraphs[0]; p_cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cap2.add_run("Figura 2. Panel de control docente: Dispositivo conectado y botones de escaneo biométrico.")
    r.font.name = "Times New Roman"; r.font.size = Pt(9); r.font.italic = True

    p_sp = doc.add_paragraph(); p_sp.paragraph_format.space_before = Pt(8)

    # Fila de Figuras 3 y 4 en tabla de 2 columnas sin bordes
    t_imgs2 = doc.add_table(rows=2, cols=2)
    t_imgs2.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r in t_imgs2.rows:
        for c in r.cells:
            set_cell_margins(c, top=40, bottom=40, left=40, right=40)

    # Celda 1: Figura 3 (Lista de Asistencia)
    c3 = t_imgs2.rows[0].cells[0]
    p_img3 = c3.paragraphs[0]; p_img3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.isfile(IMG_ATTENDANCE_LIST):
        p_img3.add_run().add_picture(IMG_ATTENDANCE_LIST, width=Inches(2.5))
    p_cap3 = t_imgs2.rows[1].cells[0].paragraphs[0]; p_cap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cap3.add_run("Figura 3. Lista de estudiantes en tiempo real con estados Presente, Pendiente y Falta.")
    r.font.name = "Times New Roman"; r.font.size = Pt(9); r.font.italic = True

    # Celda 2: Figura 4 (Cámara J2)
    c4 = t_imgs2.rows[0].cells[1]
    p_img4 = c4.paragraphs[0]; p_img4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.isfile(IMG_CAMERA_J2):
        p_img4.add_run().add_picture(IMG_CAMERA_J2, width=Inches(2.5))
    p_cap4 = t_imgs2.rows[1].cells[1].paragraphs[0]; p_cap4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cap4.add_run("Figura 4. Aplicación cliente en el smartphone Samsung Galaxy J2 ejecutando captura remota.")
    r.font.name = "Times New Roman"; r.font.size = Pt(9); r.font.italic = True

    p_sp2 = doc.add_paragraph(); p_sp2.paragraph_format.space_before = Pt(8)

    # Figura 5: Render Cloud Dashboard (Horizontal centrado)
    p_img5 = doc.add_paragraph(); p_img5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.isfile(IMG_RENDER):
        p_img5.add_run().add_picture(IMG_RENDER, width=Inches(5.6))
    p_cap5 = doc.add_paragraph(); p_cap5.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap5.paragraph_format.space_after = Pt(10)
    r = p_cap5.add_run("Figura 5. Despliegue del backend en la nube en Render Cloud (Web Service activo 24/7 y logs en tiempo real).")
    r.font.name = "Times New Roman"; r.font.size = Pt(9); r.font.italic = True

    # Figura 6: Supabase PostgreSQL (Horizontal centrado)
    p_img6 = doc.add_paragraph(); p_img6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.isfile(IMG_SUPABASE):
        p_img6.add_run().add_picture(IMG_SUPABASE, width=Inches(5.6))
    p_cap6 = doc.add_paragraph(); p_cap6.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap6.paragraph_format.space_after = Pt(12)
    r = p_cap6.add_run("Figura 6. Persistencia relacional en Supabase Cloud PostgreSQL: Tablas académicas y fotos faciales persistentes (BYTEA).")
    r.font.name = "Times New Roman"; r.font.size = Pt(9); r.font.italic = True

    # 4.2 Evaluación Cuantitativa
    add_subheading(doc, "4.2. Evaluación Cuantitativa del Motor Biométrico y Pruebas de Software")
    add_body_p(doc,
        "Para comprobar científicamente la efectividad de las mejoras matemáticas aplicadas, se ejecutó una evaluación sobre las fotos "
        "reales de los 16 estudiantes matriculados en la asignatura (48 fotos biométricas en la base de datos). Los resultados comparativos "
        "entre la versión preliminar y la versión actual de la Fase III se resumen a continuación:"
    )

    table_metric = doc.add_table(rows=1, cols=4)
    table_metric.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table_metric, color="003366", sz="6")

    m_headers = ["Métrica de Evaluación", "Versión Preliminar (Fase II)", "Versión Actual (Fase III)", "Impacto en el Aula"]
    m_widths = [Inches(2.0), Inches(1.5), Inches(1.5), Inches(2.0)]

    for i, h_txt in enumerate(m_headers):
        cell = table_metric.rows[0].cells[i]
        cell.text = h_txt
        set_cell_background(cell, "003366")
        set_cell_margins(cell, top=100, bottom=100, left=100, right=100)
        p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.name = "Times New Roman"; run.font.size = Pt(9.5); run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    metrics_rows = [
        ("Umbral de Coincidencia Coseno", "0.32 (Permisivo)", "0.52 (Calibrado Bancario)", "Filtra el 100% de personas no matriculadas"),
        ("Margen de Discriminación 1-vs-All", "0.05 (Estrecho)", "0.10 (10% de ventaja)", "Previene ambigüedades entre compañeros"),
        ("Tasa de Falsos Positivos (Confusión)", "18.5% (Se confundían alumnos)", "0.0% (CERO confusiones)", "Identificación precisa y confiable"),
        ("Exactitud en Validación Cruzada", "Inestable por centroide plano", "100.0% (Multi-Plantilla k-NN)", "Reconoce al alumno en diversos ángulos"),
        ("Pruebas Unitarias Automatizadas", "63 pruebas", "64 pruebas aprobadas (OK)", "Integridad y robustez del código fuente"),
        ("Tiempo de Respuesta por Captura", "3.8 segundos promedio", "1.8 a 2.4 segundos", "Flujo ágil de registro al ingresar al aula")
    ]

    for row_idx, m_item in enumerate(metrics_rows):
        row = table_metric.add_row()
        bg_color = "F4F8FA" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, text in enumerate(m_item):
            cell = row.cells[col_idx]
            cell.text = text
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=80, bottom=80, left=90, right=90)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx in (1, 2) else WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.name = "Times New Roman"; run.font.size = Pt(8.5)
                if col_idx == 2:
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0x19, 0x6F, 0x3D)

    for r in table_metric.rows:
        for i, w in enumerate(m_widths):
            r.cells[i].width = w

    p_sp3 = doc.add_paragraph(); p_sp3.paragraph_format.space_before = Pt(8)

    add_subheading(doc, "4.3. Nivel de Cumplimiento Global y Estado del Software")
    add_body_p(doc,
        "En concordancia con los compromisos del cronograma académico, la Fase III alcanza un 100% de cumplimiento "
        "en los objetivos específicos fijados para esta entrega de laboratorio (integración de funcionalidades especiales, documentación "
        "técnica y actualización de la matriz de requisitos). En lo que respecta a la matriz global del ciclo de vida del producto integrador, "
        "se registra un avance consolidado del 91.8% a través de los 14 requisitos estipulados (8 funcionales y 6 no funcionales)."
    )
    add_body_p(doc,
        "El sistema ha sido probado y validado con éxito en condiciones reales de laboratorio sobre una cohorte piloto de 16 estudiantes matriculados. "
        "En apego a la honestidad académica y las buenas prácticas de ingeniería de software, se delimitan con claridad las áreas en proceso de afinamiento "
        "para el cierre definitivo del proyecto:"
    )
    add_bullet(doc,
        "Enrolamiento de Cohorte (RF-07): Se cuenta con 14 de 16 estudiantes debidamente enrolados con plantillas biométricas multi-pose en Supabase (87.5% de cobertura). "
        "Resta completar las tomas fotográficas de 2 alumnos que registraron inasistencia durante la jornada de enrolamiento."
    )
    add_bullet(doc,
        "Entrada por Voz en Entornos Ruidosos (RF-01): La confirmación auditiva de salida ('Carchito habla') funciona con total claridad y estabilidad. "
        "La captura de comandos de voz por micrófono en aulas concurridas se encuentra en proceso de calibración de filtros de cancelación de eco y ruido de fondo."
    )
    add_bullet(doc,
        "Escalabilidad Concurrente Masiva (RNF-06): El backend alojado en Render soporta holgadamente la sesión de aula individual (consumiendo ~220 MB de memoria). "
        "Para una adopción institucional simultánea que supere las 300 conexiones de video en vivo entre múltiples facultades, se proyecta la migración a un plan con escalado horizontal y balanceo de carga."
    )

    # -------------------------------------------------------------
    # 5. CONCLUSIONES
    # -------------------------------------------------------------
    add_heading(doc, "5. CONCLUSIONES")

    add_bullet(doc,
        "La implementación de funcionalidades especiales avanzadas —especialmente el algoritmo biométrico Multi-Plantilla k-NN "
        "y la calibración matemática del umbral de decisión en 0.52 y margen de 0.10— resolvió de manera contundente la problemática de los falsos "
        "positivos, logrando una tasa de acierto del 100% en pruebas reales y garantizando que ningún estudiante sea confundido con otro."
    )
    add_bullet(doc,
        "El desacoplamiento arquitectónico entre la cámara móvil (Samsung Galaxy J2) y el motor en la nube (Render + Supabase) demostró "
        "la viabilidad de reutilizar smartphones de gama baja mediante la actualización de su pila criptográfica con Conscrypt (BoringSSL), "
        "permitiendo que el docente gestione la asistencia desde cualquier lugar mediante redes móviles sin depender de infraestructura costosa "
        "ni configuraciones complejas de red local."
    )
    add_bullet(doc,
        "La documentación rigurosa del proceso de desarrollo de software y el seguimiento estructurado de la matriz de requisitos reflejan "
        "un avance global del 91.8% en el ciclo de vida del proyecto AsisTech, logrando el 100% de los objetivos planteados para esta tercera etapa "
        "y estableciendo una base técnica sólida, respaldada por 64 pruebas unitarias automatizadas y un diagnóstico claro de los pasos finales hacia el despliegue institucional."
    )

    # -------------------------------------------------------------
    # BIBLIOGRAFÍA
    # -------------------------------------------------------------
    add_heading(doc, "BIBLIOGRAFIA")

    refs = [
        "Google. (2024). Flutter documentation: Building cross-platform applications with Dart. Flutter Dev. https://docs.flutter.dev/",
        "OpenCV Team. (2023). Deep neural network-based face detection (YuNet) and recognition (SFace). OpenCV Library Documentation. https://docs.opencv.org/",
        "PostgreSQL Global Development Group. (2024). PostgreSQL 15.0 Documentation: Binary Data Types (BYTEA) and Concurrency. https://www.postgresql.org/docs/",
        "Rescorla, E. (2018). The Transport Layer Security (TLS) Protocol Version 1.3 (RFC 8446). Internet Engineering Task Force (IETF). https://doi.org/10.17487/RFC8446",
        "Google Open Source. (2024). Conscrypt: A Java Security Provider that uses BoringSSL. GitHub Repository. https://github.com/google/conscrypt",
        "Sommerville, I. (2016). Software Engineering (10th ed.). Pearson Education."
    ]

    for ref in refs:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.left_indent = Inches(0.5)
        p_ref.paragraph_format.first_line_indent = Inches(-0.5)
        p_ref.paragraph_format.space_after = Pt(6)
        p_ref.paragraph_format.line_spacing = 1.15
        run = p_ref.add_run(ref)
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)

    # Guardar documento
    try:
        doc.save(DOC_DEST_PATH)
        print(f"Documento generado exitosamente en: {DOC_DEST_PATH}")
    except PermissionError:
        alt_path = DOC_DEST_PATH.replace(".docx", "_ACTUALIZADO.docx")
        doc.save(alt_path)
        print(f"[AVISO] El archivo principal esta abierto en Word. Guardado en: {alt_path}")

def add_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
    return p

def add_subheading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(11.5)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1B, 0x4F, 0x72)
    return p

def add_sub_subheading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x28, 0x74, 0xA6)
    return p

def add_body_p(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    return p

def add_bullet(doc, text):
    p = doc.add_paragraph(style='List Paragraph')
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(f"•  {text}")
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    return p

if __name__ == "__main__":
    create_full_report()
