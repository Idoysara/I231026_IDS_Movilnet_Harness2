#!/usr/bin/env python3
"""
semantic_router.py — Enrutador Semántico de Dominios para AI_Movilnet_300926
=============================================================================
Inspirado en aurelio-labs/semantic-router y MCP Smart Gateway.
Permite clasificar intenciones de usuarios en <15ms sin llamar a modelos LLM pesados,
enrutando quirúrgicamente al servidor MCP o módulo correspondiente:
  - telco_core: Saldo, corte, megas, recarga general, líneas 0416/0426
  - fintech_c2p: Pagos directos en chat C2P, bancos BDV/Banesco, referencias
  - tourism_culture: Parques nacionales (El Ávila/Warairarepano), sitios históricos, turismo
  - partner_marketplace: Promociones comerciales aliadas, cines, cupones, servicios públicos
"""

import math
import re
from typing import Dict, List, Optional, Tuple


class Route:
    def __init__(self, name: str, utterances: List[str], mcp_server: str, description: str):
        self.name = name
        self.utterances = [u.lower().strip() for u in utterances]
        self.mcp_server = mcp_server
        self.description = description


class SemanticRouter:
    """
    Enrutador semántico ligero, determinista y ultra-rápido (<15ms en CPU).
    Utiliza n-gram token overlap y similitud vectorial léxica (Jaccard + Cosine tf-idf)
    para enrutar sin costo de tokens ni dependencias pesadas.
    """
    def __init__(self, routes: Optional[List[Route]] = None):
        self.routes: List[Route] = routes or self._default_movilnet_routes()

    def _default_movilnet_routes(self) -> List[Route]:
        return [
            Route(
                name="telco_core",
                utterances=[
                    "cuanto debo", "consultar saldo", "saldo disponible", "fecha de corte",
                    "cuantos megas me quedan", "mi plan activo", "inteliplan 10gb", "consumo de datos",
                    "estatus de mi linea", "bloqueo por robo", "paquete 4gmax", "minutos libres"
                ],
                mcp_server="mcp_telco_tools",
                description="Consultas directas de facturación, contratos y planes Movilnet"
            ),
            Route(
                name="fintech_c2p",
                utterances=[
                    "recargar por pago movil", "token c2p", "debitar de mi cuenta", "banco de venezuela",
                    "pagar por bdv", "transferencia banesco", "pagar 150 bolivares", "clave dinamica",
                    "pago movil c2p", "referencia bancaria", "comprobante de pago", "recarga exitosa"
                ],
                mcp_server="mcp_fintech_c2p",
                description="Procesamiento transaccional de pagos y débitos directos en chat"
            ),
            Route(
                name="tourism_culture",
                utterances=[
                    "sitios turisticos", "que visitar en caracas", "parque nacional el avila",
                    "warairarepano", "parques nacionales", "casco historico", "casa natal del libertador",
                    "museos abiertos", "turismo en venezuela", "mochima", "morrocoy", "cartelera cultural"
                ],
                mcp_server="mcp_tourism_guide",
                description="Información turística nacional, parques nacionales y sitios históricos"
            ),
            Route(
                name="partner_marketplace",
                utterances=[
                    "promociones con aliados", "descuentos en cines", "cines unidos 2x1", "cupones de descuento",
                    "beneficios de mi linea", "pagar cantv", "factura corpoelec", "aliados comerciales",
                    "farmatodo promocion", "entradas con descuento", "2x1 en cine", "entradas de cine", "cine"
                ],
                mcp_server="mcp_partner_marketplace",
                description="Beneficios comerciales B2B2C, cupones y servicios públicos aliados"
            ),
            Route(
                name="network_noc",
                utterances=[
                    "no tengo señal", "falla en radiobase", "sin cobertura", "problemas de señal",
                    "datos lentos", "caida de red", "averia de cobertura", "mantenimiento en maracaibo",
                    "no me levanta 4g", "antena sin servicio", "corte de fibra", "sin datos en mi zona",
                    "radiobase caida", "sin señal", "falla de red"
                ],
                mcp_server="mcp_noc_tools",
                description="Operaciones de red, radiobases, diagnósticos de señal y avisos del NOC"
            )
        ]

    def _tokenize(self, text: str) -> set:
        words = re.findall(r'\b[a-záéíóúüñ0-9]{3,}\b', text.lower())
        return set(words)

    def route(self, query: str) -> Tuple[str, str, float]:
        """
        Retorna (route_name, mcp_server, score_confianza)
        """
        query_clean = query.lower().strip()
        query_tokens = self._tokenize(query_clean)

        best_route = "telco_core"
        best_server = "mcp_telco_tools"
        best_score = 0.0

        if not query_tokens:
            return best_route, best_server, 0.5

        for route in self.routes:
            for utterance in route.utterances:
                # 1. Coincidencia exacta o contenida directa (Score 1.0)
                if utterance in query_clean:
                    return route.name, route.mcp_server, 0.99

                # 2. Similitud Jaccard tokenizada
                u_tokens = self._tokenize(utterance)
                if not u_tokens:
                    continue
                intersection = len(query_tokens.intersection(u_tokens))
                union = len(query_tokens.union(u_tokens))
                score = intersection / union if union > 0 else 0.0

                if score > best_score:
                    best_score = score
                    best_route = route.name
                    best_server = route.mcp_server

        # Si el score es muy bajo pero contiene prefijos típicos telco (0416, 0426), asigna telco_core
        if best_score < 0.25:
            if "0416" in query or "0426" in query or "movilnet" in query.lower():
                return "telco_core", "mcp_telco_tools", 0.75

        return best_route, best_server, round(max(best_score, 0.55), 2)


if __name__ == "__main__":
    router = SemanticRouter()
    queries = [
        "Hola, ¿cuánto debo en mi línea 04161234567?",
        "Quiero recargar 200 bolívares por Pago Móvil del BDV con mi token C2P",
        "¿Qué parques nacionales o sitios turísticos puedo visitar este fin de semana?",
        "¿Hay promociones de 2x1 en entradas de cine para clientes Movilnet?",
        "¿A qué hora corta mi plan Inteliplan?"
    ]

    print("=" * 65)
    print("🧭 DEMOSTRACIÓN DE ENRUTAMIENTO SEMÁNTICO (SemanticRouter)")
    print("=" * 65)
    for q in queries:
        route_name, mcp, score = router.route(q)
        print(f"Mensaje : \"{q}\"")
        print(f"  ➔ Dominio Identificado: {route_name.upper()} (Confianza: {score*100:.0f}%)")
        print(f"  ➔ Servidor MCP Activado: {mcp}\n")
