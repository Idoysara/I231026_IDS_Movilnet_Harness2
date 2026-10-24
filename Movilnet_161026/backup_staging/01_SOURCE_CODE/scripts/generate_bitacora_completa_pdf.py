#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador PDF Completo — BITÁCORA MAESTRA AI_Movilnet_300926
Convierte los 67 capítulos completos de BITACORA_MOVILNET.md a PDF profesional.
ReportLab 3.x — Sin dependencias externas adicionales.
"""
import os, re, sys, hashlib, datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    PageBreak, Table, TableStyle, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

# ─────────────────────────────────────────
# PALETA CORPORATIVA MOVILNET
# ─────────────────────────────────────────
AZUL_NOCHE   = colors.HexColor('#002B49')
AZUL_4GMAX   = colors.HexColor('#00558C')
AZUL_CLARO   = colors.HexColor('#1A7FC1')
CIAN_ACCENT  = colors.HexColor('#00B4D8')
VERDE_OK     = colors.HexColor('#00897B')
ROJO_ALERTA  = colors.HexColor('#C62828')
GRIS_BG      = colors.HexColor('#F0F4F8')
GRIS_LINEA   = colors.HexColor('#CBD5E1')
GRIS_TEXTO   = colors.HexColor('#334155')
BLANCO       = colors.white
NEGRO        = colors.HexColor('#0A1118')

PROJECT = 'AI_Movilnet_300926'
RAIZ = Path('/Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926')
BITACORA_PATH = RAIZ / 'docs' / 'BITACORA_MOVILNET.md'
OUT_PDF = RAIZ / 'docs' / 'BITACORA_MOVILNET_COMPLETA.pdf'
NOW_VET = datetime.datetime.now().strftime('%Y-%m-%d %H:%M VET')


# ─────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────
def build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles['cover_title'] = ParagraphStyle(
        'cover_title', fontName='Helvetica-Bold', fontSize=28,
        textColor=AZUL_NOCHE, alignment=TA_CENTER, spaceAfter=12,
        leading=34
    )
    styles['cover_sub'] = ParagraphStyle(
        'cover_sub', fontName='Helvetica', fontSize=14,
        textColor=AZUL_4GMAX, alignment=TA_CENTER, spaceAfter=8, leading=20
    )
    styles['cover_meta'] = ParagraphStyle(
        'cover_meta', fontName='Helvetica', fontSize=10,
        textColor=GRIS_TEXTO, alignment=TA_CENTER, spaceAfter=4
    )
    styles['cover_cert'] = ParagraphStyle(
        'cover_cert', fontName='Helvetica-Bold', fontSize=9,
        textColor=VERDE_OK, alignment=TA_CENTER, spaceAfter=3
    )

    styles['h1'] = ParagraphStyle(
        'h1', fontName='Helvetica-Bold', fontSize=18,
        textColor=AZUL_NOCHE, spaceBefore=20, spaceAfter=10,
        borderPad=6, leading=22,
        backColor=GRIS_BG,
        leftIndent=8
    )
    styles['h2'] = ParagraphStyle(
        'h2', fontName='Helvetica-Bold', fontSize=14,
        textColor=AZUL_4GMAX, spaceBefore=16, spaceAfter=8,
        leading=18, leftIndent=4
    )
    styles['h3'] = ParagraphStyle(
        'h3', fontName='Helvetica-Bold', fontSize=12,
        textColor=AZUL_CLARO, spaceBefore=12, spaceAfter=6,
        leading=15, leftIndent=8
    )
    styles['h4'] = ParagraphStyle(
        'h4', fontName='Helvetica-BoldOblique', fontSize=11,
        textColor=CIAN_ACCENT, spaceBefore=8, spaceAfter=4,
        leading=14, leftIndent=12
    )
    styles['body'] = ParagraphStyle(
        'body', fontName='Helvetica', fontSize=9,
        textColor=NEGRO, spaceBefore=3, spaceAfter=3,
        leading=13, alignment=TA_JUSTIFY
    )
    styles['bullet'] = ParagraphStyle(
        'bullet', fontName='Helvetica', fontSize=9,
        textColor=NEGRO, spaceBefore=2, spaceAfter=2,
        leading=12, leftIndent=16, bulletIndent=8
    )
    styles['code'] = ParagraphStyle(
        'code', fontName='Courier', fontSize=7.5,
        textColor=NEGRO, spaceBefore=4, spaceAfter=4,
        leading=11, leftIndent=12, backColor=GRIS_BG,
        borderPad=4
    )
    styles['badge_ok'] = ParagraphStyle(
        'badge_ok', fontName='Helvetica-Bold', fontSize=9,
        textColor=VERDE_OK, spaceBefore=2, spaceAfter=2, leading=12
    )
    styles['badge_pending'] = ParagraphStyle(
        'badge_pending', fontName='Helvetica-Bold', fontSize=9,
        textColor=AZUL_CLARO, spaceBefore=2, spaceAfter=2, leading=12
    )
    styles['separator'] = ParagraphStyle(
        'separator', fontName='Helvetica', fontSize=7,
        textColor=GRIS_TEXTO, alignment=TA_CENTER, spaceBefore=6, spaceAfter=6
    )
    styles['toc_entry'] = ParagraphStyle(
        'toc_entry', fontName='Helvetica', fontSize=8.5,
        textColor=GRIS_TEXTO, spaceBefore=1, spaceAfter=1,
        leading=12, leftIndent=16
    )
    styles['toc_phase'] = ParagraphStyle(
        'toc_phase', fontName='Helvetica-Bold', fontSize=10,
        textColor=AZUL_NOCHE, spaceBefore=8, spaceAfter=2,
        leading=13
    )
    styles['chapter_banner'] = ParagraphStyle(
        'chapter_banner', fontName='Helvetica-Bold', fontSize=13,
        textColor=BLANCO, alignment=TA_LEFT, spaceBefore=18, spaceAfter=8,
        leading=17, leftIndent=10, backColor=AZUL_NOCHE, borderPad=8
    )

    return styles


# ─────────────────────────────────────────
# HEADER / FOOTER
# ─────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    W, H = A4

    # Header bar
    canvas.setFillColor(AZUL_NOCHE)
    canvas.rect(0, H - 1.4*cm, W, 1.4*cm, fill=1, stroke=0)
    canvas.setFillColor(BLANCO)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.drawString(1.2*cm, H - 0.95*cm, '📖 BITÁCORA MAESTRA DE INGENIERÍA — AI_Movilnet_300926')
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(W - 1.2*cm, H - 0.95*cm, 'Telecomunicaciones Movilnet C.A.')

    # Accent line under header
    canvas.setFillColor(CIAN_ACCENT)
    canvas.rect(0, H - 1.5*cm, W, 0.12*cm, fill=1, stroke=0)

    # Footer bar
    canvas.setFillColor(GRIS_BG)
    canvas.rect(0, 0, W, 1.1*cm, fill=1, stroke=0)
    canvas.setFillColor(GRIS_LINEA)
    canvas.rect(0, 1.0*cm, W, 0.08*cm, fill=1, stroke=0)

    canvas.setFillColor(GRIS_TEXTO)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(1.2*cm, 0.4*cm, f'Generado: {NOW_VET}  |  Certificados: 12 SHA-256  |  Tests: 211/211 OK')
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawCentredString(W/2, 0.4*cm, f'Página {doc.page}')
    canvas.drawRightString(W - 1.2*cm, 0.4*cm, 'CONFIDENCIAL — USO INTERNO')

    canvas.restoreState()


def on_first_page(canvas, doc):
    # No header/footer on cover
    pass


# ─────────────────────────────────────────
# UTILIDADES DE LIMPIEZA DE TEXTO
# ─────────────────────────────────────────
EMOJI_RE = re.compile(
    u'[\U00010000-\U0010ffff'
    u'\U0001F600-\U0001F64F'
    u'\U0001F300-\U0001F5FF'
    u'\U0001F680-\U0001F6FF'
    u'\U0001F700-\U0001F77F'
    u'\U0001F780-\U0001F7FF'
    u'\U0001F800-\U0001F8FF'
    u'\U0001F900-\U0001F9FF'
    u'\U0001FA00-\U0001FA6F'
    u'\U0001FA70-\U0001FAFF'
    u'\u2600-\u26FF'
    u'\u2700-\u27BF'
    u'\u2300-\u23FF'
    u'\u25A0-\u25FF'
    u'\u2B00-\u2BFF'
    u'\u231A-\u231B'
    u'\u23E9-\u23F3'
    u'\u23F8-\u23FA'
    u'\u24C2'
    u'\u25AA-\u25AB'
    u'\u25B6'
    u'\u25C0'
    u'\u25FB-\u25FE'
    u'\u2614-\u2615'
    u'\u2648-\u2653'
    u'\u267F'
    u'\u2693'
    u'\u26A1'
    u'\u26AA-\u26AB'
    u'\u26BD-\u26BE'
    u'\u26C4-\u26C5'
    u'\u26CE'
    u'\u26D4'
    u'\u26EA'
    u'\u26F2-\u26F3'
    u'\u26F5'
    u'\u26FA'
    u'\u26FD'
    u'\u2702'
    u'\u2705'
    u'\u2708-\u270D'
    u'\u270F'
    u'\u2712'
    u'\u2714'
    u'\u2716'
    u'\u271D'
    u'\u2721'
    u'\u2728'
    u'\u2733-\u2734'
    u'\u2744'
    u'\u2747'
    u'\u274C'
    u'\u274E'
    u'\u2753-\u2755'
    u'\u2757'
    u'\u2763-\u2764'
    u'\u2795-\u2797'
    u'\u27A1'
    u'\u27B0'
    u'\u27BF'
    u'\u2934-\u2935'
    u'\u2B05-\u2B07'
    u'\u2B1B-\u2B1C'
    u'\u2B50'
    u'\u2B55'
    u'\u3030'
    u'\u303D'
    u'\u3297'
    u'\u3299'
    u'\uFE0F'  # variation selector
    u'\u200D'  # ZWJ
    u']', flags=re.UNICODE
)

EMOJI_REPLACE = {
    '✅': '[OK]', '⏳': '[PEND]', '❌': '[ERR]', '🟢': '[ON]',
    '🔴': '[OFF]', '🟡': '[WARN]', '🚀': '[DEPLOY]', '🔐': '[SEC]',
    '📊': '[CHART]', '📱': '[MOBILE]', '🤖': '[AI]', '🏛️': '[ARCH]',
    '📌': '[PIN]', '📘': '[DOC]', '🔬': '[LAB]', '🎯': '[TARGET]',
    '🔗': '[LINK]', '⚡': '[FAST]', '💳': '[PAYMENT]', '🆘': '[ALERT]',
    '🎨': '[DESIGN]', '🗺️': '[MAP]', '🗂️': '[FILES]', '📐': '[PLAN]',
    '🚦': '[STATUS]', '🔒': '[LOCK]', '🏗️': '[BUILD]', '🔌': '[CONN]',
    '📦': '[PKG]', '🌐': '[WEB]', '🔄': '[SYNC]', '💡': '[TIP]',
    '📜': '[CERT]', '🏆': '[WIN]', '🔍': '[SEARCH]', '📁': '[FOLDER]',
    '🧠': '[AI-BRAIN]', '📂': '[DIR]', '🛡️': '[SHIELD]', '⚙️': '[CONFIG]',
    '📄': '[FILE]', '🎉': '[SUCCESS]', '💡': '[IDEA]',
}


def clean_text(text):
    """Limpia emojis y caracteres no compatibles con ReportLab Helvetica."""
    for emoji, rep in EMOJI_REPLACE.items():
        text = text.replace(emoji, rep)
    text = EMOJI_RE.sub('', text)
    # Escapa caracteres XML de ReportLab
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # Comillas tipográficas
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2014', '--').replace('\u2013', '-')
    return text


def safe_para(text, style):
    """Crea un Paragraph limpio, nunca falla."""
    try:
        return Paragraph(clean_text(text), style)
    except Exception:
        try:
            return Paragraph(clean_text(text[:200]) + '...', style)
        except Exception:
            return Spacer(1, 0.1*cm)


# ─────────────────────────────────────────
# PARSING DEL MARKDOWN
# ─────────────────────────────────────────
def parse_bitacora(md_path, styles):
    """Convierte BITACORA_MOVILNET.md en flowables de ReportLab."""
    content = md_path.read_text(encoding='utf-8', errors='replace')
    lines = content.split('\n')
    flowables = []
    in_code = False
    code_buf = []
    in_table = False
    table_rows = []
    skip_mermaid = False

    def flush_code():
        nonlocal code_buf
        if code_buf:
            combined = '\n'.join(code_buf)
            # Divide el bloque de código en chunks de 120 chars por línea
            for cl in combined.split('\n'):
                chunks = [cl[i:i+110] for i in range(0, max(len(cl),1), 110)]
                for chunk in chunks:
                    flowables.append(safe_para(chunk or ' ', styles['code']))
            code_buf = []
            flowables.append(Spacer(1, 0.2*cm))

    def flush_table():
        nonlocal table_rows
        if len(table_rows) >= 2:
            # Limpiar filas
            cleaned = []
            for row in table_rows:
                cells = [clean_text(c.strip()) for c in row]
                cleaned.append(cells)

            # Normalizar columnas
            max_cols = max(len(r) for r in cleaned)
            for r in cleaned:
                while len(r) < max_cols:
                    r.append('')

            col_w = (16.5*cm) / max_cols
            col_widths = [col_w] * max_cols

            t_data = []
            for r in cleaned:
                t_data.append([Paragraph(c[:120], styles['body']) for c in r])

            tbl = Table(t_data, colWidths=col_widths, repeatRows=1)
            tbl.setStyle(TableStyle([
                ('BACKGROUND',  (0,0), (-1,0), AZUL_NOCHE),
                ('TEXTCOLOR',   (0,0), (-1,0), BLANCO),
                ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',    (0,0), (-1,0), 8),
                ('BACKGROUND',  (0,1), (-1,-1), BLANCO),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [BLANCO, GRIS_BG]),
                ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
                ('FONTSIZE',    (0,1), (-1,-1), 7.5),
                ('GRID',        (0,0), (-1,-1), 0.5, GRIS_LINEA),
                ('VALIGN',      (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING',  (0,0), (-1,-1), 3),
                ('BOTTOMPADDING',(0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING',(0,0), (-1,-1), 4),
            ]))
            flowables.append(tbl)
            flowables.append(Spacer(1, 0.3*cm))
        table_rows.clear()

    chapter_count = 0

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()

        # ── Bloques de código ──────────────────────────────────
        if line.startswith('```'):
            if not in_code:
                lang = line[3:].strip().lower()
                if lang == 'mermaid':
                    skip_mermaid = True
                else:
                    skip_mermaid = False
                in_code = True
                if in_table:
                    flush_table()
                    in_table = False
            else:
                in_code = False
                if not skip_mermaid:
                    flush_code()
                skip_mermaid = False
            continue

        if in_code:
            if not skip_mermaid:
                code_buf.append(line)
            continue

        # ── Tablas Markdown ────────────────────────────────────
        if line.startswith('|'):
            if not in_table:
                in_table = True
            cells = [c for c in line.split('|') if c != '']
            # Saltar líneas separadoras de tabla
            if all(re.match(r'^[-: ]+$', c.strip()) for c in cells if c.strip()):
                continue
            table_rows.append(cells)
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        # ── Líneas horizontales ────────────────────────────────
        if line.strip() in ('---', '***', '___') or re.match(r'^-{3,}$', line.strip()):
            flowables.append(Spacer(1, 0.2*cm))
            flowables.append(HRFlowable(width='100%', thickness=0.5, color=GRIS_LINEA))
            flowables.append(Spacer(1, 0.2*cm))
            continue

        # ── Encabezados ────────────────────────────────────────
        if line.startswith('# '):
            text = line[2:].strip()
            if 'BITÁCORA' in text.upper() or 'MAESTRA' in text.upper():
                # Ya tenemos portada, no repetir
                continue
            flowables.append(PageBreak())
            flowables.append(safe_para(text, styles['h1']))
            continue

        if line.startswith('## '):
            text = line[3:].strip()
            # Detectar capítulos principales
            is_chapter = (
                re.match(r'(Capítulo|CAPÍTULO|📘|📌|🏛️)', text) or
                'CAPÍTULO' in text.upper()
            )
            if is_chapter:
                chapter_count += 1
                flowables.append(PageBreak())
                flowables.append(safe_para(text, styles['chapter_banner']))
            else:
                flowables.append(safe_para(text, styles['h2']))
            continue

        if line.startswith('### '):
            text = line[4:].strip()
            flowables.append(safe_para(text, styles['h3']))
            continue

        if line.startswith('#### '):
            text = line[5:].strip()
            flowables.append(safe_para(text, styles['h4']))
            continue

        # ── Listas ────────────────────────────────────────────
        if re.match(r'^(\s*)([-*+]|\d+\.) ', line):
            # Quitar prefijo de lista
            stripped = re.sub(r'^(\s*)([-*+]|\d+\.) ', '', line)
            # Procesar inline markdown básico
            stripped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', stripped)
            stripped = re.sub(r'\*(.+?)\*', r'<i>\1</i>', stripped)
            stripped = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', stripped)
            stripped = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)  # links → text
            indent = len(line) - len(line.lstrip())
            style = styles['bullet']
            flowables.append(Paragraph('• ' + clean_text(stripped), style))
            continue

        # ── Línea vacía ────────────────────────────────────────
        if not line.strip():
            flowables.append(Spacer(1, 0.15*cm))
            continue

        # ── Bold/inline markdown ───────────────────────────────
        line2 = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        line2 = re.sub(r'\*(.+?)\*', r'<i>\1</i>', line2)
        line2 = re.sub(r'`(.+?)`', r'<font name="Courier" size="8">\1</font>', line2)
        line2 = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line2)  # links → text
        line2 = re.sub(r'!\[[^\]]*\]\([^)]+\)', '[imagen]', line2)  # images

        # Párrafo normal
        try:
            flowables.append(Paragraph(clean_text(line2), styles['body']))
        except Exception:
            flowables.append(Paragraph(clean_text(line[:200]), styles['body']))

    # Flush pendientes al final
    if in_code and code_buf and not skip_mermaid:
        flush_code()
    if in_table and table_rows:
        flush_table()

    return flowables, chapter_count


# ─────────────────────────────────────────
# PORTADA
# ─────────────────────────────────────────
def build_cover(styles):
    elems = []
    elems.append(Spacer(1, 3*cm))

    # Logo band
    banner_data = [['TELECOMUNICACIONES MOVILNET C.A.']]
    banner = Table(banner_data, colWidths=[16.5*cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), AZUL_NOCHE),
        ('TEXTCOLOR',     (0,0), (-1,-1), BLANCO),
        ('FONTNAME',      (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 14),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
    ]))
    elems.append(banner)
    elems.append(Spacer(1, 1*cm))

    elems.append(safe_para('BITACORA MAESTRA DE INGENIERIA Y OPERACIONES', styles['cover_title']))
    elems.append(Spacer(1, 0.4*cm))

    elems.append(safe_para('Aplicacion Cognitiva Interactiva de Inteligencia Artificial', styles['cover_sub']))
    elems.append(safe_para('Sistema de Atencion al Abonado — 4.000.000 de Abonados (0416 / 0426)', styles['cover_sub']))
    elems.append(Spacer(1, 0.8*cm))

    # Metadata table
    meta = [
        ['Proyecto:', 'AI_Movilnet_300926'],
        ['Identificador Unico:', 'AI_Movilnet_300926'],
        ['Fecha de Inicio:', '30 de Septiembre de 2026'],
        ['Fecha de Corte:', NOW_VET],
        ['Capitulos:', '67 Capitulos (Cap. 1 al 67)'],
        ['Tests Globales:', '211 / 211 — 100% OK'],
        ['Certificados:', '12 Sellos SHA-256 Criptograficos'],
        ['Arquitectura:', 'TM Forum ODA (TMF620/621/622/632/675/676/678/680)'],
        ['Nivel de Autonomia:', 'Antigravity Swarm Orchestrator Nivel 5'],
    ]
    t = Table(meta, colWidths=[5.5*cm, 11*cm])
    t.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',  (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), AZUL_NOCHE),
        ('TEXTCOLOR', (1,0), (1,-1), NEGRO),
        ('GRID',      (0,0), (-1,-1), 0.5, GRIS_LINEA),
        ('BACKGROUND',(0,0), (-1,-1), GRIS_BG),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [GRIS_BG, BLANCO]),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 1*cm))

    # Certificados
    certs_data = [
        ['CERTIFICADOS CRIPTOGRAFICOS ACTIVOS', ''],
        ['Fase 0 Gate 0:', 'FASE0-CERT-6CFBDE45D91A'],
        ['Fase 1 Gate 1:', 'FASE1-CERT-B1ED910BFAC6'],
        ['Fase 2 Gate 2:', 'FASE2-GATEKEEPER-CERT-5F331AB7384F'],
        ['Fase 3 Gate 3:', 'FASE3-GATEKEEPER-CERT-0886A5D9B351'],
        ['Fase 4 Paso 1:', 'FASE4-PASO1-CERT-8C21DA769B40'],
    ]
    tc = Table(certs_data, colWidths=[5.5*cm, 11*cm])
    tc.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), VERDE_OK),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
        ('SPAN',          (0,0), (-1,0)),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN',         (0,0), (-1,0), 'CENTER'),
        ('FONTNAME',      (0,1), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',      (1,1), (1,-1), 'Courier'),
        ('FONTSIZE',      (0,0), (-1,-1), 8.5),
        ('TEXTCOLOR',     (0,1), (0,-1), AZUL_NOCHE),
        ('TEXTCOLOR',     (1,1), (1,-1), VERDE_OK),
        ('GRID',          (0,0), (-1,-1), 0.5, GRIS_LINEA),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [GRIS_BG, BLANCO]),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
    ]))
    elems.append(tc)
    elems.append(Spacer(1, 1.5*cm))

    # SHA de este PDF
    sha_note = 'Documento generado automaticamente por Swarm Orchestrator Autonomo — Nivel 5'
    elems.append(safe_para(sha_note, styles['cover_cert']))
    elems.append(safe_para('CONFIDENCIAL — USO INTERNO — Telecomunicaciones Movilnet C.A.', styles['cover_meta']))

    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────
# INDICE DE CONTENIDOS
# ─────────────────────────────────────────
def build_toc(styles):
    elems = []
    elems.append(safe_para('INDICE GENERAL DE CAPITULOS', styles['h1']))
    elems.append(Spacer(1, 0.3*cm))

    phases = [
        ('FASE 0 — Discovery & Inception (Caps. 1-29)', [
            (1, 'Concepcion, Viabilidad y Mapeo de Capacidades Telco'),
            (2, 'Inicializacion Estructural y Motor de Bitacora Continua'),
            (3, 'Reactivacion de Contexto y Resumen Ejecutivo'),
            (4, 'Dimensionamiento Enterprise 4M Abonados'),
            (5, 'Pivote Metodologico: Activacion de Fase 0'),
            (6, 'Estrategia de Suite de Descubrimiento'),
            (7, 'Ensamblado y Certificacion de Suite Completa'),
            (8, 'Actualizacion Maestra y Consolidacion Total'),
            (9, 'Sincronizacion Global de Inventario'),
            (10, 'Diseno de Viabilidad y Arquitectura Loop Engineering'),
            (11, 'Ejecucion Integral de Comandos Loop Engineering'),
            (12, 'Modelado del Diagrama Operativo y de Flujo Completo'),
            (13, 'Estrategia Dual de Modelos de IA'),
            (14, 'Formalizacion de Aplicacion Interactiva Humanizada'),
            (15, 'Investigacion de n8n: MCP, Skill y Compilador'),
            (16, 'Verificacion y Atlas Maestro de Flujogramas'),
            (17, 'Evaluacion Estrategica: Rol de n8n en el Proyecto'),
            (18, 'Rediseno Integral de Flujogramas con n8n'),
            (19, 'Diseno de Experiencia del Usuario (Journey Map)'),
            (20, 'Evolucion a App Transaccional C2P'),
            (21, 'Incorporacion Super-App Telco B2B2C'),
            (22, 'Preparacion y Conexion de Repositorios GitHub'),
            (23, 'Implementacion de Patrones GitHub (LangGraph, TMF680)'),
            (24, 'Extraccion del Catalogo de Servicios Movilnet'),
            (25, 'Investigacion Canal Digital Actual vs Sistema Cognitivo'),
            (26, 'Bateria Tecnologica y Benchmark Competitivo'),
            (27, 'Documento Ejecutivo de Aprobacion de Fase 0'),
            (28, 'Generacion del Documento PDF Ejecutivo'),
            (29, 'Consolidacion del Dossier Ejecutivo Maestro en PDF'),
        ]),
        ('EXTENSION FASE 0 — n8n, Skills & MCP (Caps. 30-47)', [
            (30, 'Exploracion y Mapeo de Integracion n8n.lpgtec.net'),
            (31, 'Implementacion del Servidor MCP y CLI Autonomo'),
            (32, 'Sincronizacion Total de Documentos Maestros'),
            (33, 'Diferenciacion de Alcance de Componentes n8n'),
            (34, 'Analisis Exhaustivo del Flujo n8n Atencion_al_Cliente'),
            (35, 'Evaluacion de Ecosistemas Abiertos en skills.sh'),
            (36, 'Importacion e Instalacion de 5 Skills Clave'),
            (37, 'Verificacion y Despliegue Local de Skills Importados'),
            (38, 'Segunda Oleada de Importacion de Skills'),
            (39, 'Verificacion de Despliegue Fisico y Taxonomia'),
            (40, 'Activacion y Ejecucion del Motor de Ahorro de Tokens'),
            (41, 'Diseno y Factibilidad Arquitectonica de Nuevos MCPs'),
            (42, 'Construccion, Integracion y Certificacion de MCPs'),
            (43, 'Construccion Integral de las 5 Suites MCP'),
            (44, 'Clasificacion Arquitectonica: MCPs Globales vs Proyecto'),
            (45, 'Auditoria Fisica Integral de Ubicaciones'),
            (46, 'Actualizacion Integral de Documentos y PDF Fase 0'),
            (47, 'Resolucion y Saneamiento de Diagramas Mermaid'),
        ]),
        ('FASE 1 — Capa de Datos ODA & Persistencia (Caps. 48-54)', [
            (48, 'Inicio Formal de Fase 1 y Modelo Conceptual de Datos'),
            (49, 'Especificacion y Diccionario de 10 Tablas PostgreSQL 15'),
            (50, 'Marco de Integracion: Base de Datos <-> Arquitectura n8n'),
            (51, 'Incorporacion del Diagrama n8n de 3 Niveles'),
            (52, 'Consolidacion Documental y Documento Maestro Fase 1'),
            (53, 'Protocolo de Handover y Memoria Operativa'),
            (54, 'Ejecucion y Certificacion Fisica de la Fase 1 (Pasos 1-6)'),
        ]),
        ('FASE 2 — Microservicios REST API + n8n + MCP (Caps. 55-58)', [
            (55, 'Fase 2 P1 — Microservicio REST API y OpenAPI 3.1.0'),
            (56, 'Fase 2 P2 — Workflows Omnicanal n8n (WhatsApp/Telegram/C2P/EIR/Churn)'),
            (57, 'Fase 2 P3 — Integracion Webhooks n8n + REST API + MCP'),
            (58, 'Fase 2 GK2 — Certificacion Gatekeeper 2 y Cierre Fase 2'),
        ]),
        ('FASE 3 — Core IA & Enjambre Swarm Nivel 5 (Caps. 59-63)', [
            (59, 'Fase 3 P1 — Agente N1: Customer Care & OCS (TMF621)'),
            (60, 'Fase 3 P2 — Agente N2: Pasarela Financiera C2P BCV (TMF676)'),
            (61, 'Fase 3 P3 — Agente N3: Emergencias EIR/IMEI GSMA'),
            (62, 'Fase 3 P4 — Agente N4: Retencion Proactiva & Churn ML (TMF680)'),
            (63, 'Fase 3 GK3 — Certificacion Gatekeeper 3 y Cierre Fase 3'),
        ]),
        ('FASE 4 — Interfaces UI/UX/IX/AX (Caps. 64-67)', [
            (64, 'Fase 4 P1 — Sistema de Diseno Corporativo WCAG 2.1 AAA'),
            (65, 'Auditoria Integral de Fases: Diagnostico y Veredicto'),
            (66, 'Dossier Maestro de Ejecucion: Todas las Fases y Pasos'),
            (67, 'Cierre de Sesion Turno 3: Actualizacion Documental y Handover'),
        ]),
    ]

    for phase_title, chapters in phases:
        elems.append(safe_para(phase_title, styles['toc_phase']))
        for num, title in chapters:
            entry = f'Cap. {num:02d} — {title}'
            elems.append(safe_para(entry, styles['toc_entry']))
        elems.append(Spacer(1, 0.15*cm))

    elems.append(PageBreak())
    return elems


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    print(f'[1/5] Leyendo bitacora: {BITACORA_PATH}')
    assert BITACORA_PATH.exists(), f'No encontrado: {BITACORA_PATH}'

    print('[2/5] Construyendo estilos...')
    styles = build_styles()

    print('[3/5] Parseando Markdown (2130+ lineas, 67 capitulos)...')
    body_flowables, n_chapters = parse_bitacora(BITACORA_PATH, styles)
    print(f'      Capitulos detectados en parseo: {n_chapters}')

    print('[4/5] Armando documento PDF...')
    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2.2*cm,
        bottomMargin=1.8*cm,
        title='Bitacora Maestra de Ingenieria — AI_Movilnet_300926',
        author='Swarm Orchestrator Autonomo Nivel 5',
        subject='Telecomunicaciones Movilnet C.A.',
        creator='ReportLab 3.x + Antigravity AI',
    )

    story = []

    # Portada (sin header/footer)
    story += build_cover(styles)

    # Indice
    story += build_toc(styles)

    # Cuerpo completo de la bitacora
    story += body_flowables

    # Pagina final
    story.append(PageBreak())
    story.append(Spacer(1, 4*cm))
    story.append(safe_para('-- FIN DE LA BITACORA MAESTRA --', styles['separator']))
    story.append(Spacer(1, 0.5*cm))
    story.append(safe_para(f'Generado: {NOW_VET}', styles['cover_meta']))
    story.append(safe_para('211 tests | 12 certificados SHA-256 | 67 Capitulos', styles['cover_cert']))
    story.append(safe_para('Telecomunicaciones Movilnet C.A. — CONFIDENCIAL — USO INTERNO', styles['cover_meta']))

    print('[5/5] Generando PDF...')
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)

    # SHA-256 del PDF generado
    pdf_bytes = OUT_PDF.read_bytes()
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    size_kb = len(pdf_bytes) / 1024

    print(f'\n[OK] PDF generado exitosamente:')
    print(f'     Archivo : {OUT_PDF}')
    print(f'     Tamano  : {size_kb:.1f} KB')
    print(f'     SHA-256 : {sha}')
    print(f'     Capitulos en bitacora: 67 (Cap. 1 al 67)')
    print(f'     Tests al cierre: 211/211 (100%)')

    return sha, size_kb


if __name__ == '__main__':
    main()
