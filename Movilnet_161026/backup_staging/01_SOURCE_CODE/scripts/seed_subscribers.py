#!/usr/bin/env python3
"""
seed_subscribers.py — Generador y Poblador Masivo Sintético de Abonados
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.

Genera poblaciones con distribución realista para pruebas de carga:
- Prefijos venezolanos oficiales: 0416 (70%) y 0426 (30%)
- 95% casos nominales (activos, al día)
- 5% casos de borde (SIM Swap < 24h, moras de facturación, bloqueos por hurto, riesgo churn)
"""

import sys
import uuid
import random
import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import DatabaseConnectionManager, compute_blind_index

PLAN_IDS = [
    "PLAN_10GB_4GMAX", "PLAN_20GB_4GMAX", "PLAN_5GB_BASICO",
    "PLAN_3GB_LIGERO", "PLAN_1GB_SOCIAL", "PLAN_50GB_CORP",
    "PLAN_POSPAGO_PLUS", "PLAN_ESTUDIANTE_CONECTA"
]

BANK_CODES = ["0102", "0105", "0108", "0134", "0114", "0172", "0163"]

CELL_IDS = [
    "CAR-CCS-ENB-001", "CAR-CCS-ENB-042", "MIR-LOS-ENB-015",
    "ZUL-MAR-ENB-102", "CAR-VAL-ENB-088", "LAR-BAR-ENB-034"
]


