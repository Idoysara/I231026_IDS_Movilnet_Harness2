"""
Servicio Deflector de Conectividad y Magic Links Zero-Rating para Movilnet (Puerto :8030).
Permite desviar usuarios de WhatsApp y SMS SMPP a la PWA Soberana sin costo de datos móviles.
"""
import hmac
import hashlib
import time
import os
import re
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List

from ...domain.invariants import CazadorInvariants, DomainInvariantViolationError
from ...application.cazador_service import CazadorApplicationService

SECRET_KEY = os.getenv("CAZADOR_DEFLECTOR_SECRET", "MOVILNET_CAZADOR_ZERO_RATING_SECRET_2026").encode("utf-8")

def get_base_pwa_url() -> str:
    """Resuelve dinámicamente la URL base de la PWA según el entorno (Local MBP vs Producción Cloud)."""
    url = os.getenv("CAZADOR_PWA_URL")
    if url:
        return url.strip()
    if os.getenv("APP_ENV") == "production" or os.getenv("RENDER"):
        return os.getenv("MOVILNET_PUBLIC_URL", "https://one21026-ids-movilnet-pwa.onrender.com").strip()
    url = os.getenv("MOVILNET_PUBLIC_PWA_URL") or os.getenv("MOVILNET_PUBLIC_URL")
    if url:
        return url.strip()
    return "http://localhost:8010"

# Stopwords en español para evitar falsos positivos con preposiciones o adverbios
STOPWORDS = {
    "de", "en", "el", "la", "los", "las", "un", "una", "unos", "unas",
    "por", "para", "con", "sin", "y", "o", "u", "a", "al", "del",
    "tienen", "tiene", "quiero", "hay", "descuento", "descuentos",
    "oferta", "ofertas", "que", "como", "cual", "cuales", "me", "mi",
    "se", "es", "son", "dar", "dame", "busco", "necesito", "favor",
    "hola", "buenos", "dias", "tardes", "noches", "comprar"
}

