#!/usr/bin/env python3
"""
Generador de Gráficos y Diagramas Vectoriales para el PDF de Movilnet IA (Sin emojis en texto matplotlib)
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "img")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Colores Corporativos Movilnet
C_BLUE_DARK = "#002B49"
C_BLUE_MED = "#00558C"
C_BLUE_LIGHT = "#0088CE"
C_ACCENT = "#FF6A13"      # Naranja Movilnet
C_BG = "#F4F7FB"
C_CARD_BG = "#FFFFFF"
C_TEXT = "#1A1A2E"
C_GREEN = "#2E7D32"
C_RED = "#C62828"
C_GRAY = "#757575"
C_BORDER = "#D0D7DE"


def create_user_flow_diagram():
    """1. Diagrama de Flujo de Experiencia de Usuario"""
    fig, ax = plt.subplots(figsize=(10, 2.6), dpi=300)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.6)
    ax.axis('off')

    steps = [
        ("Paso 1: Ingesta", "Abonado escribe en\nWhatsApp / Web / TG", C_BLUE_MED),
        ("Paso 2: Perímetro", "Verificación KYC\ny Rate Limit Redis", C_BLUE_DARK),
        ("Paso 3: Router", "Semantic Router\n<15ms en CPU", C_ACCENT),
        ("Paso 4: Agentes", "Telco / Fintech\nTurismo / VAS", C_BLUE_LIGHT),
        ("Paso 5: Solución", "Saldo / Pago C2P\nRespuesta Humana", C_GREEN)
    ]

    for i, (title, desc, col) in enumerate(steps):
        x = 0.3 + i * 1.95
        y = 0.35
        w = 1.65
        h = 1.9
        
        rect_s = patches.FancyBboxPatch((x+0.03, y-0.03), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                                        facecolor="#E8E8E8", edgecolor="none")
        ax.add_patch(rect_s)
        
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                                      facecolor=C_CARD_BG, edgecolor=col, linewidth=1.8)
        ax.add_patch(rect)
        
        header = patches.FancyBboxPatch((x, y+1.3), w, 0.6, boxstyle="round,pad=0.06,rounding_size=0.1",
                                        facecolor=col, edgecolor=col, linewidth=1)
        ax.add_patch(header)
        
        ax.text(x + w/2, y + 1.6, title, color="white", fontsize=8.5, fontweight="bold", ha="center", va="center")
        ax.text(x + w/2, y + 0.65, desc, color=C_TEXT, fontsize=7.2, ha="center", va="center", linespacing=1.2)
        
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + 0.26, y + 0.95), xytext=(x + w + 0.04, y + 0.95),
                        arrowprops=dict(arrowstyle="->", color=C_BLUE_DARK, lw=2.2, mutation_scale=14))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diag_user_flow.png")
    plt.savefig(path, bbox_inches='tight', dpi=300)
    plt.close()
    return path


def create_architecture_diagram():
    """2. Diagrama de Arquitectura de 9 Capas"""
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=300)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis('off')

    layers = [
        ("CAPA 1: Canales e Ingesta", "WhatsApp Meta Cloud API | n8n Webhook | WebChat WebSockets | Telegram Gateway", "#E3F2FD", C_BLUE_DARK),
        ("CAPA 2: Perímetro y Seguridad", "SecurityShield Middleware | Redis Rate Limiting (5 req/min) | Enmascaramiento PII", "#E8EAF6", C_BLUE_DARK),
        ("CAPA 3: Enrutamiento Semántico", "SemanticRouter (<15ms CPU) | Smart MCP Gateway Isolation | LangGraph Supervisor", "#FFF3E0", C_ACCENT),
        ("CAPA 4: Enjambre Multi-Agente", "[Telco Core] [Fintech C2P] [Turismo/Cultura] [VAS Marketplace] [QA Checker]", "#E0F2F1", C_GREEN),
        ("CAPA 5: Model Gateway Multi-IA", "MVP ($0): Google AI Studio, DeepSeek, Groq -> Produccion: vLLM On-Premise (Qwen 72B)", "#EDE7F6", "#4A148C"),
        ("CAPA 6: Servidores MCP", "mcp_telco_tools (Consultas) | mcp_fintech_c2p (Banca) | mcp_discovery_tools (Auditoria)", "#F3E5F5", "#6A1B9A"),
        ("CAPA 7: Persistencia y Cache", "PostgreSQL 15 Particionado (0416/0426 - 4M Abonados) | Redis 7 (TTL 120s) | PgBouncer", "#E1F5FE", C_BLUE_MED),
        ("CAPA 8: Estandares Telecom", "TM Forum ODA (TMF620, TMF678, TMF680, TMF632) | GSMA Open Gateway (Carrier Billing)", "#ECEFF1", C_GRAY),
        ("CAPA 9: DevOps y Observabilidad", "Docker Multi-Stage | docker-compose | Prometheus + Grafana | Bitacora SHA-256 Continua", "#FAFAFA", "#212121")
    ]

    for i, (title, desc, bg_col, border_col) in enumerate(layers):
        y = 4.15 - (i * 0.47)
        h = 0.38
        w = 9.4
        x = 0.3
        
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.06",
                                      facecolor=bg_col, edgecolor=border_col, linewidth=1.1)
        ax.add_patch(rect)
        
        ax.text(x + 0.15, y + h/2, title, color=border_col, fontsize=7.5, fontweight="bold", va="center")
        ax.text(x + 2.7, y + h/2, desc, color=C_TEXT, fontsize=6.8, va="center")

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diag_architecture_9layers.png")
    plt.savefig(path, bbox_inches='tight', dpi=300)
    plt.close()
    return path


def create_financial_comparison_chart():
    """3. Gráfico de Comparativa Financiera y Costos"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.0), dpi=300)
    fig.patch.set_facecolor('white')

    # Gráfico 1: Licenciamiento Anual (Software)
    categories = ['Movistar\n(Salesforce/Botmaker)', 'Digitel\n(Oracle/Infobip)', 'Movilnet IA\n(Open-Source)']
    costs = [225000, 150000, 0]
    colors_list = [C_BLUE_DARK, C_BLUE_MED, C_GREEN]

    bars1 = ax1.bar(categories, costs, color=colors_list, width=0.55, edgecolor=C_BORDER)
    ax1.set_title('Costo Anual de Licenciamiento SaaS (USD)', fontsize=9, fontweight='bold', color=C_BLUE_DARK, pad=8)
    ax1.set_ylabel('USD / Año', fontsize=7.5, color=C_GRAY)
    ax1.set_ylim(0, 260000)
    ax1.grid(axis='y', linestyle='--', alpha=0.4)
    ax1.tick_params(axis='x', labelsize=7.5)
    ax1.tick_params(axis='y', labelsize=7.5)

    for bar in bars1:
        yval = bar.get_height()
        if yval == 0:
            ax1.text(bar.get_x() + bar.get_width()/2, 8000, "$0.00\n(100% Ahorro)", ha='center', va='bottom', fontsize=8, fontweight='bold', color=C_GREEN)
        else:
            ax1.text(bar.get_x() + bar.get_width()/2, yval + 4000, f"${yval:,.0f}", ha='center', va='bottom', fontsize=7.5, fontweight='bold', color=C_TEXT)

    # Gráfico 2: Distribución de Tráfico y Costo de Tokens
    labels = ['Fast-Path Deterministico\n(70% Consultas - $0)', 'Inferencia LLM Hibrida\n(30% Consultas - Con Caching)']
    sizes = [70, 30]
    colors_pie = [C_GREEN, C_BLUE_MED]
    explode = (0.05, 0)

    wedges, texts, autotexts = ax2.pie(sizes, explode=explode, labels=labels, autopct='%1.0f%%',
                                       shadow=False, startangle=140, colors=colors_pie,
                                       textprops=dict(color=C_TEXT, fontsize=7.5))
    for at in autotexts:
        at.set_color('white')
        at.set_fontweight('bold')
        at.set_fontsize(8.5)
    ax2.set_title('Optimizacion de Tokens (60k-320k req/dia)\nCosto Mensual Estimado: $127.80 USD', fontsize=8.5, fontweight='bold', color=C_BLUE_DARK)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart_financial_analysis.png")
    plt.savefig(path, bbox_inches='tight', dpi=300)
    plt.close()
    return path


