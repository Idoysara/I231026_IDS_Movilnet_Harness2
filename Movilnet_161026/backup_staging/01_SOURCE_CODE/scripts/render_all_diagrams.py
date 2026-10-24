#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador Maestro de Gráficos y Diagramas Vectoriales de Alta Resolución (300 DPI)
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Genera imágenes nítidas para las arquitecturas, flujos y esquemas del sistema.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "img")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Paleta Corporativa Movilnet
C_DARK    = "#002B49"  # Azul Noche Institucional
C_MED     = "#00558C"  # Azul Eléctrico 4GMAX
C_LIGHT   = "#0088CE"  # Azul Claro
C_CYAN    = "#00B4D8"  # Cyan Accent
C_ORANGE  = "#FF6A13"  # Naranja Dinámico
C_GREEN   = "#2E7D32"  # Verde Éxito
C_RED     = "#C62828"  # Rojo Alerta
C_BG      = "#F8FAFC"  # Fondo Claro
C_CARD    = "#FFFFFF"  # Tarjeta Blanca
C_TEXT    = "#0A1118"  # Texto Primario
C_BORDER  = "#CBD5E1"  # Borde Suave

def draw_card(ax, x, y, w, h, bg=C_CARD, border=C_MED, lw=1.5, radius=0.1):
    # Sombra
    shadow = patches.FancyBboxPatch((x+0.04, y-0.04), w, h, boxstyle=f"round,pad=0.03,rounding_size={radius}",
                                    facecolor="#E2E8F0", edgecolor="none")
    ax.add_patch(shadow)
    # Tarjeta
    card = patches.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.03,rounding_size={radius}",
                                  facecolor=bg, edgecolor=border, linewidth=lw)
    ax.add_patch(card)
    return card

