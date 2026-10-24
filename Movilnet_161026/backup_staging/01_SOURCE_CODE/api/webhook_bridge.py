#!/usr/bin/env python3
"""
webhook_bridge.py — Puente de Webhooks, Eventos Asíncronos & Orquestación MCP
==============================================================================
Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
Fase 2: Paso 3 — Integración Bidireccional de Webhooks (n8n ↔ API REST ↔ MCP)
Estándares: TM Forum ODA (TMF688 Events / TMF676 / TMF678 / TMF680), RFC 2104 (HMAC-SHA256)
Arquitectura: Despachador de eventos asíncronos con reintentos exponenciales y jitter,
              firma criptográfica HMAC anti-repetición, Dead Letter Queue (DLQ),
              deduplicación idempotente y enlace bidireccional en vivo con las 5 suites MCP.
"""

from __future__ import annotations

import os
import sys
import json
import time
import uuid
import hmac
import random
import hashlib
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Asegurar path al raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.repository import MovilnetRepository
from mcp.master_gateway import MovilnetMasterMcpGateway
from mcp.n8n_tools import mcp_n8n_trigger_webhook

# Clave secreta estándar para firmas HMAC (configurable vía env o rotación KMS)
DEFAULT_WEBHOOK_SECRET = os.environ.get("MOVILNET_WEBHOOK_SECRET", "MOVILNET_HMAC_SECRET_TOKEN_2026_PROD")
SIGNATURE_HEADER = "X-Movilnet-Signature"
TIMESTAMP_HEADER = "X-Movilnet-Timestamp"
DELIVERY_ID_HEADER = "X-Movilnet-Delivery-ID"
EVENT_TYPE_HEADER = "X-Movilnet-Event-Type"
MAX_TIMESTAMP_TOLERANCE_SECONDS = 300  # Ventana de 5 minutos anti-replay


# ============================================================================
# 1. MODELOS DE DATOS DE EVENTOS Y WEBHOOKS
# ============================================================================

@dataclass
class WebhookEvent:
    """Representación formal de un evento para transporte vía Webhook."""
    event_id: str
    event_type: str
    source: str
    payload: Dict[str, Any]
    timestamp: str
    delivery_attempts: int = 0
    status: str = "PENDING"  # PENDING, DELIVERED, FAILED, DLQ
    signature: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WebhookDeliveryResult:
    """Resultado de la ejecución de entrega de un Webhook."""
    delivery_id: str
    event_id: str
    event_type: str
    target_url: str
    success: bool
    status_code: int
    attempts: int
    latency_ms: float
    error_message: Optional[str] = None
    response_body: Optional[str] = None
    routed_to_dlq: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# 2. SEGURIDAD Y FIRMA CRIPTOGRÁFICA HMAC-SHA256
# ============================================================================

