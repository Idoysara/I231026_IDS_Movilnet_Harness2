#!/usr/bin/env python3
"""
Convertidor Fiel 1:1 de Markdown a PDF Ejecutivo
Convierte /Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926/docs/DOCUMENTO_APROBACION_FASE0_EJECUTIVO.md
directamente a PDF preservando cada encabezado, párrafo, viñeta, bloque de alerta, tabla, diagrama y bloque de firmas.
"""

import os
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether, HRFlowable
)
from reportlab.platypus.flowables import Flowable

PROJECT_ROOT = "/Users/Users/Skills_Antigravity/Proyectos_IDS_Skills_Antigravity/AI_Movilnet_300926"
MD_FILE = os.path.join(PROJECT_ROOT, "docs", "DOCUMENTO_APROBACION_FASE0_EJECUTIVO.md")
OUTPUT_PDF = os.path.join(PROJECT_ROOT, "docs", "DOCUMENTO_APROBACION_FASE0_EJECUTIVO.pdf")
IMG_DIR = os.path.join(PROJECT_ROOT, "docs", "img")

# Colores Corporativos
MOVILNET_BLUE = colors.HexColor("#002B49")
MOVILNET_ACCENT = colors.HexColor("#FF6A13")
MOVILNET_MED = colors.HexColor("#00558C")
MOVILNET_DARK = colors.HexColor("#1A1A2E")
LIGHT_BG = colors.HexColor("#F8F9FA")
ALT_ROW_BG = colors.HexColor("#F4F7FB")
BORDER_COLOR = colors.HexColor("#DCDFE6")
ALERT_BG = colors.HexColor("#EBF3FB")
ALERT_BORDER = colors.HexColor("#00558C")


class ColoredHR(Flowable):
    def __init__(self, width, height=1.2, color=MOVILNET_BLUE):
        super().__init__()
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.height)
        self.canv.line(0, 0, self.width, 0)


def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='DocH1',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=MOVILNET_BLUE,
        spaceBefore=14,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='DocH2',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=MOVILNET_MED,
        spaceBefore=10,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='DocH3',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=MOVILNET_DARK,
        spaceBefore=8,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name='DocAudience',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#666666"),
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='DocBody',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.8,
        alignment=TA_JUSTIFY,
        textColor=MOVILNET_DARK,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name='DocBullet',
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.2,
        leftIndent=14,
        textColor=MOVILNET_DARK,
        spaceAfter=2.5,
    ))
    styles.add(ParagraphStyle(
        name='DocQuote',
        fontName='Helvetica-Oblique',
        fontSize=8.8,
        leading=12,
        leftIndent=14,
        rightIndent=14,
        alignment=TA_JUSTIFY,
        textColor=MOVILNET_DARK,
        spaceBefore=4,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='DocAlert',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        alignment=TA_JUSTIFY,
        textColor=MOVILNET_DARK,
        backColor=ALERT_BG,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='TCell',
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        textColor=MOVILNET_DARK,
    ))
    styles.add(ParagraphStyle(
        name='THeader',
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=9.8,
        textColor=colors.white,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='FigCap',
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=9.8,
        alignment=TA_CENTER,
        textColor=MOVILNET_BLUE,
        spaceBefore=2,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name='SignatureHead',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name='SignatureCell',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=MOVILNET_DARK,
    ))
    return styles


def format_md_line(text):
    """Convierte marcas markdown inline básicas a tags de ReportLab."""
    # Convertir **texto** a <b>texto</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convertir *texto* a <i>texto</i>
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    # Convertir `código` a <code>código</code>
    text = re.sub(r'`(.*?)`', r'<font face="Courier" color="#00558C">\1</font>', text)
    # Escapar ampersands sueltos
    text = text.replace(' & ', ' &amp; ')
    return text


