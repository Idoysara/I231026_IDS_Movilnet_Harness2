---
name: venezuela-geo-locator
description: Skill de validación de jerarquía político-territorial de la República Bolivariana de Venezuela (Estados, Municipios, Parroquias oficiales según INE e IGVSB). Permite verificar demarcaciones y transformar coordenadas geodésicas WGS84 a demarcaciones administrativas.
---

# 🗺️ Venezuela Geo-Locator Skill

Este skill proporciona la base de conocimiento y los algoritmos para verificar, clasificar y enriquecer cualquier coordenada GPS dentro del territorio de Venezuela.

## 📌 Jerarquía Político-Territorial Oficial
1. **Nivel 1: Entidad Federal / Estado** (23 Estados, 1 Distrito Capital y Dependencias Federales).
2. **Nivel 2: Municipio** (335 Municipios oficiales).
3. **Nivel 3: Parroquia** (1.136 Parroquias oficiales).

## 🧭 Bounding Box Nacional de Venezuela
- **Latitud Norte:** ~12° 12' 00" N (Cabo San Román, Falcón)
- **Latitud Sur:** ~0° 38' 53" N (Nacimiento del Río Ararí, Amazonas)
- **Longitud Este:** ~-59° 48' 00" W (Punta Playa, Delta Amacuro)
- **Longitud Oeste:** ~-73° 23' 00" W (Nacimiento del Río Intermedio, Zulia)

## 🛠️ Reglas de Uso en Agentes
1. Todo punto fuera del Bounding Box Nacional debe ser catalogado como `ERR_OUTSIDE_VENEZUELA`.
2. Las coordenadas deben compararse contra el bounding box o polígono del Municipio respectivo antes de persistir o confirmar un POI al abonado.
3. Se debe asegurar la correspondencia entre Estado y Municipio declarados.
