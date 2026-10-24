#!/usr/bin/env python3
"""
mcp/geo_tools.py — Suite MCP Geoespacial de Venezuela
======================================================
Proyecto: AI_Movilnet_300926 / Antigravity Model Context Protocol
Estándar: Model Context Protocol (MCP) JSON-RPC 2.0 (2024-11-05)

Herramientas MCP Expuestas:
  1. mcp_geo_spatial_search: Búsqueda espacial por coordenadas GPS (lat, lon) y radio (metros).
  2. mcp_geo_structured_query: Búsqueda estructurada por Estado, Municipio, Parroquia y Categoría.
  3. mcp_geo_ingest_feature: Ingestión y normalización de features cartográficos (OSM GeoJSON / Shapefile).
  4. mcp_geo_validate_boundaries: Validación de límites político-territoriales oficiales de Venezuela.
"""

from __future__ import annotations

import json
import sqlite3
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.geo_catalog import (
    DB_PATH,
    VENEZUELA_TERRITORIAL_DIVISIONS,
    haversine_distance_meters,
    find_nearest_movilnet_agency,
    find_agencies_by_city_or_state,
    is_point_in_venezuela,
    init_geo_database
)

# Garantizar tablas creadas
init_geo_database(DB_PATH)


# ============================================================================
# 1. Herramienta MCP: Búsqueda Espacial (Geospatial Query)
# ============================================================================