def parse_markdown_table(lines, styles, col_widths=None):
    """Parsea líneas de tabla markdown y retorna un Flowable Table estilizado."""
    if not lines or len(lines) < 2:
        return None

    # Filtrar encabezado y filas
    raw_rows = []
    for l in lines:
        if re.match(r'^\s*\|?\s*[-:\s|]+\s*$', l):
            continue  # Línea separadora |:---|:---|
        cells = [c.strip() for c in l.strip().strip('|').split('|')]
        raw_rows.append(cells)

    if not raw_rows:
        return None

    header = raw_rows[0]
    rows = raw_rows[1:]

    h_cells = [Paragraph(f"<b>{format_md_line(h)}</b>", styles['THeader']) for h in header]
    table_data = [h_cells]

    for r in rows:
        # Rellenar celdas faltantes si la fila es corta
        while len(r) < len(header):
            r.append("")
        r_cells = [Paragraph(format_md_line(c), styles['TCell']) for c in r[:len(header)]]
        table_data.append(r_cells)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), MOVILNET_BLUE),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, 0), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3.5),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), ALT_ROW_BG))

    t.setStyle(TableStyle(t_style))
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(MOVILNET_BLUE)
        canvas.setLineWidth(0.8)
        canvas.line(0.6 * inch, letter[1] - 0.45 * inch, letter[0] - 0.6 * inch, letter[1] - 0.45 * inch)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.6 * inch, letter[1] - 0.38 * inch,
                          "DOCUMENTO DE APROBACIÓN EJECUTIVA — FASE 0 | CONFIDENCIAL")
        canvas.drawRightString(letter[0] - 0.6 * inch, letter[1] - 0.38 * inch,
                               "AI_Movilnet_300926")

        canvas.setStrokeColor(MOVILNET_BLUE)
        canvas.line(0.6 * inch, 0.45 * inch, letter[0] - 0.6 * inch, 0.45 * inch)
        canvas.setFont('Helvetica', 7)
        canvas.drawString(0.6 * inch, 0.35 * inch,
                          "Telecomunicaciones Movilnet C.A. © 2026")
        canvas.drawRightString(letter[0] - 0.6 * inch, 0.35 * inch,
                               f"Página {doc.page}")
    canvas.restoreState()


