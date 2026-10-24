#!/usr/bin/env python3
"""
mcp_spatial_radar: Servidor MCP de Inteligencia Geoespacial y Proximidad de 3 Zonas.
Calcula distancias geodésicas en sub-milisegundos, filtra por anillos (500m, 1km, 3km)
y evita que el LLM gaste tokens calculando geometría o coordenadas.
"""
import sys
import math
import json
import argparse
from typing import Dict, Any, List, Tuple

EARTH_RADIUS_METERS = 6371000.0

class SpatialRadarEngine:
    RINGS = {
        "zona_1_inmediata": 500.0,
        "zona_2_vecindario": 1000.0,
        "zona_3_urbana": 3000.0
    }

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula la distancia esférica en metros entre dos pares de coordenadas."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

        return EARTH_RADIUS_METERS * c

    def classify_ring(self, distance_m: float) -> str:
        if distance_m <= self.RINGS["zona_1_inmediata"]:
            return "zona_1_inmediata"
        elif distance_m <= self.RINGS["zona_2_vecindario"]:
            return "zona_2_vecindario"
        elif distance_m <= self.RINGS["zona_3_urbana"]:
            return "zona_3_urbana"
        return "fuera_de_rango"

    def filter_proximity(
        self,
        user_lat: float,
        user_lon: float,
        candidates: List[Dict[str, Any]],
        max_distance_m: float = 3000.0,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Evalúa candidatos, calcula distancias exactas y agrupa por anillo de proximidad."""
        results = []
        
        # Pre-filtrado por Bounding Box (~1 grado lat = 111 km)
        lat_delta = max_distance_m / 111000.0
        cos_lat = math.cos(math.radians(user_lat))
        lon_delta = max_distance_m / (111000.0 * max(cos_lat, 0.01))

        lat_min, lat_max = user_lat - lat_delta, user_lat + lat_delta
        lon_min, lon_max = user_lon - lon_delta, user_lon + lon_delta

        for item in candidates:
            c_lat = float(item.get("lat", 0.0))
            c_lon = float(item.get("lon", 0.0))
            
            # Bounding box filter (ultra-rápido)
            if not (lat_min <= c_lat <= lat_max and lon_min <= c_lon <= lon_max):
                continue
                
            dist_m = self.haversine_distance(user_lat, user_lon, c_lat, c_lon)
            if dist_m <= max_distance_m:
                ring = self.classify_ring(dist_m)
                enriched = dict(item)
                enriched["distance_meters"] = round(dist_m, 1)
                enriched["distance_km"] = round(dist_m / 1000.0, 2)
                enriched["ring"] = ring
                results.append(enriched)

        # Ordenar por distancia ascendente
        results.sort(key=lambda x: x["distance_meters"])
        selected = results[:limit]

        return {
            "origin": {"lat": user_lat, "lon": user_lon},
            "radius_applied_meters": max_distance_m,
            "total_matches": len(results),
            "returned_count": len(selected),
            "results": selected
        }

# Protocolo MCP Stdio
def run_mcp_stdio():
    radar = SpatialRadarEngine()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                tools = [
                    {
                        "name": "calculate_distance",
                        "description": "Calcula la distancia esférica exacta en metros entre dos coordenadas.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "lat1": {"type": "number"}, "lon1": {"type": "number"},
                                "lat2": {"type": "number"}, "lon2": {"type": "number"}
                            },
                            "required": ["lat1", "lon1", "lat2", "lon2"]
                        }
                    },
                    {
                        "name": "filter_nearby_entities",
                        "description": "Filtra comercios u ofertas dentro de los 3 anillos concéntricos (500m / 1km / 3km).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "user_lat": {"type": "number"},
                                "user_lon": {"type": "number"},
                                "candidates": {
                                    "type": "array",
                                    "items": {"type": "object"}
                                },
                                "max_distance_m": {"type": "number", "default": 3000.0},
                                "limit": {"type": "integer", "default": 10}
                            },
                            "required": ["user_lat", "user_lon", "candidates"]
                        }
                    }
                ]
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}) + "\n")
                sys.stdout.flush()
                
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                
                if name == "calculate_distance":
                    dist = radar.haversine_distance(args["lat1"], args["lon1"], args["lat2"], args["lon2"])
                    res = {"distance_meters": round(dist, 1), "ring": radar.classify_ring(dist)}
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}) + "\n")
                elif name == "filter_nearby_entities":
                    res = radar.filter_proximity(
                        user_lat=args["user_lat"],
                        user_lon=args["user_lon"],
                        candidates=args.get("candidates", []),
                        max_distance_m=args.get("max_distance_m", 3000.0),
                        limit=args.get("limit", 10)
                    )
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mcp-spatial-radar server")
    parser.add_argument("--test", action="store_true", help="Ejecutar autoverificación formal con aserciones")
    args = parser.parse_args()
    
    if args.test:
        radar = SpatialRadarEngine()
        # Coordenadas de prueba: Caracas (Plaza Venezuela: 10.4965, -66.8858)
        lat_pv, lon_pv = 10.4965, -66.8858
        
        # Punto A: A 300m (Zona 1)
        lat_a, lon_a = 10.4980, -66.8845
        d_a = radar.haversine_distance(lat_pv, lon_pv, lat_a, lon_a)
        assert d_a < 500, f"Punto A debió ser Zona 1 (<500m), dio {d_a}m"
        assert radar.classify_ring(d_a) == "zona_1_inmediata"

        # Punto B: A 4000m (Fuera de rango)
        lat_b, lon_b = 10.4600, -66.8858
        d_b = radar.haversine_distance(lat_pv, lon_pv, lat_b, lon_b)
        assert d_b > 3000, f"Punto B debió ser >3000m, dio {d_b}m"
        assert radar.classify_ring(d_b) == "fuera_de_rango"
        
        # Test de filtrado por lote
        candidates = [
            {"id": "tienda_1", "name": "Panadería El Sol", "lat": lat_a, "lon": lon_a},
            {"id": "tienda_2", "name": "Supermercado Lejano", "lat": lat_b, "lon": lon_b}
        ]
        res = radar.filter_proximity(lat_pv, lon_pv, candidates, max_distance_m=1000.0)
        assert res["returned_count"] == 1
        assert res["results"][0]["id"] == "tienda_1"
        
        print("✅ SpatialRadarEngine: 3/3 Tests PASSED [Exit code: 0]")
        sys.exit(0)
    else:
        run_mcp_stdio()