# 1. Diagrama de las 5 Fases del Proyecto
def gen_diag_phases():
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis('off')

    phases = [
        ("FASE 0", "Discovery & Inception", "41 Tests (100%)\nCertificado Oficial\nDossier Aprobado", C_DARK, "[OK]"),
        ("FASE 1", "Persistencia & ODA", "10 Tablas ODA\nPostgres + WAL\n8 Tests (100%)", C_MED, "[OK]"),
        ("FASE 2", "API & n8n Omnicanal", "OpenAPI 3.1.0\n5 Workflows n8n\n75 Tests (100%)", C_LIGHT, "[OK]"),
        ("FASE 3", "Core IA Swarm L5", "4 Agentes (N1-N4)\nC2P, EIR, Churn\n74 Tests (100%)", C_ORANGE, "[OK]"),
        ("FASE 4", "UI/UX & Despliegue", "Design Tokens AAA\nDashboard NOC\n211 Tests Globales", C_GREEN, "[ACTIVA]"),
    ]

    for i, (title, sub, desc, col, badge) in enumerate(phases):
        x = 0.25 + i * 1.95
        y = 0.35
        w = 1.65
        h = 2.4
        draw_card(ax, x, y, w, h, bg=C_CARD, border=col, lw=2)

        # Header banner de la tarjeta
        header = patches.FancyBboxPatch((x, y+1.7), w, 0.7, boxstyle="round,pad=0.01,rounding_size=0.08",
                                        facecolor=col, edgecolor="none")
        ax.add_patch(header)
        ax.text(x+w/2, y+2.15, title, ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        ax.text(x+w/2, y+1.85, badge, ha='center', va='center', fontsize=7.5, fontweight='bold', color=C_CYAN if badge=="[OK]" else "#FFF")

        # Texto interior
        ax.text(x+w/2, y+1.4, sub, ha='center', va='center', fontsize=7.5, fontweight='bold', color=C_TEXT)
        ax.text(x+w/2, y+0.75, desc, ha='center', va='center', fontsize=6.5, color="#475569", linespacing=1.3)

        # Flecha conectora
        if i < len(phases) - 1:
            ax.annotate('', xy=(x+w+0.28, y+1.2), xytext=(x+w+0.02, y+1.2),
                        arrowprops=dict(arrowstyle="->", color=C_DARK, lw=2, mutation_scale=12))

    ax.set_title("MAPA MAESTRO DE FASES CERTIFICADAS — TELECOMUNICACIONES MOVILNET C.A.",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=10)
    p = os.path.join(OUTPUT_DIR, "diag_roadmap_phases.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 2. Diagrama de Arquitectura en 9 Capas
def gen_diag_9layers():
    fig, ax = plt.subplots(figsize=(10, 5.0), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.0)
    ax.axis('off')

    layers = [
        ("Capa 1: Canales de Contacto", "WhatsApp Cloud API · Telegram Bot · Webchat PWA · Portal Autoservicio", C_DARK),
        ("Capa 2: Seguridad & Perímetro", "HMAC-SHA256 · Anti-Replay 300s · Rate Limit Redis · Zero-Knowledge PII", C_RED),
        ("Capa 3: Orquestación Visual n8n", "5 Workflows Omnicanal · Parsing Webhooks · Enrutamiento Ágil · Dispatcher", C_ORANGE),
        ("Capa 4: Microservicio REST API", "FastAPI / HTTP Core · 23 Endpoints · OpenAPI 3.1.0 TM Forum ODA", C_MED),
        ("Capa 5: Enjambre Swarm Nivel 5", "N1 Customer Care · N2 Fintech C2P · N3 EIR Emergencias · N4 Churn ML", C_LIGHT),
        ("Capa 6: Inteligencia Artificial", "Fast-Path Regex (<0.3ms) · LLM Reasoning Gemini/DeepSeek · Scikit-Learn 1.7.2", C_CYAN),
        ("Capa 7: Pasarela MCP (Model Context)", "5 Suites MCP Modulares (26 herramientas) · JSON-RPC 2.0 Gateway", C_MED),
        ("Capa 8: Persistencia & Datos ODA", "PostgreSQL 15 Particionado (8 Shards HASH + RANGE CDR) + SQLite WAL", C_DARK),
        ("Capa 9: SRE, DevOps & Observabilidad", "Ring Buffer (<25ms) · Métricas de Latencia · Docker Compose · Auditoría SAST", C_GREEN),
    ]

    for i, (title, desc, col) in enumerate(layers):
        y = 4.4 - i * 0.48
        # Barra lateral de color
        bar = patches.Rectangle((0.4, y), 0.15, 0.4, facecolor=col, edgecolor="none")
        ax.add_patch(bar)
        # Caja principal
        box = patches.FancyBboxPatch((0.6, y), 9.0, 0.4, boxstyle="round,pad=0.01,rounding_size=0.04",
                                     facecolor=C_BG, edgecolor=C_BORDER, linewidth=0.8)
        ax.add_patch(box)
        ax.text(0.8, y+0.2, title, va='center', fontsize=7.5, fontweight='bold', color=C_DARK)
        ax.text(3.8, y+0.2, desc, va='center', fontsize=6.5, color="#334155")

    ax.set_title("ARQUITECTURA ENTERPRISE EN 9 CAPAS — MOVILNET IA",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=12)
    p = os.path.join(OUTPUT_DIR, "diag_architecture_9layers.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 3. Diagrama de Customer Journey y Experiencia de Usuario
def gen_diag_user_flow():
    fig, ax = plt.subplots(figsize=(10, 2.8), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.8)
    ax.axis('off')

    steps = [
        ("1. Contacto", "Abonado escribe en\nWhatsApp / Web\n\"Me quedé sin datos\"", C_DARK),
        ("2. Identidad", "Blind Index HMAC\nCédula V/E/J\nZero-Knowledge PII", C_MED),
        ("3. Fast-Path", "Clasificador sintáctico\n<0.2ms en RAM\n$0.00 en tokens", C_ORANGE),
        ("4. Solución C2P", "Débito bancario BCV\nRecarga en chat\n23 bancos SUDEBAN", C_GREEN),
        ("5. Confirmación", "Bono 4GMAX activo\nFactura digital SMS\nSatisfacción NPS 95%", C_CYAN),
    ]

    for i, (title, desc, col) in enumerate(steps):
        x = 0.25 + i * 1.95
        y = 0.35
        w = 1.65
        h = 2.0
        draw_card(ax, x, y, w, h, border=col, lw=1.8)
        
        # Header
        h_patch = patches.FancyBboxPatch((x, y+1.4), w, 0.6, boxstyle="round,pad=0.01,rounding_size=0.06",
                                        facecolor=col, edgecolor="none")
        ax.add_patch(h_patch)
        ax.text(x+w/2, y+1.7, title, ha='center', va='center', fontsize=8, fontweight='bold', color='white')
        ax.text(x+w/2, y+0.7, desc, ha='center', va='center', fontsize=6.5, color=C_TEXT, linespacing=1.2)

        if i < len(steps) - 1:
            ax.annotate('', xy=(x+w+0.28, y+1.0), xytext=(x+w+0.02, y+1.0),
                        arrowprops=dict(arrowstyle="->", color=C_DARK, lw=2, mutation_scale=12))

    ax.set_title("EXPERIENCIA DEL ABONADO — INTERACCIÓN COGNITIVA NATURAL HUMANA",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=10)
    p = os.path.join(OUTPUT_DIR, "diag_user_flow.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 4. Diagrama del Enjambre Swarm L5 (4 Agentes)
def gen_diag_swarm():
    fig, ax = plt.subplots(figsize=(10, 4.0), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.0)
    ax.axis('off')

    # Centro: Swarm Orchestrator
    draw_card(ax, 3.8, 1.4, 2.4, 1.2, bg=C_DARK, border=C_CYAN, lw=2)
    ax.text(5.0, 2.1, "SWARM ORCHESTRATOR", ha='center', va='center', fontsize=8, fontweight='bold', color='white')
    ax.text(5.0, 1.7, "Nivel 5 Autonomía\nCoordinación Cruzada\nHandoffs Sub-Milisegundo", ha='center', va='center', fontsize=6.5, color=C_CYAN, linespacing=1.2)

    # 4 Agentes alrededor
    agents = [
        ("N1: Customer Care", "TMF621 OCS\nFast-Path 0.207ms\nCaché L1 60s", 0.6, 2.4, C_MED),
        ("N2: Fintech C2P", "TMF676 BCV 41.52\n23 Bancos SUDEBAN\nAnti-Replay", 0.6, 0.4, C_GREEN),
        ("N3: Emergencias EIR", "GSMA Blacklist\nLuhn-10 IMEI\nSIM-Swap <72h", 7.0, 2.4, C_RED),
        ("N4: Retención Churn", "TMF680 ML 0.88ms\nScikit-Learn 1.7.2\nCupones NBA", 7.0, 0.4, C_ORANGE),
    ]

    for title, desc, x, y, col in agents:
        w = 2.4
        h = 1.2
        draw_card(ax, x, y, w, h, border=col, lw=2)
        ax.text(x+w/2, y+0.85, title, ha='center', va='center', fontsize=7.5, fontweight='bold', color=col)
        ax.text(x+w/2, y+0.4, desc, ha='center', va='center', fontsize=6.2, color=C_TEXT, linespacing=1.2)

        # Conexiones bidireccionales con el centro
        cx, cy = (5.0, 2.0)
        target_x = x + w if x < 5.0 else x
        target_y = y + h/2
        orig_x = 3.8 if x < 5.0 else 6.2
        orig_y = 2.0
        ax.annotate('', xy=(target_x, target_y), xytext=(orig_x, orig_y),
                    arrowprops=dict(arrowstyle="<->", color=col, lw=1.5, ls="--"))

    ax.set_title("ENJAMBRE MULTI-AGENTE AUTÓNOMO SWARM L5 — COORDINACIÓN EN VIVO",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=10)
    p = os.path.join(OUTPUT_DIR, "diag_swarm_l5.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 5. Diagrama de Integración n8n de 3 Niveles
def gen_diag_n8n():
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis('off')

    boxes = [
        ("NIVEL 1: ENTRADA", "Meta WhatsApp Cloud API\nTelegram Bot API\nWebhooks Omnicanal\n(Firma HMAC-SHA256)", 0.4, C_DARK),
        ("NIVEL 2: ORQUESTADOR n8n", "Canvas krfZSDSsTHGUliCU\n5 Workflows Desplegados\nEnrutamiento Fast-Path\nDead Letter Queue (DLQ)", 3.7, C_ORANGE),
        ("NIVEL 3: MOTOR & DATOS", "REST API Core (FastAPI)\nPostgreSQL 15 (8 Shards)\nCaché L1 Redis (<2ms)\n5 Suites MCP de Soporte", 7.0, C_MED),
    ]

    for title, desc, x, col in boxes:
        y = 0.4
        w = 2.6
        h = 2.3
        draw_card(ax, x, y, w, h, border=col, lw=2)

        header = patches.FancyBboxPatch((x, y+1.7), w, 0.6, boxstyle="round,pad=0.01,rounding_size=0.06",
                                        facecolor=col, edgecolor="none")
        ax.add_patch(header)
        ax.text(x+w/2, y+2.0, title, ha='center', va='center', fontsize=7.5, fontweight='bold', color='white')
        ax.text(x+w/2, y+0.85, desc, ha='center', va='center', fontsize=6.5, color=C_TEXT, linespacing=1.3)

    # Conectores Nivel 1 -> Nivel 2 -> Nivel 3
    ax.annotate('', xy=(3.65, 1.55), xytext=(3.05, 1.55),
                arrowprops=dict(arrowstyle="->", color=C_DARK, lw=2.5, mutation_scale=14))
    ax.annotate('', xy=(6.95, 1.55), xytext=(6.35, 1.55),
                arrowprops=dict(arrowstyle="->", color=C_DARK, lw=2.5, mutation_scale=14))

    ax.set_title("TOPOLOGÍA DE INTEGRACIÓN N8N DE 3 NIVELES — MOVILNET IA",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=10)
    p = os.path.join(OUTPUT_DIR, "diag_n8n_3levels.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 6. Diagrama Financiero & Token Optimization
def gen_diag_financial():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.4), dpi=300)
    fig.patch.set_facecolor('white')

    # Gráfico de barras: Costos Tradicional vs Antigravity Zero-Cost
    cats = ['Licenciamiento\nPropietario', 'Infraestructura\nCloud Prop.', 'Movilnet IA\n(Zero-Cost Stack)']
    costs = [185000, 45000, 127.80]
    bar_cols = [C_RED, C_ORANGE, C_GREEN]

    bars = ax1.bar(cats, costs, color=bar_cols, width=0.55, edgecolor=C_BORDER)
    ax1.set_yscale('log')
    ax1.set_ylabel('Costo Estimado Anual USD (Escala Log)', fontsize=7.5, color=C_DARK)
    ax1.set_title('Comparativa de Costo de Licenciamiento', fontsize=8.5, fontweight='bold', color=C_DARK)
    ax1.tick_params(axis='both', labelsize=7)

    for bar, val in zip(bars, costs):
        yval = bar.get_height()
        if val > 1000:
            ax1.text(bar.get_x() + bar.get_width()/2, yval*1.3, f"${val:,.0f}", ha='center', va='bottom', fontsize=7, fontweight='bold', color=C_DARK)
        else:
            ax1.text(bar.get_x() + bar.get_width()/2, yval*1.8, f"${val:.2f}\n(99.9% Ahorro)", ha='center', va='bottom', fontsize=7, fontweight='bold', color=C_GREEN)

    # Gráfico circular: Fast-Path vs LLM
    labels = ['Fast-Path (<0.3ms)\nCero Tokens ($0)', 'Inferencia LLM\n(Con Caché y Poda)']
    sizes = [70, 30]
    colors_pie = [C_GREEN, C_MED]
    explode = (0.05, 0)

    wedges, texts, autotexts = ax2.pie(sizes, explode=explode, labels=labels, autopct='%1.0f%%',
                                       startangle=140, colors=colors_pie,
                                       textprops=dict(color=C_TEXT, fontsize=7.5))
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
        at.set_fontsize(8)

    ax2.set_title('Estrategia de Optimización de Tokens', fontsize=8.5, fontweight='bold', color=C_DARK)

    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "chart_financial_analysis.png")
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 7. Diagrama del Ecosistema Super-App
def gen_diag_superapp():
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.2)
    ax.axis('off')

    # Centro: Movilnet Línea Móvil
    draw_card(ax, 3.8, 1.0, 2.4, 1.2, bg=C_DARK, border=C_MED, lw=2)
    ax.text(5.0, 1.75, "MOVILNET TELCO", ha='center', va='center', fontsize=8.5, fontweight='bold', color='white')
    ax.text(5.0, 1.35, "Línea 0416 / 0426\n4M de Abonados\nIdentidad Móvil", ha='center', va='center', fontsize=6.8, color=C_CYAN, linespacing=1.2)

    partners = [
        ("Fintech & Banca", "Pago Móvil C2P\n23 Bancos SUDEBAN\nTasa Oficial BCV", 0.5, 1.0, C_GREEN),
        ("Turismo & Hoteles", "Venetur · Conviasa\nPaquetes y Vuelos\nAtención al Viajero", 3.8, 2.2, C_CYAN),
        ("Comercio B2B2C", "Marketplace Aliado\nRecargas y Cupones\nFidelización NBA", 3.8, 0.05, C_ORANGE),
        ("Gobierno & Servicios", "Sistema Patria\nTrámites Digitales\nEmergencias EIR", 7.1, 1.0, C_MED),
    ]

    for title, desc, x, y, col in partners:
        w = 2.4
        h = 0.95
        draw_card(ax, x, y, w, h, border=col, lw=1.6)
        ax.text(x+w/2, y+0.65, title, ha='center', va='center', fontsize=7.2, fontweight='bold', color=col)
        ax.text(x+w/2, y+0.3, desc, ha='center', va='center', fontsize=6.0, color=C_TEXT, linespacing=1.2)

        # Línea al centro
        ax.plot([x+w/2, 5.0], [y+h/2, 1.6], color=col, ls=":", lw=1.2)

    ax.set_title("ECOSISTEMA SUPER-APP TELCO B2B2C — INTEGRACIÓN DE SERVICIOS",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=10)
    p = os.path.join(OUTPUT_DIR, "diag_superapp_ecosystem.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

# 8. Diagrama de Seguridad EIR y Bloqueo IMEI
def gen_diag_eir():
    fig, ax = plt.subplots(figsize=(10, 2.6), dpi=300)
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.6)
    ax.axis('off')

    steps = [
        ("1. Denuncia Hurto", "Abonado reporta en\nWhatsApp / Chat\nLínea 0416/0426", C_RED),
        ("2. Validación IMEI", "Algoritmo Luhn Mod 10\n15 dígitos TAC+SNR\nLatencia 0.013ms", C_DARK),
        ("3. Auditoría SIM", "Ventana crítica 24h\nRisk Score fraude\nAlerta si < 72h", C_ORANGE),
        ("4. Bloqueo Inmutable", "Lista Negra GSMA\nTicket EIR Formal\nDesconexión de Red", C_RED),
        ("5. Retención N4", "Cupón Fidelización\nOferta Rescate post-hurto\nReemplazo SIM sin costo", C_GREEN),
    ]

    for i, (title, desc, col) in enumerate(steps):
        x = 0.25 + i * 1.95
        y = 0.35
        w = 1.65
        h = 1.9
        draw_card(ax, x, y, w, h, border=col, lw=1.8)

        h_patch = patches.FancyBboxPatch((x, y+1.35), w, 0.55, boxstyle="round,pad=0.01,rounding_size=0.06",
                                        facecolor=col, edgecolor="none")
        ax.add_patch(h_patch)
        ax.text(x+w/2, y+1.62, title, ha='center', va='center', fontsize=7.5, fontweight='bold', color='white')
        ax.text(x+w/2, y+0.7, desc, ha='center', va='center', fontsize=6.2, color=C_TEXT, linespacing=1.2)

        if i < len(steps) - 1:
            ax.annotate('', xy=(x+w+0.28, y+1.0), xytext=(x+w+0.02, y+1.0),
                        arrowprops=dict(arrowstyle="->", color=C_DARK, lw=2, mutation_scale=12))

    ax.set_title("PROTOCOLO DE GESTIÓN DE EMERGENCIAS Y BLOQUEO EIR/IMEI GSMA",
                 fontsize=10, fontweight='bold', color=C_DARK, pad=10)
    p = os.path.join(OUTPUT_DIR, "diag_eir_security.png")
    plt.tight_layout()
    plt.savefig(p, dpi=300)
    plt.close()
    return p

if __name__ == '__main__':
    print("Renderizando suite completa de gráficos 300 DPI...")
    print("1. Fases:", gen_diag_phases())
    print("2. 9 Capas:", gen_diag_9layers())
    print("3. User Flow:", gen_diag_user_flow())
    print("4. Swarm L5:", gen_diag_swarm())
    print("5. n8n 3 Niveles:", gen_diag_n8n())
    print("6. Financiero:", gen_diag_financial())
    print("7. Super-App:", gen_diag_superapp())
    print("8. EIR Seguridad:", gen_diag_eir())
    print("✅ Todos los gráficos renderizados exitosamente en docs/img/.")
