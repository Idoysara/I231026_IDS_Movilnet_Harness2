#!/usr/bin/env python3
"""
mcp_idempotent_gateway: Servidor MCP de Pasarela Idempotente, Centinela Financiero y Rate-Limiting.
Garantiza que transacciones de cobro y canjes no se dupliquen ante inestabilidad de red (3G/4G),
audita la Invariante II (Margen >= 35%) y gestiona el flujo de pagos.
"""
import sys
import time
import hashlib
import json
import argparse
from typing import Dict, Any, Optional

class IdempotentGatewayEngine:
    MIN_GROSS_MARGIN_PCT = 35.0

    def __init__(self):
        # Almacén de idempotencia: key -> response_payload
        self.processed_requests: Dict[str, Dict[str, Any]] = {}
        # Rate-limiter Token-Bucket: user_id -> (tokens, last_update)
        self.rate_buckets: Dict[str, Tuple[float, float]] = {}

    def validate_margin_invariant(self, sale_price: float, direct_cost: float) -> Dict[str, Any]:
        """Invariante II: Margen Bruto = (Precio - Costo) / Precio >= 35%."""
        if sale_price <= 0:
            return {"valid": False, "error": "PRECIO_INVALIDO", "message": "El precio de venta debe ser > 0."}
        
        margin_pct = ((sale_price - direct_cost) / sale_price) * 100.0
        is_valid = margin_pct >= self.MIN_GROSS_MARGIN_PCT

        return {
            "valid": is_valid,
            "sale_price": sale_price,
            "direct_cost": direct_cost,
            "margin_pct": round(margin_pct, 2),
            "threshold_required": self.MIN_GROSS_MARGIN_PCT,
            "error": None if is_valid else "MARGEN_INSUFICIENTE_RECHAZADO"
        }

    def check_rate_limit(self, user_id: str, capacity: int = 10, fill_rate_per_sec: float = 1.0) -> bool:
        """Algoritmo Token-Bucket para limitar peticiones por segundo por usuario."""
        now = time.time()
        tokens, last_update = self.rate_buckets.get(user_id, (float(capacity), now))
        
        # Recargar tokens
        delta = now - last_update
        tokens = min(float(capacity), tokens + delta * fill_rate_per_sec)
        
        if tokens >= 1.0:
            self.rate_buckets[user_id] = (tokens - 1.0, now)
            return True
        else:
            self.rate_buckets[user_id] = (tokens, now)
            return False

    def process_carrier_billing_debit(
        self,
        msisdn: str,
        amount_ves: float,
        idempotency_key: str,
        carrier_prefix: str = "0416"
    ) -> Dict[str, Any]:
        """Ejecuta débito al saldo de la línea telefónica con garantía de idempotencia."""
        # 1. Comprobar Idempotencia previa
        if idempotency_key in self.processed_requests:
            cached = self.processed_requests[idempotency_key]
            cached_res = dict(cached)
            cached_res["idempotent_replay"] = True
            return cached_res

        # 2. Validar prefijo Telco (0416 / 0426)
        clean_msisdn = msisdn.replace("+", "").replace("-", "").strip()
        if not (clean_msisdn.startswith("0416") or clean_msisdn.startswith("0426") or clean_msisdn.startswith("58416") or clean_msisdn.startswith("58426")):
            return {
                "success": False,
                "error": "OPERADORA_NO_COMPATIBLE",
                "message": f"El número {msisdn} no pertenece a los rangos soportados (0416/0426)."
            }

        # 3. Procesar cobro (Simulación de BSS/OSS)
        telco_fee = round(amount_ves * 0.20, 2)     # 20% Comisión Telco
        merchant_net = round(amount_ves * 0.80, 2)  # 80% Liquidación Comercio

        result = {
            "success": True,
            "msisdn": clean_msisdn,
            "amount_debited_ves": amount_ves,
            "split": {
                "carrier_commission_ves": telco_fee,
                "merchant_net_ves": merchant_net
            },
            "idempotency_key": idempotency_key,
            "timestamp": time.time(),
            "idempotent_replay": False
        }

        # Guardar en almacén de idempotencia
        self.processed_requests[idempotency_key] = result
        return result

# Protocolo MCP Stdio
def run_mcp_stdio():
    gateway = IdempotentGatewayEngine()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "tools/list":
                tools = [
                    {
                        "name": "check_margin_invariant",
                        "description": "Verifica que el margen bruto de una oferta o servicio cumpla la Invariante II (>= 35%).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "sale_price": {"type": "number"},
                                "direct_cost": {"type": "number"}
                            },
                            "required": ["sale_price", "direct_cost"]
                        }
                    },
                    {
                        "name": "process_idempotent_debit",
                        "description": "Procesa un cobro de saldo telefónico (Carrier Billing) protegido con Idempotency-Key.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "msisdn": {"type": "string"},
                                "amount_ves": {"type": "number"},
                                "idempotency_key": {"type": "string"}
                            },
                            "required": ["msisdn", "amount_ves", "idempotency_key"]
                        }
                    }
                ]
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}) + "\n")
                sys.stdout.flush()
                
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                
                if name == "check_margin_invariant":
                    res = gateway.validate_margin_invariant(args["sale_price"], args["direct_cost"])
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}) + "\n")
                elif name == "process_idempotent_debit":
                    res = gateway.process_carrier_billing_debit(args["msisdn"], args["amount_ves"], args["idempotency_key"])
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mcp-idempotent-gateway server")
    parser.add_argument("--test", action="store_true", help="Ejecutar autoverificación formal con aserciones")
    args = parser.parse_args()
    
    if args.test:
        gw = IdempotentGatewayEngine()
        
        # 1. Margen válido (>=35%)
        m_ok = gw.validate_margin_invariant(sale_price=100.0, direct_cost=50.0) # Margen 50%
        assert m_ok["valid"] is True
        assert m_ok["margin_pct"] == 50.0
        
        # 2. Margen inválido (<35%)
        m_bad = gw.validate_margin_invariant(sale_price=100.0, direct_cost=75.0) # Margen 25%
        assert m_bad["valid"] is False
        assert m_bad["error"] == "MARGEN_INSUFICIENTE_RECHAZADO"
        
        # 3. Transacción idempotente de débito
        key = "IDEM-TX-998811"
        res1 = gw.process_carrier_billing_debit("0416-1234567", 50.0, key)
        assert res1["success"] is True
        assert res1["idempotent_replay"] is False
        
        # 4. Reintento con la misma clave (debe retornar respuesta cacheada sin re-cobrar)
        res2 = gw.process_carrier_billing_debit("0416-1234567", 50.0, key)
        assert res2["success"] is True
        assert res2["idempotent_replay"] is True
        
        # 5. Operadora no compatible
        res_bad_telco = gw.process_carrier_billing_debit("0414-9999999", 50.0, "KEY-2")
        assert res_bad_telco["success"] is False
        assert res_bad_telco["error"] == "OPERADORA_NO_COMPATIBLE"
        
        print("✅ IdempotentGatewayEngine: 5/5 Tests PASSED [Exit code: 0]")
        sys.exit(0)
    else:
        run_mcp_stdio()
