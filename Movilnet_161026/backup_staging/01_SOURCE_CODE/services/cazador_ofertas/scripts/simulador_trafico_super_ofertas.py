#!/usr/bin/env python3
"""
Simulador de Tráfico Masivo, Interacciones B2C y Conciliación Transaccional para Cazador de Ofertas Movilnet.
Cliente 28: Cazador de Ofertas Movilnet (IDS_CORE v5.85.0).

Simula el comportamiento real de abonados móviles en Caracas:
1. Generación de 100 abonados sintéticos Movilnet (0416/0426).
2. Generación de búsquedas geoespaciales por radar (3 anillos de Haversine).
3. Reclamo de cupones con cuota anti-acaparamiento (<= 3 simultáneos).
4. Emisión de tokens dinámicos TOTP de 60s con firma HMAC-SHA256.
5. Canje presencial en terminal POS del comercio.
6. Simulación de intentos de fraude por captura de pantalla (anti-replay).
7. Liquidación de Carrier Billing con Split 20% Movilnet / 80% Comercio.
8. Cálculo formal de métricas financieras y operativas.
"""

import os
import sys
import json
import csv
import time
import random
import uuid
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

CLIENT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

for p in (str(PROJECT_ROOT), str(CLIENT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.application.cazador_service import CazadorApplicationService
from src.domain.invariants import CazadorInvariants, DomainInvariantViolationError
from src.domain.fsm import CouponFSM, IllegalCouponStateTransitionError
from src.domain.entities import EstadoCupon

DATA_DIR = CLIENT_ROOT / "data"
OUTPUT_SIM_JSON = DATA_DIR / "simulacion_trafico_cazador.json"
OUTPUT_SIM_CSV = DATA_DIR / "simulacion_transacciones_cazador.csv"

# Puntos calientes peatonales en Caracas para simulación de usuarios
ZONAS_PEATONALES_CARACAS = [
    {"zona": "Chacao - Plaza El Indio", "lat": 10.4925, "lon": -66.8550},
    {"zona": "Las Mercedes - Tolón / Calle París", "lat": 10.4810, "lon": -66.8610},
    {"zona": "Bulevar Sabana Grande - City Market", "lat": 10.4935, "lon": -66.8810},
    {"zona": "Altamira - Plaza Francia", "lat": 10.4965, "lon": -66.8490},
    {"zona": "La Trinidad - Zona Comercial", "lat": 10.4350, "lon": -66.8520},
    {"zona": "Chuao - CCCT", "lat": 10.4850, "lon": -66.8520},
    {"zona": "El Rosal - Zona Financiera", "lat": 10.4880, "lon": -66.8660}
]

class CazadorTraficoSimulator:
    """Motor de Simulación Sintética de Alta Precisión para Cazador de Ofertas."""

    def __init__(
        self,
        seed_usuarios: int = 100,
        seed_random: int = 42,
        service: Optional[CazadorApplicationService] = None,
        db_session: Optional[Any] = None
    ):
        random.seed(seed_random)
        if service is not None:
            self.service = service
        elif db_session is not None:
            self.service = CazadorApplicationService(db_session=db_session)
        else:
            self.service = CazadorApplicationService()
        self.num_usuarios = seed_usuarios
        self.usuarios = self._generar_abonados_movilnet(seed_usuarios)

    def _generar_abonados_movilnet(self, count: int) -> List[str]:
        """Genera números válidos de Movilnet con prefijos 0416 y 0426."""
        abonados = []
        for i in range(count):
            prefijo = random.choice(["0416", "0426"])
            resto = f"{random.randint(1000000, 9999999)}"
            abonados.append(f"{prefijo}{resto}")
        return abonados

    def ejecutar_simulacion_completa(
        self,
        num_busquedas: int = 250,
        num_intentos_reclamo: int = 120,
        pct_canje: float = 0.70,
        num_intentos_fraude: int = 10
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de vida completo de simulación y genera estadísticas detalladas.
        """
        print(f"🚀 Iniciando Simulación de Tráfico para {len(self.usuarios)} abonados Movilnet...")
        inicio_ts = time.time()

        # 1. Simulación de Búsquedas Radar Haversine
        busquedas_exitosas = 0
        total_ofertas_encontradas = 0
        distribucion_anillos = {"zona_1_inmediata": 0, "zona_2_vecindario": 0, "zona_3_urbana": 0}

        for _ in range(num_busquedas):
            zona = random.choice(ZONAS_PEATONALES_CARACAS)
            # Agregar pequeña dispersión aleatoria (+- 150 metros)
            disp_lat = zona["lat"] + random.uniform(-0.0015, 0.0015)
            disp_lon = zona["lon"] + random.uniform(-0.0015, 0.0015)

            res = self.service.buscar_ofertas_radar(user_lat=disp_lat, user_lon=disp_lon, max_distancia_m=3000.0)
            if res.get("success"):
                busquedas_exitosas += 1
                total_ofertas_encontradas += res.get("total_comercios_en_rango", 0)
                anillos = res.get("anillos", {})
                distribucion_anillos["zona_1_inmediata"] += len(anillos.get("zona_1_inmediata", []))
                distribucion_anillos["zona_2_vecindario"] += len(anillos.get("zona_2_vecindario", []))
                distribucion_anillos["zona_3_urbana"] += len(anillos.get("zona_3_urbana", []))

        # 2. Simulación de Reclamo de Cupones Dinámicos
        ofertas_disponibles = [o_id for o_id, o in self.service.ofertas.items() if o.activa and o.stock_disponible > 0]
        cupones_emitidos = []
        reclamos_exitosos = 0
        reclamos_rechazados_cuota = 0

        for _ in range(num_intentos_reclamo):
            msisdn = random.choice(self.usuarios)
            oferta_id = random.choice(ofertas_disponibles)
            try:
                rec = self.service.reclamar_cupon(oferta_id=oferta_id, msisdn=msisdn)
                if rec.get("success"):
                    reclamos_exitosos += 1
                    cupones_emitidos.append(rec)
            except DomainInvariantViolationError as de:
                if "Límite de acaparamiento" in str(de):
                    reclamos_rechazados_cuota += 1

        # 3. Simulación de Canje Presencial en Caja POS y Facturación
        canjes_exitosos = 0
        canjes_fallidos = 0
        transacciones_billing = []
        volumen_total_ves = 0.0
        comision_movilnet_total_ves = 0.0
        neto_comercios_total_ves = 0.0

        cupones_a_canjear = random.sample(cupones_emitidos, int(len(cupones_emitidos) * pct_canje))
        cupones_efectivamente_canjeados = []

        for rec in cupones_a_canjear:
            cup = rec["cupon"]
            ofe = rec["oferta"]
            cupon_id = cup["uuid"]
            msisdn = cup["usuario_msisdn"]
            comercio_id = cup["comercio_id"]
            firma = cup["firma_hmac"]

            try:
                res_canje = self.service.canjear_cupon(
                    cupon_id=cupon_id,
                    msisdn=msisdn,
                    comercio_id=comercio_id,
                    firma_hmac=firma
                )
                if res_canje.get("success"):
                    canjes_exitosos += 1
                    cupones_efectivamente_canjeados.append(rec)
                    precio_venta = ofe["precio_oferta_ves"]
                    # Simular cobro carrier billing / liquidación
                    idemp_key = f"IDEMP-SIM-{cupon_id}-{int(time.time()*1000)%100000}"
                    res_tx = self.service.procesar_carrier_billing(
                        msisdn=msisdn,
                        monto_ves=precio_venta,
                        idempotency_key=idemp_key
                    )
                    tx_data = res_tx.get("transaccion", {})
                    comision_telco = tx_data.get("comision_telco_ves", round(precio_venta * 0.20, 2))
                    neto_comercio = tx_data.get("neto_comercio_ves", round(precio_venta * 0.80, 2))
                    
                    volumen_total_ves += precio_venta
                    comision_movilnet_total_ves += comision_telco
                    neto_comercios_total_ves += neto_comercio

                    transacciones_billing.append({
                        "transaccion_id": tx_data.get("id", f"TX-{uuid.uuid4().hex[:8].upper()}"),
                        "cupon_id": cupon_id,
                        "msisdn": msisdn,
                        "comercio_id": comercio_id,
                        "oferta_titulo": ofe["titulo"],
                        "monto_total_ves": precio_venta,
                        "comision_movilnet_ves": comision_telco,
                        "neto_comercio_ves": neto_comercio,
                        "split_ratio": "20% / 80%",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
            except Exception as ex:
                canjes_fallidos += 1

        # 4. Simulación de Intentos de Fraude (Replay / Captura de Pantalla Reutilizada)
        fraudes_detectados_y_bloqueados = 0
        fraudes_no_detectados = 0
        intentos_reales_fraude = 0

        # Intentar re-canjear cupones ya canjeados
        cupones_para_fraude = cupones_efectivamente_canjeados if cupones_efectivamente_canjeados else cupones_a_canjear
        if cupones_para_fraude:
            for i in range(num_intentos_fraude):
                rec = cupones_para_fraude[i % len(cupones_para_fraude)]
                intentos_reales_fraude += 1
                cup = rec["cupon"]
                try:
                    self.service.canjear_cupon(
                        cupon_id=cup["uuid"],
                        msisdn=cup["usuario_msisdn"],
                        comercio_id=cup["comercio_id"],
                        firma_hmac=cup["firma_hmac"]
                    )
                    fraudes_no_detectados += 1
                except (DomainInvariantViolationError, IllegalCouponStateTransitionError):
                    # Correctamente bloqueado por FSM o Bóveda anti-replay
                    fraudes_detectados_y_bloqueados += 1

        duracion_segundos = round(time.time() - inicio_ts, 2)

        # 5. Consolidación de Métricas y KPIs
        kpis = {
            "metadata_simulacion": {
                "fecha_ejecucion": time.strftime("%Y-%m-%d %H:%M:%S"),
                "duracion_segundos": duracion_segundos,
                "territorio": "Gran Caracas, Venezuela",
                "total_abonados_simulados": len(self.usuarios)
            },
            "metricas_adquisicion_radar": {
                "total_busquedas_radar": num_busquedas,
                "busquedas_exitosas": busquedas_exitosas,
                "total_impactos_ofertas": total_ofertas_encontradas,
                "promedio_ofertas_por_busqueda": round(total_ofertas_encontradas / max(1, num_busquedas), 2),
                "distribucion_anillos": distribucion_anillos
            },
            "metricas_conversion_cupones": {
                "intentos_reclamo": num_intentos_reclamo,
                "cupones_emitidos_exitosos": reclamos_exitosos,
                "reclamos_bloqueados_por_cuota_max_3": reclamos_rechazados_cuota,
                "tasa_conversion_reclamo_pct": round((reclamos_exitosos / max(1, num_intentos_reclamo)) * 100, 2),
                "total_cupones_canjeados_en_pos": canjes_exitosos,
                "tasa_redencion_pos_pct": round((canjes_exitosos / max(1, reclamos_exitosos)) * 100, 2)
            },
            "seguridad_y_blindaje_anti_fraude": {
                "intentos_ataque_replay_simulados": intentos_reales_fraude or num_intentos_fraude,
                "ataques_bloqueados_por_boveda_y_fsm": fraudes_detectados_y_bloqueados,
                "ataques_exitosos_fuga": fraudes_no_detectados,
                "efectividad_cortafuegos_pct": round((fraudes_detectados_y_bloqueados / max(1, intentos_reales_fraude or num_intentos_fraude)) * 100, 2)
            },
            "balance_economico_y_split_transaccional": {
                "volumen_bruto_facturado_ves": round(volumen_total_ves, 2),
                "ingreso_comision_movilnet_ves_20pct": round(comision_movilnet_total_ves, 2),
                "ingreso_neto_comercios_ves_80pct": round(neto_comercios_total_ves, 2),
                "total_transacciones_asentadas": len(transacciones_billing),
                "ticket_promedio_cupon_ves": round(volumen_total_ves / max(1, canjes_exitosos), 2)
            },
            "transacciones_recientes": transacciones_billing
        }

        return kpis

    def exportar_datos(self, resultado_simulacion: Dict[str, Any]) -> Tuple[Path, Path]:
        """Exporta los resultados a JSON y CSV en el directorio data/."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 1. JSON
        with open(OUTPUT_SIM_JSON, "w", encoding="utf-8") as fj:
            json.dump(resultado_simulacion, fj, indent=2, ensure_ascii=False)

        # 2. CSV
        txs = resultado_simulacion.get("transacciones_recientes", [])
        if txs:
            headers = list(txs[0].keys())
            with open(OUTPUT_SIM_CSV, "w", newline="", encoding="utf-8") as fc:
                writer = csv.DictWriter(fc, fieldnames=headers)
                writer.writeheader()
                for tx in txs:
                    writer.writerow(tx)

        return OUTPUT_SIM_JSON, OUTPUT_SIM_CSV

def main():
    parser = argparse.ArgumentParser(description="Simulador de Tráfico y Datos Masivos para Cazador de Ofertas")
    parser.add_argument("--run", action="store_true", help="Ejecutar simulación estándar de tráfico")
    parser.add_argument("--usuarios", type=int, default=100, help="Número de abonados Movilnet a simular")
    parser.add_argument("--busquedas", type=int, default=200, help="Número de búsquedas GPS radar")
    parser.add_argument("--reclamos", type=int, default=80, help="Número de intentos de reclamo")
    parser.add_argument("--export", action="store_true", help="Exportar datos a JSON y CSV")
    parser.add_argument("--test", action="store_true", help="Ejecutar auto-verificación formal")

    args = parser.parse_args()

    simulator = CazadorTraficoSimulator(seed_usuarios=args.usuarios)

    if args.test:
        print("🧪 Ejecutando verificación de aserciones del simulador...")
        res = simulator.ejecutar_simulacion_completa(num_busquedas=20, num_intentos_reclamo=10, num_intentos_fraude=3)
        assert res["metricas_adquisicion_radar"]["busquedas_exitosas"] > 0
        assert res["seguridad_y_blindaje_anti_fraude"]["efectividad_cortafuegos_pct"] == 100.0
        assert res["balance_economico_y_split_transaccional"]["volumen_bruto_facturado_ves"] > 0
        print("✅ Simulación formal verificada con 100% de éxito y cero fallas.")
        return

    # Ejecución por defecto o con --run
    res = simulator.ejecutar_simulacion_completa(
        num_busquedas=args.busquedas,
        num_intentos_reclamo=args.reclamos,
        pct_canje=0.75,
        num_intentos_fraude=8
    )

    p_json, p_csv = simulator.exportar_datos(res)

    print("\n" + "="*70)
    print("📊 RESULTADOS EJECUTIVOS DE LA SIMULACIÓN DE TRÁFICO")
    print("="*70)
    kpis_rad = res["metricas_adquisicion_radar"]
    kpis_cup = res["metricas_conversion_cupones"]
    kpis_sec = res["seguridad_y_blindaje_anti_fraude"]
    kpis_eco = res["balance_economico_y_split_transaccional"]

    print(f"📍 Búsquedas Radar Realizadas:        {kpis_rad['total_busquedas_radar']} (Impactos: {kpis_rad['total_impactos_ofertas']})")
    print(f"🏷️ Cupones Emitidos con Éxito:        {kpis_cup['cupones_emitidos_exitosos']}")
    print(f"🛑 Reclamos Bloqueados por Cuota:     {kpis_cup['reclamos_bloqueados_por_cuota_max_3']}")
    print(f"🏬 Canjes Presenciales en Caja POS:   {kpis_cup['total_cupones_canjeados_en_pos']} ({kpis_cup['tasa_redencion_pos_pct']}% tasa de redención)")
    print(f"🛡️ Intentos de Doble Gasto Neutraliz: {kpis_sec['ataques_bloqueados_por_boveda_y_fsm']}/{kpis_sec['intentos_ataque_replay_simulados']} ({kpis_sec['efectividad_cortafuegos_pct']}% blindaje)")
    print(f"💰 Volumen Bruto Facturado:           {kpis_eco['volumen_bruto_facturado_ves']:,.2f} Bs.")
    print(f"📱 Split Movilnet (20% Carrier Bill): {kpis_eco['ingreso_comision_movilnet_ves_20pct']:,.2f} Bs.")
    print(f"🏪 Split Comercios Aliados (80%):     {kpis_eco['ingreso_neto_comercios_ves_80pct']:,.2f} Bs.")
    print(f"📁 Datasets Exportados:")
    print(f"   - JSON: {p_json} ({p_json.stat().st_size} bytes)")
    print(f"   - CSV:  {p_csv} ({p_csv.stat().st_size} bytes)")
    print("="*70)

if __name__ == "__main__":
    main()