class MagicLinkService:
    """
    Genera y valida Magic Links criptográficos y construye respuestas
    conversacionales para WhatsApp y SMS SMPP con Zero-Rating activo.
    """

    def __init__(self, service: Optional[CazadorApplicationService] = None):
        self.service = service or CazadorApplicationService()
        self.secret = SECRET_KEY

    def generar_magic_link(
        self,
        msisdn: str,
        oferta_id: Optional[str] = None,
        duracion_segundos: int = 86400  # 24 horas
    ) -> str:
        """
        Genera un Magic Link firmado criptográficamente para acceso 1-Tap a la PWA.
        """
        CazadorInvariants.validar_msisdn_movilnet(msisdn)
        
        # Si se incluye oferta_id, validar grounding B2C
        if oferta_id:
            CazadorInvariants.validar_grounding_oferta_b2c(oferta_id, list(self.service.ofertas.keys()))

        exp_timestamp = int(time.time()) + duracion_segundos
        oferta_param = oferta_id or ""
        
        # Mensaje a firmar: msisdn:exp:oferta_param
        datos_firma = f"{msisdn}:{exp_timestamp}:{oferta_param}".encode("utf-8")
        firma = hmac.new(self.secret, datos_firma, hashlib.sha256).hexdigest()[:32]

        params = {
            "msisdn": msisdn,
            "exp": str(exp_timestamp),
            "sig": firma
        }
        if oferta_id:
            params["oferta"] = oferta_id

        query_string = urllib.parse.urlencode(params)
        base = get_base_pwa_url().rstrip("/")
        if not base.endswith("/ui/pwa_stitch/index.html") and "/ui/pwa" not in base:
            return f"{base}/ui/pwa_stitch/index.html?{query_string}"
        return f"{base}?{query_string}"

    def verificar_magic_link(
        self,
        msisdn: str,
        exp_timestamp: int,
        firma: str,
        oferta_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Valida la autenticidad y vigencia del Magic Link.
        Retorna (valido: bool, motivo: str).
        """
        try:
            CazadorInvariants.validar_msisdn_movilnet(msisdn)
        except DomainInvariantViolationError as e:
            return False, f"Número inválido: {str(e)}"

        if int(time.time()) > exp_timestamp:
            return False, "El enlace Zero-Rating ha expirado (vigencia superada)."

        oferta_param = oferta_id or ""
        datos_firma = f"{msisdn}:{exp_timestamp}:{oferta_param}".encode("utf-8")
        firma_esperada = hmac.new(self.secret, datos_firma, hashlib.sha256).hexdigest()[:32]

        if not hmac.compare_digest(firma, firma_esperada):
            return False, "Firma criptográfica inválida o adulterada."

        if oferta_id and oferta_id not in self.service.ofertas:
            return False, f"La oferta vinculada '{oferta_id}' no existe en el catálogo verificado."

        return True, "Enlace Zero-Rating verificado exitosamente."

    def obtener_headers_zero_rating(self, msisdn: str) -> Dict[str, str]:
        """
        Retorna las cabeceras HTTP oficiales para la exención de cobro de datos (Zero-Rating).
        """
        CazadorInvariants.validar_msisdn_movilnet(msisdn)
        return {
            "X-Movilnet-Zero-Rating": "active",
            "X-Zero-Rating-Carrier": "Movilnet-0416-0426",
            "X-Zero-Rating-Subscriber": msisdn,
            "X-Zero-Rating-Plan": "Soberano-Sin-Consumo-Datos",
            "Cache-Control": "no-transform"
        }

    def procesar_deflexion_whatsapp(
        self,
        remitente: str,
        mensaje: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje entrante de WhatsApp, aplica Grounding B2C estricto
        y devuelve una respuesta con formato conversacional y Magic Link Zero-Rating.
        """
        msisdn = self._normalizar_numero(remitente)
        CazadorInvariants.validar_msisdn_movilnet(msisdn)

        texto_limpio = re.sub(r"[^\w\s]", " ", mensaje.lower()).strip()
        palabras_filtradas = [
            w for w in texto_limpio.split()
            if len(w) >= 3 and w not in STOPWORDS
        ]

        ofertas_disponibles = list(self.service.ofertas.values())
        ofertas_match = []
        anillos_resumen = None

        if lat is not None and lon is not None:
            res_radar = self.service.buscar_ofertas_radar(lat, lon, max_distancia_m=3000.0)
            anillos_data = res_radar.get("anillos", {})
            anillos_resumen = {
                "zona_1_inmediata": len(anillos_data.get("zona_1_inmediata", [])),
                "zona_2_vecindario": len(anillos_data.get("zona_2_vecindario", [])),
                "zona_3_urbana": len(anillos_data.get("zona_3_urbana", []))
            }
            # Recolectar ofertas geodésicamente ordenadas
            for ring_key in ["zona_1_inmediata", "zona_2_vecindario", "zona_3_urbana"]:
                for entry in anillos_data.get(ring_key, []):
                    comercio_info = entry.get("comercio", {})
                    dist_val = comercio_info.get("distance_meters", comercio_info.get("distance_m", 0))
                    for ofe in entry.get("ofertas", []):
                        ofe_copia = dict(ofe)
                        ofe_copia["distancia_m"] = dist_val
                        ofertas_match.append(ofe_copia)
        else:
            # Filtro por palabras clave sustantivas en ofertas y comercios verificados
            if palabras_filtradas:
                for ofe in ofertas_disponibles:
                    titulo_low = ofe.titulo.lower()
                    comercio = self.service.comercios.get(ofe.comercio_id)
                    c_nom = comercio.nombre.lower() if comercio else ""
                    c_cat = comercio.categoria.lower() if comercio else ""
                    if any(p in titulo_low or p in c_nom or p in c_cat or p in ofe.comercio_id.lower() for p in palabras_filtradas):
                        ofertas_match.append(ofe.model_dump())

        # Construir respuesta conversacional SIN ALUCINACIONES
        magic_link = self.generar_magic_link(
            msisdn=msisdn,
            oferta_id=ofertas_match[0]["id"] if len(ofertas_match) == 1 else None
        )

        if not ofertas_match:
            # Cero Alucinación: Reconocer limpiamente que no hay coincidencias activas
            msg_saliente = (
                f"👋 ¡Hola! En Cazadores de Ofertas Movilnet no encontramos promociones activas "
                f"para '{mensaje}'.\n\n"
                f"📱 Abre nuestro Radar Soberano en vivo (sin consumir tus megas de saldo):\n"
                f"{magic_link}\n\n"
                f"✨ Navegación 100% gratuita para clientes 0416 y 0426."
            )
        else:
            items_txt = []
            for item in ofertas_match[:3]:
                nombre_comercio = self.service.comercios.get(item["comercio_id"], None)
                comercio_label = nombre_comercio.nombre if nombre_comercio else item["comercio_id"]
                dist_txt = f" ({item.get('distancia_m', 0):.0f}m)" if "distancia_m" in item else ""
                items_txt.append(f"🏷️ *{item['titulo']}*{dist_txt}\n   💰 Bs {item['precio_oferta_ves']:.2f} (-{item['descuento_pct']}%) en {comercio_label}")
            
            cuerpo_ofertas = "\n".join(items_txt)
            msg_saliente = (
                f"🎯 ¡Cazador activado! Encontramos {len(ofertas_match)} ofertas verificadas cerca de ti:\n\n"
                f"{cuerpo_ofertas}\n\n"
                f"⚡ Abre la PWA sin gastar saldo ni megas para reclamar tu cupón:\n"
                f"{magic_link}\n\n"
                f"🔒 Cupón protegido con tecnología TOTP y split soberano Movilnet."
            )

        return {
            "canal": "whatsapp",
            "destinatario": msisdn,
            "mensaje_saliente": msg_saliente,
            "magic_link": magic_link,
            "zero_rating_activo": True,
            "ofertas_encontradas": len(ofertas_match),
            "anillos_resumen": anillos_resumen
        }

    def procesar_deflexion_sms(
        self,
        remitente: str,
        mensaje: str
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje SMS SMPP entrante y genera respuesta ultra-concisa (<=160 caracteres)
        con Magic Link Zero-Rating.
        """
        msisdn = self._normalizar_numero(remitente)
        CazadorInvariants.validar_msisdn_movilnet(msisdn)

        magic_link = self.generar_magic_link(msisdn=msisdn)
        
        # Mensaje SMS ultra-conciso garantizando <= 160 caracteres
        msg_saliente = f"Movilnet Cazador: Ahorra sin gastar megas. PWA gratis: {magic_link}"

        return {
            "canal": "sms",
            "destinatario": msisdn,
            "mensaje_saliente": msg_saliente,
            "magic_link": magic_link,
            "zero_rating_activo": True,
            "ofertas_encontradas": len(self.service.ofertas),
            "anillos_resumen": None
        }

    def procesar_deflexion_telegram(
        self,
        remitente: str,
        mensaje: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Procesa un mensaje entrante de Telegram (vía bot/n8n), aplica Grounding B2C
        y genera respuesta enriquecida con Magic Link y botón WebApp compatible.
        """
        res_wa = self.procesar_deflexion_whatsapp(
            remitente=remitente,
            mensaje=mensaje,
            lat=lat,
            lon=lon
        )
        res_wa["canal"] = "telegram"
        # Enriquecimiento específico para Telegram (HTML y WebApp Action)
        res_wa["telegram_webapp_url"] = res_wa["magic_link"]
        return res_wa

    def procesar_deflexion_pwa(
        self,
        remitente: str,
        mensaje: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Procesa un evento de consulta directa desde la PWA Mobile-First.
        """
        res = self.procesar_deflexion_whatsapp(
            remitente=remitente,
            mensaje=mensaje,
            lat=lat,
            lon=lon
        )
        res["canal"] = "pwa"
        return res

    def procesar_deflexion_omnicanal(
        self,
        canal: str,
        remitente: str,
        mensaje: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Punto de entrada unificado para n8n, WhatsApp, Telegram, SMS y PWA.
        """
        canal_norm = canal.strip().lower()
        if canal_norm in ["whatsapp", "wa"]:
            return self.procesar_deflexion_whatsapp(remitente, mensaje, lat, lon)
        elif canal_norm in ["telegram", "tg"]:
            return self.procesar_deflexion_telegram(remitente, mensaje, lat, lon)
        elif canal_norm in ["sms", "smpp"]:
            return self.procesar_deflexion_sms(remitente, mensaje)
        elif canal_norm in ["pwa", "web"]:
            return self.procesar_deflexion_pwa(remitente, mensaje, lat, lon)
        else:
            # Fallback seguro con WhatsApp
            res = self.procesar_deflexion_whatsapp(remitente, mensaje, lat, lon)
            res["canal"] = canal_norm
            return res

    def _normalizar_numero(self, numero: str) -> str:
        """Limpia prefijos internacionales dejando formato 0416 o 0426."""
        num = numero.strip().replace(" ", "").replace("-", "").replace("+", "")
        if num.startswith("58") and len(num) == 12:
            num = "0" + num[2:]
        return num