def seed_subscribers(total_count: int = 1000, batch_size: int = 500, clean: bool = False):
    print(f"🚀 Iniciando Sembrado de {total_count:,} Abonados Movilnet...")
    t0 = time.time()
    
    mgr = DatabaseConnectionManager()
    
    with mgr.get_cursor() as cur:
        if clean:
            print("  🧹 Limpiando registros previos...")
            if mgr.engine_type == "POSTGRESQL_15":
                cur.execute("TRUNCATE TABLE usage_records_cdr, financial_transactions, balances_and_quotas, churn_metrics, eir_security_events, telco_lines, subscribers CASCADE;")
            else:
                cur.execute("DELETE FROM usage_records_cdr;")
                cur.execute("DELETE FROM financial_transactions;")
                cur.execute("DELETE FROM balances_and_quotas;")
                cur.execute("DELETE FROM churn_metrics;")
                cur.execute("DELETE FROM eir_security_events;")
                cur.execute("DELETE FROM telco_lines;")
                cur.execute("DELETE FROM subscribers;")
        else:
            cur.execute("SELECT count(*) FROM subscribers;")
            row = cur.fetchone()
            existing_offset = row[0] if row else 0
    
    subscribers_data = []
    lines_data = []
    balances_data = []
    cdrs_data = []
    fts_data = []
    churn_data = []
    eir_data = []
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    created = 0
    while created < total_count:
        chunk_size = min(batch_size, total_count - created)
        
        subs_chunk = []
        lines_chunk = []
        bals_chunk = []
        
        for i in range(chunk_size):
            idx = (existing_offset if not clean else 0) + created + i + 1
            prefix = "0416" if random.random() < 0.70 else "0426"
            num_suffix = f"{idx:07d}"
            msisdn = f"{prefix}{num_suffix}"
            
            sub_id = str(uuid.uuid4())
            cid_num = 10000000 + idx
            cid = f"V-{cid_num}"
            blind_cid = compute_blind_index(cid)
            
            plan_id = random.choice(PLAN_IDS)
            
            # Casos de borde (5%)
            is_edge = random.random() < 0.05
            
            if is_edge:
                case_type = random.choice(["SIM_SWAP_RECENT", "DEBT_OVERDUE", "THEFT_SUSPENDED", "CHURN_RISK"])
                if case_type == "SIM_SWAP_RECENT":
                    last_swap = (now - timedelta(hours=random.randint(1, 12))).isoformat()
                    line_status = "ACTIVO"
                    days_overdue = 0
                    bal_ves = random.uniform(50.0, 500.0)
                elif case_type == "DEBT_OVERDUE":
                    last_swap = (now - timedelta(days=90)).isoformat()
                    line_status = "SUSPENDIDO_SALDO"
                    days_overdue = random.randint(15, 60)
                    bal_ves = 0.0
                elif case_type == "THEFT_SUSPENDED":
                    last_swap = (now - timedelta(days=120)).isoformat()
                    line_status = "BLOQUEADO_ROBO"
                    days_overdue = 0
                    bal_ves = random.uniform(10.0, 80.0)
                    eir_data.append((
                        f"TKT-EIR-{idx:06d}", msisdn, f"35{msisdn[-10:]}0", f"73406{msisdn[-10:]}",
                        "THEFT_LOCK", "Denuncia de hurto procesada por canal de emergencias",
                        "ANTIGRAVITY_MCP_AGENT", f"CICPC-DEN-{idx:04d}", now_iso
                    ))
                else:  # CHURN_RISK
                    last_swap = (now - timedelta(days=60)).isoformat()
                    line_status = "ACTIVO"
                    days_overdue = 5
                    bal_ves = random.uniform(5.0, 20.0)
                    churn_data.append((
                        str(uuid.uuid4()), msisdn, 88.50, "CRITICAL_RISK", 45, 3, 72.50,
                        "BONUS_PACK_RELOAD", "RET-4GMAX-30", now_iso
                    ))
            else:
                last_swap = (now - timedelta(days=random.randint(35, 300))).isoformat()
                line_status = "ACTIVO"
                days_overdue = 0
                bal_ves = round(random.uniform(100.0, 1500.0), 2)
            
            subs_chunk.append((
                sub_id, blind_cid, "NATURAL", "ACTIVO" if line_status != "BLOQUEADO_ROBO" else "SUSPENDIDO",
                "PREPAGO_MASIVO", now_iso, now_iso
            ))
            
            imsi = f"73406{msisdn[-10:]}"
            iccid = f"895806{msisdn[-10:]}01"
            imei = f"35{msisdn[-10:]}0"
            cell = random.choice(CELL_IDS)
            
            lines_chunk.append((
                msisdn, sub_id, imsi, iccid, imei, plan_id, cell, line_status, last_swap, now_iso, now_iso
            ))
            
            bal_id = str(uuid.uuid4())
            quota_mb = 10240 if "10GB" in plan_id else (20480 if "20GB" in plan_id else 5120)
            rem_mb = int(quota_mb * random.uniform(0.1, 0.9)) if line_status == "ACTIVO" else 0
            
            bals_chunk.append((
                msisdn, bal_id, bal_ves, round(bal_ves / 36.85, 2), rem_mb, quota_mb,
                "2026-10-31", days_overdue, now_iso
            ))
            
            # Generar CDR y Transacción de muestra para los primeros 200 abonados
            if idx <= 200:
                cdrs_data.append((
                    now_iso, str(uuid.uuid4()), msisdn, "DATA_4G", random.randint(5000000, 50000000), 0, cell, "SUCCESS"
                ))
                fts_data.append((
                    now_iso, f"REF-SEED-{idx:06d}", msisdn, random.choice(BANK_CODES),
                    bal_ves, round(bal_ves / 36.85, 2), 36.85, "PAGO_MOVIL_C2P", "COMPLETADO",
                    f"{cid[:3]}***{cid[-3:]}"
                ))

        # Inserción en lote
        with mgr.get_cursor() as cur:
            param_marker = "%s" if mgr.engine_type == "POSTGRESQL_15" else "?"
            
            p_sub = f"INSERT INTO subscribers VALUES ({','.join([param_marker]*7)});"
            p_line = f"INSERT INTO telco_lines VALUES ({','.join([param_marker]*11)});"
            p_bal = f"INSERT INTO balances_and_quotas VALUES ({','.join([param_marker]*9)});"
            
            cur.executemany(p_sub, subs_chunk)
            cur.executemany(p_line, lines_chunk)
            cur.executemany(p_bal, bals_chunk)

        created += chunk_size
        print(f"  • Insertadas {created:,}/{total_count:,} líneas ({created/total_count*100:.1f}%)")

    # Inserción de CDRs, Finanzas, Churn y EIR
    with mgr.get_cursor() as cur:
        marker = "%s" if mgr.engine_type == "POSTGRESQL_15" else "?"
        if cdrs_data:
            cur.executemany(f"INSERT INTO usage_records_cdr VALUES ({','.join([marker]*8)});", cdrs_data)
        if fts_data:
            cur.executemany(f"INSERT INTO financial_transactions VALUES ({','.join([marker]*10)});", fts_data)
        if churn_data:
            cur.executemany(f"INSERT INTO churn_metrics VALUES ({','.join([marker]*10)});", churn_data)
        if eir_data:
            cur.executemany(f"INSERT INTO eir_security_events VALUES ({','.join([marker]*9)});", eir_data)

    duration = time.time() - t0
    rate = total_count / duration if duration > 0 else total_count
    print(f"\n✅ Sembrado Completado con Éxito:")
    print(f"   • Total Abonados y Líneas: {total_count:,}")
    print(f"   • CDRs Generados:           {len(cdrs_data):,}")
    print(f"   • Transacciones C2P:        {len(fts_data):,}")
    print(f"   • Incidentes EIR / Churn:   {len(eir_data) + len(churn_data):,}")
    print(f"   • Tiempo Total:             {duration:.2f} s ({rate:,.0f} registros/segundo)\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sembrador masivo sintético de abonados Movilnet")
    parser.add_argument("--count", type=int, default=1000, help="Cantidad de abonados a generar")
    parser.add_argument("--batch-size", type=int, default=500, help="Tamaño de lote de inserción")
    parser.add_argument("--clean", action="store_true", help="Limpiar registros previos antes de sembrar")
    args = parser.parse_args()
    
    seed_subscribers(total_count=args.count, batch_size=args.batch_size, clean=args.clean)