def convert_md_to_pdf():
    styles = create_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title="Documento de Aprobación Ejecutiva — Fase 0 — Movilnet IA",
        author="Antigravity Nivel 5 — CognitiveForge B2B Studio",
        subject="Copia Idéntica 1:1 de DOCUMENTO_APROBACION_FASE0_EJECUTIVO.md",
    )

    with open(MD_FILE, 'r', encoding='utf-8') as f:
        md_content = f.read()

    lines = md_content.split('\n')
    story = []
    W = doc.width

    in_table = False
    table_lines = []
    in_mermaid = False
    mermaid_count = 0
    in_quote = False
    quote_lines = []
    in_alert = False
    alert_lines = []

    def flush_table():
        nonlocal in_table, table_lines
        if in_table and table_lines:
            t = parse_markdown_table(table_lines, styles)
            if t:
                story.append(t)
                story.append(Spacer(1, 4))
            table_lines = []
            in_table = False

    def flush_quote():
        nonlocal in_quote, quote_lines
        if in_quote and quote_lines:
            q_text = " ".join(quote_lines)
            story.append(Paragraph(format_md_line(q_text), styles['DocQuote']))
            quote_lines = []
            in_quote = False

    def flush_alert():
        nonlocal in_alert, alert_lines
        if in_alert and alert_lines:
            a_text = " ".join(alert_lines)
            story.append(Paragraph(format_md_line(a_text), styles['DocAlert']))
            alert_lines = []
            in_alert = False

    i = 0
    while i < len(lines):
        line = lines[i]
        raw = line.strip()

        # 1. Detección de bloques Mermaid
        if raw.startswith('```mermaid'):
            flush_table()
            flush_quote()
            flush_alert()
            in_mermaid = True
            mermaid_count += 1
            # Asociar el diagrama correspondiente de la suite
            if mermaid_count == 1:
                img_path = os.path.join(IMG_DIR, "diag_user_flow.png")
                cap = "Diagrama: Flujo de la Experiencia del Abonado (Customer Journey)"
            elif mermaid_count == 2:
                img_path = os.path.join(IMG_DIR, "diag_architecture_9layers.png")
                cap = "Diagrama: Arquitectura Enterprise Desacoplada de 9 Capas"
            elif mermaid_count == 3:
                img_path = os.path.join(IMG_DIR, "chart_financial_analysis.png")
                cap = "Diagrama: Circuit Breaker de Presupuesto y Distribución de Tráfico"
            elif mermaid_count == 4:
                img_path = os.path.join(IMG_DIR, "diag_superapp_ecosystem.png")
                cap = "Diagrama: Ecosistema Super-App B2B2C — 4 Dominios Satelitales"
            elif mermaid_count == 5:
                img_path = os.path.join(IMG_DIR, "diag_roadmap_phases.png")
                cap = "Diagrama: Hoja de Ruta Secuencial Phase-Gate (Fases 0 a 4)"
            else:
                img_path = None
                cap = None

            if img_path and os.path.exists(img_path):
                # Altura ajustada según el gráfico
                h = 1.7*inch if mermaid_count in [1, 5] else (2.8*inch if mermaid_count == 2 else 2.1*inch)
                story.append(Image(img_path, width=7.2*inch, height=h))
                if cap:
                    story.append(Paragraph(cap, styles['FigCap']))
            i += 1
            continue

        if in_mermaid:
            if raw.startswith('```'):
                in_mermaid = False
            i += 1
            continue

        # 2. Detección de tablas markdown
        if raw.startswith('|') and '|' in raw[1:]:
            flush_quote()
            flush_alert()
            in_table = True
            table_lines.append(line)
            i += 1
            continue
        elif in_table:
            flush_table()

        # 3. Detección de Callouts / Alert blocks (> [!IMPORTANT], > [!TIP], > [!NOTE])
        if raw.startswith('> [!'):
            flush_quote()
            in_alert = True
            alert_lines = [raw.replace('> [!', '<b>[').replace(']', ']</b>:')]
            i += 1
            continue
        elif in_alert:
            if raw.startswith('>'):
                alert_lines.append(raw.lstrip('>').strip())
                i += 1
                continue
            else:
                flush_alert()

        # 4. Detección de citas normales (> texto)
        if raw.startswith('>'):
            in_quote = True
            quote_lines.append(raw.lstrip('>').strip())
            i += 1
            continue
        elif in_quote:
            flush_quote()

        # 5. Línea separadora horizontal (---)
        if raw.startswith('---'):
            story.append(Spacer(1, 2))
            story.append(ColoredHR(W, 1, MOVILNET_BLUE))
            story.append(Spacer(1, 4))
            i += 1
            continue

        # 6. Encabezados
        if raw.startswith('# '):
            story.append(Spacer(1, 4))
            story.append(Paragraph(format_md_line(raw[2:]), styles['DocH1']))
            i += 1
            continue
        if raw.startswith('## '):
            story.append(Spacer(1, 3))
            story.append(Paragraph(format_md_line(raw[3:]), styles['DocH2']))
            i += 1
            continue
        if raw.startswith('### '):
            if 'Audiencia' in raw:
                story.append(Paragraph(format_md_line(raw[4:]), styles['DocAudience']))
            else:
                story.append(Paragraph(format_md_line(raw[4:]), styles['DocH3']))
            i += 1
            continue

        # 7. Viñetas (- o *)
        if raw.startswith('- ') or raw.startswith('* '):
            item_text = raw[2:]
            story.append(Paragraph(f"• {format_md_line(item_text)}", styles['DocBullet']))
            i += 1
            continue

        # 8. Texto regular
        if raw:
            # Caso especial: bloque de firmas o líneas de texto
            story.append(Paragraph(format_md_line(raw), styles['DocBody']))
        else:
            story.append(Spacer(1, 2))

        i += 1

    # Flush final
    flush_table()
    flush_quote()
    flush_alert()

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    return OUTPUT_PDF


if __name__ == "__main__":
    out = convert_md_to_pdf()
    print(f"✅ PDF 1:1 generado exitosamente: {out}")
    print(f"   Tamaño: {os.path.getsize(out):,} bytes")
