"""
Módulo Autónomo de Despacho Multimodal — Capa de Infraestructura: Cliente WhatsApp Resiliente
Gobernanza: Universal Best Practices Engineering Rule (Pilares I, II, III, IV, VI)
"""

import argparse
import http.server
import json
import logging
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple

# Bootstrap de ruta para ejecución autónoma (Pilar II)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(CURRENT_DIR)
if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)

from domain.enums import MediaType

logger = logging.getLogger("WhatsAppMultimodalClient")

OFFICIAL_PWA_URL = os.environ.get(
    "OFFICIAL_PWA_URL",
    "https://one21026-ids-movilnet-pwa.onrender.com/ui/pwa_stitch/index.html"
)


class CircuitBreakerState(str, Enum):
    """Estados del Circuit Breaker según estándar de resiliencia."""
    CLOSED = "CLOSED"        # Operación normal: el tráfico fluye
    OPEN = "OPEN"            # Fallo masivo: tráfico bloqueado temporalmente
    HALF_OPEN = "HALF_OPEN"  # Estado de prueba: se valida si el servicio externo revivió


class CircuitBreaker:
    """
    Circuit Breaker para proteger servicios de despacho y evitar sobrecargar
    gateways externos caídos o degradados (Pilar IV: Resiliencia).
    """

    def __init__(self, failure_threshold: int = 5, recovery_time_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """Determina si una petición tiene autorización para ser despachada."""
        with self._lock:
            now = time.time()
            if self.state == CircuitBreakerState.OPEN:
                if now - self.last_failure_time >= self.recovery_time_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("⚡ CircuitBreaker pasó a HALF_OPEN (probando recuperación de WhatsApp Gateway)")
                    return True
                return False
            return True

    def record_success(self) -> None:
        """Registra un despacho exitoso y restablece el circuito."""
        with self._lock:
            if self.state != CircuitBreakerState.CLOSED:
                logger.info("✅ CircuitBreaker recuperado: estado CLOSED")
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Registra un fallo de despacho y evalúa si abre el circuito."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitBreakerState.HALF_OPEN or self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    f"🚨 CircuitBreaker activado: estado OPEN ({self.failure_count} fallos consecutivos). "
                    f"Bloqueando tráfico por {self.recovery_time_seconds}s"
                )

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado de telemetría del breaker."""
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "last_failure_time": self.last_failure_time,
                "recovery_time_seconds": self.recovery_time_seconds
            }


def mask_phone_pii(phone: str) -> str:
    """
    Enmascara el número de teléfono para logs y auditoría (Zero-PII, Pilar VI).
    Ejemplo: '+584166251587' -> '+58416***1587'
    """
    if not phone:
        return ""
    clean = phone.strip()
    if len(clean) <= 6:
        return clean[:2] + "***"
    return clean[:6] + "***" + clean[-4:]


def ensure_pwa_link(text: str) -> str:
    """
    Garantiza que todo mensaje saliente de Movilnet concluya con el enlace PWA oficial inviolable.
    """
    if OFFICIAL_PWA_URL in text:
        return text
    clean_text = text.rstrip()
    if not clean_text:
        return f"👉 {OFFICIAL_PWA_URL}"
    return f"{clean_text}\n\n👉 {OFFICIAL_PWA_URL}"


class WhatsAppMultimodalClient:
    """
    Cliente empresarial para despacho de mensajes multimedia y texto hacia WhatsApp.
    Implementa:
      - Despacho real HTTP a Meta Cloud API o Gateway de Staging (Evolution API / n8n webhook)
      - Modo 'mock' hermético para pruebas unitarias sin internet
      - Circuit Breaker con estados CLOSED, OPEN y HALF_OPEN
      - Exponential Backoff para fallos transitorios de red
      - Política Zero-PII y validación del enlace PWA
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        mode: Optional[str] = None,
        max_retries: int = 3,
        base_delay_seconds: float = 0.5,
        timeout_seconds: float = 10.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
        http_requester: Optional[Any] = None
    ):
        self.mode = mode or os.environ.get("WHATSAPP_CLIENT_MODE", "mock").lower()
        self.api_url = api_url or os.environ.get("WHATSAPP_API_URL", "https://graph.facebook.com/v20.0")
        self.api_token = api_token or os.environ.get("WHATSAPP_API_TOKEN", "mock_token")
        self.phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "default_phone_id")
        self.max_retries = max(1, max_retries)
        self.base_delay_seconds = base_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker = circuit_breaker or CircuitBreaker(failure_threshold=5, recovery_time_seconds=30.0)
        self.http_requester = http_requester or urllib.request.urlopen
        self.outbox_history: List[Dict[str, Any]] = []

    def dispatch_media_message(
        self,
        phone_number: str,
        media_type: MediaType,
        media_url_or_path: str,
        caption: str = "",
        mime_type: str = ""
    ) -> Dict[str, Any]:
        """
        Despacha un mensaje multimedia con caption a WhatsApp.
        Garantiza el enlace PWA en el caption.
        """
        final_caption = ensure_pwa_link(caption)
        type_str = media_type.value.lower()

        # Construcción de payload según especificación Meta Cloud API
        media_payload: Dict[str, Any] = {"link": media_url_or_path}
        if final_caption:
            media_payload["caption"] = final_caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": type_str,
            type_str: media_payload
        }

        return self._dispatch_envelope(phone_number, payload, final_caption, media_type.value)

    def dispatch_text_message(
        self,
        phone_number: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Despacha un mensaje de texto puro con garantía del enlace PWA.
        """
        final_text = ensure_pwa_link(text)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": final_text
            }
        }
        return self._dispatch_envelope(phone_number, payload, final_text, "text")

    def _dispatch_envelope(
        self,
        phone_number: str,
        payload: Dict[str, Any],
        text_content: str,
        message_type: str
    ) -> Dict[str, Any]:
        """Orquesta la entrega según el modo configurado y registra auditoría Zero-PII."""
        masked_phone = mask_phone_pii(phone_number)
        record_idx = len(self.outbox_history) + 1

        # Registro en historial interno
        dispatch_record = {
            "index": record_idx,
            "phone_masked": masked_phone,
            "phone_number": phone_number,
            "type": message_type,
            "caption": text_content,
            "timestamp": time.time(),
            "mode": self.mode
        }

        # 1. Modo Deshabilitado
        if self.mode == "disabled":
            dispatch_record["status"] = "DISABLED"
            self.outbox_history.append(dispatch_record)
            logger.info(f"⏸️ Despacho desactivado (WHATSAPP_CLIENT_MODE=disabled) hacia {masked_phone}")
            return {
                "success": False,
                "status": "DISABLED",
                "message_id": None,
                "mode": "DISABLED",
                "delivered_to": phone_number
            }

        # 2. Modo Mock (Hermético para desarrollo y tests)
        if self.mode == "mock":
            message_id = f"wamid_mock_{record_idx}_{int(time.time())}"
            dispatch_record["status"] = "DELIVERED"
            dispatch_record["message_id"] = message_id
            self.outbox_history.append(dispatch_record)
            logger.info(f"🧪 [MOCK] Despacho registrado exitosamente para {masked_phone} (id: {message_id})")
            return {
                "success": True,
                "message_id": message_id,
                "mode": "MOCK_DISPATCH",
                "delivered_to": phone_number,
                "status": "DELIVERED"
            }

        # 3. Modo Live / Webhook (Conexión HTTP real con Circuit Breaker y Reintentos)
        target_url = self._resolve_target_url()
        http_result = self._send_http_with_resilience(target_url, payload, masked_phone)

        dispatch_record["status"] = "DELIVERED" if http_result.get("success") else "FAILED"
        dispatch_record["response"] = http_result
        self.outbox_history.append(dispatch_record)

        return http_result

    def _resolve_target_url(self) -> str:
        """Determina la URL destino HTTP según el modo de operación."""
        url = self.api_url.rstrip("/")
        if self.mode == "meta_cloud" or "graph.facebook.com" in url:
            # Endpoint estándar de Meta Cloud API
            return f"{url}/{self.phone_number_id}/messages"
        # Endpoint de webhook o gateway de staging (ej. n8n o Evolution API)
        return url

    def _send_http_with_resilience(
        self,
        url: str,
        payload: Dict[str, Any],
        masked_phone: str
    ) -> Dict[str, Any]:
        """
        Ejecuta el POST HTTP con Circuit Breaker, Exponential Backoff y captura estricta de excepciones.
        """
        # A. Chequeo de Circuit Breaker
        if not self.circuit_breaker.allow_request():
            logger.error(f"🚨 Despacho a {masked_phone} rechazado: CircuitBreaker está OPEN")
            return {
                "success": False,
                "status": "CIRCUIT_OPEN",
                "error": "Circuit breaker is OPEN due to repeated consecutive failures",
                "delivered_to": masked_phone
            }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "MovilnetMultimodalClient/1.0"
        }

        last_error = ""
        last_status_code = None

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
                with self.http_requester(req, timeout=self.timeout_seconds) as response:
                    status_code = response.getcode()
                    resp_bytes = response.read()
                    resp_data = {}
                    if resp_bytes:
                        try:
                            resp_data = json.loads(resp_bytes.decode("utf-8"))
                        except Exception:
                            resp_data = {"raw_response": resp_bytes.decode("utf-8", errors="replace")}

                    # Éxito: registrar y retornar
                    self.circuit_breaker.record_success()
                    msg_id = ""
                    if "messages" in resp_data and isinstance(resp_data["messages"], list) and resp_data["messages"]:
                        msg_id = resp_data["messages"][0].get("id", "")
                    elif "message_id" in resp_data:
                        msg_id = resp_data["message_id"]
                    else:
                        msg_id = f"wamid_live_{int(time.time())}"

                    logger.info(f"✅ Despacho HTTP exitoso ({status_code}) a {masked_phone} (msg_id: {msg_id})")
                    return {
                        "success": True,
                        "status": "DELIVERED",
                        "status_code": status_code,
                        "message_id": msg_id,
                        "mode": "LIVE_API",
                        "delivered_to": masked_phone,
                        "gateway_response": resp_data
                    }

            except urllib.error.HTTPError as he:
                last_status_code = he.code
                last_error = f"HTTP {he.code}: {he.reason}"
                try:
                    err_body = he.read().decode("utf-8", errors="replace")
                    last_error += f" | {err_body}"
                except Exception:
                    pass

                # Errores 4xx (excepto 429 Too Many Requests) no son transitorios: no reintentar
                if 400 <= he.code < 500 and he.code != 429:
                    logger.error(f"❌ Error de cliente no recuperable hacia {masked_phone}: {last_error}")
                    self.circuit_breaker.record_failure()
                    return {
                        "success": False,
                        "status": "CLIENT_ERROR",
                        "status_code": he.code,
                        "error": last_error,
                        "delivered_to": masked_phone
                    }

                # Errores 5xx o 429: registrar advertencia y reintentar con backoff
                logger.warning(
                    f"⚠️ Fallo HTTP transitorio en intento {attempt}/{self.max_retries} para {masked_phone}: {last_error}"
                )

            except (urllib.error.URLError, socket.timeout, TimeoutError) as net_err:
                last_error = f"Error de conexión: {str(net_err)}"
                logger.warning(
                    f"⚠️ Fallo de red en intento {attempt}/{self.max_retries} para {masked_phone}: {last_error}"
                )

            # Espera exponencial antes del siguiente intento
            if attempt < self.max_retries:
                delay = self.base_delay_seconds * (2 ** (attempt - 1))
                time.sleep(delay)

        # Si agotó todos los reintentos
        self.circuit_breaker.record_failure()
        logger.error(f"❌ Despacho fallido definitivamente tras {self.max_retries} intentos hacia {masked_phone}: {last_error}")
        return {
            "success": False,
            "status": "FAILED",
            "status_code": last_status_code,
            "error": last_error,
            "delivered_to": masked_phone
        }


def _run_in_process_test_server(port: int, status_code_to_return: int = 200, response_json: dict = None):
    """Servidor HTTP efímero para pruebas unitarias e integración en proceso."""
    resp_body = json.dumps(response_json or {"messages": [{"id": "test_wamid_123"}]}).encode("utf-8")

    class TestHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(status_code_to_return)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), TestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente WhatsApp Resiliente para Despacho Multimodal")
    parser.add_argument("--test", action="store_true", help="Ejecutar suite de auto-verificación formal del cliente")
    parser.add_argument("--status", action="store_true", help="Mostrar estado y configuración del cliente")
    parser.add_argument("--demo", action="store_true", help="Despachar mensaje de demostración en modo mock")
    args = parser.parse_args()

    client = WhatsAppMultimodalClient()

    if args.status:
        cb_status = client.circuit_breaker.get_status()
        print("=" * 60)
        print("  ESTADO DEL CLIENTE WHATSAPP RESILIENTE — MOVILNET")
        print("=" * 60)
        print(f"Modo:               {client.mode}")
        print(f"API URL:            {client.api_url}")
        print(f"Phone Number ID:    {client.phone_number_id}")
        print(f"Circuit Breaker:    {cb_status['state']} (Fallos: {cb_status['failure_count']}/{cb_status['failure_threshold']})")
        print(f"Enlace PWA Oficial: {OFFICIAL_PWA_URL}")
        print("=" * 60)

    elif args.demo:
        demo_phone = "+584166251587"
        res = client.dispatch_media_message(
            phone_number=demo_phone,
            media_type=MediaType.IMAGE,
            media_url_or_path="https://storage.movilnet.com.ve/recibos/demo.pdf",
            caption="Recibo de recarga electrónica C2P verificado exitosamente."
        )
        print(f"Resultado del despacho demo:\n{json.dumps(res, indent=2)}")

    elif args.test:
        print("Iniciando auto-verificación formal de WhatsAppMultimodalClient...")

        # 1. Test Zero-PII Masking
        assert mask_phone_pii("+584166251587") == "+58416***1587", "Error en enmascaramiento PII"
        assert mask_phone_pii("123") == "12***", "Error en enmascaramiento corto"

        # 2. Test Enlace PWA Inviolable
        txt_with_pwa = ensure_pwa_link("Hola Movilnet")
        assert OFFICIAL_PWA_URL in txt_with_pwa, "El enlace PWA debe estar presente"
        assert txt_with_pwa.count(OFFICIAL_PWA_URL) == 1, "No debe duplicarse el enlace PWA"

        # 3. Test Modo Mock
        mock_cli = WhatsAppMultimodalClient(mode="mock")
        res_mock = mock_cli.dispatch_text_message("+584166251587", "Mensaje de prueba")
        assert res_mock["success"] is True
        assert res_mock["mode"] == "MOCK_DISPATCH"
        assert len(mock_cli.outbox_history) == 1

        # 4. Test Modo Disabled
        dis_cli = WhatsAppMultimodalClient(mode="disabled")
        res_dis = dis_cli.dispatch_text_message("+584166251587", "Mensaje disabled")
        assert res_dis["success"] is False
        assert res_dis["status"] == "DISABLED"

        # 5. Test Circuit Breaker
        cb = CircuitBreaker(failure_threshold=2, recovery_time_seconds=0.2)
        assert cb.allow_request() is True
        cb.record_failure()
        assert cb.allow_request() is True
        cb.record_failure()
        assert cb.allow_request() is False
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.25)
        # Debe pasar a HALF_OPEN
        assert cb.allow_request() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

        # 6. Test Despacho Live con Transporte In-Memory
        class _FakeResponse:
            def __init__(self, code: int, data_dict: dict):
                self.code = code
                self.bytes_data = json.dumps(data_dict).encode("utf-8")

            def getcode(self):
                return self.code

            def read(self):
                return self.bytes_data

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        def _mock_requester_ok(req, timeout):
            return _FakeResponse(200, {"messages": [{"id": "wamid_live_ok"}]})

        live_cli = WhatsAppMultimodalClient(
            mode="webhook",
            api_url="https://mock-gateway.movilnet.com.ve/webhook",
            api_token="test_tok",
            base_delay_seconds=0.01,
            timeout_seconds=2.0,
            http_requester=_mock_requester_ok
        )
        res_live = live_cli.dispatch_text_message("+584166251587", "Texto live")
        assert res_live["success"] is True
        assert res_live["message_id"] == "wamid_live_ok"
        assert res_live["status"] == "DELIVERED"

        # 7. Test Reintentos y Resiliencia ante error 500 transitorio
        attempt_tracker = {"count": 0}
        def _mock_requester_retry(req, timeout):
            attempt_tracker["count"] += 1
            if attempt_tracker["count"] < 3:
                import io
                raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, io.BytesIO(b'{"error": "temporarily unavailable"}'))
            return _FakeResponse(200, {"messages": [{"id": "wamid_recovered"}]})

        retry_cli = WhatsAppMultimodalClient(
            mode="webhook",
            api_url="https://mock-gateway.movilnet.com.ve/webhook",
            api_token="test_tok",
            max_retries=3,
            base_delay_seconds=0.01,
            http_requester=_mock_requester_retry
        )
        res_retry = retry_cli.dispatch_text_message("+584166251587", "Texto con reintento")
        assert res_retry["success"] is True
        assert res_retry["message_id"] == "wamid_recovered"
        assert attempt_tracker["count"] == 3, f"Esperados 3 intentos, se hicieron {attempt_tracker['count']}"

        print("✅ Todas las verificaciones formales de WhatsAppMultimodalClient pasaron al 100%.")
    else:
        parser.print_help()