class HMACSignatureValidator:
    """
    Generador y Validador criptográfico de firmas HMAC-SHA256.
    Protege los webhooks contra manipulación de datos y ataques de repetición (Replay Attacks).
    """

    @staticmethod
    def generate_signature(payload_bytes: bytes, secret: str, timestamp_str: str) -> str:
        """
        Calcula firma HMAC-SHA256 concatenando timestamp y payload:
        firma = HMAC_SHA256(secret, "{timestamp}." + payload_bytes)
        """
        message = f"{timestamp_str}.".encode("utf-8") + payload_bytes
        return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_signature(
        signature: Optional[str],
        payload_bytes: bytes,
        secret: str,
        timestamp_str: Optional[str],
        tolerance_seconds: int = MAX_TIMESTAMP_TOLERANCE_SECONDS
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida que la firma coincida de forma temporalmente constante y que
        el timestamp esté dentro de la ventana de tolerancia admitida.
        """
        if not signature:
            return False, "Cabecera de firma requerida ausente ('X-Movilnet-Signature')"

        if not timestamp_str:
            return False, "Cabecera de marca de tiempo requerida ausente ('X-Movilnet-Timestamp')"

        # 1. Validar ventana temporal anti-replay
        try:
            # Soporta formato Unix epoch o ISO-8601
            if timestamp_str.isdigit():
                event_ts = float(timestamp_str)
            else:
                event_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                event_ts = event_dt.timestamp()

            now_ts = time.time()
            drift = abs(now_ts - event_ts)
            if drift > tolerance_seconds:
                return False, f"Timestamp fuera de la ventana de tolerancia ({drift:.1f}s > {tolerance_seconds}s)"
        except Exception as e:
            return False, f"Formato de timestamp inválido: {str(e)}"

        # 2. Calcular firma esperada
        expected = HMACSignatureValidator.generate_signature(payload_bytes, secret, timestamp_str)

        # 3. Comparación segura en tiempo constante (protección contra timing attacks)
        if not hmac.compare_digest(expected, signature):
            return False, "Firma HMAC-SHA256 no coincide con el payload y secreto autorizados"

        return True, None


# ============================================================================
# 3. COLA DE MENSAJES MUERTOS (DEAD LETTER QUEUE - DLQ) Y BITÁCORA DE ENTREGAS
# ============================================================================

class WebhookDeadLetterQueue:
    """
    Almacén de mensajes muertos (DLQ) para auditoría, reprocesamiento y resiliencia.
    Conserva los eventos que superaron el umbral de reintentos máximos.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._dlq: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def push(self, event: WebhookEvent, target_url: str, last_error: str, attempts: int) -> None:
        """Encola un evento no entregable en la DLQ."""
        with self._lock:
            record = {
                "dlq_id": f"dlq-{uuid.uuid4().hex[:12]}",
                "event": event.to_dict(),
                "target_url": target_url,
                "last_error": last_error,
                "attempts": attempts,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "reprocessed": False
            }
            if len(self._dlq) >= self.max_size:
                self._dlq.pop(0)  # Evitar desborde en memoria
            self._dlq.append(record)

    def list_all(self, limit: int = 50, unresolved_only: bool = True) -> List[Dict[str, Any]]:
        """Lista registros de la DLQ."""
        with self._lock:
            items = self._dlq
            if unresolved_only:
                items = [x for x in items if not x.get("reprocessed")]
            return list(reversed(items[-limit:]))

    def mark_reprocessed(self, dlq_id: str) -> bool:
        """Marca un elemento de la DLQ como reprocesado exitosamente."""
        with self._lock:
            for item in self._dlq:
                if item.get("dlq_id") == dlq_id:
                    item["reprocessed"] = True
                    item["reprocessed_at"] = datetime.now(timezone.utc).isoformat()
                    return True
            return False

    def get_by_id(self, dlq_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un registro específico de la DLQ."""
        with self._lock:
            for item in self._dlq:
                if item.get("dlq_id") == dlq_id:
                    return dict(item)
            return None

    def count(self) -> Dict[str, int]:
        """Contadores estadísticos de la DLQ."""
        with self._lock:
            total = len(self._dlq)
            unresolved = sum(1 for x in self._dlq if not x.get("reprocessed"))
            return {"total_dlq": total, "unresolved_dlq": unresolved}


class WebhookDeliveryTracker:
    """Historial rotativo de auditoría de entregas de webhooks."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self.stats = {
            "total_sent": 0,
            "success_count": 0,
            "failed_count": 0,
            "dlq_count": 0,
            "retries_count": 0
        }

    def record(self, result: WebhookDeliveryResult) -> None:
        """Registra el resultado de una entrega."""
        with self._lock:
            self.stats["total_sent"] += 1
            if result.success:
                self.stats["success_count"] += 1
            else:
                self.stats["failed_count"] += 1

            if result.routed_to_dlq:
                self.stats["dlq_count"] += 1

            if result.attempts > 1:
                self.stats["retries_count"] += (result.attempts - 1)

            if len(self._history) >= self.max_history:
                self._history.pop(0)
            self._history.append(result.to_dict())

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna las entregas más recientes."""
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        """Retorna resumen estadístico."""
        with self._lock:
            total = self.stats["total_sent"]
            success = self.stats["success_count"]
            rate = round((success / total * 100.0), 2) if total > 0 else 100.0
            return {
                **self.stats,
                "success_rate_pct": rate
            }


# ============================================================================
# 4. DESPACHADOR CON RETROCESO EXPONENCIAL Y JITTER
# ============================================================================

class WebhookDispatcher:
    """
    Despachador HTTP de Webhooks salientes con política de reintentos exponenciales,
    firma HMAC-SHA256 automática y enrutamiento a DLQ en caso de fallo permanente.
    """

    def __init__(
        self,
        default_secret: str = DEFAULT_WEBHOOK_SECRET,
        dlq: Optional[WebhookDeadLetterQueue] = None,
        tracker: Optional[WebhookDeliveryTracker] = None,
        transport_override: Optional[Callable[[urllib.request.Request, float], Tuple[int, str]]] = None
    ):
        self.secret = default_secret
        self.dlq = dlq or WebhookDeadLetterQueue()
        self.tracker = tracker or WebhookDeliveryTracker()
        self.transport_override = transport_override  # Hook para pruebas unitarias sin socket real

    def _calculate_backoff(self, attempt: int, base_seconds: float = 0.05, max_seconds: float = 1.0) -> float:
        """
        Calcula retardo exponencial con Full Jitter:
        delay = random(0, min(max_seconds, base_seconds * (2 ** (attempt - 1))))
        """
        temp = min(max_seconds, base_seconds * (2 ** (attempt - 1)))
        return random.uniform(0, temp)

    def dispatch(
        self,
        target_url: str,
        event_type: str,
        payload: Dict[str, Any],
        source: str = "movilnet.api.service",
        max_retries: int = 3,
        secret: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> WebhookDeliveryResult:
        """
        Despacha un webhook hacia una URL de destino (e.g. n8n webhook receptor).
        Ejecuta hasta `max_retries` reintentos ante errores transitorios.
        """
        effective_secret = secret or self.secret
        event_id = f"evt-{uuid.uuid4().hex}"
        delivery_id = f"del-{uuid.uuid4().hex}"
        timestamp_str = datetime.now(timezone.utc).isoformat()

        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            source=source,
            payload=payload,
            timestamp=timestamp_str,
            status="PENDING"
        )

        # Serializar payload para envío y firma
        payload_json = json.dumps(payload, ensure_ascii=False)
        payload_bytes = payload_json.encode("utf-8")

        # Generar firma HMAC-SHA256
        sig = HMACSignatureValidator.generate_signature(payload_bytes, effective_secret, timestamp_str)
        event.signature = sig

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Movilnet-Webhook-Bridge/1.0",
            SIGNATURE_HEADER: sig,
            TIMESTAMP_HEADER: timestamp_str,
            DELIVERY_ID_HEADER: delivery_id,
            EVENT_TYPE_HEADER: event_type
        }
        if custom_headers:
            headers.update(custom_headers)

        attempts = 0
        last_status_code = 0
        last_error: Optional[str] = None
        last_body: Optional[str] = None
        start_overall = time.time()

        while attempts < max_retries:
            attempts += 1
            event.delivery_attempts = attempts
            attempt_start = time.time()

            try:
                if self.transport_override:
                    # Uso de hook de transporte (ideal para simulaciones locales y unit tests)
                    req = urllib.request.Request(target_url, data=payload_bytes, headers=headers, method="POST")
                    status_code, body = self.transport_override(req, 5.0)
                else:
                    req = urllib.request.Request(target_url, data=payload_bytes, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        status_code = resp.status
                        body = resp.read().decode("utf-8", errors="ignore")

                latency_ms = round((time.time() - start_overall) * 1000, 2)

                # Éxito 2xx
                if 200 <= status_code < 300:
                    event.status = "DELIVERED"
                    result = WebhookDeliveryResult(
                        delivery_id=delivery_id,
                        event_id=event_id,
                        event_type=event_type,
                        target_url=target_url,
                        success=True,
                        status_code=status_code,
                        attempts=attempts,
                        latency_ms=latency_ms,
                        response_body=body,
                        routed_to_dlq=False
                    )
                    self.tracker.record(result)
                    return result

                # Errores 4xx (cliente): no reintentar a menos que sea 429
                last_status_code = status_code
                last_body = body
                last_error = f"HTTP {status_code}: Error del receptor"

                if 400 <= status_code < 500 and status_code != 429:
                    # Error no reintentable (payload inválido, firma rechazada, etc.)
                    break

            except urllib.error.HTTPError as e:
                last_status_code = e.code
                last_error = f"HTTPError {e.code}: {e.reason}"
                last_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
                if 400 <= e.code < 500 and e.code != 429:
                    break

            except Exception as e:
                last_status_code = 0
                last_error = f"ConnectionError: {str(e)}"
                last_body = None

            # Si quedan reintentos, esperar backoff exponencial
            if attempts < max_retries:
                delay = self._calculate_backoff(attempts)
                time.sleep(delay)

        # Falló tras agotar los intentos permitidos
        total_latency_ms = round((time.time() - start_overall) * 1000, 2)
        event.status = "DLQ"

        # Enrutar a Dead Letter Queue
        self.dlq.push(event, target_url, last_error or "Unknown failure", attempts)

        result = WebhookDeliveryResult(
            delivery_id=delivery_id,
            event_id=event_id,
            event_type=event_type,
            target_url=target_url,
            success=False,
            status_code=last_status_code,
            attempts=attempts,
            latency_ms=total_latency_ms,
            error_message=last_error,
            response_body=last_body,
            routed_to_dlq=True
        )
        self.tracker.record(result)
        return result


# ============================================================================
# 5. PUENTE DE INTEROPERABILIDAD BIDIRECCIONAL CON SUITES MCP & REPOSITORIO
# ============================================================================

class WebhookBridgeService:
    """
    Servicio central que orquesta la recepción y despacho de webhooks,
    la invocación de las Suites MCP en vivo y la persistencia en base de datos.
    """

    def __init__(
        self,
        repository: Optional[MovilnetRepository] = None,
        mcp_gateway: Optional[MovilnetMasterMcpGateway] = None,
        dispatcher: Optional[WebhookDispatcher] = None,
        secret: str = DEFAULT_WEBHOOK_SECRET
    ):
        self.repo = repository or MovilnetRepository()
        self.mcp = mcp_gateway or MovilnetMasterMcpGateway()
        self.dlq = WebhookDeadLetterQueue()
        self.tracker = WebhookDeliveryTracker()
        self.dispatcher = dispatcher or WebhookDispatcher(default_secret=secret, dlq=self.dlq, tracker=self.tracker)
        self.secret = secret

        # Caché de deduplicación idempotente (TTL 10 minutos)
        self._processed_delivery_ids: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._customer_care_agent = None
        self._fintech_c2p_agent = None
        self._emergency_eir_agent = None
        self._retention_churn_agent = None

    @property
    def customer_care_agent(self):
        if self._customer_care_agent is None:
            from api.agents.agent_customer_care import CustomerCareAgent
            self._customer_care_agent = CustomerCareAgent(repo=self.repo, mcp_gateway=self.mcp)
        return self._customer_care_agent

    @property
    def fintech_c2p_agent(self):
        if self._fintech_c2p_agent is None:
            from api.agents.agent_fintech_c2p import FintechC2PAgent
            self._fintech_c2p_agent = FintechC2PAgent(repo=self.repo, mcp_gateway=self.mcp)
        return self._fintech_c2p_agent

    @property
    def emergency_eir_agent(self):
        if self._emergency_eir_agent is None:
            from api.agents.agent_emergency_eir import EmergencyEIRAgent
            self._emergency_eir_agent = EmergencyEIRAgent(
                repo=self.repo,
                mcp_gateway=self.mcp,
                customer_care_agent=self.customer_care_agent
            )
        return self._emergency_eir_agent

    @property
    def retention_churn_agent(self):
        if self._retention_churn_agent is None:
            from api.agents.agent_retention_churn import RetentionChurnAgent
            self._retention_churn_agent = RetentionChurnAgent(
                repo=self.repo,
                mcp=self.mcp
            )
        return self._retention_churn_agent


    # ------------------------------------------------------------------------
    # Verificación de Idempotencia
    # ------------------------------------------------------------------------

    def is_duplicate(self, delivery_id: Optional[str]) -> bool:
        """Verifica si un delivery_id ya fue procesado recientemente."""
        if not delivery_id:
            return False
        with self._lock:
            now = time.time()
            # Limpiar entradas mayores a 600s
            expired = [k for k, v in self._processed_delivery_ids.items() if now - v > 600]
            for k in expired:
                del self._processed_delivery_ids[k]

            if delivery_id in self._processed_delivery_ids:
                return True
            self._processed_delivery_ids[delivery_id] = now
            return False

    # ------------------------------------------------------------------------
    # Procesador de Eventos Entrantes (Inbound Webhook Processor)
    # ------------------------------------------------------------------------

    def process_inbound_event(
        self,
        headers: Dict[str, str],
        body_bytes: bytes,
        skip_hmac_check: bool = False
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Punto de entrada universal para eventos de webhook recibidos desde n8n,
        pasarelas de pago externas o sistemas OSS/BSS.
        """
        start_time = time.time()

        # 1. Normalizar cabeceras a minúsculas
        norm_headers = {k.lower(): v for k, v in headers.items()}
        signature = norm_headers.get(SIGNATURE_HEADER.lower())
        timestamp_str = norm_headers.get(TIMESTAMP_HEADER.lower())
        delivery_id = norm_headers.get(DELIVERY_ID_HEADER.lower())
        event_type = norm_headers.get(EVENT_TYPE_HEADER.lower(), "event.generic")

        # 2. Validación de firma criptográfica
        if not skip_hmac_check:
            valid, err_msg = HMACSignatureValidator.verify_signature(
                signature=signature,
                payload_bytes=body_bytes,
                secret=self.secret,
                timestamp_str=timestamp_str
            )
            if not valid:
                return 401, {
                    "code": "ERR_INVALID_SIGNATURE",
                    "reason": "Fallo de autenticación de webhook",
                    "message": err_msg or "Firma HMAC inválida",
                    "status": 401,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        # 3. Control de Idempotencia
        if delivery_id and self.is_duplicate(delivery_id):
            return 200, {
                "status": "already_processed",
                "message": f"Evento {delivery_id} ya fue procesado previamente (idempotencia activa)",
                "delivery_id": delivery_id,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 4. Parsear JSON Payload
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            return 400, {
                "code": "ERR_INVALID_JSON",
                "reason": "Payload mal formado",
                "message": "El cuerpo del webhook no contiene JSON válido",
                "status": 400,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 5. Enrutamiento y Ejecución según el tipo de evento (Event Dispatch)
        processing_result: Dict[str, Any] = {}
        target_mcp_suite: Optional[str] = None

        if event_type in ["c2p.payment.reconcile", "c2p.callback"]:
            status_code, processing_result = self._handle_c2p_webhook_event(payload)
            target_mcp_suite = "Suite 2: mcp_fintech_c2p"

        elif event_type in ["eir.terminal.lock", "eir.callback"]:
            status_code, processing_result = self._handle_eir_webhook_event(payload)
            target_mcp_suite = "Suite 1: mcp_telco_tools"

        elif event_type in ["whatsapp.inbound", "telegram.inbound", "omnichannel.message"]:
            status_code, processing_result = self._handle_omnichannel_inbound_event(payload)
            target_mcp_suite = "Suite 5: mcp_omnichannel_whatsapp & Suite 4: mcp_privacy_guard"

        elif event_type in ["crm.retention.trigger", "crm.churn.evaluate"]:
            status_code, processing_result = self._handle_crm_retention_event(payload)
            target_mcp_suite = "Suite 3: mcp_crm_retention"

        else:
            # Evento genérico aceptado
            status_code = 200
            processing_result = {
                "message": f"Evento de tipo '{event_type}' recibido y registrado.",
                "payload_keys": list(payload.keys())
            }
            target_mcp_suite = "Core Webhook Bridge"

        latency_ms = round((time.time() - start_time) * 1000, 2)
        response_payload = {
            "status": "success" if status_code < 400 else "error",
            "event_type": event_type,
            "delivery_id": delivery_id or f"gen-{uuid.uuid4().hex[:8]}",
            "mcp_suite_engaged": target_mcp_suite,
            "processing_result": processing_result,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return status_code, response_payload

    # ------------------------------------------------------------------------
    # Manejadores de Eventos Específicos Integrados con MCP y DB
    # ------------------------------------------------------------------------

    def _handle_c2p_webhook_event(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Concilia un pago móvil C2P asíncrono mediante el Agente Nivel 2 (Fintech C2P)
        con evaluación antifraude vía Fintech MCP y liquidación atómica en OCS.
        """
        ref_id = payload.get("reference_id") or payload.get("reference")
        phone = payload.get("msisdn") or payload.get("phone")
        bank_code = payload.get("bank_code", "0102")
        amount = float(payload.get("amount_ves", payload.get("amount", 0.0)))
        payer_cid = payload.get("payer_cid", "V-10000001")
        otp = payload.get("otp_token", "123456")

        if not ref_id or not phone or amount <= 0:
            return 400, {
                "error": "Parámetros incompletos para conciliación C2P (requiere reference_id, phone, amount > 0)"
            }

        # 1. Ejecutar validación antifraude con Suite MCP Fintech
        mcp_res = self.mcp.dispatch("mcp_c2p_validate_transaction", {
            "phone": phone,
            "payer_cid": payer_cid,
            "bank_code": bank_code,
            "amount_bs": amount,
            "reference_id": ref_id
        })

        # 2. Despachar a través del Agente Nivel 2 (Fintech C2P)
        from api.agents.agent_fintech_c2p import C2PPaymentRequest
        c2p_req = C2PPaymentRequest(
            msisdn=phone,
            amount_ves=amount,
            bank_code=bank_code,
            payer_cid=payer_cid,
            otp_token=otp,
            reference_id=ref_id,
            channel="webhook"
        )
        c2p_resp = self.fintech_c2p_agent.process_payment(c2p_req)

        if not c2p_resp.success:
            err_msg = c2p_resp.metadata.get("error_reason", "Fallo en procesamiento de pago C2P")
            return 404 if "no se encuentra registrada" in err_msg else 400, {"error": err_msg, "agent_c2p_response": c2p_resp.to_dict()}

        return 200, {
            "reconciliation": "COMPLETED",
            "reference_id": ref_id,
            "msisdn": phone,
            "amount_accredited_ves": amount,
            "new_balance_ves": c2p_resp.new_balance_ves,
            "transaction": c2p_resp.metadata.get("transaction_record", {}),
            "fintech_mcp_validation": mcp_res.get("result", {}),
            "agent_c2p_response": c2p_resp.to_dict()
        }

    def _handle_eir_webhook_event(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Procesa reporte y confirmación de bloqueo de terminal en lista negra EIR
        con validación SIM-swap previa vía Telco MCP y delegación al Agente Nivel 3.
        """
        imei = payload.get("imei")
        msisdn = payload.get("msisdn")
        reason = payload.get("reason", "ROBO_EXTRAVIO_EMERGENCIA")
        reported_by = payload.get("reported_by", "SISTEMA_WEBHOOK_N8N")
        police = payload.get("police_report_number")

        if not imei:
            return 400, {"error": "El campo 'imei' (14-16 dígitos) es mandatorio"}

        # 1. Auditoría SIM-Swap previa vía Telco MCP
        sim_swap_audit = {}
        if msisdn:
            mcp_swap = self.mcp.dispatch("mcp_telco_verify_sim_swap", {"msisdn": msisdn})
            sim_swap_audit = mcp_swap.get("result", {})

        # 2. Despachar a través del Agente Nivel 3 (EmergencyEIRAgent)
        from api.agents.agent_emergency_eir import EmergencyEIRRequest
        req = EmergencyEIRRequest(
            msisdn=msisdn or "04160000000",
            imei=imei,
            lock_type="THEFT_LOCK",
            reason=reason,
            police_report_number=police,
            reporting_agent=reported_by,
            source_channel="webhook"
        )
        agent_res = self.emergency_eir_agent.process_emergency_lock(req)

        ticket_id = agent_res.ticket_id
        blacklist_record = self.repo.get_eir_event_by_ticket(ticket_id) or {
            "ticket_id": ticket_id,
            "status": "LOCKED_IN_EIR"
        }

        updated_line = self.repo.get_line_details(msisdn) if msisdn else None
        line_blocked = updated_line.get("status") in ["BLOQUEADO_ROBO", "SUSPENDIDO_FRAUDE", "BLOQUEADO_EXTRAVIO"] if updated_line else False

        return 200, {
            "eir_status": "BLOCKED_CONFIRMED",
            "imei": agent_res.imei,
            "ticket_id": ticket_id,
            "line_blocked": line_blocked,
            "blacklist_record": blacklist_record,
            "sim_swap_telemetry": sim_swap_audit or agent_res.sim_swap_audit,
            "agent_eir_response": agent_res.to_dict()
        }


    def _handle_omnichannel_inbound_event(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Procesa mensaje omnicanal (WhatsApp/Telegram), sanitiza PII con Privacy Guard MCP,
        ejecuta el Agente Nivel 1 (Customer Care Fast-Path / LLM) y estructura respuesta interactiva.
        """
        # Extraer texto y teléfono según formato plano, WhatsApp o Telegram
        raw_message = ""
        sender_phone = ""
        channel = payload.get("channel", "whatsapp")

        if isinstance(payload.get("text"), str):
            raw_message = payload.get("text", "")
        elif isinstance(payload.get("message"), str):
            raw_message = payload.get("message", "")
        elif isinstance(payload.get("message"), dict):
            # Formato Telegram Bot
            channel = "telegram"
            tg_msg = payload.get("message", {})
            raw_message = tg_msg.get("text", "")
            contact = tg_msg.get("contact", {})
            sender_phone = contact.get("phone_number") or str(tg_msg.get("from", {}).get("id", ""))
        elif "entry" in payload:
            # Formato WhatsApp Cloud API
            channel = "whatsapp"
            try:
                wa_change = payload["entry"][0]["changes"][0]["value"]
                wa_msg = wa_change["messages"][0]
                raw_message = wa_msg.get("text", {}).get("body", "")
                sender_phone = wa_msg.get("from", "")
            except Exception:
                raw_message = ""

        if not sender_phone:
            sender_phone = str(payload.get("from", payload.get("phone", "")))

        session_id = payload.get("session_id")

        # 1. Sanitizar mensaje para logs y trazabilidad con Suite 4 (Privacy Guard)
        pii_res = self.mcp.dispatch("mcp_pii_sanitize_text", {"text": raw_message})
        sanitized_text = pii_res.get("result", {}).get("sanitized_text", raw_message)

        # 2. Despachar a través del Agente Nivel 1 (Customer Care & Consultas OCS)
        from api.agents.agent_customer_care import AgentMessage
        agent_msg = AgentMessage(
            text=raw_message,
            msisdn=sender_phone,
            session_id=session_id,
            channel=channel
        )
        agent_response = self.customer_care_agent.process_message(agent_msg)

        # 3. Formatear opciones interactivas con Suite 5 (WhatsApp MCP)
        buttons_to_use = agent_response.interactive_options[:3] if agent_response.interactive_options else [
            {"id": "btn_saldo", "title": "Consultar Saldo"},
            {"id": "btn_recarga", "title": "Recargar C2P"},
            {"id": "btn_planes", "title": "Planes 4GMAX"}
        ]
        buttons_res = self.mcp.dispatch("mcp_whatsapp_format_buttons", {
            "body_text": agent_response.response_text,
            "buttons": buttons_to_use
        })
        mcp_reply = buttons_res.get("result", {})
        suggested_reply = mcp_reply.get("meta_payload", {})

        sub_info = self.repo.get_subscriber_by_msisdn(sender_phone) if sender_phone else None

        return 200, {
            "workflow": "OMNICHANNEL_INBOUND_PROCESSED",
            "sanitized_input": sanitized_text,
            "subscriber_found": bool(sub_info),
            "agent_response": agent_response.to_dict(),
            "suggested_reply": suggested_reply
        }

    def _handle_crm_retention_event(self, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Evalúa riesgo de churn y emite recomendación de retención con Suite 3 (CRM Retention MCP)
        y delegación al Agente Nivel 4 (RetentionChurnAgent).
        """
        msisdn = payload.get("msisdn", "04160000001")
        days_unpaid = int(payload.get("days_inactive", payload.get("days_unpaid", 15)))

        crm_res = self.mcp.dispatch("mcp_crm_evaluate_churn_risk", {
            "msisdn": msisdn,
            "days_unpaid": days_unpaid
        })

        agent_offer = self.retention_churn_agent.generate_retention_offer(msisdn)

        return 200, {
            "crm_action": "CHURN_RISK_EVALUATED",
            "msisdn": msisdn,
            "assessment": crm_res.get("result", {}),
            "agent_n4_response": agent_offer.to_dict()
        }

    # ------------------------------------------------------------------------
    # Disparador Hacia n8n (Outbound to n8n Webhook)
    # ------------------------------------------------------------------------

    def notify_n8n_workflow(
        self,
        webhook_path: str,
        event_type: str,
        payload: Dict[str, Any],
        is_test: bool = False
    ) -> WebhookDeliveryResult:
        """
        Dispara un webhook hacia n8n usando la URL base configurada
        o el despachador con reintentos.
        """
        base_url = os.environ.get("N8N_BASE_URL", "https://n8n.lpgtec.net").rstrip("/")
        mode = "webhook-test" if is_test else "webhook"
        target_url = f"{base_url}/{mode}/{webhook_path.lstrip('/')}"

        return self.dispatcher.dispatch(
            target_url=target_url,
            event_type=event_type,
            payload=payload,
            source="movilnet.api.webhook_bridge"
        )


# Instancia singleton del puente
_default_bridge: Optional[WebhookBridgeService] = None

def get_webhook_bridge() -> WebhookBridgeService:
    global _default_bridge
    if _default_bridge is None:
        _default_bridge = WebhookBridgeService()
    return _default_bridge
