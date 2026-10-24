#!/usr/bin/env python3
"""
services/cazador_ofertas/scripts/generar_40_superofertas_por_urbanizacion_caracas.py
===================================================================================
Generador y Sembrador Masivo de SuperOfertas para Caracas.
Cumplimiento Soberano: Por lo menos 40 SuperOfertas activas en cada urbanización
de cada alcaldía / municipio de la Gran Caracas.

Cobertura:
  • Municipio Chacao: 5 urbanizaciones (Chacao, Altamira, Los Palos Grandes, El Rosal, Bello Campo/CCCT)
  • Municipio Baruta: 5 urbanizaciones (Las Mercedes, Colinas de Bello Monte, La Trinidad, El Cafetal/Santa Sofía, Prados del Este/Santa Fe)
  • Municipio Sucre: 5 urbanizaciones (Los Dos Caminos, Boleíta/Los Ruices, La California/CC Líder, Sebucán/Los Chorros, Terrazas del Ávila/El Marqués)
  • Municipio El Hatillo: 4 urbanizaciones (El Hatillo Pueblo, Los Naranjos, La Lagunita/Paseo El Hatillo, La Boyera/El Cigarral)
  • Municipio Libertador: 8 urbanizaciones (Sabana Grande, Plaza Venezuela, La Candelaria, Centro Histórico/El Silencio, San Bernardino, El Paraíso, Montalbán, Catia)

Total: 27 urbanizaciones × 40 ofertas = 1.080 SuperOfertas activas en Caracas.
Invariantes: Invariante II (Margen Bruto >= 35%), Invariante III (Geo real), Stock > 0.
"""

import os
import sys
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

CLIENT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = CLIENT_ROOT / "data"
DB_PATH = DATA_DIR / "cazador_local.db"
SEED_JSON = DATA_DIR / "seed_data.json"

# Importar catálogo canónico de zonas de Caracas
sys.path.insert(0, str(CLIENT_ROOT))
from src.domain.zones import CANONICAL_ZONES

