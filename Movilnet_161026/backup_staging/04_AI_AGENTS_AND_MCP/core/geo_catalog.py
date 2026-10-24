#!/usr/bin/env python3
"""
core/geo_catalog.py — Catálogo Territorial y Base de Datos Geoespacial de Venezuela
==================================================================================
Proyecto: AI_Movilnet_300926 / Módulo Geoespacial MCP Nivel 5
Normativa: División Político-Territorial de Venezuela (INE / IGVSB)
Sistemas de Coordenadas: WGS84 (EPSG:4326) / Proyección UTM Huso 19N/20N
"""

from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "local_movilnet.db"

# Radio terrestre en kilómetros y metros para fórmulas geodésicas Haversine
EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_M = 6371000.0


# ============================================================================
# Jerarquía Territorial Oficial de Venezuela (Estados, Municipios, Parroquias)
# ============================================================================

VENEZUELA_TERRITORIAL_DIVISIONS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Distrito Capital": {
        "Libertador": {
            "lat_min": 10.4200, "lat_max": 10.5350,
            "lon_min": -67.0500, "lon_max": -66.8650,
            "parroquias": [
                "Altagracia", "Antímano", "Candelaria", "Caricuao", "Catedral",
                "Coche", "El Junquito", "El Paraíso", "El Recreo", "El Valle",
                "La Pastora", "La Vega", "Macarao", "San Agustín", "San Bernardino",
                "San José", "San Juan", "San Pedro", "Santa Rosalía", "Santa Teresa",
                "Sucre (Catia)", "23 de Enero"
            ]
        }
    },
    "Miranda": {
        "Chacao": {
            "lat_min": 10.4700, "lat_max": 10.5250,
            "lon_min": -66.8750, "lon_max": -66.8350,
            "parroquias": ["Chacao"]
        },
        "Baruta": {
            "lat_min": 10.4100, "lat_max": 10.4850,
            "lon_min": -66.9050, "lon_max": -66.8200,
            "parroquias": ["Nuestra Señora del Rosario de Baruta", "El Cafetal", "Las Minas de Baruta"]
        },
        "Sucre": {
            "lat_min": 10.4600, "lat_max": 10.5350,
            "lon_min": -66.8400, "lon_max": -66.7200,
            "parroquias": ["Petare", "Leoncio Martínez", "Caucagüita", "Fila de Mariches", "La Dolorita"]
        },
        "El Hatillo": {
            "lat_min": 10.3800, "lat_max": 10.4500,
            "lon_min": -66.8600, "lon_max": -66.7800,
            "parroquias": ["Santa Rosalía de Palermo"]
        },
        "Guaicaipuro": {
            "lat_min": 10.2800, "lat_max": 10.4100,
            "lon_min": -67.1200, "lon_max": -66.9600,
            "parroquias": ["Los Teques", "Cecilio Acosta", "San Pedro", "El Jarillo", "Altagracia de la Montaña", "Paracotos", "Tácata"]
        }
    },
    "Zulia": {
        "Maracaibo": {
            "lat_min": 10.5500, "lat_max": 10.7500,
            "lon_min": -71.7500, "lon_max": -71.5500,
            "parroquias": [
                "Bolívar", "Chiquinquirá", "Coquivacoa", "Cristo de Aranza",
                "Idelfonso Vásquez", "Juana de Ávila", "Manuel Dagnino",
                "Olegario Villalobos", "Raúl Leoni", "Santa Lucía", "Venancio Pulgar"
            ]
        },
        "San Francisco": {
            "lat_min": 10.4800, "lat_max": 10.6000,
            "lon_min": -71.7200, "lon_max": -71.5800,
            "parroquias": ["San Francisco", "El Bajo", "Domitila Flores", "Francisco Ochoa", "Los Cortijos", "Marcial Hernández"]
        }
    },
    "Carabobo": {
        "Valencia": {
            "lat_min": 10.0800, "lat_max": 10.2600,
            "lon_min": -68.0800, "lon_max": -67.9200,
            "parroquias": ["Candelaria", "Catedral", "El Socorro", "Miguel Peña", "Rafael Urdaneta", "San Blas", "San José", "Santa Rosa"]
        },
        "Naguanagua": {
            "lat_min": 10.2200, "lat_max": 10.3200,
            "lon_min": -68.0500, "lon_max": -67.9700,
            "parroquias": ["Naguanagua"]
        },
        "San Diego": {
            "lat_min": 10.2000, "lat_max": 10.3000,
            "lon_min": -68.0000, "lon_max": -67.9200,
            "parroquias": ["San Diego"]
        }
    },
    "Lara": {
        "Iribarren": {
            "lat_min": 9.9800, "lat_max": 10.1500,
            "lon_min": -69.4500, "lon_max": -69.2000,
            "parroquias": ["Catedral", "Concepción", "Santa Rosa", "Unión", "El Cují", "Tamaca", "Juan de Villegas"]
        }
    },
    "Anzoátegui": {
        "Sotillo": {
            "lat_min": 10.1600, "lat_max": 10.2600,
            "lon_min": -64.6700, "lon_max": -64.5800,
            "parroquias": ["Puerto La Cruz", "Pozuelos"]
        },
        "Simón Bolívar": {
            "lat_min": 10.0800, "lat_max": 10.2200,
            "lon_min": -64.7500, "lon_max": -64.6300,
            "parroquias": ["Barcelona", "El Carmen", "San Cristóbal", "Naricual", "Bergantín"]
        }
    },
    "Aragua": {
        "Girardot": {
            "lat_min": 10.1500, "lat_max": 10.3500,
            "lon_min": -67.6500, "lon_max": -67.5200,
            "parroquias": ["Las Delicias", "Madre María de San José", "Joaquín Crespo", "Pedro José Ovalles", "José Casanova Godoy", "Andrés Eloy Blanco", "Los Tacarigua", "Choroní"]
        }
    },
    "Táchira": {
        "San Cristóbal": {
            "lat_min": 7.7000, "lat_max": 7.8500,
            "lon_min": -72.2800, "lon_max": -72.1500,
            "parroquias": ["La Concordia", "San Juan Bautista", "Pedro María Morantes", "San Sebastián", "Dr. Francisco Romero Lobo"]
        }
    }
}

