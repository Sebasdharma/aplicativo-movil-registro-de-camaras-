# -*- coding: utf-8 -*-
"""
Script para generar el Informe de Laboratorio Nº 5 de Aplicaciones Móviles
Universidad Politécnica Estatal del Carchi (UPEC)
Autor: Reina Gordon Jhoel Sebastian
Docente: Msc. Samuel Lascano Rivera
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOC_PATH = r"C:\Users\joel_\Desktop\aplicaciones moviles portaafolio\Guía de práctica de laboratorio_5_folio_23 - (1).docx"

# Rutas de imágenes de evidencia
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

def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_table_borders(table, color="B0C4DE", sz="4", val="single"):
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

def add_styled_paragraph(doc, text="", style='Normal', space_after=6, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph(style=style)
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    if text:
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    return p

def add_heading_2(doc, title_text, space_before=12, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(title_text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x00, 0x33, 0x66) # Azul institucional elegante
    return p

def add_heading_3(doc, title_text, space_before=8, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(title_text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1B, 0x4F, 0x72)
    return p

print("Helper functions ready")
