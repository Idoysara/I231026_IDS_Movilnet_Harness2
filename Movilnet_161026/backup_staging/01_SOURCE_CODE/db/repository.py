"""
repository.py — Capa DAO (Data Access Object) de Persistencia
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Conforme a estándares TM Forum ODA (TMF620, TMF622, TMF632, TMF676, TMF678, TMF680)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from db.connection import DatabaseConnectionManager, compute_blind_index


class MovilnetRepository:
    """Repositorio empresarial para operaciones CRUD de alta concurrencia y baja latencia."""

    def __init__(self):
        self.db = DatabaseConnectionManager()

    def _execute(self, cur, sql: str, params: tuple = ()):
        if self.db.engine_type == "POSTGRESQL_15":
            sql_adapted = sql.replace("?", "%s")
            cur.execute(sql_adapted, params)
        else:
            cur.execute(sql, params)

    def _row_to_dict(self, row) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        if hasattr(row, "keys"):
            return {k: row[k] for k in row.keys()}
        return dict(row)

    # =========================================================================
    # TMF632: IDENTIDAD Y ABONADOS (SUBSCRIBERS & BLIND INDEX)
    # =========================================================================

    def get_subscriber_by_cid(self, cid: str) -> Optional[Dict[str, Any]]:
        """Busca un abonado por Cédula de Identidad en O(1) usando Blind Index determinista."""
        blind_idx = compute_blind_index(cid)
        sql = "SELECT * FROM subscribers WHERE blind_index_cid = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (blind_idx,))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def get_subscriber_by_msisdn(self, msisdn: str) -> Optional[Dict[str, Any]]:
        """Obtiene el titular de una línea mediante JOIN entre subscribers y telco_lines."""
        clean_phone = msisdn.strip()
        sql = """
        SELECT s.*, l.msisdn, l.plan_id, l.status AS line_status, l.cell_id, l.last_sim_swap_at
        FROM subscribers s
        INNER JOIN telco_lines l ON s.id = l.subscriber_id
        WHERE l.msisdn = ? LIMIT 1;
        """
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (clean_phone,))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def get_lines_by_subscriber_id(self, subscriber_id: str) -> List[Dict[str, Any]]:
        """Retorna todas las líneas telefónicas asociadas a un abonado."""
        sql = "SELECT * FROM telco_lines WHERE subscriber_id = ? ORDER BY created_at ASC;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (subscriber_id.strip(),))
            rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def create_subscriber_with_line(
        self,
        cid: str,
        msisdn: str,
        plan_id: str,
        customer_type: str = "NATURAL",
        segment: str = "PREPAGO_MASIVO",
        balance_ves: float = 0.0,
        quota_mb: int = 10240,
        imsi: Optional[str] = None,
        iccid: Optional[str] = None,
        imei: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crea atómicamente un abonado con su línea telefónica y saldo inicial."""
        sub_id = str(uuid.uuid4())
        blind_idx = compute_blind_index(cid)
        now_iso = datetime.now(timezone.utc).isoformat()
        
        sim_imsi = imsi or f"73406{msisdn[-10:]}"
        sim_iccid = iccid or f"895806{msisdn[-10:]}01"
        term_imei = imei or f"35{msisdn[-10:]}0"

        with self.db.get_cursor() as cur:
            # 1. Insertar Abonado
            sql_sub = """
            INSERT INTO subscribers (id, blind_index_cid, customer_type, status, segment, created_at, updated_at)
            VALUES (?, ?, ?, 'ACTIVO', ?, ?, ?);
            """
            self._execute(cur, sql_sub, (sub_id, blind_idx, customer_type, segment, now_iso, now_iso))

            # 2. Insertar Línea
            sql_line = """
            INSERT INTO telco_lines (msisdn, subscriber_id, imsi, iccid, imei, plan_id, cell_id, status, last_sim_swap_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'CAR-CCS-ENB-001', 'ACTIVO', ?, ?, ?);
            """
            self._execute(cur, sql_line, (msisdn, sub_id, sim_imsi, sim_iccid, term_imei, plan_id, now_iso, now_iso, now_iso))

            # 3. Insertar Saldo Inicial
            bal_id = str(uuid.uuid4())
            sql_bal = """
            INSERT INTO balances_and_quotas (msisdn, id, balance_ves, balance_usd_equiv, remaining_data_mb, total_quota_mb, billing_cutoff_date, days_overdue, last_sync_at)
            VALUES (?, ?, ?, ?, ?, ?, '2026-10-31', 0, ?);
            """
            self._execute(cur, sql_bal, (msisdn, bal_id, balance_ves, round(balance_ves / 36.85, 2), quota_mb, quota_mb, now_iso))

        return {
            "success": True,
            "subscriber_id": sub_id,
            "msisdn": msisdn,
            "blind_index_cid": blind_idx,
            "plan_id": plan_id,
            "status": "ACTIVO"
        }

    # =========================================================================
    # TMF622: INVENTARIO DE LÍNEAS (TELCO LINES)
    # =========================================================================

    def get_line_details(self, msisdn: str) -> Optional[Dict[str, Any]]:
        """Retorna detalles técnicos de la línea (IMSI, IMEI, Cell ID, SIM Swap)."""
        sql = "SELECT * FROM telco_lines WHERE msisdn = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (msisdn.strip(),))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def update_line_status(self, msisdn: str, new_status: str) -> bool:
        """Actualiza el estado operacional de la línea (ej. BLOQUEADO_ROBO)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = "UPDATE telco_lines SET status = ?, updated_at = ? WHERE msisdn = ?;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (new_status, now_iso, msisdn.strip()))
            return cur.rowcount > 0

    # =========================================================================
    # TMF678: SALDOS Y BOLSAS DE NAVEGACIÓN (BALANCES & QUOTAS)
    # =========================================================================

    def get_balance_and_quotas(self, msisdn: str) -> Optional[Dict[str, Any]]:
        """Consulta en O(1) el saldo disponible y cuota de megas de un abonado."""
        sql = "SELECT * FROM balances_and_quotas WHERE msisdn = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (msisdn.strip(),))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def update_balance_and_quotas(
        self,
        msisdn: str,
        ves_delta: float = 0.0,
        usd_delta: float = 0.0,
        mb_delta: int = 0
    ) -> Dict[str, Any]:
        """Ajusta atómicamente el saldo monetario o cuota de datos por recargas o consumos."""
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        UPDATE balances_and_quotas
        SET balance_ves = MAX(0.0, balance_ves + ?),
            balance_usd_equiv = MAX(0.0, balance_usd_equiv + ?),
            remaining_data_mb = MAX(0, remaining_data_mb + ?),
            last_sync_at = ?
        WHERE msisdn = ?;
        """
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (ves_delta, usd_delta, mb_delta, now_iso, msisdn.strip()))
            updated = cur.rowcount > 0

        current = self.get_balance_and_quotas(msisdn)
        return {
            "success": updated,
            "msisdn": msisdn,
            "new_balance_ves": current.get("balance_ves") if current else 0.0,
            "new_remaining_mb": current.get("remaining_data_mb") if current else 0
        }

    # =========================================================================
    # TMF620: CATÁLOGO DE PRODUCTOS (PRODUCT PLANS)
    # =========================================================================

    def get_active_plans(self) -> List[Dict[str, Any]]:
        """Retorna todos los planes comerciales vigentes homologados."""
        sql = "SELECT * FROM product_plans WHERE is_active = 1 ORDER BY price_usd ASC;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql)
            rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_plan_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Busca la ficha técnica de un plan comercial específico."""
        sql = "SELECT * FROM product_plans WHERE plan_id = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (plan_id.strip(),))
            row = cur.fetchone()
            return self._row_to_dict(row)

    # =========================================================================
    # TMF676: FINTECH, BANCOS SUDEBAN Y PAGOS C2P
    # =========================================================================

    def get_sudeban_banks(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista las instituciones bancarias autorizadas para Pago Móvil C2P."""
        sql = "SELECT * FROM banks_sudeban"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY bank_code ASC;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql)
            rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def is_reference_duplicate(self, reference_id: str) -> bool:
        """Verifica en O(1) si una referencia bancaria ya fue conciliada previamente."""
        sql = "SELECT 1 FROM financial_transactions WHERE reference_id = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (reference_id.strip(),))
            return cur.fetchone() is not None

    def record_c2p_transaction(
        self,
        reference_id: str,
        msisdn: str,
        bank_code: str,
        amount_ves: float,
        amount_usd: float,
        bcv_rate: float,
        payer_cid: str,
        status: str = "COMPLETADO"
    ) -> Dict[str, Any]:
        """Registra una transacción C2P inmutable con chequeo de unicidad."""
        clean_ref = reference_id.strip()
        if self.is_reference_duplicate(clean_ref):
            return {
                "success": False,
                "error_code": "ERR_DUPLICATE_REFERENCE",
                "message": f"La referencia '{clean_ref}' ya fue procesada anteriormente."
            }

        masked_cid = payer_cid[:3] + "***" + payer_cid[-3:] if len(payer_cid) > 6 else payer_cid
        now_iso = datetime.now(timezone.utc).isoformat()

        sql = """
        INSERT INTO financial_transactions (
            executed_at, reference_id, msisdn, bank_code, amount_ves,
            amount_usd, bcv_rate_applied, payment_method, status, payer_cid_masked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PAGO_MOVIL_C2P', ?, ?);
        """
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (
                now_iso, clean_ref, msisdn.strip(), bank_code.strip(),
                amount_ves, amount_usd, bcv_rate, status, masked_cid
            ))

        # Acreditar saldo automáticamente al abonado si el estado es completado
        if status == "COMPLETADO":
            self.update_balance_and_quotas(msisdn, ves_delta=amount_ves, usd_delta=amount_usd)

        return {
            "success": True,
            "reference_id": clean_ref,
            "status": status,
            "amount_ves": amount_ves,
            "executed_at": now_iso
        }

    # =========================================================================
    # TMF678: REGISTROS DE DETALLE DE LLAMADA Y DATOS (CDRs)
    # =========================================================================

    def record_cdr_usage(
        self,
        msisdn: str,
        event_type: str,
        data_volume_bytes: int = 0,
        duration_seconds: int = 0,
        cell_id: str = "CAR-CCS-ENB-001",
        status_code: str = "SUCCESS"
    ) -> Dict[str, Any]:
        """Inserta un registro de consumo en la tabla particionada de CDRs."""
        cdr_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        INSERT INTO usage_records_cdr (event_timestamp, id, msisdn, event_type, data_volume_bytes, duration_seconds, cell_id, status_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (now_iso, cdr_id, msisdn.strip(), event_type, data_volume_bytes, duration_seconds, cell_id, status_code))

        # Si es consumo de datos, descontar de la bolsa restante
        if event_type == "DATA_4G" and data_volume_bytes > 0:
            mb_used = int(data_volume_bytes / (1024 * 1024))
            if mb_used > 0:
                self.update_balance_and_quotas(msisdn, mb_delta=-mb_used)

        return {"success": True, "cdr_id": cdr_id, "timestamp": now_iso}

    # =========================================================================
    # TMF680: RETENCIÓN, CHURN PREDICTIVO Y SEGURIDAD EIR
    # =========================================================================

    def save_churn_evaluation(
        self,
        msisdn: str,
        churn_score: float,
        risk_segment: str,
        days_without_recharge: int,
        complaints_count_30d: int,
        data_drop_pct: float,
        recommended_action: str,
        coupon_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Almacena la evaluación analítica del suscriptor para campañas de retención."""
        eval_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        INSERT INTO churn_metrics (
            id, msisdn, churn_score, risk_segment, days_without_recharge,
            complaints_count_30d, data_drop_pct, recommended_action, coupon_code_offered, evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (
                eval_id, msisdn.strip(), churn_score, risk_segment,
                days_without_recharge, complaints_count_30d, data_drop_pct,
                recommended_action, coupon_code, now_iso
            ))
        return {"success": True, "eval_id": eval_id, "risk_segment": risk_segment}

    def get_latest_churn_metric(self, msisdn: str) -> Optional[Dict[str, Any]]:
        """Recupera la evaluación analítica de churn más reciente para una línea."""
        sql = "SELECT * FROM churn_metrics WHERE msisdn = ? ORDER BY evaluated_at DESC LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (msisdn.strip(),))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def get_churn_metrics_history(self, msisdn: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recupera el historial cronológico de evaluaciones de churn de un abonado."""
        sql = "SELECT * FROM churn_metrics WHERE msisdn = ? ORDER BY evaluated_at DESC LIMIT ?;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (msisdn.strip(), limit))
            rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_subscriber_churn_features(self, msisdn: str) -> Dict[str, Any]:
        """Extrae y consolida las características operacionales del abonado para el modelo predictivo de Churn."""
        clean_phone = msisdn.strip()
        line = self.get_line_details(clean_phone)
        sub = self.get_subscriber_by_msisdn(clean_phone)
        bal = self.get_balance_and_quotas(clean_phone)
        latest_churn = self.get_latest_churn_metric(clean_phone)
        
        # Calcular antigüedad estimada en meses
        antiquity_months = 12.0
        if line and line.get("created_at"):
            try:
                created = datetime.fromisoformat(line["created_at"].replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                delta_days = (now - created).days
                antiquity_months = max(1.0, round(delta_days / 30.4, 1))
            except Exception:
                antiquity_months = 12.0

        # Obtener precio del plan
        plan_price = 10.0
        if line and line.get("plan_id"):
            plan = self.get_plan_by_id(line["plan_id"])
            if plan:
                plan_price = float(plan.get("price_usd", 10.0))

        # Detectar si el terminal es 4G (IMEI TAC o celda)
        has_4g = 1
        if line and line.get("imei"):
            imei_str = str(line["imei"])
            has_4g = 1 if not imei_str.startswith("3500") else 0

        # Días sin recarga, reclamos y caída de datos
        days_without_recharge = 5
        complaints_count = 0
        data_drop = 0.0
        if latest_churn:
            days_without_recharge = int(latest_churn.get("days_without_recharge", 5))
            complaints_count = int(latest_churn.get("complaints_count_30d", 0))
            data_drop = float(latest_churn.get("data_drop_pct", 0.0))
        elif bal and bal.get("days_overdue", 0) > 0:
            days_without_recharge = int(bal["days_overdue"])

        # Promedio mensual de recargas VES
        avg_recharge = 450.0
        if bal:
            current_ves = float(bal.get("balance_ves", 0.0))
            if current_ves > 0:
                avg_recharge = max(150.0, current_ves * 1.5)

        return {
            "msisdn": clean_phone,
            "antiquity_months": antiquity_months,
            "days_without_recharge": days_without_recharge,
            "avg_monthly_recharge_ves": avg_recharge,
            "data_usage_trend_pct": data_drop,
            "complaints_count_30d": complaints_count,
            "plan_tier_price_usd": plan_price,
            "has_4gmax_device": has_4g,
            "failed_transactions_count": 0,
            "subscriber_id": sub.get("id") if sub else None,
            "plan_id": line.get("plan_id") if line else None
        }


    def record_eir_security_lock(
        self,
        ticket_id: str,
        msisdn: str,
        imei: str,
        imsi: str,
        event_type: str,
        reason: str,
        agent: str = "ANTIGRAVITY_MCP_AGENT",
        police_report: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registra un bloqueo formal en la lista negra del Equipment Identity Register."""
        now_iso = datetime.now(timezone.utc).isoformat()
        sql = """
        INSERT INTO eir_security_events (ticket_id, msisdn, imei, imsi, event_type, reason, reporting_agent, police_report_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (
                ticket_id.strip(), msisdn.strip(), imei.strip(), imsi.strip(),
                event_type, reason, agent, police_report, now_iso
            ))
            
        # Actualizar el estado de la línea a BLOQUEADO_ROBO
        if event_type == "THEFT_LOCK":
            self.update_line_status(msisdn, "BLOQUEADO_ROBO")

        return {"success": True, "ticket_id": ticket_id, "status": "LOCKED_IN_EIR"}

    def is_imei_blacklisted(self, imei: str) -> bool:
        """Verifica en O(1) si un IMEI se encuentra bloqueado en el Equipment Identity Register (EIR)."""
        sql = "SELECT 1 FROM eir_security_events WHERE imei = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (imei.strip(),))
            return cur.fetchone() is not None

    def get_eir_event_by_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un evento de seguridad EIR por su identificador de ticket."""
        sql = "SELECT * FROM eir_security_events WHERE ticket_id = ? LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (ticket_id.strip(),))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def get_eir_event_by_imei(self, imei: str) -> Optional[Dict[str, Any]]:
        """Recupera el registro de lista negra más reciente para un IMEI específico."""
        sql = "SELECT * FROM eir_security_events WHERE imei = ? ORDER BY created_at DESC LIMIT 1;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (imei.strip(),))
            row = cur.fetchone()
            return self._row_to_dict(row)

    def get_eir_events_by_msisdn(self, msisdn: str) -> List[Dict[str, Any]]:
        """Retorna el historial de eventos EIR asociados a una línea telefónica."""
        sql = "SELECT * FROM eir_security_events WHERE msisdn = ? ORDER BY created_at DESC;"
        with self.db.get_cursor() as cur:
            self._execute(cur, sql, (msisdn.strip(),))
            rows = cur.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_subscriber_balance(self, msisdn: str) -> float:
        """Retorna el saldo monetario disponible en Bolívares (VES) para una línea."""
        bal = self.get_balance_and_quotas(msisdn)
        return float(bal.get("balance_ves", 0.0)) if bal else 0.0