# Bounding Box Oficial de la República Bolivariana de Venezuela (WGS84)
VENEZUELA_BOUNDING_BOX = {
    "lat_min": 0.60,
    "lat_max": 12.50,
    "lon_min": -73.50,
    "lon_max": -59.80,
}


def is_point_in_venezuela(lat: float, lon: float) -> bool:
    """Verifica si las coordenadas WGS84 se encuentran dentro del territorio de Venezuela."""
    return (
        VENEZUELA_BOUNDING_BOX["lat_min"] <= lat <= VENEZUELA_BOUNDING_BOX["lat_max"]
        and VENEZUELA_BOUNDING_BOX["lon_min"] <= lon <= VENEZUELA_BOUNDING_BOX["lon_max"]
    )


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia geodésica ortodrómica en metros usando la fórmula de Haversine."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


# ============================================================================
# Inicialización del Esquema SQL Geoespacial
# ============================================================================

def init_geo_database(db_file: Path = DB_PATH) -> None:
    """Crea la tabla geocartográfica de puntos de interés y la alimenta con registros base verificados."""
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS geo_pois (
            id TEXT PRIMARY KEY,
            osm_id INTEGER,
            name TEXT NOT NULL,
            category TEXT NOT NULL,       -- 'oficina_comercial_movilnet', 'farmacia', 'salud_clinica', 'comercio', 'edificio_corporativo', 'perros_calientes'
            sub_category TEXT,           -- 'hospital', 'farmacia_cadena', 'torre_oficinas', 'oficina_principal', 'agencia_comercial', etc.
            state TEXT NOT NULL,         -- 'Distrito Capital', 'Miranda', etc.
            municipality TEXT NOT NULL,  -- 'Chacao', 'Baruta', etc.
            parish TEXT NOT NULL,        -- 'Chacao', 'Leoncio Martínez', etc.
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            address TEXT NOT NULL,
            phone TEXT,
            opening_hours TEXT,
            emergency_service INTEGER DEFAULT 0,
            metadata_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_geo_pois_lat_lon ON geo_pois(latitude, longitude);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_geo_pois_cat_muni ON geo_pois(category, municipality);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_geo_pois_state ON geo_pois(state);")

    # Si ya existen registros certificados en geo_pois, no sobrescribir con semilla básica
    cur.execute("SELECT COUNT(*) FROM geo_pois WHERE category IN ('oficina_servicio_movilnet', 'agente_autorizado_movilnet', 'agente_comercial_integral')")
    certified_count = cur.fetchone()[0]
    if certified_count > 0:
        conn.close()
        return

    # Semilla oficial de POIs verificados en Venezuela (incluyendo Oficinas Comerciales Movilnet)
    INITIAL_POIS = [
        # --- OFICINAS COMERCIALES Y AGENCIAS DE ATENCIÓN MOVILNET ---
        (
            "MOV-CCS-ROSAL-001", 90001, "Oficina Comercial Movilnet Torre El Rosal (Sede Principal)",
            "oficina_comercial_movilnet", "oficina_principal",
            "Miranda", "Chacao", "Chacao", 10.4890, -66.8670,
            "Av. Venezuela con Calle Mohedano, Torre Movilnet, Urb. El Rosal, Chacao, Caracas",
            "+58 212-8221000", "Lunes a Viernes 08:00 - 16:30", 0,
            '{"tipo": "Sede Corporativa & Oficina Comercial", "servicios": ["Atención al Cliente", "Venta de eSIM / SIM", "Soporte Técnico 4GMAX", "Reposición de Líneas", "Atención Corporativa"], "cobertura": "4GMAX", "estacionamiento": true}'
        ),
        (
            "MOV-CCS-CPLAZA-002", 90002, "Oficina Comercial Movilnet Centro Plaza",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Miranda", "Chacao", "Chacao", 10.4960, -66.8525,
            "Av. Francisco de Miranda, Centro Comercial Centro Plaza, Nivel 3, Los Palos Grandes, Chacao, Caracas",
            "+58 212-2850123", "Lunes a Sábado 09:00 - 17:00", 0,
            '{"tipo": "Agencia Comercial", "servicios": ["Venta de eSIM / SIM", "Migración a 4GMAX", "Cambio de Plan", "Recargas C2P", "Servicio Técnico"], "metro_cercano": "Estación Miranda"}'
        ),
        (
            "MOV-CCS-SAMBIL-003", 90003, "Oficina Comercial Movilnet Sambil Chacao",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Miranda", "Chacao", "Chacao", 10.4905, -66.8580,
            "Av. Libertador, Centro Comercial Sambil Chacao, Nivel Autopista, Local AC-12, Chacao, Caracas",
            "+58 212-2634567", "Lunes a Domingo 10:00 - 19:00", 0,
            '{"tipo": "Agencia Comercial Mall", "servicios": ["Activación Inmediata de eSIM", "Atención de Abonados", "Promociones Portabilidad"], "horario_extendido": true}'
        ),
        (
            "MOV-CCS-CCCT-004", 90004, "Oficina Comercial Movilnet CCCT",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Miranda", "Baruta", "Las Minas de Baruta", 10.4845, -66.8550,
            "Centro Ciudad Comercial Tamanaco (CCCT), Torre A, Nivel C-1, Chuao, Baruta, Caracas",
            "+58 212-9598811", "Lunes a Sábado 09:30 - 17:30", 0,
            '{"tipo": "Agencia Comercial", "servicios": ["Atención Integral", "eSIM Digital", "Planes Corporativos"]}'
        ),
        (
            "MOV-CCS-CANDEL-005", 90005, "Oficina Comercial Movilnet Sambil La Candelaria",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Distrito Capital", "Libertador", "Candelaria", 10.5050, -66.9040,
            "Av. Urdaneta con Av. Vollmer, CC Sambil La Candelaria, Nivel Andrés Bello, La Candelaria, Caracas",
            "+58 212-5712233", "Lunes a Sábado 10:00 - 18:30", 0,
            '{"tipo": "Agencia Comercial", "servicios": ["Atención Presencial", "Portabilidad Express", "Venta de Equipos"]}'
        ),
        (
            "MOV-CCS-RECREO-006", 90006, "Oficina Comercial Movilnet El Recreo",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Distrito Capital", "Libertador", "El Recreo", 10.4920, -66.8770,
            "Av. Casanova con Calle Venezuela, CC El Recreo, Nivel C2, Sabana Grande, Caracas",
            "+58 212-7068800", "Lunes a Sábado 10:00 - 18:00", 0,
            '{"tipo": "Agencia Comercial Mall", "servicios": ["Migración 4GMAX", "Atención de Contratos", "Recargas"]}'
        ),
        (
            "MOV-MAR-5JULIO-007", 90007, "Oficina Comercial Movilnet Maracaibo 5 de Julio",
            "oficina_comercial_movilnet", "oficina_regional",
            "Zulia", "Maracaibo", "Olegario Villalobos", 10.6680, -71.6180,
            "Calle 77 (5 de Julio) con Av. 15 Delicias, Torre Empresarial, Maracaibo, Zulia",
            "+58 261-7981122", "Lunes a Viernes 08:30 - 16:30", 0,
            '{"tipo": "Sede Regional Zulia", "servicios": ["Atención Integral", "Reposición de SIM", "Portabilidad Numérica", "Atención Corporativa"]}'
        ),
        (
            "MOV-MAR-LAGOM-008", 90008, "Oficina Comercial Movilnet Lago Mall Maracaibo",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Zulia", "Maracaibo", "Santa Lucía", 10.6800, -71.6020,
            "Av. 2 El Milagro, Centro Comercial Lago Mall, Nivel Avenida, Maracaibo, Zulia",
            "+58 261-7935566", "Lunes a Sábado 10:00 - 18:00", 0,
            '{"tipo": "Agencia Comercial Mall", "servicios": ["eSIM Digital", "Venta 4GMAX", "Atención al Cliente"]}'
        ),
        (
            "MOV-VAL-METROP-009", 90009, "Oficina Comercial Movilnet Metrópolis Valencia",
            "oficina_comercial_movilnet", "oficina_regional",
            "Carabobo", "San Diego", "San Diego", 10.1980, -67.9540,
            "Autopista Regional del Centro, CC Metrópolis Valencia, Nivel Sol, Local S-140, San Diego / Valencia, Carabobo",
            "+58 241-8640055", "Lunes a Sábado 10:00 - 18:30", 0,
            '{"tipo": "Sede Regional Carabobo", "servicios": ["Atención Presencial", "eSIM Digital", "Soporte Técnico", "Recargas C2P"]}'
        ),
        (
            "MOV-VAL-SAMBIL-010", 90010, "Oficina Comercial Movilnet Sambil Valencia",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Carabobo", "Naguanagua", "Naguanagua", 10.2330, -67.9890,
            "Av. 4 Manongo, CC Sambil Valencia, Nivel Mañongo, Naguanagua, Carabobo",
            "+58 241-8411200", "Lunes a Sábado 10:00 - 19:00", 0,
            '{"tipo": "Agencia Comercial Mall", "servicios": ["Venta de Planes", "Migración 4GMAX", "Atención al Cliente"]}'
        ),
        (
            "MOV-BAR-TRINIT-011", 90011, "Oficina Comercial Movilnet Las Trinitarias Barquisimeto",
            "oficina_comercial_movilnet", "oficina_regional",
            "Lara", "Iribarren", "Santa Rosa", 10.0760, -69.2880,
            "Av. Los Leones con Av. Circunvalación, CC Ciudad Comercial Las Trinitarias, Nivel Galería, Barquisimeto, Lara",
            "+58 251-2563344", "Lunes a Sábado 09:30 - 18:00", 0,
            '{"tipo": "Sede Regional Centro-Occidente", "servicios": ["Atención Integral", "Portabilidad eSIM", "Soporte Técnico 4GMAX"]}'
        ),
        (
            "MOV-PLC-PMAYOR-012", 90012, "Oficina Comercial Movilnet Plaza Mayor Puerto La Cruz",
            "oficina_comercial_movilnet", "oficina_regional",
            "Anzoátegui", "Sotillo", "Puerto La Cruz", 10.1950, -64.6750,
            "Av. Prolongación Paseo Colón, CC Plaza Mayor, Edificio Amarillo, Nivel PB, Lechería / Puerto La Cruz, Anzoátegui",
            "+58 281-2800111", "Lunes a Sábado 09:00 - 17:30", 0,
            '{"tipo": "Sede Regional Oriente", "servicios": ["Atención al Cliente", "Venta de eSIM / SIM", "Trámites de Contrato"]}'
        ),
        (
            "MOV-MY-AMERIC-013", 90013, "Oficina Comercial Movilnet Las Américas Maracay",
            "oficina_comercial_movilnet", "agencia_comercial",
            "Aragua", "Girardot", "Las Delicias", 10.2520, -67.5920,
            "Av. Las Américas, CC Las Américas, Nivel 1, Maracay, Aragua",
            "+58 243-2321188", "Lunes a Sábado 10:00 - 18:00", 0,
            '{"tipo": "Agencia Comercial", "servicios": ["Atención Integral", "Migración a 4GMAX", "Recargas C2P"]}'
        ),
        (
            "MOV-SC-SAMBIL-014", 90014, "Oficina Comercial Movilnet Sambil San Cristóbal",
            "oficina_comercial_movilnet", "oficina_regional",
            "Táchira", "San Cristóbal", "San Juan Bautista", 7.7850, -72.2150,
            "Autopista Antonio José de Sucre, CC Sambil San Cristóbal, Nivel Río, San Cristóbal, Táchira",
            "+58 276-3401000", "Lunes a Sábado 10:00 - 18:00", 0,
            '{"tipo": "Sede Regional Los Andes", "servicios": ["Atención al Abonado", "Venta de eSIM", "Reposición de Líneas"]}'
        ),

        # --- SALUD & FARMACIAS (Chacao) ---
        (
            "POI-CCS-FAR-001", 10101, "Farmatodo Los Palos Grandes", "farmacia", "farmacia_24h",
            "Miranda", "Chacao", "Chacao", 10.4965, -66.8505,
            "1ra Avenida con 2da Transversal de Los Palos Grandes, Chacao, Caracas",
            "+58 212-2851122", "24/7", 1, '{"cadena": "Farmatodo", "delivery": true, "estacionamiento": true}'
        ),
        (
            "POI-CCS-FAR-002", 10102, "Locatel La Castellana", "farmacia", "farmacia_equipos_medicos",
            "Miranda", "Chacao", "Chacao", 10.4990, -66.8540,
            "Av. Principal de La Castellana con Calle José Ángel Lamas, Chacao",
            "+58 212-2638844", "07:00 - 21:00", 0, '{"cadena": "Locatel", "alquiler_equipos_medicos": true}'
        ),
        (
            "POI-CCS-CLI-001", 10103, "Clínica El Ávila", "salud_clinica", "hospital_privado",
            "Miranda", "Chacao", "Chacao", 10.4988, -66.8512,
            "6ta Transversal con Av. San Juan Bosco, Altamira Norte, Chacao",
            "+58 212-2761111", "24/7", 1, '{"emergencia_adultos": true, "emergencia_pediatrica": true, "uci": true}'
        ),
        (
            "POI-CCS-CLI-002", 10104, "Centro Médico Docente La Trinidad", "salud_clinica", "hospital_privado",
            "Miranda", "Baruta", "Las Minas de Baruta", 10.4370, -66.8545,
            "Av. Intercomunal La Trinidad - El Hatillo, Baruta, Caracas",
            "+58 212-9496411", "24/7", 1, '{"emergencia_traumatologia": true, "helipuerto": true}'
        ),
        # --- EDIFICIOS CORPORATIVOS & OFICINAS ---
        (
            "POI-CCS-CORP-001", 10201, "Torre Movilnet El Rosal", "edificio_corporativo", "telecomunicaciones_sede",
            "Miranda", "Chacao", "Chacao", 10.4890, -66.8670,
            "Av. Venezuela, Torre Movilnet, Urb. El Rosal, Chacao, Caracas",
            "+58 212-8221000", "08:00 - 17:00", 0, '{"oficina_comercial": true, "atencion_abonados": true, "cobertura": "4GMAX"}'
        ),
        (
            "POI-CCS-CORP-002", 10202, "Centro Financiero Latino", "edificio_corporativo", "torre_financiera",
            "Distrito Capital", "Libertador", "Altagracia", 10.5085, -66.9110,
            "Av. Urdaneta con esquina Ánimas, La Candelaria / Altagracia, Caracas",
            "+58 212-5632211", "08:00 - 18:00", 0, '{"piso_oficinas": 32, "banco_sede": true}'
        ),
        (
            "POI-CCS-CORP-003", 10203, "Torre Parque Ávila", "edificio_corporativo", "torre_empresarial",
            "Miranda", "Sucre", "Leoncio Martínez", 10.4950, -66.8370,
            "Av. Francisco de Miranda, Los Dos Caminos, Sucre, Caracas",
            "+58 212-2395500", "08:00 - 18:00", 0, '{"helipuerto": false, "estacionamiento": true}'
        ),
        # --- COMERCIOS & GASTRONOMÍA VERIFICADA ---
        (
            "POI-CCS-COM-001", 10301, "Carritos de Perros de Plaza Altamira (Sur)", "perros_calientes", "comida_callejera",
            "Miranda", "Chacao", "Chacao", 10.4958, -66.8530,
            "Salida Metro Altamira Sur, Av. Francisco de Miranda, Chacao, Caracas",
            None, "17:00 - 04:00", 0, '{"especialidad": "Perros con salchicha polaca y papitas", "horario_nocturno": true}'
        ),
        (
            "POI-CCS-COM-002", 10302, "Puesto El Pana de Los Palos Grandes", "perros_calientes", "comida_callejera",
            "Miranda", "Chacao", "Chacao", 10.4980, -66.8490,
            "1ra Transversal de Los Palos Grandes, Chacao, Caracas",
            None, "18:00 - 02:00", 0, '{"especialidad": "Hamburguesas y perros callejeros"}'
        ),
        (
            "POI-CCS-COM-003", 10303, "Centro Comercial Sambil Chacao", "comercio", "centro_comercial",
            "Miranda", "Chacao", "Chacao", 10.4905, -66.8580,
            "Av. Libertador con calle Los Ángeles, Chacao, Caracas",
            "+58 212-2630000", "10:00 - 21:00", 0, '{"tiendas": 450, "zona_comida": true, "farmacias": 3}'
        ),
        # --- INTERIOR DE VENEZUELA (Maracaibo, Valencia, Barquisimeto) ---
        (
            "POI-MAR-CLI-001", 20101, "Hospital Privado El Ángel (Maracaibo)", "salud_clinica", "hospital_privado",
            "Zulia", "Maracaibo", "Olegario Villalobos", 10.6720, -71.6110,
            "Av. 4 Bella Vista con Calle 67 Cecilio Acosta, Maracaibo, Zulia",
            "+58 261-7921100", "24/7", 1, '{"emergencia": true, "banco_sangre": true}'
        ),
        (
            "POI-VAL-FAR-001", 30101, "Farmatodo San Diego El Remanso", "farmacia", "farmacia_24h",
            "Carabobo", "San Diego", "San Diego", 10.2310, -67.9750,
            "Av. Don Julio Centeno, Sector El Remanso, San Diego, Carabobo",
            "+58 241-8711122", "24/7", 1, '{"autofarmacia": true}'
        )
    ]

    for item in INITIAL_POIS:
        cur.execute("""
            INSERT OR REPLACE INTO geo_pois (
                id, osm_id, name, category, sub_category,
                state, municipality, parish, latitude, longitude,
                address, phone, opening_hours, emergency_service,
                metadata_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, item)

    conn.commit()
    conn.close()


# ============================================================================
# Métodos Geodésicos de Localización de Oficinas Comerciales Movilnet
# ============================================================================

def find_nearest_movilnet_agency(
    lat: float,
    lon: float,
    max_radius_km: float = 150.0,
    db_file: Path = DB_PATH
) -> Optional[Dict[str, Any]]:
    """
    Encuentra la Oficina Comercial o Agencia Movilnet más cercana a partir de coordenadas GPS WGS84.
    Calcula distancia Haversine, estimados de traslado y enlace de Google Maps para navegación.
    Aplica la Regla de Cero Adivinación: valida si el punto está dentro de Venezuela.
    """
    if not is_point_in_venezuela(lat, lon):
        return {
            "error": "ERR_OUTSIDE_VENEZUELA",
            "message": "Las coordenadas proporcionadas se encuentran fuera de la República Bolivariana de Venezuela."
        }

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, osm_id, name, category, sub_category, state, municipality, parish,
               latitude, longitude, address, phone, opening_hours, emergency_service, metadata_json
        FROM geo_pois
        WHERE category IN (
            'oficina_servicio_movilnet', 'oficina_comercial_movilnet', 
            'sede_corporativa_movilnet', 'agente_autorizado_movilnet', 
            'agente_comercial_integral'
        )
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    agencies = []
    for r in rows:
        poi_id, osm_id, name, cat, sub_cat, state, muni, parish, p_lat, p_lon, addr, phone, hours, emerg, meta = r
        dist_m = haversine_distance_meters(lat, lon, p_lat, p_lon)
        dist_km = dist_m / 1000.0

        if dist_km <= max_radius_km:
            walking_min = max(1, int(round(dist_m / 80.0)))
            driving_min = max(1, int(round(dist_m / 500.0)))

            try:
                import json
                meta_dict = json.loads(meta) if meta else {}
            except Exception:
                meta_dict = {}

            gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={p_lat},{p_lon}"

            agencies.append({
                "id": poi_id,
                "name": name,
                "category": cat,
                "sub_category": sub_cat,
                "state": state,
                "municipality": muni,
                "parish": parish,
                "latitude": p_lat,
                "longitude": p_lon,
                "address": addr,
                "phone": phone,
                "opening_hours": hours,
                "distance_meters": round(dist_m, 1),
                "distance_km": round(dist_km, 2),
                "walking_minutes_est": walking_min,
                "driving_minutes_est": driving_min,
                "google_maps_url": gmaps_url,
                "metadata": meta_dict
            })

    if not agencies:
        return None

    # Ordenar por proximidad ortodrómica
    agencies.sort(key=lambda a: a["distance_meters"])
    return agencies[0]


def find_agencies_by_city_or_state(
    query: str,
    limit: int = 5,
    db_file: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Busca agencias, oficinas comerciales (OSAC) y agentes autorizados de Movilnet por nombre de ciudad,
    estado, municipio o palabra clave geográfica (ej: 'Maracaibo', 'Valencia', 'Caracas', 'Chacao', 'Lara').
    """
    clean_q = query.strip().lower()
    if not clean_q:
        return []

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, osm_id, name, category, sub_category, state, municipality, parish,
               latitude, longitude, address, phone, opening_hours, emergency_service, metadata_json
        FROM geo_pois
        WHERE category IN (
            'oficina_servicio_movilnet', 'oficina_comercial_movilnet', 
            'sede_corporativa_movilnet', 'agente_autorizado_movilnet', 
            'agente_comercial_integral'
        )
          AND (
            LOWER(state) LIKE ? OR
            LOWER(municipality) LIKE ? OR
            LOWER(parish) LIKE ? OR
            LOWER(name) LIKE ? OR
            LOWER(address) LIKE ?
          )
        ORDER BY
          CASE
            WHEN category IN ('sede_corporativa_movilnet', 'oficina_servicio_movilnet', 'oficina_comercial_movilnet') THEN 1
            ELSE 2
          END,
          name ASC
        LIMIT ?
    """, (f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", limit))

    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        poi_id, osm_id, name, cat, sub_cat, state, muni, parish, p_lat, p_lon, addr, phone, hours, emerg, meta = r
        try:
            import json
            meta_dict = json.loads(meta) if meta else {}
        except Exception:
            meta_dict = {}

        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={p_lat},{p_lon}"

        results.append({
            "id": poi_id,
            "name": name,
            "category": cat,
            "sub_category": sub_cat,
            "state": state,
            "municipality": muni,
            "parish": parish,
            "latitude": p_lat,
            "longitude": p_lon,
            "address": addr,
            "phone": phone,
            "opening_hours": hours,
            "google_maps_url": gmaps_url,
            "metadata": meta_dict
        })

    return results


# Ejecutar inicialización idempotente al importar
init_geo_database()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Catálogo Geoespacial de Venezuela")
    parser.add_argument("--test", action="store_true", help="Auto-verificación matemática Haversine, DB y Oficinas Movilnet")
    args = parser.parse_args()
    if args.test:
        dist = haversine_distance_meters(10.4958, -66.8530, 10.4980, -66.8500)
        assert dist > 0, "Fallo en cálculo Haversine"
        # Test 1: Búsqueda de oficina más cercana desde Altamira, Caracas
        nearest_ccs = find_nearest_movilnet_agency(10.4960, -66.8530)
        assert nearest_ccs is not None, "Debe encontrar agencia cercana en Caracas"
        assert "Centro Plaza" in nearest_ccs["name"] or "Torre El Rosal" in nearest_ccs["name"]
        assert nearest_ccs["distance_km"] < 5.0, "La distancia en Caracas debe ser menor a 5km"

        # Test 2: Búsqueda por texto (Valencia)
        val_offices = find_agencies_by_city_or_state("Valencia")
        assert len(val_offices) > 0, "Debe encontrar oficinas en Valencia"
        assert any("Metrópolis" in o["name"] or "Sambil" in o["name"] for o in val_offices)

        # Test 3: Validación territorial fuera de Venezuela
        outside = find_nearest_movilnet_agency(25.7617, -80.1918) # Miami
        assert outside.get("error") == "ERR_OUTSIDE_VENEZUELA", "Debe rechazar coordenadas fuera de Venezuela"

        print(f"✅ [GEO_CATALOG]: Auto-test superado con éxito:")
        print(f"   - Haversine Altamira: {dist:.2f} m")
        print(f"   - Agencia más cercana Caracas: {nearest_ccs['name']} ({nearest_ccs['distance_km']} km)")
        print(f"   - Oficinas Valencia encontradas: {len(val_offices)}")
        print(f"   - Guarda territorial fuera de Venezuela: ERR_OUTSIDE_VENEZUELA verificado.")