def mcp_geo_spatial_search(
    latitude: float,
    longitude: float,
    radius_meters: int = 2500,
    category: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    [MCP Tool] Busca puntos de interés (farmacias, clínicas, comercios, torres corporativas)
    filtrando por radio esférico Haversine desde las coordenadas GPS (lat, lon).
    """
    start_time = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = """
        SELECT id, osm_id, name, category, sub_category, state, municipality, parish,
               latitude, longitude, address, phone, opening_hours, emergency_service, metadata_json
        FROM geo_pois
    """
    params: List[Any] = []
    if category:
        query += " WHERE category = ?"
        params.append(category)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    results: List[Dict[str, Any]] = []

    for r in rows:
        poi_id, osm_id, name, cat, sub_cat, state, muni, parish, p_lat, p_lon, addr, phone, hours, emerg, meta = r
        dist_m = haversine_distance_meters(latitude, longitude, p_lat, p_lon)

        if dist_m <= radius_meters:
            walking_min = max(1, int(round(dist_m / 80.0)))
            driving_min = max(1, int(round(dist_m / 500.0)))

            try:
                parsed_meta = json.loads(meta) if meta else {}
            except Exception:
                parsed_meta = {}

            results.append({
                "id": poi_id,
                "osm_id": osm_id,
                "name": name,
                "category": cat,
                "sub_category": sub_cat,
                "state": state,
                "municipality": muni,
                "parish": parish,
                "coordinates": {"latitude": p_lat, "longitude": p_lon},
                "distance_meters": round(dist_m, 1),
                "distance_km": round(dist_m / 1000.0, 2),
                "walking_minutes_est": walking_min,
                "driving_minutes_est": driving_min,
                "address": addr,
                "phone": phone,
                "opening_hours": hours,
                "emergency_service_24h": bool(emerg),
                "metadata": parsed_meta
            })

    # Ordenar por proximidad geodésica
    results.sort(key=lambda x: x["distance_meters"])
    matched_results = results[:limit]

    return {
        "success": True,
        "query_center": {"latitude": latitude, "longitude": longitude},
        "search_radius_meters": radius_meters,
        "category_filter": category or "TODAS",
        "total_matches": len(matched_results),
        "results": matched_results,
        "execution_ms": round((time.time() - start_time) * 1000, 2)
    }


# ============================================================================
# 2. Herramienta MCP: Consulta Estructurada por Territorio y Categoría
# ============================================================================

def mcp_geo_structured_query(
    state: Optional[str] = None,
    municipality: Optional[str] = None,
    parish: Optional[str] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    [MCP Tool] Realiza búsquedas estructuradas en el directorio cartográfico
    por jerarquía administrativa (Estado, Municipio, Parroquia) y/o tipo comercial.
    """
    start_time = time.time()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    conditions: List[str] = []
    params: List[Any] = []

    if state:
        conditions.append("LOWER(state) LIKE ?")
        params.append(f"%{state.strip().lower()}%")
    if municipality:
        conditions.append("LOWER(municipality) LIKE ?")
        params.append(f"%{municipality.strip().lower()}%")
    if parish:
        conditions.append("LOWER(parish) LIKE ?")
        params.append(f"%{parish.strip().lower()}%")
    if category:
        conditions.append("LOWER(category) = ?")
        params.append(category.strip().lower())
    if keyword:
        conditions.append("(LOWER(name) LIKE ? OR LOWER(address) LIKE ?)")
        kw = f"%{keyword.strip().lower()}%"
        params.extend([kw, kw])

    sql = """
        SELECT id, osm_id, name, category, sub_category, state, municipality, parish,
               latitude, longitude, address, phone, opening_hours, emergency_service, metadata_json
        FROM geo_pois
    """
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += f" ORDER BY name ASC LIMIT {max(1, limit)}"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    results: List[Dict[str, Any]] = []
    for r in rows:
        poi_id, osm_id, name, cat, sub_cat, st, muni, prsh, p_lat, p_lon, addr, phone, hours, emerg, meta = r
        try:
            parsed_meta = json.loads(meta) if meta else {}
        except Exception:
            parsed_meta = {}

        results.append({
            "id": poi_id,
            "name": name,
            "category": cat,
            "sub_category": sub_cat,
            "state": st,
            "municipality": muni,
            "parish": prsh,
            "coordinates": {"latitude": p_lat, "longitude": p_lon},
            "address": addr,
            "phone": phone,
            "opening_hours": hours,
            "emergency_service_24h": bool(emerg),
            "metadata": parsed_meta
        })

    return {
        "success": True,
        "filters_applied": {
            "state": state,
            "municipality": municipality,
            "parish": parish,
            "category": category,
            "keyword": keyword
        },
        "total_records_found": len(results),
        "records": results,
        "execution_ms": round((time.time() - start_time) * 1000, 2)
    }


# ============================================================================
# 3. Herramienta MCP: Ingestión y Normalización de Features (OSM / GeoPackage)
# ============================================================================

def mcp_geo_ingest_feature(
    feature: Dict[str, Any],
    source_format: str = "geojson_osm"
) -> Dict[str, Any]:
    """
    [MCP Tool] Ingesta, normaliza y persiste un elemento cartográfico desde OpenStreetMap (OSM) o GeoPackage.
    Valida coordenadas, extrae tags (amenity, shop, office) y normaliza la entidad.
    """
    start_time = time.time()

    # Soporte para formato GeoJSON Feature o diccionario plano
    props = feature.get("properties", feature)
    geometry = feature.get("geometry", {})

    # Extracción de coordenadas
    lat = props.get("latitude") or props.get("lat")
    lon = props.get("longitude") or props.get("lon")

    if geometry and geometry.get("type") == "Point":
        coords = geometry.get("coordinates", [])
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]

    if lat is None or lon is None:
        return {
            "success": False,
            "error": "ERR_MISSING_COORDINATES",
            "message": "El feature carece de coordenadas de latitud/longitud válidas."
        }

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return {"success": False, "error": "ERR_INVALID_COORDINATES", "message": "Coordenadas no numéricas."}

    # Normalización de categorías a partir de tags OSM estándar
    name = props.get("name") or props.get("nombre") or "Punto de Interés Sin Nombre"
    osm_amenity = props.get("amenity", "").lower()
    osm_shop = props.get("shop", "").lower()
    osm_office = props.get("office", "").lower()

    category = "comercio"
    sub_category = "general"
    emergency_service = 0

    if osm_amenity in ["pharmacy", "farmacia"]:
        category = "farmacia"
        sub_category = "farmacia_cadena" if "farmatodo" in name.lower() or "locatel" in name.lower() else "farmacia_independiente"
    elif osm_amenity in ["hospital", "clinic", "doctors", "salud"]:
        category = "salud_clinica"
        sub_category = "hospital_privado" if "clínica" in name.lower() else "centro_salud"
        emergency_service = 1 if props.get("emergency") == "yes" or "urgencia" in name.lower() else 0
    elif osm_office or "torre" in name.lower() or "edificio" in name.lower() or "centro empresarial" in name.lower():
        category = "edificio_corporativo"
        sub_category = "torre_oficinas"
    elif osm_amenity == "fast_food" or "perro" in name.lower() or "churro" in name.lower():
        category = "perros_calientes" if "perro" in name.lower() else "comida_rapida"
        sub_category = "comida_callejera"

    state = props.get("state") or props.get("estado") or "Miranda"
    municipality = props.get("municipality") or props.get("municipio") or "Chacao"
    parish = props.get("parish") or props.get("parroquia") or municipality

    poi_id = f"POI-INGEST-{int(time.time()*1000)}"
    osm_id = props.get("osm_id") or props.get("id") or int(time.time())
    address = props.get("address") or props.get("addr:street") or f"Ubicado en {municipality}, {state}"
    phone = props.get("phone") or props.get("contact:phone")
    opening_hours = props.get("opening_hours") or "08:00 - 18:00"

    # Persistencia
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO geo_pois (
            id, osm_id, name, category, sub_category,
            state, municipality, parish, latitude, longitude,
            address, phone, opening_hours, emergency_service,
            metadata_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        poi_id, osm_id, name, category, sub_category,
        state, municipality, parish, lat, lon,
        address, phone, opening_hours, emergency_service,
        json.dumps(props, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "ingested_id": poi_id,
        "source_format": source_format,
        "name": name,
        "category": category,
        "sub_category": sub_category,
        "coordinates": {"latitude": lat, "longitude": lon},
        "territorial_location": {"state": state, "municipality": municipality, "parish": parish},
        "execution_ms": round((time.time() - start_time) * 1000, 2)
    }


# ============================================================================
# 4. Herramienta MCP: Validación de Límites Político-Territoriales
# ============================================================================

def mcp_geo_validate_boundaries(
    latitude: float,
    longitude: float,
    declared_state: str,
    declared_municipality: str,
    declared_parish: Optional[str] = None
) -> Dict[str, Any]:
    """
    [MCP Tool] Valida que un punto GPS pertenezca efectivamente a los límites político-territoriales
    oficiales del Estado, Municipio y Parroquia declarados para evitar registros huérfanos o fuera de Venezuela.
    """
    # 1. Bounding Box Global de la República Bolivariana de Venezuela
    # Latitud: ~0.6°N a 12.5°N | Longitud: ~-73.4°W a -59.8°W
    if not (0.6 <= latitude <= 12.5 and -73.5 <= longitude <= -59.8):
        return {
            "success": True,
            "is_valid": False,
            "error_code": "ERR_OUTSIDE_VENEZUELA",
            "reason": f"Las coordenadas ({latitude}, {longitude}) se encuentran fuera del territorio de la República Bolivariana de Venezuela."
        }

    # 2. Validación de jerarquía estatal y municipal
    target_state = None
    for st in VENEZUELA_TERRITORIAL_DIVISIONS:
        if st.lower() == declared_state.strip().lower():
            target_state = st
            break

    if not target_state:
        return {
            "success": True,
            "is_valid": False,
            "error_code": "ERR_UNKNOWN_STATE",
            "reason": f"El Estado '{declared_state}' no figura en el catálogo territorial oficial de Venezuela."
        }

    munis = VENEZUELA_TERRITORIAL_DIVISIONS[target_state]
    target_muni = None
    for m in munis:
        if m.lower() == declared_municipality.strip().lower():
            target_muni = m
            break

    if not target_muni:
        return {
            "success": True,
            "is_valid": False,
            "error_code": "ERR_UNKNOWN_MUNICIPALITY",
            "reason": f"El Municipio '{declared_municipality}' no pertenece al Estado '{target_state}'."
        }

    muni_data = munis[target_muni]

    # Validar bounding box municipal
    lat_ok = muni_data["lat_min"] <= latitude <= muni_data["lat_max"]
    lon_ok = muni_data["lon_min"] <= longitude <= muni_data["lon_max"]

    if not (lat_ok and lon_ok):
        return {
            "success": True,
            "is_valid": False,
            "error_code": "ERR_COORDINATES_MISMATCH",
            "reason": (
                f"Las coordenadas ({latitude}, {longitude}) no corresponden a la demarcación del Municipio {target_muni} "
                f"[{muni_data['lat_min']}..{muni_data['lat_max']}, {muni_data['lon_min']}..{muni_data['lon_max']}]."
            )
        }

    # Validar parroquia si se declaró
    parish_valid = True
    if declared_parish:
        official_parishes = [p.lower() for p in muni_data.get("parroquias", [])]
        if declared_parish.strip().lower() not in official_parishes:
            parish_valid = False

    return {
        "success": True,
        "is_valid": parish_valid,
        "state": target_state,
        "municipality": target_muni,
        "parish": declared_parish if parish_valid else f"PARROQUIA_NO_OFICIAL ({declared_parish})",
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "status": "TERRITORIO_VALIDADO_CONFORME" if parish_valid else "OBSERVACION_PARROQUIA"
    }


# ============================================================================
# 5. Herramienta MCP: Búsqueda de la Agencia Movilnet Más Cercana (GPS)
# ============================================================================

def mcp_geo_find_nearest_agency(
    latitude: float,
    longitude: float,
    max_radius_km: float = 150.0
) -> Dict[str, Any]:
    """
    [MCP Tool] Encuentra la Oficina Comercial o Agencia Movilnet más cercana
    a las coordenadas GPS WGS84 proporcionadas (latitud, longitud).
    Calcula distancia Haversine, tiempos de traslado y enlace de Google Maps.
    """
    start_time = time.time()
    nearest = find_nearest_movilnet_agency(lat=latitude, lon=longitude, max_radius_km=max_radius_km)
    exec_ms = round((time.time() - start_time) * 1000, 2)

    if nearest and "error" in nearest:
        return {
            "success": False,
            "error_code": nearest["error"],
            "message": nearest["message"],
            "execution_ms": exec_ms
        }

    if not nearest:
        return {
            "success": True,
            "found": False,
            "message": f"No se encontraron oficinas comerciales Movilnet en un radio de {max_radius_km} km.",
            "agency": None,
            "execution_ms": exec_ms
        }

    return {
        "success": True,
        "found": True,
        "query_coordinates": {"latitude": latitude, "longitude": longitude},
        "agency": nearest,
        "execution_ms": exec_ms
    }


# ============================================================================
# 6. Herramienta MCP: Búsqueda de Agencias Movilnet por Ciudad o Zona (Texto)
# ============================================================================

def mcp_geo_find_agencies_by_city(
    query: str,
    limit: int = 5
) -> Dict[str, Any]:
    """
    [MCP Tool] Busca oficinas comerciales y agencias Movilnet por nombre de ciudad,
    estado, municipio o palabra clave geográfica (ej: 'Maracaibo', 'Valencia', 'Caracas').
    """
    start_time = time.time()
    results = find_agencies_by_city_or_state(query=query, limit=limit)
    return {
        "success": True,
        "query": query,
        "total_found": len(results),
        "agencies": results,
        "execution_ms": round((time.time() - start_time) * 1000, 2)
    }


# ============================================================================
# Servidor MCP Despachador (GeoVenezuelaMcpServer)
# ============================================================================

class GeoVenezuelaMcpServer:
    """Servidor MCP JSON-RPC 2.0 para la Suite Geoespacial y Cartográfica de Venezuela."""

    TOOLS = {
        "mcp_geo_spatial_search": mcp_geo_spatial_search,
        "mcp_geo_structured_query": mcp_geo_structured_query,
        "mcp_geo_ingest_feature": mcp_geo_ingest_feature,
        "mcp_geo_validate_boundaries": mcp_geo_validate_boundaries,
        "mcp_geo_find_nearest_agency": mcp_geo_find_nearest_agency,
        "mcp_geo_find_agencies_by_city": mcp_geo_find_agencies_by_city,
    }

    @classmethod
    def get_manifest(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "mcp_geo_spatial_search",
                "description": "Búsqueda espacial geodésica de farmacias, clínicas, comercios y torres corporativas por coordenadas GPS (lat, lon) y radio en metros.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitud WGS84"},
                        "longitude": {"type": "number", "description": "Longitud WGS84"},
                        "radius_meters": {"type": "integer", "description": "Radio en metros de búsqueda (ej. 2000)", "default": 2500},
                        "category": {"type": "string", "description": "Filtro: 'oficina_comercial_movilnet', 'farmacia', 'salud_clinica', 'comercio', 'edificio_corporativo', 'perros_calientes'"},
                        "limit": {"type": "integer", "description": "Número máximo de resultados", "default": 10}
                    },
                    "required": ["latitude", "longitude"]
                }
            },
            {
                "name": "mcp_geo_structured_query",
                "description": "Consulta estructurada del directorio cartográfico por Estado, Municipio, Parroquia, categoría o palabra clave.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "description": "Nombre del Estado (ej. Miranda)"},
                        "municipality": {"type": "string", "description": "Nombre del Municipio (ej. Chacao)"},
                        "parish": {"type": "string", "description": "Nombre de la Parroquia (ej. Chacao)"},
                        "category": {"type": "string", "description": "Categoría comercial o asistencial"},
                        "keyword": {"type": "string", "description": "Término de búsqueda libre"},
                        "limit": {"type": "integer", "description": "Límite de registros", "default": 20}
                    }
                }
            },
            {
                "name": "mcp_geo_ingest_feature",
                "description": "Ingesta y normaliza un punto de interés o feature cartográfico desde OpenStreetMap (OSM) o GeoPackage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "feature": {"type": "object", "description": "Objeto Feature GeoJSON o diccionario con metadatos"},
                        "source_format": {"type": "string", "default": "geojson_osm"}
                    },
                    "required": ["feature"]
                }
            },
            {
                "name": "mcp_geo_validate_boundaries",
                "description": "Valida que las coordenadas GPS pertenezcan formalmente a la jerarquía político-territorial de Venezuela.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitud GPS"},
                        "longitude": {"type": "number", "description": "Longitud GPS"},
                        "declared_state": {"type": "string", "description": "Estado declarado"},
                        "declared_municipality": {"type": "string", "description": "Municipio declarado"},
                        "declared_parish": {"type": "string", "description": "Parroquia declarada"}
                    },
                    "required": ["latitude", "longitude", "declared_state", "declared_municipality"]
                }
            },
            {
                "name": "mcp_geo_find_nearest_agency",
                "description": "Encuentra la Agencia u Oficina Comercial de Movilnet más cercana a partir de coordenadas GPS (latitud, longitud).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitud WGS84 del usuario"},
                        "longitude": {"type": "number", "description": "Longitud WGS84 del usuario"},
                        "max_radius_km": {"type": "number", "description": "Radio máximo de búsqueda en kilómetros", "default": 150.0}
                    },
                    "required": ["latitude", "longitude"]
                }
            },
            {
                "name": "mcp_geo_find_agencies_by_city",
                "description": "Busca oficinas comerciales de Movilnet por nombre de ciudad, estado o zona (ej: 'Maracaibo', 'Valencia', 'Caracas').",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Nombre de ciudad, estado o zona"},
                        "limit": {"type": "integer", "description": "Máximo de resultados", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        ]

    def handle_request(self, method: str, params: Optional[Dict[str, Any]] = None, request_id: Any = 1) -> Dict[str, Any]:
        params = params or {}
        if method not in self.TOOLS:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method '{method}' not found in GeoVenezuelaMcpServer."},
                "id": request_id
            }

        start = time.time()
        try:
            handler = self.TOOLS[method]
            result = handler(**params)
            duration_ms = round((time.time() - start) * 1000, 2)
            return {
                "jsonrpc": "2.0",
                "result": result,
                "execution_ms": duration_ms,
                "id": request_id
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": f"Internal execution error in {method}: {str(e)}"},
                "id": request_id
            }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Suite MCP Geoespacial de Venezuela")
    parser.add_argument("--test", action="store_true", help="Auto-verificación Suite MCP Geo")
    args = parser.parse_args()
    if args.test:
        server = GeoVenezuelaMcpServer()
        # Test 1: Búsqueda genérica espacial
        resp = server.handle_request("mcp_geo_spatial_search", {"latitude": 10.4958, "longitude": -66.8530, "radius_meters": 2000})
        assert resp["result"]["success"] is True, "Fallo en MCP Geo search"

        # Test 2: Búsqueda de agencia Movilnet más cercana por GPS (Altamira)
        resp_agency = server.handle_request("mcp_geo_find_nearest_agency", {"latitude": 10.4960, "longitude": -66.8530})
        assert resp_agency["result"]["success"] is True, "Fallo en MCP find nearest agency"
        assert resp_agency["result"]["found"] is True
        assert "Centro Plaza" in resp_agency["result"]["agency"]["name"]

        # Test 3: Búsqueda de agencias por texto de ciudad (Maracaibo)
        resp_city = server.handle_request("mcp_geo_find_agencies_by_city", {"query": "Maracaibo"})
        assert resp_city["result"]["success"] is True, "Fallo en MCP find agencies by city"
        assert resp_city["result"]["total_found"] >= 2

        # Test 4: Rechazo fuera de Venezuela
        resp_out = server.handle_request("mcp_geo_find_nearest_agency", {"latitude": 40.7128, "longitude": -74.0060}) # NY
        assert resp_out["result"]["success"] is False
        assert resp_out["result"]["error_code"] == "ERR_OUTSIDE_VENEZUELA"

        print(f"✅ [MCP_GEO_TOOLS]: Auto-verificación superada (4 pruebas superadas con éxito).")