def create_superapp_ecosystem_diagram():
    """4. Diagrama del Ecosistema Super-App B2B2C"""
    fig, ax = plt.subplots(figsize=(10, 3.0), dpi=300)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.0)
    ax.axis('off')

    # Centro: La Línea Móvil Movilnet
    center_s = patches.FancyBboxPatch((3.75, 0.85), 2.5, 1.3, boxstyle="round,pad=0.06,rounding_size=0.12",
                                      facecolor="#E0E0E0", edgecolor="none")
    ax.add_patch(center_s)
    center = patches.FancyBboxPatch((3.7, 0.9), 2.5, 1.3, boxstyle="round,pad=0.06,rounding_size=0.12",
                                    facecolor=C_BLUE_DARK, edgecolor=C_ACCENT, linewidth=1.8)
    ax.add_patch(center)
    ax.text(4.95, 1.65, "LINEA MOVILNET", color="white", fontsize=9.5, fontweight="bold", ha="center")
    ax.text(4.95, 1.3, "Pasaporte Digital Unico\n(4M Abonados 0416/0426)", color="#E3F2FD", fontsize=7.2, ha="center")

    # Los 4 Dominios Satelitales
    domains = [
        ("1. TELCO CORE", "• Saldo y Megas 4GMAX\n• Planes y Fechas de Corte\n• Facturas y Roaming", 0.4, 1.6, C_BLUE_MED),
        ("2. FINTECH & BANCA", "• Pago Movil C2P en Chat\n• BDV, Banesco, Patria\n• Recargas Directas", 0.4, 0.15, C_GREEN),
        ("3. TURISMO NACIONAL", "• Parques (Avila, Mochima)\n• Museos y Sitios Historicos\n• Guia Cultural y Eventos", 6.8, 1.6, C_ACCENT),
        ("4. MARKETPLACE B2B2C", "• Cupones y Beneficios\n• Comercios Aliados y Cines\n• Servicios Publicos", 6.8, 0.15, "#6A1B9A"),
    ]

    for title, bullets, x, y, col in domains:
        w, h = 2.8, 1.25
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.1",
                                      facecolor="#FFFFFF", edgecolor=col, linewidth=1.3)
        ax.add_patch(rect)
        header = patches.FancyBboxPatch((x, y+0.88), w, 0.37, boxstyle="round,pad=0.05,rounding_size=0.08",
                                        facecolor=col, edgecolor=col)
        ax.add_patch(header)
        ax.text(x + w/2, y + 1.06, title, color="white", fontsize=7.8, fontweight="bold", ha="center")
        ax.text(x + 0.15, y + 0.42, bullets, color=C_TEXT, fontsize=6.8, va="center", linespacing=1.2)

        if x < 3.7:
            ax.annotate("", xy=(3.65, 1.55 if y > 1 else 1.25), xytext=(x + w + 0.05, y + h/2),
                        arrowprops=dict(arrowstyle="<->", color=col, lw=1.3))
        else:
            ax.annotate("", xy=(6.25, 1.55 if y > 1 else 1.25), xytext=(x - 0.05, y + h/2),
                        arrowprops=dict(arrowstyle="<->", color=col, lw=1.3))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diag_superapp_ecosystem.png")
    plt.savefig(path, bbox_inches='tight', dpi=300)
    plt.close()
    return path


