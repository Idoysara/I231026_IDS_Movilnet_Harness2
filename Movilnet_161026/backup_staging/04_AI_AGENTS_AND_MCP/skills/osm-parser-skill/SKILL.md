---
name: osm-parser-skill
description: Skill para el procesamiento, extracción y normalización de capas cartográficas y puntos de interés (amenities de salud, farmacias, clínicas, comercio, oficinas) provenientes de fuentes libres OpenStreetMap (archivos .osm.pbf, GeoJSON y consultas Overpass API).
---

# 🌍 OpenStreetMap (OSM) Cartographic Parser Skill

Este skill define las pautas de extracción, mapeo ontológico y normalización de entidades cartográficas libres desde OpenStreetMap hacia la base de datos empresarial de Movilnet.

## 🏷️ Mapeo de Tags OSM a Categorías Empresariales

| Tag OSM Clave | Tag OSM Valor | Categoría Movilnet | Sub-Categoría | Prioridad / Emergencia |
| :--- | :--- | :--- | :--- | :--- |
| `amenity` | `pharmacy` | `farmacia` | `farmacia_cadena` / `independiente` | Normal (o 24/7 si `opening_hours=24/7`) |
| `amenity` | `hospital` / `clinic` | `salud_clinica` | `hospital_privado` / `ambulatorio` | Alta (`emergency_service=1`) |
| `amenity` | `fast_food` | `perros_calientes` / `comida_rapida` | `comida_callejera` | Normal |
| `office` | `company` / `telecommunication` | `edificio_corporativo` | `torre_empresarial` | Normal |
| `shop` | `mall` / `department_store` | `comercio` | `centro_comercial` | Normal |

## 📐 Transformación de Coordenadas
- Toda coordenada entrante debe ser normalizada a proyección esférica estándar **WGS84 (EPSG:4326)** con precisión de 6 decimales (~0.1m en el ecuador).
- Se descartan geometrías nulas o polígonos sin centroide calculable.