# Definición de las 27 urbanizaciones organizadas por Alcaldía / Municipio
URBANIZACIONES_CARACAS = [
    # 1. Municipio Chacao (5 urbanizaciones)
    {
        "municipio": "Chacao",
        "slug": "chacao",
        "key_zone": "chacao",
        "nombre_urb": "Chacao",
        "prefijo_id": "CHAC",
        "rif_base": "30101",
        "marcas": [
            ("Central Madeirense San Ignacio", "Supermercados", "Av. Blandín, Centro San Ignacio, Nivel Jardín", 0.0012, -0.0008),
            ("Farmatodo Casco Chacao", "Farmacias y Salud", "Av. Francisco de Miranda, frente a Plaza Bolívar Chacao", -0.0005, 0.0010),
            ("El Cine Restaurant Chacao", "Restaurantes", "Calle Elice con Av. Francisco de Miranda, Chacao", 0.0008, 0.0015),
            ("Arturo's Sambil Chacao", "Comida Rápida y Franquicias", "Centro Sambil Chacao, Nivel Autopista, Feria de Comida", -0.0015, -0.0012),
            ("Panadería Danubio Chacao", "Café y Panadería", "Calle Los Ángeles con Av. Miranda, Chacao", 0.0018, 0.0005),
            ("Óptica Caroní Sambil", "Belleza y Cuidado Personal", "Centro Sambil Chacao, Nivel Acuario", -0.0010, -0.0020)
        ]
    },
    {
        "municipio": "Chacao",
        "slug": "altamira",
        "key_zone": "altamira",
        "nombre_urb": "Altamira",
        "prefijo_id": "ALTA",
        "rif_base": "30102",
        "marcas": [
            ("Automercados Plaza's Altamira", "Supermercados", "Av. San Juan Bosco con 3ra Transversal, Altamira", 0.0015, -0.0010),
            ("Farmatodo Plaza Francia Altamira", "Farmacias y Salud", "Av. Luis Roche con Av. Francisco de Miranda, Altamira", -0.0008, 0.0005),
            ("El Almacén Bistró Altamira", "Restaurantes", "1ra Transversal de Altamira, entre Av. San Juan Bosco y Av. Ávila", 0.0010, 0.0012),
            ("Ávila Burger Altamira", "Comida Rápida y Franquicias", "4ta Transversal con Av. San Juan Bosco, Altamira", 0.0020, -0.0005),
            ("Café Francés Altamira", "Café y Panadería", "Av. Luis Roche, frente a la Plaza Francia Sur", -0.0012, 0.0018),
            ("Spacio Spa & Peluquería Altamira", "Belleza y Cuidado Personal", "Av. San Juan Bosco, Edif. Altamira Palace", 0.0005, -0.0015)
        ]
    },
    {
        "municipio": "Chacao",
        "slug": "los-palos-grandes",
        "key_zone": "los palos grandes",
        "nombre_urb": "Los Palos Grandes",
        "prefijo_id": "LPG",
        "rif_base": "30103",
        "marcas": [
            ("Excelsior Gama Los Palos Grandes", "Supermercados", "2da Transversal con Av. Andrés Bello, Los Palos Grandes", 0.0010, 0.0010),
            ("Locatel Parque Cristal", "Farmacias y Salud", "Av. Francisco de Miranda, Edif. Parque Cristal", -0.0015, 0.0012),
            ("La Casa Bistro Cuadra Gastronómica", "Restaurantes", "3ra Transversal entre 2da y 3ra Av., Los Palos Grandes", 0.0018, -0.0010),
            ("Bonsai Sushi Centro Plaza", "Comida Rápida y Franquicias", "Av. Francisco de Miranda, Centro Plaza, Nivel 4", -0.0020, -0.0015),
            ("Artesano Cafetería LPG", "Café y Panadería", "Av. Andrés Bello con 1ra Transversal, Los Palos Grandes", 0.0008, 0.0020),
            ("Mundo Móvil Accesorios Centro Plaza", "Servicios y Hogar", "Centro Plaza, Nivel PB, Torre A", -0.0018, 0.0005)
        ]
    },
    {
        "municipio": "Chacao",
        "slug": "el-rosal",
        "key_zone": "el rosal",
        "nombre_urb": "El Rosal",
        "prefijo_id": "ROSL",
        "rif_base": "30104",
        "marcas": [
            ("Bodegón Gourmet El Rosal", "Supermercados", "Av. Venezuela, Torre BNC, PB", 0.0010, -0.0012),
            ("Farmatodo El Rosal", "Farmacias y Salud", "Av. Tamanaco con Av. Sorocaima, El Rosal", -0.0012, 0.0015),
            ("Urrutia Asador Restaurante", "Restaurantes", "Av. Francisco Solano López con Calle Los Mangos, El Rosal", 0.0015, 0.0008),
            ("Subway Torre Lido", "Comida Rápida y Franquicias", "Av. Francisco de Miranda, Centro Lido, Nivel Galería", 0.0020, -0.0020),
            ("Pastelería Mozart El Rosal", "Café y Panadería", "Av. Tamanaco, Torre Tamanaco, Local PB", -0.0005, -0.0010),
            ("CarWash & Detailing El Rosal", "Servicios y Hogar", "Av. Sorocaima con Av. Libertador, El Rosal", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Chacao",
        "slug": "bello-campo-ccct",
        "key_zone": "bello campo",
        "nombre_urb": "Bello Campo / CCCT / Chuao",
        "prefijo_id": "CCCT",
        "rif_base": "30105",
        "marcas": [
            ("Supermercado Unicasa Bello Campo", "Supermercados", "Av. Principal de Bello Campo, Centro Bello Campo", 0.0025, 0.0010),
            ("Farmacias SAAS CCCT", "Farmacias y Salud", "Centro Ciudad Comercial Tamanaco, Nivel C1, Local 42", -0.0010, -0.0015),
            ("Hard Rock Cafe Caracas CCCT", "Restaurantes", "CCCT, Nivel C2, Terraza Oeste", -0.0008, 0.0010),
            ("Churromanía CCCT", "Comida Rápida y Franquicias", "CCCT, Nivel Feria de Comida Central", -0.0012, 0.0005),
            ("Café Il Duomo Cubo Negro", "Café y Panadería", "Av. La Estancia, Centro Banaven (Cubo Negro), PB", -0.0020, 0.0020),
            ("TecnoZone Celulares CCCT", "Servicios y Hogar", "CCCT, Nivel C1, Eje Comercial", -0.0005, -0.0020)
        ]
    },

    # 2. Municipio Baruta (5 urbanizaciones)
    {
        "municipio": "Baruta",
        "slug": "las-mercedes",
        "key_zone": "las mercedes",
        "nombre_urb": "Las Mercedes",
        "prefijo_id": "MERC",
        "rif_base": "30201",
        "marcas": [
            ("Río Supermarket Las Mercedes", "Supermercados", "Av. Río de Janeiro con Calle Trinidad, Las Mercedes", 0.0015, -0.0012),
            ("Farmatodo Río de Janeiro", "Farmacias y Salud", "Av. Río de Janeiro con Calle New York, Las Mercedes", -0.0010, 0.0010),
            ("La Estancia Restaurante Carnes", "Restaurantes", "Av. Principal de Las Mercedes con Calle Monterrey", 0.0012, 0.0015),
            ("Hamburguesas 212 Tolón", "Comida Rápida y Franquicias", "Tolón Fashion Mall, Nivel Feria 4", -0.0015, -0.0010),
            ("Café Páramo Las Mercedes", "Café y Panadería", "Calle París con Calle Caroní, Las Mercedes", 0.0020, 0.0005),
            ("AutoLavado VIP Las Mercedes", "Servicios y Hogar", "Av. Principal de Las Mercedes con Calle Mucuchíes", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Baruta",
        "slug": "colinas-bello-monte",
        "key_zone": "colinas de bello monte",
        "nombre_urb": "Colinas de Bello Monte",
        "prefijo_id": "BLMT",
        "rif_base": "30202",
        "marcas": [
            ("Automercados Plaza's Bello Monte", "Supermercados", "Av. Principal de Bello Monte, Edif. Centro Comercial", 0.0015, -0.0010),
            ("Locatel Bello Monte", "Farmacias y Salud", "Av. Principal con Calle Chopin, Colinas de Bello Monte", -0.0012, 0.0015),
            ("Restaurante El Mayorazgo Bello Monte", "Restaurantes", "Calle Beethoven con Av. Principal, Bello Monte", 0.0018, 0.0008),
            ("Arturo's Ciudad Banesco", "Comida Rápida y Franquicias", "Av. Principal de Bello Monte, frente a Ciudad Banesco", -0.0020, -0.0012),
            ("Panadería Cueva de Iria", "Café y Panadería", "Av. Miguelángel con Calle Beethoven, Bello Monte", 0.0008, 0.0020),
            ("Ferretería Baruta Express", "Servicios y Hogar", "Av. Principal de Colinas de Bello Monte, Local 18", -0.0015, -0.0018)
        ]
    },
    {
        "municipio": "Baruta",
        "slug": "la-trinidad",
        "key_zone": "la trinidad",
        "nombre_urb": "La Trinidad",
        "prefijo_id": "TRIN",
        "rif_base": "30203",
        "marcas": [
            ("Central Madeirense La Trinidad", "Supermercados", "Av. Intercomunal La Trinidad con Calle Soledad", 0.0015, -0.0015),
            ("Farmatodo La Trinidad CMDLT", "Farmacias y Salud", "Av. Principal La Trinidad, frente a Bomberos", -0.0010, 0.0012),
            ("El Fogón Grill La Trinidad", "Restaurantes", "Av. San Sebastián con Calle Guaicaipuro, La Trinidad", 0.0018, 0.0010),
            ("Domino's Pizza La Trinidad", "Comida Rápida y Franquicias", "Av. Principal de La Trinidad, Edif. Industrial", -0.0015, -0.0010),
            ("Panadería Flor de La Trinidad", "Café y Panadería", "Calle Real de La Trinidad, Edif. San José", 0.0005, 0.0020),
            ("Taller Mecánico & Alineación Express Trinidad", "Servicios y Hogar", "Zona Industrial La Trinidad, Calle 3", -0.0020, 0.0015)
        ]
    },
    {
        "municipio": "Baruta",
        "slug": "el-cafetal",
        "key_zone": "el cafetal",
        "nombre_urb": "El Cafetal / Santa Sofía",
        "prefijo_id": "CAFT",
        "rif_base": "30204",
        "marcas": [
            ("Automercados Plaza's El Cafetal", "Supermercados", "Av. Principal de El Cafetal, CC Plaza Las Américas, Nivel 1", 0.0012, -0.0012),
            ("Farmatodo Santa Sofía", "Farmacias y Salud", "Av. Principal de Santa Sofía con Calle Limón", -0.0010, 0.0015),
            ("Da Guido Ristorante Italiano Cafetal", "Restaurantes", "Av. Principal de El Cafetal, CC San Luis", 0.0015, 0.0010),
            ("Burger Shack Plaza Las Américas", "Comida Rápida y Franquicias", "CC Plaza Las Américas II, Nivel Feria", -0.0018, -0.0010),
            ("Pastelería La Mansión del Cafetal", "Café y Panadería", "Av. Principal de El Cafetal con Boulevard Santa Clara", 0.0008, 0.0018),
            ("Clínica Veterinaria & Spa Pet El Cafetal", "Servicios y Hogar", "CC Santa Marta, Local 12, El Cafetal", -0.0015, 0.0020)
        ]
    },
    {
        "municipio": "Baruta",
        "slug": "prados-del-este",
        "key_zone": "prados del este",
        "nombre_urb": "Prados del Este / Santa Fe",
        "prefijo_id": "PRAD",
        "rif_base": "30205",
        "marcas": [
            ("Excelsior Gama Santa Fe", "Supermercados", "Av. José María Vargas, CC Santa Fe Norte, PB", 0.0015, -0.0010),
            ("Farmatodo Galerías Prados del Este", "Farmacias y Salud", "Av. Francisco Lazo Martí, CC Galerías Prados del Este", -0.0012, 0.0015),
            ("Tutto Pasta Prados del Este", "Restaurantes", "Av. Principal de Prados del Este, CC Galerías, Nivel C1", 0.0018, 0.0008),
            ("Pollo Arturos Galerías Prados del Este", "Comida Rápida y Franquicias", "CC Galerías Prados del Este, Nivel PB", -0.0015, -0.0012),
            ("Panadería Gran Prado", "Café y Panadería", "Av. El Paseo con Calle Maracaibo, Prados del Este", 0.0005, 0.0020),
            ("Librería & Papelería Santa Fe", "Servicios y Hogar", "CC Santa Fe Sur, Nivel 2, Local 25", -0.0020, -0.0015)
        ]
    },

    # 3. Municipio Sucre (5 urbanizaciones)
    {
        "municipio": "Sucre",
        "slug": "los-dos-caminos",
        "key_zone": "los dos caminos",
        "nombre_urb": "Los Dos Caminos / Millenium",
        "prefijo_id": "2CAM",
        "rif_base": "30301",
        "marcas": [
            ("Central Madeirense Millenium Mall", "Supermercados", "Av. Rómulo Gallegos, CC Millenium Mall, Nivel C2", 0.0012, -0.0010),
            ("Farmatodo Los Dos Caminos", "Farmacias y Salud", "Av. Sucre con Av. Francisco de Miranda, Los Dos Caminos", -0.0010, 0.0015),
            ("Tony Roma's Millenium", "Restaurantes", "CC Millenium Mall, Nivel Terraza", 0.0015, 0.0012),
            ("KFC Millenium Mall", "Comida Rápida y Franquicias", "CC Millenium Mall, Nivel Feria", -0.0018, -0.0012),
            ("Churros y Café Millenium", "Café y Panadería", "CC Millenium Mall, Nivel PB, Plaza Central", 0.0005, 0.0018),
            ("Móvil Planet Los Dos Caminos", "Servicios y Hogar", "Av. Rómulo Gallegos, CC Dos Caminos, Local 8", -0.0015, 0.0020)
        ]
    },
    {
        "municipio": "Sucre",
        "slug": "boleita",
        "key_zone": "boleita",
        "nombre_urb": "Boleíta / Los Ruices",
        "prefijo_id": "BOLE",
        "rif_base": "30302",
        "marcas": [
            ("Automercados Plaza's Los Cortijos", "Supermercados", "Av. Francisco de Miranda con Av. Principal de Los Ruices", 0.0015, -0.0012),
            ("Locatel Boleíta Center", "Farmacias y Salud", "Av. Principal de Boleíta Norte, CC Boleíta Center, Nivel 1", -0.0012, 0.0015),
            ("Rincón Campestre Boleíta", "Restaurantes", "4ta Transversal de Boleíta Sur, Edif. Industrial", 0.0018, 0.0010),
            ("Arturo's Los Ruices", "Comida Rápida y Franquicias", "Av. Francisco de Miranda, Los Ruices, frente a estación Metro", -0.0015, -0.0015),
            ("Panadería Flor de Boleíta", "Café y Panadería", "Av. Rómulo Gallegos con Calle Milán, Boleíta Sur", 0.0008, 0.0020),
            ("Ferretería EPA Los Ruices", "Servicios y Hogar", "Av. Principal de Los Ruices con Autopista Francisco Fajardo", -0.0020, 0.0012)
        ]
    },
    {
        "municipio": "Sucre",
        "slug": "la-california",
        "key_zone": "la california",
        "nombre_urb": "La California / CC Líder",
        "prefijo_id": "CALI",
        "rif_base": "30303",
        "marcas": [
            ("Gama Plus CC Líder", "Supermercados", "Av. Francisco de Miranda, CC Líder, Nivel Entretenimiento", 0.0012, -0.0010),
            ("Farmatodo La California Norte", "Farmacias y Salud", "Av. Madrid con Av. Francisco de Miranda, La California", -0.0010, 0.0015),
            ("Hard Rock Food Líder", "Restaurantes", "CC Líder, Terraza Gourmet Nivel 6", 0.0015, 0.0012),
            ("McDonald's CC Líder", "Comida Rápida y Franquicias", "CC Líder, Nivel Feria, Local F-18", -0.0018, -0.0015),
            ("Café Galipán Macaracuay", "Café y Panadería", "Av. Principal de Macaracuay, CC Macaracuay Plaza", 0.0005, 0.0020),
            ("ElectroHogar La California", "Servicios y Hogar", "Av. Francisco de Miranda, Edif. California Sur", -0.0015, 0.0018)
        ]
    },
    {
        "municipio": "Sucre",
        "slug": "sebucan",
        "key_zone": "sebucan",
        "nombre_urb": "Sebucán / Los Chorros",
        "prefijo_id": "SEBU",
        "rif_base": "30304",
        "marcas": [
            ("Automercados Plaza's Sebucán", "Supermercados", "Av. Principal de Sebucán, CC Los Patios de Sebucán", 0.0012, -0.0010),
            ("Farmatodo Santa Eduvigis", "Farmacias y Salud", "Av. Rómulo Gallegos con Av. Principal Santa Eduvigis", -0.0010, 0.0015),
            ("Taverna Los Chorros Grill", "Restaurantes", "Av. Principal de Los Chorros con 2da Transversal", 0.0015, 0.0012),
            ("Ávila Burger Sebucán", "Comida Rápida y Franquicias", "CC Sebucán Mall, Terraza Gastronómica", -0.0015, -0.0012),
            ("Panadería Sebucán Deli", "Café y Panadería", "Av. Principal de Sebucán con Calle Los Mangos", 0.0008, 0.0018),
            ("Spa Natural Los Chorros", "Belleza y Cuidado Personal", "Av. Los Castaños, Sebucán Norte", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Sucre",
        "slug": "terrazas-del-avila",
        "key_zone": "terrazas del avila",
        "nombre_urb": "Terrazas del Ávila / El Marqués",
        "prefijo_id": "TAVIL",
        "rif_base": "30305",
        "marcas": [
            ("Excelsior Gama El Marqués", "Supermercados", "Av. Sanz con Av. Francisco de Miranda, El Marqués", 0.0015, -0.0012),
            ("Farmatodo Terrazas del Ávila", "Farmacias y Salud", "Calle 1, CC Terrazas del Ávila, Nivel PB", -0.0010, 0.0015),
            ("Pizzas El Marqués Ristorante", "Restaurantes", "Av. Rómulo Gallegos con Av. Sanz, El Marqués", 0.0018, 0.0010),
            ("Arturo's El Marqués", "Comida Rápida y Franquicias", "Av. Francisco de Miranda, frente a estación La California", -0.0015, -0.0015),
            ("Café Unimet Terrazas", "Café y Panadería", "Distribuidor Metropolitano, Campus Unimet", 0.0005, 0.0020),
            ("Autoservicio El Marqués LubriExpress", "Servicios y Hogar", "Av. Sanz, Edif. Sanz Plaza, El Marqués", -0.0020, 0.0015)
        ]
    },

    # 4. Municipio El Hatillo (4 urbanizaciones)
    {
        "municipio": "El Hatillo",
        "slug": "el-hatillo",
        "key_zone": "el hatillo",
        "nombre_urb": "El Hatillo (Pueblo)",
        "prefijo_id": "HATI",
        "rif_base": "30401",
        "marcas": [
            ("Bodegón Hatillano Gourmet", "Supermercados", "Calle Bolívar con Calle Santa Rosalía, El Hatillo", 0.0010, -0.0010),
            ("Farmacias SAAS Casco Hatillo", "Farmacias y Salud", "Calle Sucre, frente a Plaza Bolívar El Hatillo", -0.0008, 0.0012),
            ("Restaurante Casa 22 El Hatillo", "Restaurantes", "Calle Bella Vista con Calle Santa Rosalía, El Hatillo", 0.0015, 0.0015),
            ("Dulces Típicos El Hatillo Criollo", "Comida Rápida y Franquicias", "Calle Comercio con Calle La Paz, El Hatillo", -0.0012, -0.0010),
            ("Café Kakao El Hatillo", "Café y Panadería", "Calle Bolívar, Casa Tradicional 14, El Hatillo", 0.0008, 0.0018),
            ("Artesanías El Campanario", "Servicios y Hogar", "Calle Santa Rosalía, Local 6, El Hatillo", -0.0015, 0.0010)
        ]
    },
    {
        "municipio": "El Hatillo",
        "slug": "los-naranjos",
        "key_zone": "los naranjos",
        "nombre_urb": "Los Naranjos",
        "prefijo_id": "NARA",
        "rif_base": "30402",
        "marcas": [
            ("Automercados Plaza's Los Naranjos", "Supermercados", "Av. Principal Los Naranjos, CC Galerías Los Naranjos, Nivel C1", 0.0012, -0.0012),
            ("Farmatodo Galerías Los Naranjos", "Farmacias y Salud", "CC Galerías Los Naranjos, Nivel PB", -0.0010, 0.0015),
            ("Il Forno Trattoria Los Naranjos", "Restaurantes", "CC Casa Mall Los Naranjos, Nivel Terraza", 0.0018, 0.0010),
            ("Burger Joint Los Naranjos", "Comida Rápida y Franquicias", "CC Galerías Los Naranjos, Nivel Feria", -0.0015, -0.0010),
            ("Panadería Cacao Los Naranjos", "Café y Panadería", "Av. Principal Los Naranjos, CC Los Naranjos Plaza", 0.0005, 0.0020),
            ("Salón de Belleza Glam Naranjos", "Belleza y Cuidado Personal", "CC Galerías Los Naranjos, Nivel 2", -0.0020, 0.0015)
        ]
    },
    {
        "municipio": "El Hatillo",
        "slug": "la-lagunita",
        "key_zone": "la lagunita",
        "nombre_urb": "La Lagunita / Paseo El Hatillo",
        "prefijo_id": "LAGU",
        "rif_base": "30403",
        "marcas": [
            ("Gama Plus Paseo El Hatillo", "Supermercados", "Av. Sur La Lagunita, Mall Paseo El Hatillo, Nivel 1", 0.0012, -0.0010),
            ("Locatel Paseo El Hatillo", "Farmacias y Salud", "Mall Paseo El Hatillo La Lagunita, Nivel Piso 2", -0.0010, 0.0015),
            ("Hangar Steakhouse La Lagunita", "Restaurantes", "Mall Paseo El Hatillo, Piso 5 Gourmet", 0.0015, 0.0012),
            ("Bonsai Sushi Paseo El Hatillo", "Comida Rápida y Franquicias", "Mall Paseo El Hatillo, Nivel Feria 4", -0.0015, -0.0012),
            ("Café Fragola Paseo El Hatillo", "Café y Panadería", "Mall Paseo El Hatillo, Nivel Plaza Central", 0.0008, 0.0018),
            ("Móvil Accesorios Paseo El Hatillo", "Servicios y Hogar", "Mall Paseo El Hatillo, Nivel Galería PB", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "El Hatillo",
        "slug": "la-boyera",
        "key_zone": "la boyera",
        "nombre_urb": "La Boyera / El Cigarral",
        "prefijo_id": "BOYE",
        "rif_base": "30404",
        "marcas": [
            ("Automercados Plaza's La Boyera", "Supermercados", "Av. Intercomunal La Boyera, CC Los Geranios, PB", 0.0012, -0.0012),
            ("Farmatodo La Boyera", "Farmacias y Salud", "Av. Intercomunal El Hatillo, Sector La Boyera", -0.0010, 0.0015),
            ("Ristorante La Boyera Grill", "Restaurantes", "Calle El Cigarral, CC El Cigarral, Nivel Mezzanina", 0.0018, 0.0010),
            ("Subway La Boyera", "Comida Rápida y Franquicias", "CC Los Geranios, Nivel Plaza Comercial", -0.0015, -0.0010),
            ("Panadería Dulce Boyera", "Café y Panadería", "Av. Principal de La Boyera, Edif. Boyera Palace", 0.0005, 0.0020),
            ("Ferretería El Cigarral Express", "Servicios y Hogar", "Av. Intercomunal La Boyera, Local 8", -0.0020, 0.0015)
        ]
    },

    # 5. Municipio Libertador (8 urbanizaciones)
    {
        "municipio": "Libertador",
        "slug": "sabana-grande",
        "key_zone": "sabana grande",
        "nombre_urb": "Sabana Grande",
        "prefijo_id": "SABG",
        "rif_base": "30501",
        "marcas": [
            ("Central Madeirense El Recreo", "Supermercados", "Av. Casanova, CC El Recreo, Nivel C2", 0.0012, -0.0010),
            ("Farmatodo Bulevar Sabana Grande", "Farmacias y Salud", "Bulevar de Sabana Grande con Calle Los Galpones", -0.0010, 0.0015),
            ("Gran Café de Sabana Grande", "Restaurantes", "Bulevar de Sabana Grande con Calle Las Flores", 0.0015, 0.0012),
            ("Arturo's City Market", "Comida Rápida y Franquicias", "Bulevar de Sabana Grande, Centro City Market, Nivel Feria", -0.0015, -0.0012),
            ("Panadería Danubio Chacaíto", "Café y Panadería", "Av. Casanova con Calle Élice, Chacaíto", 0.0008, 0.0018),
            ("TecnoMarket City Market", "Servicios y Hogar", "Centro City Market, Nivel Plaza Tecnológica", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "plaza-venezuela",
        "key_zone": "plaza venezuela",
        "nombre_urb": "Plaza Venezuela",
        "prefijo_id": "PVEN",
        "rif_base": "30502",
        "marcas": [
            ("Hipermercado Bicentenario Plaza Venezuela", "Supermercados", "Av. Paseo Colón, Edf. Bicentenario", 0.0012, -0.0010),
            ("Locatel Previsora", "Farmacias y Salud", "Av. Abraham Lincoln, Torre La Previsora, PB", -0.0010, 0.0015),
            ("Picanha Criolla Plaza Venezuela", "Restaurantes", "Av. La Salle con Av. Lima, Los Caobos", 0.0015, 0.0012),
            ("Domino's Pizza Plaza Venezuela", "Comida Rápida y Franquicias", "Av. Las Acacias con Av. Casanova, Plaza Venezuela", -0.0015, -0.0012),
            ("Cafetería Las Tres Gracias", "Café y Panadería", "Plaza Las Tres Gracias, Los Símbolos", 0.0008, 0.0018),
            ("Repuestos & Baterías Plaza Venezuela", "Servicios y Hogar", "Av. Andrés Bello con Calle Real de Quebrada Honda", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "la-candelaria",
        "key_zone": "la candelaria",
        "nombre_urb": "La Candelaria",
        "prefijo_id": "CAND",
        "rif_base": "30503",
        "marcas": [
            ("Río Supermarket Sambil La Candelaria", "Supermercados", "Av. Vollmer con Av. Urdaneta, Sambil Candelaria, Nivel 1", 0.0012, -0.0010),
            ("Farmatodo Plaza La Candelaria", "Farmacias y Salud", "Esquina Candilito a Cruz de la Candelaria", -0.0010, 0.0015),
            ("La Cita Restaurante Español Candelaria", "Restaurantes", "Esquina Alcabala a Peligro, La Candelaria", 0.0015, 0.0012),
            ("Arturo's Sambil La Candelaria", "Comida Rápida y Franquicias", "Sambil La Candelaria, Nivel Zona Gourmet", -0.0015, -0.0012),
            ("Pastelería y Panadería La Candelaria Imperial", "Café y Panadería", "Av. Urdaneta, Esquina Veroes a Jesuitas", 0.0008, 0.0018),
            ("Óptica Caroní Sambil Candelaria", "Belleza y Cuidado Personal", "Sambil La Candelaria, Nivel Galería", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "centro-caracas-silencio",
        "key_zone": "centro historico",
        "nombre_urb": "Centro Histórico / El Silencio",
        "prefijo_id": "CENT",
        "rif_base": "30504",
        "marcas": [
            ("Automercado Central Silencio", "Supermercados", "Av. Baralt, Edif. Bloque 1 de El Silencio, PB", 0.0012, -0.0010),
            ("Farmatodo Capitolio", "Farmacias y Salud", "Av. Universidad, Esquina La Bolsa a San Francisco", -0.0010, 0.0015),
            ("Café del Centro Histórico Bolívar", "Restaurantes", "Esquina Gradillas a Monjas, Plaza Bolívar Caracas", 0.0015, 0.0012),
            ("Pollo El Silencio Tradición", "Comida Rápida y Franquicias", "Plaza O'Leary, Edf. Bloque 4, El Silencio", -0.0015, -0.0012),
            ("Panadería San Francisco Catedral", "Café y Panadería", "Av. Baralt con Esquina Pedrera, Centro", 0.0008, 0.0018),
            ("Electrónica & Telefonía Centro Plaza Baralt", "Servicios y Hogar", "Av. Baralt, Edif. Pasaje Capitolio", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "san-bernardino",
        "key_zone": "san bernardino",
        "nombre_urb": "San Bernardino",
        "prefijo_id": "SBER",
        "rif_base": "30505",
        "marcas": [
            ("Automercados Plaza's San Bernardino", "Supermercados", "Av. Vollmer con Av. Cecilio Acosta, San Bernardino", 0.0012, -0.0010),
            ("Locatel Clínicas Caracas", "Farmacias y Salud", "Av. Panteón con Av. Alameda, Centro Médico Docente", -0.0010, 0.0015),
            ("Ristorante San Bernardino Grill", "Restaurantes", "Av. Los Próceres con Av. Cajigal, San Bernardino", 0.0015, 0.0012),
            ("Subway Hospital de Clínicas", "Comida Rápida y Franquicias", "Av. Vollmer, Edif. Centro Clínico, Local PB", -0.0015, -0.0012),
            ("Panadería Flor de San Bernardino", "Café y Panadería", "Av. Cecilio Acosta con Av. Vollmer", 0.0008, 0.0018),
            ("Centro Óptico San Bernardino", "Belleza y Cuidado Personal", "Av. Panteón, Edf. Galipán, PB", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "el-paraiso",
        "key_zone": "el paraiso",
        "nombre_urb": "El Paraíso",
        "prefijo_id": "PARA",
        "rif_base": "30506",
        "marcas": [
            ("Central Madeirense Multiplaza El Paraíso", "Supermercados", "Av. Páez, CC Multiplaza El Paraíso, Nivel 1", 0.0012, -0.0010),
            ("Farmatodo Plaza Madariaga", "Farmacias y Salud", "Av. Washington con Av. Páez, frente a Plaza Madariaga", -0.0010, 0.0015),
            ("Restaurante El Pinar Criollo", "Restaurantes", "Av. Páez con Calle Las Fuentes, El Paraíso", 0.0015, 0.0012),
            ("Arturo's Multiplaza El Paraíso", "Comida Rápida y Franquicias", "CC Multiplaza El Paraíso, Nivel Feria", -0.0015, -0.0012),
            ("Panadería Gran Paraíso", "Café y Panadería", "Av. Páez con Calle El Ejército, El Paraíso", 0.0008, 0.0018),
            ("Autolavado & Detailing El Paraíso", "Servicios y Hogar", "Av. Guzmán Blanco con Av. Washington", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "montalban-la-villa",
        "key_zone": "montalban",
        "nombre_urb": "Montalbán / La Vega",
        "prefijo_id": "MONT",
        "rif_base": "30507",
        "marcas": [
            ("Automercados Plaza's La Villa", "Supermercados", "Av. Teherán, CC La Villa, Montalbán II, PB", 0.0012, -0.0010),
            ("Farmatodo Montalbán I", "Farmacias y Salud", "Av. Teherán con Calle 2, frente a Universidad UCAB", -0.0010, 0.0015),
            ("Pizzería La Fontana Montalbán", "Restaurantes", "CC La Villa, Nivel Mezzanina, Montalbán", 0.0015, 0.0012),
            ("Ávila Burger La Villa", "Comida Rápida y Franquicias", "CC La Villa, Terraza Gastronómica", -0.0015, -0.0012),
            ("Café Estudiantil UCAB", "Café y Panadería", "Av. Teherán, Campus UCAB Montalbán, Módulo 4", 0.0008, 0.0018),
            ("Centro Fotocopiado & Papelería Montalbán", "Servicios y Hogar", "Av. Teherán con Calle 1, Montalbán I", -0.0018, 0.0020)
        ]
    },
    {
        "municipio": "Libertador",
        "slug": "catia-perez-bonalde",
        "key_zone": "catia",
        "nombre_urb": "Catia (Pérez Bonalde)",
        "prefijo_id": "CATI",
        "rif_base": "30508",
        "marcas": [
            ("Supermercado Central Catia", "Supermercados", "Av. Sucre con Calle Colombia, Catia", 0.0012, -0.0010),
            ("Farmacias SAAS Plaza Sucre", "Farmacias y Salud", "Av. Sucre, frente a estación Metro Plaza Sucre", -0.0010, 0.0015),
            ("Restaurante Pollo Sabroso Pérez Bonalde", "Restaurantes", "Bulevar Pérez Bonalde con Calle Argentina", 0.0015, 0.0012),
            ("Arturo's Propatria", "Comida Rápida y Franquicias", "Centro Comercial Propatria, Nivel PB", -0.0015, -0.0012),
            ("Panadería Gran Catia", "Café y Panadería", "Calle Colombia con Calle España, Pérez Bonalde", 0.0008, 0.0018),
            ("Reparación & Celulares Bulevar Catia", "Servicios y Hogar", "Bulevar Pérez Bonalde, Edif. Comercio Local 5", -0.0018, 0.0020)
        ]
    }
]

# Plantillas de Ofertas por Rubro Comercial
# Cumplen estrictamente Invariante II: (precio_oferta - costo_directo) / precio_oferta >= 0.35
OFERTAS_TEMPLATES_BY_RUBRO: Dict[str, List[Tuple[str, float, float, float, str]]] = {
    "Supermercados": [
        ("Combo Despensa Familiar (Arroz, Harina PAN, Pasta, Aceite)", 320.0, 210.0, 110.0, "08:00 - 21:00"), # Margen: 47.6%
        ("Pack Proteínas Express (Pollo Entero + Carne Molida Especial 1kg)", 480.0, 310.0, 160.0, "08:00 - 20:00"), # Margen: 48.4%
        ("Pack Desayuno Venezolano (Queso Llanero 1kg + Mantequilla + Café 500g)", 390.0, 250.0, 130.0, "08:00 - 21:00"), # Margen: 48.0%
        ("Canasta Charcutería Premium (Jamón Superior + Queso Amarillo Torondoy)", 440.0, 290.0, 150.0, "08:00 - 20:00"), # Margen: 48.3%
        ("Combo Limpieza y Cuidado del Hogar (Detergente + Cloro + Desinfectante)", 280.0, 185.0, 95.0, "08:00 - 21:00"), # Margen: 48.6%
        ("Pack Lácteos & Yogur (Leche Entera 1L x3 + Yogur Familiar Los Andes)", 260.0, 175.0, 90.0, "08:00 - 20:00"), # Margen: 48.6%
        ("Bolsa Granos & Víveres (Caraotas Negras 1kg + Lentejas + Azúcar)", 210.0, 140.0, 75.0, "08:00 - 21:00"), # Margen: 46.4%
    ],
    "Farmacias y Salud": [
        ("Kit Primeros Auxilios & Salud Familiar (Alcohol + Gasas + Curitas + Betadine)", 220.0, 145.0, 70.0, "24 Horas"), # Margen: 51.7%
        ("Pack Multivitamínico Vitamina C 1000mg + Zinc (Defensas Total)", 340.0, 220.0, 110.0, "08:00 - 22:00"), # Margen: 50.0%
        ("Cuidado Personal & Aseo (Shampoo + Jabón Líquido + Crema Dental Colgate)", 290.0, 190.0, 95.0, "24 Horas"), # Margen: 50.0%
        ("Combo Alivio Gripal (Antigripal Noche/Día + Vitamina C Efervescente)", 250.0, 160.0, 80.0, "24 Horas"), # Margen: 50.0%
        ("Protector Solar Facial FPS 50+ Resistente al Agua", 460.0, 295.0, 145.0, "08:00 - 22:00"), # Margen: 50.8%
        ("Pack Cuidado Pediátrico (Pañales Etapa 3 + Toallitas Húmedas + Crema)", 380.0, 255.0, 130.0, "08:00 - 22:00"), # Margen: 49.0%
        ("Tensiómetro Digital Automático de Brazo + Estuche Protector", 750.0, 480.0, 240.0, "08:00 - 20:00"), # Margen: 50.0%
    ],
    "Restaurantes": [
        ("Menú Ejecutivo 3 Tiempos (Sopa del Día + Plato Fuerte + Bebida Natural)", 240.0, 160.0, 80.0, "12:00 - 16:00"), # Margen: 50.0%
        ("Combo Parrilla Especial 2 Personas (Carne Solomo + Chorizo + Arepitas + Guasacaca)", 580.0, 380.0, 190.0, "12:00 - 22:00"), # Margen: 50.0%
        ("Plato Degustación Criollo (Pabellón Criollo Completo + Jugo de Papelón con Limón)", 270.0, 180.0, 90.0, "11:30 - 17:00"), # Margen: 50.0%
        ("Pizza Familiar Tradicional 8 Porciones + Ración Palitos de Ajo + Refresco 1.5L", 420.0, 275.0, 135.0, "12:00 - 22:30"), # Margen: 50.9%
        ("Ración Tequeños Gourmet x12 con Salsa Tártara de la Casa", 190.0, 125.0, 60.0, "12:00 - 22:00"), # Margen: 52.0%
        ("Almuerzo de Pastas Caseras (Fettuccine Alfredo o Bolognese + Pan al Ajo + Bebida)", 260.0, 170.0, 85.0, "12:00 - 17:00"), # Margen: 50.0%
        ("Cena Romántica / Dúo (2 Platos Principales + 2 Postres + 2 Bebidas)", 680.0, 440.0, 220.0, "18:00 - 23:00"), # Margen: 50.0%
    ],
    "Comida Rápida y Franquicias": [
        ("Combo Hamburguesa Clásica Doble Carne + Papas Fritas Grandes + Refresco", 260.0, 175.0, 85.0, "11:00 - 22:00"), # Margen: 51.4%
        ("Combo Pollo Broaster 4 Piezas + Ensalada Rallada + Arepitas Fritas + Bebida", 320.0, 215.0, 105.0, "11:00 - 22:00"), # Margen: 51.2%
        ("Combo 2 Perros Calientes Especiales con Queso Amarillo + Papas Ralladas + Bebida", 180.0, 120.0, 55.0, "11:00 - 23:00"), # Margen: 54.2%
        ("Barco Sushi Mixto 24 Piezas (Rolls Fritos + Salmón + California)", 550.0, 360.0, 175.0, "12:00 - 22:30"), # Margen: 51.4%
        ("Balde Familiar Pollo Crujiente 8 Piezas + 2 Raciones Papas Fritas", 490.0, 320.0, 160.0, "11:00 - 22:00"), # Margen: 50.0%
        ("Combo Sándwich Sub 30cm + Galleta con Chispas + Refresco Refill", 290.0, 195.0, 95.0, "10:30 - 21:30"), # Margen: 51.3%
        ("Ración Churros Rellenos Dulce de Leche x8 + Chocolate Caliente", 170.0, 110.0, 50.0, "14:00 - 21:00"), # Margen: 54.5%
    ],
    "Café y Panadería": [
        ("Combo Desayuno Cafetería (Café con Leche Grande + Cachito de Jamón Recién Horneado)", 140.0, 95.0, 45.0, "07:00 - 12:00"), # Margen: 52.6%
        ("Tarde de Café & Dulce (Capuchino Italiano + Porción Torta Tres Leches o Selva Negra)", 160.0, 105.0, 50.0, "14:00 - 19:30"), # Margen: 52.4%
        ("Pack Croissants Mantequilla x4 + Mermelada Artesanal 250g", 210.0, 140.0, 68.0, "07:30 - 18:00"), # Margen: 51.4%
        ("Desayuno Tradicional Arepa Reina Pepiada o Jamón y Queso + Jugo de Naranja Natural", 190.0, 125.0, 60.0, "07:00 - 12:30"), # Margen: 52.0%
        ("Pack Pan Campesino Artesanal x2 + Pan Canilla x4 Recién Salidos", 120.0, 80.0, 38.0, "07:00 - 19:00"), # Margen: 52.5%
        ("Combo Merienda Familiar (Café Molido 500g Especialidad + Caja Galletería Surtida)", 310.0, 205.0, 100.0, "08:00 - 20:00"), # Margen: 51.2%
    ],
    "Belleza y Cuidado Personal": [
        ("Corte de Cabello Unisex + Lavado con Mascarilla Hidratante + Secado Express", 260.0, 170.0, 80.0, "09:00 - 19:00"), # Margen: 52.9%
        ("Manicura Spa Rusa + Pedicura Completa con Esmaltado Semipermanente", 350.0, 230.0, 110.0, "09:00 - 19:00"), # Margen: 52.2%
        ("Limpieza Facial Profunda con Vapor de Ozono + Extracción + Mascarilla LED", 450.0, 290.0, 140.0, "09:00 - 18:00"), # Margen: 51.7%
        ("Masaje Relajante Descontracturante 45 min con Aceites Esenciales", 420.0, 270.0, 130.0, "10:00 - 19:00"), # Margen: 51.9%
        ("Examen Visual Computarizado Completo + Descuento Especial en Cristales Antirreflejo", 310.0, 195.0, 95.0, "09:00 - 18:00"), # Margen: 51.3%
        ("Montura Oftálmica de Diseñador + Estuche Rígido + Paño Microfibra", 590.0, 380.0, 180.0, "09:00 - 18:00"), # Margen: 52.6%
    ],
    "Servicios y Hogar": [
        ("Lavado Completo de Vehículo (Chasis + Carrocería + Aspirado Profundo + Silicón)", 280.0, 180.0, 85.0, "08:00 - 17:00"), # Margen: 52.8%
        ("Servicio de Alineación Delantera + Balanceo 4 Ruedas Computarizado", 390.0, 250.0, 120.0, "08:00 - 17:00"), # Margen: 52.0%
        ("Cambio de Aceite Mineral/Semisintético + Filtro de Aceite Instalado", 620.0, 410.0, 200.0, "08:00 - 16:30"), # Margen: 51.2%
        ("Protector de Pantalla Cerámico / Hidrogel + Instalación Especializada", 150.0, 95.0, 42.0, "09:30 - 18:30"), # Margen: 55.8%
        ("Cargador Rápido 20W Tipo-C Certificado + Cable Blindado Reforzado", 220.0, 140.0, 65.0, "09:30 - 19:00"), # Margen: 53.6%
        ("Kit Herramientas Básicas para el Hogar (Destornilladores + Martillo + Pinza)", 340.0, 220.0, 105.0, "08:30 - 18:00"), # Margen: 52.3%
    ]
}

def generar_datos_caracas():
    """Genera la estructura de comercios y ofertas garantizando >= 40 por cada una de las 27 urbanizaciones."""
    print("=" * 80)
    print("🚀 GENERADOR SOBERANO DE SUPEROFERTAS — GRAN CARACAS (5 MUNICIPIOS / 27 URBANIZACIONES)")
    print("=" * 80)

    comercios_generados = []
    ofertas_generadas = []
    ofertas_por_urbanizacion: Dict[str, int] = {}
    
    total_ofertas_ccs = 0
    total_comercios_ccs = 0

    now = time.time()

    for urb in URBANIZACIONES_CARACAS:
        urb_slug = urb["slug"]
        urb_nombre = urb["nombre_urb"]
        municipio = urb["municipio"]
        key_zone = urb["key_zone"]
        prefijo_id = urb["prefijo_id"]
        rif_base = urb["rif_base"]
        
        canonical_info = CANONICAL_ZONES.get(key_zone)
        if not canonical_info:
            raise ValueError(f"Error: la zona {key_zone} no existe en CANONICAL_ZONES")
        
        centroide_lat = canonical_info["centroide"]["lat"]
        centroide_lon = canonical_info["centroide"]["lon"]
        radio_zona = canonical_info["radio_zona_m"]

        urb_comercios = []
        urb_ofertas = []
        
        # Cada urbanización tiene 6 comercios
        # Para llegar a exactamente 40 ofertas:
        # Comercio 0: 7 ofertas
        # Comercio 1: 7 ofertas
        # Comercio 2: 7 ofertas
        # Comercio 3: 7 ofertas
        # Comercio 4: 6 ofertas
        # Comercio 5: 6 ofertas
        # Total = 7 + 7 + 7 + 7 + 6 + 6 = 40 ofertas EXACTAS por urbanización.
        distribucion_cuota = [7, 7, 7, 7, 6, 6]

        for idx, (marca_nombre, cat, direccion, d_lat, d_lon) in enumerate(urb["marcas"]):
            comercio_id = f"COM-CCS-{prefijo_id}-{idx+1:02d}"
            rif = f"J-{rif_base}{idx+1:03d}-9"
            lat = round(centroide_lat + d_lat, 5)
            lon = round(centroide_lon + d_lon, 5)
            
            comercio_dict = {
                "id": comercio_id,
                "rif": rif,
                "nombre": marca_nombre,
                "categoria": cat,
                "lat": lat,
                "lon": lon,
                "tier": "VIP_RADAR" if idx < 3 else "PREMIUM",
                "activo": True,
                "tipo_cobertura": "ZONA",
                "zona_sector": urb_nombre,
                "radio_cobertura_m": radio_zona,
                "direccion": direccion,
                "ofertas": []
            }

            cuota = distribucion_cuota[idx]
            plantillas = OFERTAS_TEMPLATES_BY_RUBRO.get(cat, OFERTAS_TEMPLATES_BY_RUBRO["Supermercados"])

            for o_idx in range(cuota):
                t_idx = o_idx % len(plantillas)
                base_titulo, p_reg, p_ofe, c_dir, horario = plantillas[t_idx]
                
                # Ajuste ligero de precios según la sucursal para variedad realista
                factor_precio = 1.0 + ((idx * 3 + o_idx) % 5) * 0.03 # +/- 0% a 12%
                p_reg_adj = round(p_reg * factor_precio, 2)
                p_ofe_adj = round(p_ofe * factor_precio, 2)
                c_dir_adj = round(c_dir * factor_precio, 2)
                
                desc_pct = round(((p_reg_adj - p_ofe_adj) / p_reg_adj) * 100, 1)
                marg_pct = round(((p_ofe_adj - c_dir_adj) / p_ofe_adj) * 100, 1)

                # Invariante II: Margen Bruto >= 35%
                assert marg_pct >= 35.0, f"Error Invariante II violada: {marg_pct}% < 35% en {base_titulo}"
                assert p_ofe_adj < p_reg_adj, f"Error: Oferta no menor a regular en {base_titulo}"

                oferta_id = f"OFE-CCS-{prefijo_id}-{len(urb_ofertas)+1:02d}"
                stock = 70 + ((idx * 11 + o_idx * 7) % 50) # 70 a 120 cupones

                oferta_dict = {
                    "id": oferta_id,
                    "comercio_id": comercio_id,
                    "titulo": f"{base_titulo} ({marca_nombre.split()[0]})",
                    "precio_regular_ves": p_reg_adj,
                    "precio_oferta_ves": p_ofe_adj,
                    "costo_directo_ves": c_dir_adj,
                    "descuento_pct": desc_pct,
                    "margen_pct": marg_pct,
                    "stock_disponible": stock,
                    "horario_validez": horario,
                    "activa": True
                }

                comercio_dict["ofertas"].append(oferta_dict)
                urb_ofertas.append(oferta_dict)
                ofertas_generadas.append(oferta_dict)

            urb_comercios.append(comercio_dict)
            comercios_generados.append(comercio_dict)

        ofertas_por_urbanizacion[urb_nombre] = len(urb_ofertas)
        total_ofertas_ccs += len(urb_ofertas)
        total_comercios_ccs += len(urb_comercios)
        
        # Validar meta
        assert len(urb_ofertas) >= 40, f"Error: {urb_nombre} tiene menos de 40 ofertas: {len(urb_ofertas)}"

    print(f"📊 Generación completada con éxito:")
    print(f"   • Total Urbanizaciones en Caracas: {len(URBANIZACIONES_CARACAS)}")
    print(f"   • Total Comercios Aliados Generados: {total_comercios_ccs}")
    print(f"   • Total SuperOfertas Generadas: {total_ofertas_ccs}")
    print(f"   • Mínimo de ofertas por urbanización: {min(ofertas_por_urbanizacion.values())}")
    print(f"   • Máximo de ofertas por urbanización: {max(ofertas_por_urbanizacion.values())}")

    return comercios_generados, ofertas_generadas, ofertas_por_urbanizacion

def sembrar_en_sqlite_y_json(comercios, ofertas):
    """Inserta atómicamente los comercios y ofertas en SQLite y sincroniza seed_data.json."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No existe la base de datos en {DB_PATH}")

    now = time.time()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Asegurar columnas necesarias en comercios si no existieran
        cursor.execute("PRAGMA table_info(comercios)")
        cols = [c[1] for c in cursor.fetchall()]
        if "tipo_cobertura" not in cols:
            cursor.execute("ALTER TABLE comercios ADD COLUMN tipo_cobertura TEXT DEFAULT 'PUNTO_INTERES'")
        if "zona_sector" not in cols:
            cursor.execute("ALTER TABLE comercios ADD COLUMN zona_sector TEXT")
        if "radio_cobertura_m" not in cols:
            cursor.execute("ALTER TABLE comercios ADD COLUMN radio_cobertura_m REAL DEFAULT 500.0")
        if "direccion" not in cols:
            cursor.execute("ALTER TABLE comercios ADD COLUMN direccion TEXT")

        conn.commit()

        # Inserción en lote
        for c in comercios:
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

        for ofe in ofertas:
            cursor.execute("""
                INSERT OR REPLACE INTO ofertas (
                    id, comercio_id, titulo, precio_regular_ves, precio_oferta_ves,
                    costo_directo_ves, descuento_pct, margen_pct, stock_disponible,
                    horario_validez, activa, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ofe["id"], ofe["comercio_id"], ofe["titulo"],
                ofe["precio_regular_ves"], ofe["precio_oferta_ves"],
                ofe["costo_directo_ves"], ofe["descuento_pct"],
                ofe["margen_pct"], ofe["stock_disponible"],
                ofe["horario_validez"], 1 if ofe["activa"] else 0,
                now, now
            ))

        conn.commit()
        print("💾 Inserción en SQLite `cazador_local.db` completada con éxito.")

        # Verificación en BD
        cur = conn.cursor()
        total_c = cur.execute("SELECT count(*) FROM comercios WHERE activo = 1").fetchone()[0]
        total_o = cur.execute("SELECT count(*) FROM ofertas WHERE activa = 1 AND stock_disponible > 0").fetchone()[0]
        print(f"   • Total Comercios Activos en BD: {total_c}")
        print(f"   • Total Ofertas Activas en BD: {total_o}")

    finally:
        conn.close()

    # Sincronización de seed_data.json
    try:
        if SEED_JSON.exists():
            with open(SEED_JSON, "r", encoding="utf-8") as f:
                data_seed = json.load(f)
        else:
            data_seed = {"comercios": [], "ofertas": []}

        existing_c_map = {item["id"]: item for item in data_seed.get("comercios", [])}
        existing_o_map = {item["id"]: item for item in data_seed.get("ofertas", [])}

        for c in comercios:
            existing_c_map[c["id"]] = {
                "id": c["id"],
                "nombre": c["nombre"],
                "rif": c["rif"],
                "lat": c["lat"],
                "lon": c["lon"],
                "categoria": c["categoria"],
                "tier": c["tier"],
                "activo": c["activo"],
                "municipio": c["zona_sector"],
                "tipo_cobertura": c["tipo_cobertura"],
                "zona_sector": c["zona_sector"],
                "radio_cobertura_m": c["radio_cobertura_m"],
                "direccion": c["direccion"]
            }

        for ofe in ofertas:
            existing_o_map[ofe["id"]] = {
                "id": ofe["id"],
                "comercio_id": ofe["comercio_id"],
                "titulo": ofe["titulo"],
                "precio_regular_ves": ofe["precio_regular_ves"],
                "precio_oferta_ves": ofe["precio_oferta_ves"],
                "costo_directo_ves": ofe["costo_directo_ves"],
                "descuento_pct": ofe["descuento_pct"],
                "margen_pct": ofe["margen_pct"],
                "stock_inicial": ofe["stock_disponible"],
                "stock_disponible": ofe["stock_disponible"],
                "horario_validez": ofe["horario_validez"],
                "activa": ofe["activa"]
            }

        data_seed["comercios"] = list(existing_c_map.values())
        data_seed["ofertas"] = list(existing_o_map.values())

        with open(SEED_JSON, "w", encoding="utf-8") as f:
            json.dump(data_seed, f, indent=2, ensure_ascii=False)
        print(f"📁 `seed_data.json` sincronizado con {len(data_seed['comercios'])} comercios y {len(data_seed['ofertas'])} ofertas.")
    except Exception as e:
        print(f"⚠️ Advertencia al actualizar seed_data.json: {e}")

def imprimir_auditoria_detallada(ofertas_por_urb):
    """Imprime el desglose y balance por Alcaldía y Urbanización."""
    print("\n" + "=" * 80)
    print("📋 TABLA FORENSE DE CERTIFICACIÓN POR MUNICIPIO Y URBANIZACIÓN (CARACAS)")
    print("=" * 80)
    print(f"{'Municipio / Alcaldía':<20} | {'Urbanización / Sector':<32} | {'Ofertas':<8} | {'Estado':<10}")
    print("-" * 80)

    for urb in URBANIZACIONES_CARACAS:
        nombre = urb["nombre_urb"]
        mun = urb["municipio"]
        qty = ofertas_por_urb.get(nombre, 0)
        status = "✅ CUMPLE (>=40)" if qty >= 40 else "❌ INSUFICIENTE"
        print(f"{mun:<20} | {nombre:<32} | {qty:<8} | {status}")

    print("=" * 80)

def main():
    comercios, ofertas, conteo_urb = generar_datos_caracas()
    sembrar_en_sqlite_y_json(comercios, ofertas)
    imprimir_auditoria_detallada(conteo_urb)
    print("\n🎯 Certificación exitosa: 100% de las 27 urbanizaciones de Caracas cuentan con >= 40 SuperOfertas.")

if __name__ == "__main__":
    main()