def create_roadmap_diagram():
    """5. Diagrama de la Hoja de Ruta (Fases 0 a 4)"""
    fig, ax = plt.subplots(figsize=(10, 2.0), dpi=300)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.0)
    ax.axis('off')

    phases = [
        ("FASE 0", "Discovery & Inception\n26 Capitulos | 41 Tests\n(Completada OK)", C_GREEN),
        ("FASE 1", "Capa de Datos\nPostgreSQL Particionado\nSeed 4M | MCP Telco", C_ACCENT),
        ("FASE 2", "API & Microservicios\nFastAPI | OpenAPI\nn8n WhatsApp Flows", C_BLUE_MED),
        ("FASE 3", "Agente Cognitivo\nMulti-Modelo | C2P\nPruebas con Usuarios", C_BLUE_DARK),
        ("FASE 4", "Produccion On-Premise\nvLLM Datacenter\nDespliegue Masivo", "#2E7D32"),
    ]

    for i, (title, desc, col) in enumerate(phases):
        x = 0.3 + i * 1.95
        y = 0.25
        w = 1.65
        h = 1.5
        
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.1",
                                      facecolor="#FFFFFF", edgecolor=col, linewidth=1.5)
        ax.add_patch(rect)
        
        header = patches.FancyBboxPatch((x, y+1.02), w, 0.48, boxstyle="round,pad=0.05,rounding_size=0.08",
                                        facecolor=col, edgecolor=col)
        ax.add_patch(header)
        
        ax.text(x + w/2, y + 1.26, title, color="white", fontsize=8, fontweight="bold", ha="center")
        ax.text(x + w/2, y + 0.5, desc, color=C_TEXT, fontsize=6.5, ha="center", va="center", linespacing=1.2)
        
        if i < len(phases) - 1:
            ax.annotate("", xy=(x + w + 0.26, y + 0.75), xytext=(x + w + 0.04, y + 0.75),
                        arrowprops=dict(arrowstyle="->", color=C_BLUE_DARK, lw=1.8, mutation_scale=11))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "diag_roadmap_phases.png")
    plt.savefig(path, bbox_inches='tight', dpi=300)
    plt.close()
    return path


if __name__ == "__main__":
    p1 = create_user_flow_diagram()
    p2 = create_architecture_diagram()
    p3 = create_financial_comparison_chart()
    p4 = create_superapp_ecosystem_diagram()
    p5 = create_roadmap_diagram()
    print("✅ Todos los diagramas generados limpiamente sin warnings.")
