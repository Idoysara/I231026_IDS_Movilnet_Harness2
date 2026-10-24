#!/usr/bin/env python3
"""
services/cazador_ofertas/scripts/sembrar_ofertas_ciudades_piloto.py
===================================================================
Siembra de Comercios y SuperOfertas Activas para Pruebas Piloto Reales
en las 7 Ciudades Estratégicas de Venezuela:
1. Caracas (Distrito Capital / Miranda)
2. Maracay (Aragua)
3. Valencia (Carabobo)
4. La Guaira (Vargas)
5. Barquisimeto (Lara)
6. Maracaibo (Zulia)
7. Lechería (Anzoátegui)

Gobernanza: Invariante II (Margen Bruto >= 35%), Cero Alucinación B2C
y Modelo de Cero Fricción para Anunciantes (Polígonos Canónicos).
"""

import os
import sys
import json
import sqlite3
import time
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = CLIENT_ROOT / "data"
DB_PATH = DATA_DIR / "cazador_local.db"
SEED_JSON = DATA_DIR / "seed_data.json"

COMERCIOS_PILOTO = [
    # -------------------------------------------------------------------------
    # 1. MARACAY (Aragua)
    # -------------------------------------------------------------------------
    {
        "id": "COM-MCY-001",
        "rif": "J-31456789-1",
        "nombre": "Farmatodo Las Delicias Maracay",
        "categoria": "Farmacias y Salud",
        "lat": 10.2650,
        "lon": -67.5900,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Maracay",
        "radio_cobertura_m": 3500.0,
        "direccion": "Av. Las Delicias con Calle El Bosque, Maracay",
        "ofertas": [
            {
                "id": "OFE-MCY-01",
                "titulo": "Kit Vitaminas y Cuidado Familiar (Farmatodo Las Delicias)",
                "precio_regular_ves": 250.0,
                "precio_oferta_ves": 160.0,
                "costo_directo_ves": 80.0,
                "stock": 100,
                "horario": "24 Horas"
            }
        ]
    },
    {
        "id": "COM-MCY-002",
        "rif": "J-40123987-2",
        "nombre": "Pollos Los Aviadores Grill",
        "categoria": "Restaurantes",
        "lat": 10.1980,
        "lon": -67.5750,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Maracay",
        "radio_cobertura_m": 4000.0,
        "direccion": "CC Parque Los Aviadores, Nivel Feria, Maracay",
        "ofertas": [
            {
                "id": "OFE-MCY-02",
                "titulo": "Combo Familiar Pollo a la Brasa + Ración Hulla + Bebida (Los Aviadores)",
                "precio_regular_ves": 420.0,
                "precio_oferta_ves": 270.0,
                "costo_directo_ves": 140.0,
                "stock": 80,
                "horario": "11:00 - 21:00"
            }
        ]
    },
    {
        "id": "COM-MCY-003",
        "rif": "J-50112233-3",
        "nombre": "Ávila Burger Maracay San Jacinto",
        "categoria": "Comida Rápida y Franquicias",
        "lat": 10.2450,
        "lon": -67.5750,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Maracay",
        "radio_cobertura_m": 3500.0,
        "direccion": "Av. Bolívar Este, Sector San Jacinto, Maracay",
        "ofertas": [
            {
                "id": "OFE-MCY-03",
                "titulo": "Duo Burger Ávila Especial con Papas Rústicas (San Jacinto)",
                "precio_regular_ves": 340.0,
                "precio_oferta_ves": 215.0,
                "costo_directo_ves": 110.0,
                "stock": 90,
                "horario": "12:00 - 22:00"
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 2. VALENCIA (Carabobo)
    # -------------------------------------------------------------------------
    {
        "id": "COM-VLN-001",
        "rif": "J-30987654-1",
        "nombre": "Farmatodo El Viñedo Valencia",
        "categoria": "Farmacias y Salud",
        "lat": 10.2180,
        "lon": -68.0060,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Valencia",
        "radio_cobertura_m": 4000.0,
        "direccion": "Av. Monseñor Adams, Urbanización El Viñedo, Valencia",
        "ofertas": [
            {
                "id": "OFE-VLN-01",
                "titulo": "Pack Cuidado Dermocosmético y Protección Solar (El Viñedo)",
                "precio_regular_ves": 380.0,
                "precio_oferta_ves": 240.0,
                "costo_directo_ves": 120.0,
                "stock": 100,
                "horario": "24 Horas"
            }
        ]
    },
    {
        "id": "COM-VLN-002",
        "rif": "J-40998811-2",
        "nombre": "Sambil Valencia & Cinex",
        "categoria": "Centros Comerciales",
        "lat": 10.2520,
        "lon": -68.0130,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Valencia",
        "radio_cobertura_m": 4500.0,
        "direccion": "Urb. Mañongo, Naguanagua, Sambil Valencia",
        "ofertas": [
            {
                "id": "OFE-VLN-02",
                "titulo": "Pase Doble Cine 2D + Cotufas Grandes + Refresco (Sambil Valencia)",
                "precio_regular_ves": 280.0,
                "precio_oferta_ves": 175.0,
                "costo_directo_ves": 85.0,
                "stock": 120,
                "horario": "13:00 - 22:00"
            }
        ]
    },
    {
        "id": "COM-VLN-003",
        "rif": "J-50119988-3",
        "nombre": "Supermercados Kalea Valencia",
        "categoria": "Supermercados",
        "lat": 10.2300,
        "lon": -68.0080,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Valencia",
        "radio_cobertura_m": 4000.0,
        "direccion": "Calle de los Cafés, El Viñedo, Valencia",
        "ofertas": [
            {
                "id": "OFE-VLN-03",
                "titulo": "Combo Charcutería y Quesos Premium Nacionales (Kalea Valencia)",
                "precio_regular_ves": 450.0,
                "precio_oferta_ves": 290.0,
                "costo_directo_ves": 150.0,
                "stock": 75,
                "horario": "08:00 - 21:00"
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 3. LA GUAIRA (Vargas)
    # -------------------------------------------------------------------------
    {
        "id": "COM-LAG-001",
        "rif": "J-31223344-1",
        "nombre": "Farmatodo Caribe La Guaira",
        "categoria": "Farmacias y Salud",
        "lat": 10.6120,
        "lon": -66.8650,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "La Guaira",
        "radio_cobertura_m": 4500.0,
        "direccion": "Av. La Costanera, Sector Caribe, Caraballeda",
        "ofertas": [
            {
                "id": "OFE-LAG-01",
                "titulo": "Kit Playero Protección Solar e Hidratación (Caribe)",
                "precio_regular_ves": 310.0,
                "precio_oferta_ves": 195.0,
                "costo_directo_ves": 95.0,
                "stock": 100,
                "horario": "24 Horas"
            }
        ]
    },
    {
        "id": "COM-LAG-002",
        "rif": "J-40556677-2",
        "nombre": "Marisquería El Pescador Catia La Mar",
        "categoria": "Restaurantes",
        "lat": 10.6030,
        "lon": -67.0320,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "La Guaira",
        "radio_cobertura_m": 5000.0,
        "direccion": "Paseo La Marina, Catia La Mar, La Guaira",
        "ofertas": [
            {
                "id": "OFE-LAG-02",
                "titulo": "Rueda de Pescado Fresco con Tostones y Ensalada Playera (Catia La Mar)",
                "precio_regular_ves": 490.0,
                "precio_oferta_ves": 310.0,
                "costo_directo_ves": 160.0,
                "stock": 60,
                "horario": "11:00 - 19:00"
            }
        ]
    },
    {
        "id": "COM-LAG-003",
        "rif": "J-50334455-3",
        "nombre": "Parador Turístico Maiquetía",
        "categoria": "Cafeterías y Panaderías",
        "lat": 10.5980,
        "lon": -66.9550,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "La Guaira",
        "radio_cobertura_m": 4500.0,
        "direccion": "Av. Soublette, Distribuidor El Trébol, Maiquetía",
        "ofertas": [
            {
                "id": "OFE-LAG-03",
                "titulo": "Desayuno Criollo Playero con Empanadas de Cazón y Jugo Natural",
                "precio_regular_ves": 160.0,
                "precio_oferta_ves": 99.0,
                "costo_directo_ves": 45.0,
                "stock": 150,
                "horario": "06:30 - 16:00"
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 4. BARQUISIMETO (Lara)
    # -------------------------------------------------------------------------
    {
        "id": "COM-BQM-001",
        "rif": "J-31667788-1",
        "nombre": "Farmatodo Zona Este Barquisimeto",
        "categoria": "Farmacias y Salud",
        "lat": 10.0710,
        "lon": -69.3050,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Barquisimeto",
        "radio_cobertura_m": 4000.0,
        "direccion": "Av. Lara con Calle 8, Urbanización Nueva Segovia, Barquisimeto",
        "ofertas": [
            {
                "id": "OFE-BQM-01",
                "titulo": "Combo Vitaminas y Cuidado Pediátrico (Zona Este Barquisimeto)",
                "precio_regular_ves": 270.0,
                "precio_oferta_ves": 170.0,
                "costo_directo_ves": 85.0,
                "stock": 100,
                "horario": "24 Horas"
            }
        ]
    },
    {
        "id": "COM-BQM-002",
        "rif": "J-40889900-2",
        "nombre": "Pepitos El Guaro Barquisimeto",
        "categoria": "Comida Rápida y Franquicias",
        "lat": 10.0730,
        "lon": -69.2940,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Barquisimeto",
        "radio_cobertura_m": 4500.0,
        "direccion": "Av. Venezuela frente al Sambil Barquisimeto",
        "ofertas": [
            {
                "id": "OFE-BQM-02",
                "titulo": "Pepito Tradicional Guaro Mixto 30cm con Papas y Salsa Especial",
                "precio_regular_ves": 350.0,
                "precio_oferta_ves": 220.0,
                "costo_directo_ves": 110.0,
                "stock": 90,
                "horario": "17:00 - 23:30"
            }
        ]
    },
    {
        "id": "COM-BQM-003",
        "rif": "J-50445566-3",
        "nombre": "Café Gourmet Nueva Segovia",
        "categoria": "Cafeterías y Panaderías",
        "lat": 10.0650,
        "lon": -69.2980,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Barquisimeto",
        "radio_cobertura_m": 3500.0,
        "direccion": "Carrera 2 con Calle 5, Nueva Segovia, Barquisimeto",
        "ofertas": [
            {
                "id": "OFE-BQM-03",
                "titulo": "Duo Capuchino Larense + Porción Torta Tres Leches",
                "precio_regular_ves": 180.0,
                "precio_oferta_ves": 110.0,
                "costo_directo_ves": 55.0,
                "stock": 80,
                "horario": "08:00 - 20:00"
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 5. MARACAIBO (Zulia)
    # -------------------------------------------------------------------------
    {
        "id": "COM-MAR-001",
        "rif": "J-31889900-1",
        "nombre": "Farmatodo 5 de Julio Maracaibo",
        "categoria": "Farmacias y Salud",
        "lat": 10.6690,
        "lon": -71.6150,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Maracaibo",
        "radio_cobertura_m": 4500.0,
        "direccion": "Calle 77 (5 de Julio) con Av. 13A, Maracaibo",
        "ofertas": [
            {
                "id": "OFE-MAR-01",
                "titulo": "Kit Hidratación Extrema y Suero Oral Familiar (5 de Julio)",
                "precio_regular_ves": 230.0,
                "precio_oferta_ves": 145.0,
                "costo_directo_ves": 70.0,
                "stock": 120,
                "horario": "24 Horas"
            }
        ]
    },
    {
        "id": "COM-MAR-002",
        "rif": "J-40113355-2",
        "nombre": "Patacón & Cepillado Zuliano El Lago",
        "categoria": "Restaurantes",
        "lat": 10.6620,
        "lon": -71.6020,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Maracaibo",
        "radio_cobertura_m": 4500.0,
        "direccion": "Av. El Milagro, frente a Lago Mall, Maracaibo",
        "ofertas": [
            {
                "id": "OFE-MAR-02",
                "titulo": "Super Patacón Maracucho Mixto con Queso de Mano y Cepillado de Tamarindo",
                "precio_regular_ves": 380.0,
                "precio_oferta_ves": 240.0,
                "costo_directo_ves": 120.0,
                "stock": 100,
                "horario": "11:30 - 22:30"
            }
        ]
    },
    {
        "id": "COM-MAR-003",
        "rif": "J-50887766-3",
        "nombre": "De Cándido Delicias Norte",
        "categoria": "Supermercados",
        "lat": 10.6850,
        "lon": -71.6350,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Maracaibo",
        "radio_cobertura_m": 4500.0,
        "direccion": "Av. 15 Delicias Norte con Calle 45, Maracaibo",
        "ofertas": [
            {
                "id": "OFE-MAR-03",
                "titulo": "Cesta Ahorro Lácteos Zulianos y Víveres Básicos (De Cándido)",
                "precio_regular_ves": 580.0,
                "precio_oferta_ves": 370.0,
                "costo_directo_ves": 190.0,
                "stock": 70,
                "horario": "08:00 - 20:30"
            }
        ]
    },

    # -------------------------------------------------------------------------
    # 6. LECHERÍA (Anzoátegui)
    # -------------------------------------------------------------------------
    {
        "id": "COM-LEC-001",
        "rif": "J-31998877-1",
        "nombre": "Farmatodo Plaza Mayor Lechería",
        "categoria": "Farmacias y Salud",
        "lat": 10.1920,
        "lon": -64.6930,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Lechería",
        "radio_cobertura_m": 3500.0,
        "direccion": "CC Plaza Mayor, Canal Principal, Lechería",
        "ofertas": [
            {
                "id": "OFE-LEC-01",
                "titulo": "Pack Verano Protector Solar + Vitaminas Náuticas (Plaza Mayor)",
                "precio_regular_ves": 360.0,
                "precio_oferta_ves": 230.0,
                "costo_directo_ves": 115.0,
                "stock": 90,
                "horario": "24 Horas"
            }
        ]
    },
    {
        "id": "COM-LEC-002",
        "rif": "J-40224466-2",
        "nombre": "Asador Playa Mansa Lechería",
        "categoria": "Restaurantes",
        "lat": 10.1990,
        "lon": -64.6980,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Lechería",
        "radio_cobertura_m": 3500.0,
        "direccion": "Bulevar Playa Mansa, Quinta Los Cocos, Lechería",
        "ofertas": [
            {
                "id": "OFE-LEC-02",
                "titulo": "Parrilla Mar y Tierra Especial 2 Personas con Tostones Playeros",
                "precio_regular_ves": 620.0,
                "precio_oferta_ves": 395.0,
                "costo_directo_ves": 200.0,
                "stock": 50,
                "horario": "12:00 - 23:00"
            }
        ]
    },
    {
        "id": "COM-LEC-003",
        "rif": "J-50998844-3",
        "nombre": "Gelatería & Café Puerto Morro",
        "categoria": "Cafeterías y Panaderías",
        "lat": 10.1950,
        "lon": -64.7010,
        "tier": "VIP_RADAR",
        "activo": True,
        "tipo_cobertura": "ZONA",
        "zona_sector": "Lechería",
        "radio_cobertura_m": 3000.0,
        "direccion": "Av. Principal de Lechería, Edif. Peñón del Faro",
        "ofertas": [
            {
                "id": "OFE-LEC-03",
                "titulo": "Duo Gelato Artesanal Italiano + Café Espresso Crema",
                "precio_regular_ves": 190.0,
                "precio_oferta_ves": 120.0,
                "costo_directo_ves": 60.0,
                "stock": 110,
                "horario": "10:00 - 22:00"
            }
        ]
    }
]

def sembrar_ciudades_piloto():
    print("🚀 Iniciando siembra de Comercios y SuperOfertas en las 7 Ciudades Piloto...")
    now = time.time()
    
    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        
        comercios_insertados = 0
        ofertas_insertadas = 0
        
        for c in COMERCIOS_PILOTO:
            # Validar e insertar comercio
            cursor.execute("""
                INSERT OR REPLACE INTO comercios (
                    id, rif, nombre, categoria, lat, lon, tier, activo,
                    created_at, updated_at, tipo_cobertura, zona_sector,
                    radio_cobertura_m, direccion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"], c["rif"], c["nombre"], c["categoria"],
                c["lat"], c["lon"], c["tier"], 1 if c["activo"] else 0,
                now, now, c["tipo_cobertura"], c["zona_sector"],
                c["radio_cobertura_m"], c["direccion"]
            ))
            comercios_insertados += 1
            
            # Insertar ofertas asociadas
            for ofe in c.get("ofertas", []):
                p_reg = ofe["precio_regular_ves"]
                p_ofe = ofe["precio_oferta_ves"]
                c_dir = ofe["costo_directo_ves"]
                desc_pct = round(((p_reg - p_ofe) / p_reg) * 100, 1)
                marg_pct = round(((p_ofe - c_dir) / p_ofe) * 100, 1)
                
                # Invariante II: Margen Bruto >= 35%
                assert marg_pct >= 35.0, f"Error: Margen menor al 35% en {ofe['titulo']}: {marg_pct}%"
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ofertas (
                        id, comercio_id, titulo, precio_regular_ves, precio_oferta_ves,
                        costo_directo_ves, descuento_pct, margen_pct, stock_disponible,
                        horario_validez, activa, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ofe["id"], c["id"], ofe["titulo"], p_reg, p_ofe,
                    c_dir, desc_pct, marg_pct, ofe["stock"],
                    ofe["horario"], 1, now, now
                ))
                ofertas_insertadas += 1
                
        conn.commit()

        # Recuento general
        total_c = cursor.execute("SELECT count(*) FROM comercios WHERE activo = 1").fetchone()[0]
        total_o = cursor.execute("SELECT count(*) FROM ofertas WHERE activa = 1 AND stock_disponible > 0").fetchone()[0]
        
    print(f"✅ Siembra completada con éxito:")
    print(f"   • Comercios Nuevos / Actualizados: {comercios_insertados}")
    print(f"   • SuperOfertas Nuevas / Actualizadas: {ofertas_insertadas}")
    print(f"   • Total Comercios Activos en DB: {total_c}")
    print(f"   • Total Ofertas con Stock en DB: {total_o}")

    # También actualizar seed_data.json si existe para que mantenga sincronía
    try:
        if SEED_JSON.exists():
            with open(SEED_JSON, "r", encoding="utf-8") as f:
                data_seed = json.load(f)
            
            existing_c_map = {item["id"]: item for item in data_seed.get("comercios", [])}
            existing_o_map = {item["id"]: item for item in data_seed.get("ofertas", [])}
            
            for c in COMERCIOS_PILOTO:
                existing_c_map[c["id"]] = {
                    "id": c["id"],
                    "nombre": c["nombre"],
                    "rif": c["rif"],
                    "lat": c["lat"],
                    "lon": c["lon"],
                    "categoria": c["categoria"],
                    "tier": c["tier"],
                    "activo": c["activo"],
                    "municipio": c["zona_sector"]
                }
                for ofe in c.get("ofertas", []):
                    existing_o_map[ofe["id"]] = {
                        "id": ofe["id"],
                        "comercio_id": c["id"],
                        "titulo": ofe["titulo"],
                        "precio_regular_ves": ofe["precio_regular_ves"],
                        "precio_oferta_ves": ofe["precio_oferta_ves"],
                        "costo_directo_ves": ofe["costo_directo_ves"],
                        "stock_inicial": ofe["stock"],
                        "stock_disponible": ofe["stock"],
                        "horario_validez": ofe["horario"],
                        "activa": True
                    }
                    
            data_seed["comercios"] = list(existing_c_map.values())
            data_seed["ofertas"] = list(existing_o_map.values())
            
            with open(SEED_JSON, "w", encoding="utf-8") as f:
                json.dump(data_seed, f, indent=2, ensure_ascii=False)
            print(f"📁 `seed_data.json` sincronizado con {len(data_seed['comercios'])} comercios y {len(data_seed['ofertas'])} ofertas.")
    except Exception as e:
        print(f"⚠️ Advertencia al actualizar seed_data.json: {e}")

if __name__ == "__main__":
    sembrar_ciudades_piloto()
