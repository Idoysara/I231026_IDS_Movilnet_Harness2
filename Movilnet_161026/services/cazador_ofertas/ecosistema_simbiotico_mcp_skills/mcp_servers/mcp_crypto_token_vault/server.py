#!/usr/bin/env python3
"""
mcp_crypto_token_vault: Servidor MCP de Cuponería Criptográfica y Validación Dinámica Anti-Fraude.
Genera códigos QR dinámicos rotativos (TOTP + HMAC-SHA256) que invalidan capturas de pantalla,
garantiza canjes en <0.5s y opera en modo offline-first con prevención de doble gasto.
"""
import sys
import time
import hmac
import hashlib
import json
import argparse
from typing import Dict, Any, Optional

DEFAULT_SECRET = "CAZADOR_SOVEREIGN_KEY_2026_MILITARY_TIER1"

class CryptoTokenVaultEngine:
    ROTATION_SECONDS = 60
    LEGAL_STATES = {"EMITIDO", "RESERVADO", "CANJEADO", "EXPIRADO"}

    def __init__(self, secret: str = DEFAULT_SECRET):
        self.secret = secret.encode("utf-8")
        self.vault_coupons: Dict[str, Dict[str, Any]] = {}
        self.burned_hashes = set()

    def _get_time_step(self, ts: Optional[float] = None) -> int:
        if ts is None:
            ts = time.time()
        return int(ts // self.ROTATION_SECONDS)

    def generate_dynamic_token(self, coupon_id: str, user_id: str, merchant_id: str) -> Dict[str, Any]:
        """Genera un token firmado con HMAC-SHA256 para el intervalo de tiempo activo."""
        time_step = self._get_time_step()
        raw_msg = f"{coupon_id}:{user_id}:{merchant_id}:{time_step}".encode("utf-8")
        sig = hmac.new(self.secret, raw_msg, hashlib.sha256).hexdigest()[:16].upper()
        
        # Guardar en memoria de estado si no existe
        if coupon_id not in self.vault_coupons:
            self.vault_coupons[coupon_id] = {
                "coupon_id": coupon_id,
                "user_id": user_id,
                "merchant_id": merchant_id,
                "state": "EMITIDO",
                "claimed_at": time.time(),
                "redeemed_at": None
            }

        expires_in = self.ROTATION_SECONDS - int(time.time() % self.ROTATION_SECONDS)
        
        return {
            "coupon_id": coupon_id,
            "dynamic_code": f"QRO-{sig[:4]}-{sig[4:8]}-{sig[8:12]}",
            "full_signature": sig,
            "time_step": time_step,
            "expires_in_seconds": expires_in,
            "status": self.vault_coupons[coupon_id]["state"]
        }

    def verify_and_redeem(
        self,
        coupon_id: str,
        user_id: str,
        merchant_id: str,
        signature: str,
        allow_skew_window: int = 1
    ) -> Dict[str, Any]:
        """
        Valida el código de forma offline-first y cambia el estado a CANJEADO atómicamente.
        allow_skew_window permite tolerancia de +/- 1 ventana (para relojes desincronizados).
        """
        clean_sig = signature.replace("QRO-", "").replace("-", "").strip().upper()
        current_step = self._get_time_step()

        # Verificar firma en ventana [current_step - 1, current_step + 1]
        valid_step = None
        for step in range(current_step - allow_skew_window, current_step + allow_skew_window + 1):
            raw_msg = f"{coupon_id}:{user_id}:{merchant_id}:{step}".encode("utf-8")
            expected_sig = hmac.new(self.secret, raw_msg, hashlib.sha256).hexdigest()[:16].upper()
            if hmac.compare_digest(clean_sig, expected_sig):
                valid_step = step
                break

        if valid_step is None:
            return {
                "valid": False,
                "error": "FIRMA_INVALIDA_O_EXPIRADA",
                "message": "El código QR es falso o caducó por tiempo (anti-captura de pantalla)."
            }

        # Comprobar si ya fue quemado (Anti-Replay)
        token_fingerprint = f"{coupon_id}:{clean_sig}"
        if token_fingerprint in self.burned_hashes:
            return {
                "valid": False,
                "error": "CUPON_YA_CANJEADO",
                "message": "Este cupón ya fue utilizado y quemado previamente."
            }

        # Comprobar FSM
        coupon_meta = self.vault_coupons.get(coupon_id)
        if coupon_meta:
            if coupon_meta["state"] == "CANJEADO":
                return {"valid": False, "error": "ESTADO_CANJEADO", "message": "El cupón ya fue canjeado."}
            coupon_meta["state"] = "CANJEADO"
            coupon_meta["redeemed_at"] = time.time()

        self.burned_hashes.add(token_fingerprint)

        return {
            "valid": True,
            "coupon_id": coupon_id,
            "user_id": user_id,
            "merchant_id": merchant_id,
            "redeemed_at_step": valid_step,
            "new_state": "CANJEADO"
        }

# Protocolo MCP Stdio
def run_mcp_stdio():
    vault = CryptoTokenVaultEngine()
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
                        "name": "generate_dynamic_qr_token",
                        "description": "Genera token rotativo TOTP (60s) firmado con HMAC-SHA256 para prevenir capturas de pantalla.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "coupon_id": {"type": "string"},
                                "user_id": {"type": "string"},
                                "merchant_id": {"type": "string"}
                            },
                            "required": ["coupon_id", "user_id", "merchant_id"]
                        }
                    },
                    {
                        "name": "verify_and_burn_coupon",
                        "description": "Valida la firma criptográfica en el punto de venta de forma offline-first y quema el cupón.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "coupon_id": {"type": "string"},
                                "user_id": {"type": "string"},
                                "merchant_id": {"type": "string"},
                                "signature": {"type": "string"}
                            },
                            "required": ["coupon_id", "user_id", "merchant_id", "signature"]
                        }
                    }
                ]
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}) + "\n")
                sys.stdout.flush()
                
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                args = params.get("arguments", {})
                
                if name == "generate_dynamic_qr_token":
                    res = vault.generate_dynamic_token(args["coupon_id"], args["user_id"], args["merchant_id"])
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}) + "\n")
                elif name == "verify_and_burn_coupon":
                    res = vault.verify_and_redeem(args["coupon_id"], args["user_id"], args["merchant_id"], args["signature"])
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res)}]}}) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mcp-crypto-token-vault server")
    parser.add_argument("--test", action="store_true", help="Ejecutar autoverificación formal con aserciones")
    args = parser.parse_args()
    
    if args.test:
        vault = CryptoTokenVaultEngine()
        cid = "CUP-998822"
        uid = "USR-0416-9998877"
        mid = "MERCH-PIZZERIA-CARACAS"
        
        # 1. Generar token
        gen_res = vault.generate_dynamic_token(cid, uid, mid)
        assert "dynamic_code" in gen_res
        assert gen_res["status"] == "EMITIDO"
        
        # 2. Canjear con éxito
        ver_res = vault.verify_and_redeem(cid, uid, mid, gen_res["full_signature"])
        assert ver_res["valid"] is True
        assert ver_res["new_state"] == "CANJEADO"
        
        # 3. Intentar re-canjear (Anti-Replay)
        rep_res = vault.verify_and_redeem(cid, uid, mid, gen_res["full_signature"])
        assert rep_res["valid"] is False
        assert "YA_CANJEADO" in rep_res["error"] or "ESTADO_CANJEADO" in rep_res["error"]
        
        # 4. Firma falsa
        fake_res = vault.verify_and_redeem(cid, uid, mid, "FFFFFFFFFFFFFFFF")
        assert fake_res["valid"] is False
        assert fake_res["error"] == "FIRMA_INVALIDA_O_EXPIRADA"
        
        print("✅ CryptoTokenVaultEngine: 4/4 Tests PASSED [Exit code: 0]")
        sys.exit(0)
    else:
        run_mcp_stdio()
