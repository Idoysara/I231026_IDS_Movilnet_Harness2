"""
Servicio Coordinador de Aplicación para Cazador de Ofertas Movilnet.
Estación 3: Dominio Puro y Motores de Cálculo Simbióticos.
Conecta los Repositorios Hexagonales ORM con el Ecosistema Simbiótico:
- mcp_spatial_radar (Haversine & 3 Anillos)
- mcp_crypto_token_vault (TOTP 60s & Firma HMAC-SHA256)
- mcp_idempotent_gateway (Carrier Billing & Split 20/80)
- mcp_universal_memory (SQLite FTS5 Memoria Presupuestada)
"""
import os
import sys
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

# Asegurar importación de la raíz local del servicio y del workspace
LOCAL_SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
for _p in [LOCAL_SERVICE_ROOT, WORKSPACE_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ecosistema_simbiotico_mcp_skills.mcp_servers.mcp_spatial_radar.server import SpatialRadarEngine
from ecosistema_simbiotico_mcp_skills.mcp_servers.mcp_crypto_token_vault.server import CryptoTokenVaultEngine
from ecosistema_simbiotico_mcp_skills.mcp_servers.mcp_idempotent_gateway.server import IdempotentGatewayEngine
from ecosistema_simbiotico_mcp_skills.mcp_servers.mcp_universal_memory.server import UniversalMemoryEngine

from ..domain.entities import (
    Comercio,
    Oferta,
    Cupon,
    TransaccionBilling,
    EstadoCupon,
    TierComercio,
    NivelUsuario,
    TipoCobertura
)
from ..domain.zones import resolver_zona, listar_zonas_disponibles
from ..domain.fsm import CouponFSM, IllegalCouponStateTransitionError
from ..domain.invariants import CazadorInvariants, DomainInvariantViolationError
from ..domain.rea_clean_room_deals_engine import (
    ReaCleanRoomDealsEngine,
    AdvancedPromotionRule,
    PromotionRuleType,
    CompactQRCodec,
    CashierAntiCollusionSentinel,
    RuleEvaluationResult
)

from ..infrastructure.persistence.database import SessionFactory, init_db
from ..infrastructure.persistence.models import (
    ComercioModel,
    OfertaModel,
    CuponModel,
    TransaccionBillingModel,
    BovedaHashesQuemadosModel
)
from ..infrastructure.persistence.repositories import (
    ComercioRepository,
    OfertaRepository,
    CuponRepository,
    BillingRepository
)

SEED_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/seed_data.json")

class CazadorApplicationService:
    def __init__(self, db_session: Optional[Session] = None, seed_path: Optional[str] = SEED_DATA_PATH):
        # 1. Motores simbióticos
        self.radar_engine = SpatialRadarEngine()
        self.vault_engine = CryptoTokenVaultEngine()
        self.gateway_engine = IdempotentGatewayEngine()
        try:
            self.memory_engine = UniversalMemoryEngine()
        except Exception:
            self.memory_engine = None

        # Motor Clean-Room Anti-Colusión REA
        self.anti_collusion_sentinel = CashierAntiCollusionSentinel()

        # Adaptador OCS de Movilnet Core
        try:
            from ..infrastructure.movilnet_ocs_adapter import MovilnetOCSAdapter
            self.ocs_adapter = MovilnetOCSAdapter()
        except Exception:
            self.ocs_adapter = None

        # 2. Sesión y Repositorios Hexagonales de Persistencia
        self.session = db_session or SessionFactory()
        self.comercio_repo = ComercioRepository(self.session)
        self.oferta_repo = OfertaRepository(self.session)
        self.cupon_repo = CuponRepository(self.session)
        self.billing_repo = BillingRepository(self.session)

        # 3. Memoria de Estado de Dominio
        self.comercios: Dict[str, Comercio] = {}
        self.ofertas: Dict[str, Oferta] = {}
        self.cupones: Dict[str, Cupon] = {}
        self.transacciones: Dict[str, TransaccionBilling] = {}

        # 4. Hidratar desde repositorios o cargar semilla
        self._inicializar_repositorios_y_dominio(seed_path)

    def _inicializar_repositorios_y_dominio(self, seed_path: Optional[str]) -> None:
        """Sincroniza la capa de dominio con la base de datos relacional y carga semilla si está vacía."""
        # Comprobar si hay comercios en base de datos
        comercios_db = self.comercio_repo.get_active()
        
        if not comercios_db and seed_path and os.path.exists(seed_path):
            self.cargar_semilla(seed_path)
        else:
            # Hidratar comercios
            for c_orm in comercios_db:
                tipo_cob = TipoCobertura(c_orm.tipo_cobertura) if hasattr(c_orm, "tipo_cobertura") and c_orm.tipo_cobertura in TipoCobertura._value2member_map_ else TipoCobertura.PUNTO_INTERES
                comercio = Comercio(
                    id=c_orm.id,
                    rif=c_orm.rif,
                    nombre=c_orm.nombre,
                    categoria=c_orm.categoria,
                    lat=c_orm.lat,
                    lon=c_orm.lon,
                    tier=TierComercio(c_orm.tier) if c_orm.tier in TierComercio._value2member_map_ else TierComercio.BASICO,
                    activo=c_orm.activo,
                    tipo_cobertura=tipo_cob,
                    zona_sector=getattr(c_orm, "zona_sector", None),
                    radio_cobertura_m=getattr(c_orm, "radio_cobertura_m", 500.0) or 500.0,
                    direccion=getattr(c_orm, "direccion", None)
                )
                self.comercios[comercio.id] = comercio

            # Hidratar ofertas
            for o_orm in self.oferta_repo.get_all():
                oferta = Oferta(
                    id=o_orm.id,
                    comercio_id=o_orm.comercio_id,
                    titulo=o_orm.titulo,
                    precio_regular_ves=o_orm.precio_regular_ves,
                    precio_oferta_ves=o_orm.precio_oferta_ves,
                    costo_directo_ves=o_orm.costo_directo_ves,
                    descuento_pct=o_orm.descuento_pct,
                    stock_disponible=o_orm.stock_disponible,
                    horario_validez=o_orm.horario_validez,
                    activa=o_orm.activa
                )
                self.ofertas[oferta.id] = oferta

            # Hidratar cupones
            for cup_orm in self.cupon_repo.get_all():
                cupon = Cupon(
                    uuid=cup_orm.uuid,
                    oferta_id=cup_orm.oferta_id,
                    usuario_msisdn=cup_orm.usuario_msisdn,
                    comercio_id=cup_orm.comercio_id,
                    codigo_dinamico=cup_orm.codigo_dinamico,
                    firma_hmac=cup_orm.firma_hmac,
                    estado=EstadoCupon(cup_orm.estado),
                    time_step_emision=cup_orm.time_step_emision,
                    expira_en_paso=cup_orm.time_step_emision + 1,
                    canjeado_en=cup_orm.canjeado_en
                )
                self.cupones[cupon.uuid] = cupon

    def cargar_semilla(self, file_path: str) -> None:
        """Carga y valida los comercios y ofertas semilla verificando invariantes y persistiendo."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for c_data in data.get("comercios", []):
            comercio = Comercio(**c_data)
            self.comercios[comercio.id] = comercio

            # Guardar en repositorio si no existe
            if not self.comercio_repo.get_by_id(comercio.id):
                c_orm = ComercioModel(
                    id=comercio.id,
                    rif=comercio.rif,
                    nombre=comercio.nombre,
                    categoria=comercio.categoria,
                    lat=comercio.lat,
                    lon=comercio.lon,
                    tier=comercio.tier.value,
                    activo=comercio.activo,
                    tipo_cobertura=comercio.tipo_cobertura.value,
                    zona_sector=comercio.zona_sector,
                    radio_cobertura_m=comercio.radio_cobertura_m,
                    direccion=comercio.direccion
                )
                self.comercio_repo.save(c_orm)

        for o_data in data.get("ofertas", []):
            # Validar Invariante II antes de registrar
            CazadorInvariants.validar_margen_bruto(
                o_data["precio_oferta_ves"],
                o_data["costo_directo_ves"]
            )
            oferta = Oferta(**o_data)
            self.ofertas[oferta.id] = oferta

            # Guardar en repositorio si no existe
            if not self.oferta_repo.get_by_id(oferta.id):
                margen = ((oferta.precio_oferta_ves - oferta.costo_directo_ves) / oferta.precio_oferta_ves) * 100.0
                o_orm = OfertaModel(
                    id=oferta.id,
                    comercio_id=oferta.comercio_id,
                    titulo=oferta.titulo,
                    precio_regular_ves=oferta.precio_regular_ves,
                    precio_oferta_ves=oferta.precio_oferta_ves,
                    costo_directo_ves=oferta.costo_directo_ves,
                    descuento_pct=oferta.descuento_pct,
                    margen_pct=round(margen, 2),
                    stock_disponible=oferta.stock_disponible,
                    horario_validez=oferta.horario_validez,
                    activa=oferta.activa
                )
                self.oferta_repo.save(o_orm)

    # =========================================================================
    # 1. GEOESPACIAL: Búsqueda y Clasificación por Radar (mcp_spatial_radar)
    # =========================================================================
    def buscar_ofertas_radar(
        self,
        user_lat: float,
        user_lon: float,
        max_distancia_m: float = 3000.0,
        categoria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula distancias geodésicas en sub-milisegundo hacia todos los comercios activos,
        clasifica en 3 anillos (500m, 1000m, 3000m) y vincula sus ofertas vigentes.
        """
        # Preparar candidatos desde memoria de dominio o repositorio
        candidatos = []
        candidatos_ron = []
        for c in self.comercios.values():
            if not c.activo:
                continue
            if categoria and c.categoria.lower() != categoria.lower():
                continue

            # Escenario 2: Run of Network cubre toda la ciudad metropolitana
            if c.tipo_cobertura == TipoCobertura.RUN_OF_NETWORK:
                candidatos_ron.append({
                    "id": c.id,
                    "nombre": c.nombre,
                    "rif": c.rif,
                    "lat": user_lat,
                    "lon": user_lon,
                    "categoria": c.categoria,
                    "tier": c.tier.value,
                    "tipo_cobertura": c.tipo_cobertura.value,
                    "zona_sector": c.zona_sector or "Toda la Ciudad (Run of Network)",
                    "radio_cobertura_m": c.radio_cobertura_m,
                    "distance_meters": 0.0,
                    "distance_km": 0.0,
                    "ring": "zona_1_inmediata",
                    "run_of_network": True
                })
                continue

            candidatos.append({
                "id": c.id,
                "nombre": c.nombre,
                "rif": c.rif,
                "lat": c.lat,
                "lon": c.lon,
                "categoria": c.categoria,
                "tier": c.tier.value,
                "tipo_cobertura": c.tipo_cobertura.value,
                "zona_sector": c.zona_sector,
                "radio_cobertura_m": c.radio_cobertura_m
            })

        radar_res = self.radar_engine.filter_proximity(
            user_lat=user_lat,
            user_lon=user_lon,
            candidates=candidatos,
            max_distance_m=max_distancia_m,
            limit=50
        )

        anillos = {
            "zona_1_inmediata": [],
            "zona_2_vecindario": [],
            "zona_3_urbana": []
        }

        total_ofertas_encontradas = 0
        items_candidatos = radar_res.get("results", radar_res.get("items", []))
        for m_item in items_candidatos:
            c_id = m_item["id"]
            c_ofertas = [
                o.model_dump() for o in self.ofertas.values()
                if o.comercio_id == c_id and o.activa and o.stock_disponible > 0 and o.descuento_pct > 0
            ]
            if not c_ofertas:
                continue

            entry = {
                "comercio": m_item,
                "ofertas": c_ofertas
            }
            ring_name = m_item.get("ring", "zona_3_urbana")
            if ring_name in anillos:
                anillos[ring_name].append(entry)
                total_ofertas_encontradas += len(c_ofertas)

        # Inyectar campañas Run of Network metropolitanas (Escenario 2)
        campanas_metropolitanas = []
        for ron_item in candidatos_ron:
            c_id = ron_item["id"]
            c_ofertas = [
                o.model_dump() for o in self.ofertas.values()
                if o.comercio_id == c_id and o.activa and o.stock_disponible > 0 and o.descuento_pct > 0
            ]
            if not c_ofertas:
                continue
            entry = {
                "comercio": ron_item,
                "ofertas": c_ofertas
            }
            campanas_metropolitanas.append(entry)
            anillos["zona_1_inmediata"].insert(0, entry)
            total_ofertas_encontradas += len(c_ofertas)

        return {
            "success": True,
            "user_coords": {"lat": user_lat, "lon": user_lon},
            "max_distance_meters": max_distancia_m,
            "total_comercios_en_rango": radar_res.get("total_matches", 0) + len(candidatos_ron),
            "total_ofertas_disponibles": total_ofertas_encontradas,
            "campanas_metropolitanas": campanas_metropolitanas,
            "anillos": anillos
        }

    # =========================================================================
    # 2. CUPONERÍA DINÁMICA: Emisión TOTP + HMAC-SHA256 (mcp_crypto_token_vault)
    # =========================================================================
    def reclamar_cupon(self, oferta_id: str, msisdn: str) -> Dict[str, Any]:
        """
        Reclama un cupón para una oferta:
        - Valida número Movilnet (0416/0426).
        - Valida Grounding Estricto B2C (prohibición de alucinación).
        - Valida Cuota de Usuario (máximo 3 cupones activos simultáneos).
        - Verifica y decrementa el stock disponible atómicamente.
        - Genera código dinámico y firma criptográfica mediante CryptoTokenVault.
        - Registra evento en Memoria Universal FTS5.
        """
        # 1. Validar prefijo Movilnet
        clean_msisdn = CazadorInvariants.validar_msisdn_movilnet(msisdn)

        # 2. Validar existencia y grounding estricto B2C en catálogo físico
        CazadorInvariants.validar_grounding_oferta_b2c(oferta_id, set(self.ofertas.keys()))
        
        oferta = self.ofertas[oferta_id]
        if not oferta.activa:
            raise DomainInvariantViolationError("Esta oferta ya no se encuentra activa.")
        if oferta.stock_disponible <= 0:
            raise DomainInvariantViolationError("Oferta agotada. No hay stock disponible.")

        # 3. Validar cuota de acaparamiento de usuario (máximo 3 cupones activos)
        cupones_activos_usuario = sum(
            1 for c in self.cupones.values()
            if c.usuario_msisdn == clean_msisdn and c.estado in (EstadoCupon.EMITIDO, EstadoCupon.RESERVADO)
        )
        if cupones_activos_usuario >= 3:
            raise DomainInvariantViolationError(
                "Límite de acaparamiento alcanzado: Máximo 3 cupones activos simultáneos por usuario. Canjee sus cupones pendientes."
            )

        # 4. Generar UUID y token dinámico en la bóveda
        cupon_uuid = f"CUP-{uuid.uuid4().hex[:8].upper()}"
        vault_res = self.vault_engine.generate_dynamic_token(
            coupon_id=cupon_uuid,
            user_id=clean_msisdn,
            merchant_id=oferta.comercio_id
        )

        # 5. Crear entidad de dominio
        cupon = Cupon(
            uuid=cupon_uuid,
            oferta_id=oferta.id,
            usuario_msisdn=clean_msisdn,
            comercio_id=oferta.comercio_id,
            codigo_dinamico=vault_res["dynamic_code"],
            firma_hmac=vault_res["full_signature"],
            estado=EstadoCupon.EMITIDO,
            expira_en_paso=vault_res["time_step"]
        )

        # 6. Reducción atómica de stock en memoria y persistencia
        oferta.stock_disponible -= 1
        if oferta.stock_disponible == 0:
            oferta.activa = False

        self.cupones[cupon.uuid] = cupon

        # Sincronizar en repositorios
        try:
            self.oferta_repo.decrement_stock_atomic(oferta.id)
            c_orm = CuponModel(
                uuid=cupon.uuid,
                oferta_id=cupon.oferta_id,
                comercio_id=cupon.comercio_id,
                usuario_msisdn=cupon.usuario_msisdn,
                codigo_dinamico=cupon.codigo_dinamico,
                firma_hmac=cupon.firma_hmac,
                estado=cupon.estado.value,
                time_step_emision=cupon.expira_en_paso
            )
            self.cupon_repo.save(c_orm)
        except Exception:
            pass

        # 7. Registrar evento en Memoria Universal FTS5
        if self.memory_engine:
            try:
                self.memory_engine.store(
                    layer="USER",
                    entity_id=clean_msisdn,
                    title=f"Reclamo de Cupón {cupon.uuid}",
                    content=f"Usuario {clean_msisdn} reclamó oferta '{oferta.titulo}' en comercio {oferta.comercio_id}",
                    tags="cupon,reclamo,b2c"
                )
            except Exception:
                pass

        comercio = self.comercios.get(oferta.comercio_id)

        return {
            "success": True,
            "cupon": cupon.model_dump(),
            "oferta": oferta.model_dump(),
            "comercio": comercio.model_dump() if comercio else None,
            "expires_in_seconds": vault_res["expires_in_seconds"]
        }

    # =========================================================================
    # 3. CANJE SEGURO: FSM + Verificación Anti-Replay en Bóveda
    # =========================================================================
    def canjear_cupon(
        self,
        cupon_id: str,
        msisdn: str,
        comercio_id: str,
        firma_hmac: str
    ) -> Dict[str, Any]:
        """
        Canjea un cupón en el POS del comercio:
        - Valida la FSM (EMITIDO -> CANJEADO o RESERVADO -> CANJEADO).
        - Verifica la firma criptográfica TOTP con tolerancia de reloj.
        - Quema el hash de forma atómica para prevenir ataques de replay o capturas de pantalla.
        - Registra evento de decisión en Memoria Universal FTS5.
        """
        clean_msisdn = CazadorInvariants.validar_msisdn_movilnet(msisdn)

        if cupon_id not in self.cupones:
            raise DomainInvariantViolationError(f"Cupón '{cupon_id}' no encontrado en el sistema.")

        cupon = self.cupones[cupon_id]

        if cupon.comercio_id != comercio_id:
            raise DomainInvariantViolationError(
                f"Cupón emitido para el comercio '{cupon.comercio_id}', no coincide con el comercio validador '{comercio_id}'."
            )

        # 1. Comprobación estricta de FSM
        CouponFSM.validar_transicion(cupon.estado, EstadoCupon.CANJEADO)

        # 2. Verificación de Bóveda Anti-Replay Persistente
        fingerprint = f"{cupon_id}:{firma_hmac.strip().upper()}"
        if self.cupon_repo.is_hash_burned(fingerprint):
            raise DomainInvariantViolationError(
                "Este cupón ya fue utilizado y quemado previamente en la bóveda de seguridad."
            )

        # 3. Validación criptográfica en la bóveda TOTP
        vault_redeem = self.vault_engine.verify_and_redeem(
            coupon_id=cupon_id,
            user_id=clean_msisdn,
            merchant_id=comercio_id,
            signature=firma_hmac,
            allow_skew_window=1
        )

        if not (vault_redeem.get("valid", False) or vault_redeem.get("success", False)):
            raise DomainInvariantViolationError(
                f"Fallo de validación de firma o expiración TOTP: {vault_redeem.get('message', 'Firma inválida')}."
            )

        # 4. Transición formal en el dominio
        cupon.estado = EstadoCupon.CANJEADO
        cupon.canjeado_en = time.time()

        # 5. Sincronizar quema y estado en repositorio persistente
        try:
            self.cupon_repo.burn_hash(fingerprint, cupon_id, comercio_id)
            self.cupon_repo.update_estado(cupon_id, "CANJEADO", canjeado_en=cupon.canjeado_en)
        except Exception:
            pass

        # 6. Registrar evento en Memoria Universal FTS5
        if self.memory_engine:
            try:
                self.memory_engine.store(
                    layer="DECISION",
                    entity_id=cupon_id,
                    title=f"Canje de Cupón {cupon_id}",
                    content=f"Cupón {cupon_id} canjeado exitosamente en comercio {comercio_id} para {clean_msisdn}",
                    tags="canje,pos,fsm"
                )
            except Exception:
                pass

        return {
            "success": True,
            "cupon_id": cupon_id,
            "estado": cupon.estado.value,
            "canjeado_en": cupon.canjeado_en,
            "mensaje": "¡Cupón canjeado exitosamente! Descuento aplicado en caja."
        }

    # =========================================================================
    # 4. CARRIER BILLING: Pasarela Idempotente y Split 20/80 (mcp_idempotent_gateway)
    # =========================================================================
    def procesar_carrier_billing(
        self,
        msisdn: str,
        monto_ves: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Procesa el cobro a través del saldo Movilnet:
        - Valida formato de idempotencia.
        - Aplica split transaccional: 20% Movilnet / 80% Comercio & Plataforma.
        - Asienta transacción en repositorio inmutable.
        """
        clean_msisdn = CazadorInvariants.validar_msisdn_movilnet(msisdn)
        clean_key = CazadorInvariants.validar_idempotencia_key(idempotency_key)

        # Usar motor de pasarela idempotente
        gw_res = self.gateway_engine.process_carrier_billing_debit(
            msisdn=clean_msisdn,
            amount_ves=monto_ves,
            idempotency_key=clean_key
        )

        if not gw_res.get("success", False):
            raise DomainInvariantViolationError(f"Error en pasarela de facturación: {gw_res.get('message')}")

        # Ejecutar débito en el OCS Movilnet
        ocs_info = None
        if self.ocs_adapter:
            try:
                ocs_info = self.ocs_adapter.debitar_saldo(
                    msisdn=clean_msisdn,
                    monto_ves=monto_ves,
                    idempotency_key=clean_key,
                    comercio_id="CARRIER_BILLING_OFERTA"
                )
                if not ocs_info.get("success"):
                    raise DomainInvariantViolationError(ocs_info.get("message", "Fallo al debitar en OCS Movilnet"))
            except DomainInvariantViolationError:
                raise
            except Exception:
                pass

        # Calcular split 20/80
        comision_telco, neto = CazadorInvariants.calcular_split_transaccional(monto_ves)

        tx_id = gw_res.get("transaction_id", f"TX-{uuid.uuid4().hex[:8].upper()}")
        
        # Registrar en dominio
        tx = TransaccionBilling(
            id=tx_id,
            idempotency_key=clean_key,
            msisdn=clean_msisdn,
            monto_ves=monto_ves,
            comision_telco_ves=comision_telco,
            neto_comercio_ves=neto,
            estatus="PROCESADO"
        )
        self.transacciones[tx.id] = tx

        # Sincronizar en repositorio persistente si no existe
        try:
            if not self.billing_repo.get_by_idempotency_key(clean_key):
                self.billing_repo.record_billing(
                    tx_id=tx.id,
                    idempotency_key=clean_key,
                    msisdn=clean_msisdn,
                    monto_ves=monto_ves,
                    comision_telco_ves=comision_telco,
                    neto_comercio_ves=neto,
                    estatus="PROCESADO"
                )
        except Exception:
            pass

        # Registrar en Memoria FTS5
        if self.memory_engine:
            try:
                self.memory_engine.store(
                    layer="PROJECT",
                    entity_id=tx.id,
                    title=f"Carrier Billing {tx.id}",
                    content=f"Cobro {monto_ves} VES a {clean_msisdn} con split {comision_telco} VES Movilnet",
                    tags="carrier_billing,telco,split"
                )
            except Exception:
                pass

        return {
            "success": True,
            "transaccion": tx.model_dump(),
            "idempotent_replay": gw_res.get("idempotent_replay", False),
            "carrier": "Movilnet 0416/0426",
            "split": {
                "telco_20_pct": comision_telco,
                "neto_80_pct": neto
            }
        }

    # =========================================================================
    # 5. PUBLICACIÓN DE OFERTAS Y COMERCIOS (Con Guardas Invariantes)
    # =========================================================================
    def registrar_comercio(self, datos_comercio: Dict[str, Any]) -> Comercio:
        comercio = Comercio(**datos_comercio)
        self.comercios[comercio.id] = comercio
        try:
            c_orm = ComercioModel(
                id=comercio.id,
                rif=comercio.rif,
                nombre=comercio.nombre,
                categoria=comercio.categoria,
                lat=comercio.lat,
                lon=comercio.lon,
                tier=comercio.tier.value,
                activo=comercio.activo,
                tipo_cobertura=comercio.tipo_cobertura.value,
                zona_sector=comercio.zona_sector,
                radio_cobertura_m=comercio.radio_cobertura_m,
                direccion=comercio.direccion
            )
            self.comercio_repo.save(c_orm)
        except Exception:
            pass
        return comercio

    def registrar_comercio_zero_friccion(
        self,
        nombre: str,
        rif: str,
        categoria: str,
        tipo_cobertura: str = "PUNTO_INTERES",
        zona_sector: Optional[str] = None,
        direccion: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_manual_m: Optional[float] = None,
        tier: str = "BASICO"
    ) -> Dict[str, Any]:
        """
        Registra un comercio aliado bajo el Modelo Espacial de Cero Fricción (3 Escenarios Automáticos).
        El anunciante o dueño de negocio NO tiene que ingresar ningún radio en metros ni calcular geometría.
        """
        if not nombre or len(nombre.strip()) < 2:
            raise DomainInvariantViolationError("El nombre comercial es obligatorio (mínimo 2 caracteres).")
        if not rif or len(rif.strip()) < 5:
            raise DomainInvariantViolationError("El RIF fiscal es obligatorio y debe tener formato válido.")

        clean_rif = rif.strip().upper()
        clean_nombre = nombre.strip()
        clean_categoria = categoria.strip() if categoria else "Comercio General"

        # Resolver Tipo de Cobertura
        tipo_str = (tipo_cobertura or "PUNTO_INTERES").strip().upper()
        if tipo_str not in TipoCobertura._value2member_map_:
            tipo_str = "PUNTO_INTERES"
        tipo_enum = TipoCobertura(tipo_str)

        escenario_num = 3
        escenario_desc = ""
        radio_final_m = 500.0
        zona_asignada = None

        if tipo_enum == TipoCobertura.ZONA:
            escenario_num = 1
            zona_meta = resolver_zona(zona_sector or direccion or "")
            if zona_meta:
                zona_asignada = zona_meta["nombre"]
                lat = float(lat if lat is not None else zona_meta["centroide"]["lat"])
                lon = float(lon if lon is not None else zona_meta["centroide"]["lon"])
                radio_final_m = float(zona_meta["radio_zona_m"])
                escenario_desc = f"Escenario 1: Polígono automático de Zona '{zona_asignada}' ({radio_final_m:.0f}m)"
            else:
                zona_asignada = zona_sector or "Zona Comercial Urbana"
                lat = float(lat if lat is not None else 10.4925)
                lon = float(lon if lon is not None else -66.8550)
                radio_final_m = 1200.0
                escenario_desc = f"Escenario 1: Sector '{zona_asignada}' con radio sectorial automático (1200m)"

        elif tipo_enum == TipoCobertura.RUN_OF_NETWORK:
            escenario_num = 2
            lat = float(lat if lat is not None else 10.4900)
            lon = float(lon if lon is not None else -66.8800)
            radio_final_m = CazadorInvariants.MAX_METROPOLITAN_RADIUS_METERS
            zona_asignada = "Toda la Ciudad (Run of Network)"
            escenario_desc = "Escenario 2: Toda la Ciudad (Run of Network) — Rotación metropolitana sin geocercas restrictivas"

        else:
            escenario_num = 3
            tipo_enum = TipoCobertura.PUNTO_INTERES
            if radio_manual_m is not None and float(radio_manual_m) > 0:
                radio_final_m = CazadorInvariants.validar_radio_comercio(float(radio_manual_m))
                escenario_desc = f"Escenario 3 (Avanzado): Radio manual explícito ({radio_final_m:.0f}m)"
            else:
                radio_final_m = CazadorInvariants.DEFAULT_SMART_RADIUS_METERS
                escenario_desc = "Escenario 3: Smart Default de 500m cinemático/peatonal automático (0 cálculos requeridos)"

            if lat is None or lon is None:
                if direccion:
                    zona_ref = resolver_zona(direccion)
                    if zona_ref:
                        lat = float(zona_ref["centroide"]["lat"])
                        lon = float(zona_ref["centroide"]["lon"])
                        zona_asignada = zona_ref["nombre"]
                if lat is None or lon is None:
                    lat = 10.4925
                    lon = -66.8550

        # Validar si ya existe por RIF
        existente = self.comercio_repo.get_by_rif(clean_rif)
        if existente:
            comercio_id = existente.id
        else:
            comercio_id = f"COM-{uuid.uuid4().hex[:6].upper()}"

        tier_enum = TierComercio(tier) if tier in TierComercio._value2member_map_ else TierComercio.BASICO

        comercio = Comercio(
            id=comercio_id,
            nombre=clean_nombre,
            rif=clean_rif,
            lat=float(lat),
            lon=float(lon),
            categoria=clean_categoria,
            tier=tier_enum,
            activo=True,
            tipo_cobertura=tipo_enum,
            zona_sector=zona_asignada,
            radio_cobertura_m=radio_final_m,
            direccion=direccion
        )
        self.comercios[comercio.id] = comercio

        try:
            c_orm = self.comercio_repo.get_by_id(comercio_id)
            if not c_orm:
                c_orm = ComercioModel(
                    id=comercio.id,
                    rif=comercio.rif,
                    nombre=comercio.nombre,
                    categoria=comercio.categoria,
                    lat=comercio.lat,
                    lon=comercio.lon,
                    tier=comercio.tier.value,
                    activo=comercio.activo,
                    tipo_cobertura=comercio.tipo_cobertura.value,
                    zona_sector=comercio.zona_sector,
                    radio_cobertura_m=comercio.radio_cobertura_m,
                    direccion=comercio.direccion
                )
                self.comercio_repo.save(c_orm)
            else:
                c_orm.nombre = comercio.nombre
                c_orm.categoria = comercio.categoria
                c_orm.lat = comercio.lat
                c_orm.lon = comercio.lon
                c_orm.tier = comercio.tier.value
                c_orm.activo = comercio.activo
                c_orm.tipo_cobertura = comercio.tipo_cobertura.value
                c_orm.zona_sector = comercio.zona_sector
                c_orm.radio_cobertura_m = comercio.radio_cobertura_m
                c_orm.direccion = comercio.direccion
                self.session.commit()
        except Exception:
            pass

        return {
            "success": True,
            "comercio": comercio.model_dump(),
            "escenario": {
                "numero": escenario_num,
                "nombre": tipo_enum.value,
                "descripcion": escenario_desc,
                "radio_aplicado_m": radio_final_m,
                "friccion_usuario": "0 metros ingresados (100% automatizado)" if not radio_manual_m else "Radio manual opcional aplicado"
            }
        }

    def publicar_oferta(self, datos_oferta: Dict[str, Any]) -> Oferta:
        # Validar Invariante II (Margen >= 35%)
        CazadorInvariants.validar_margen_bruto(
            datos_oferta["precio_oferta_ves"],
            datos_oferta["costo_directo_ves"]
        )
        oferta = Oferta(**datos_oferta)
        self.ofertas[oferta.id] = oferta
        try:
            margen = ((oferta.precio_oferta_ves - oferta.costo_directo_ves) / oferta.precio_oferta_ves) * 100.0
            o_orm = OfertaModel(
                id=oferta.id,
                comercio_id=oferta.comercio_id,
                titulo=oferta.titulo,
                precio_regular_ves=oferta.precio_regular_ves,
                precio_oferta_ves=oferta.precio_oferta_ves,
                costo_directo_ves=oferta.costo_directo_ves,
                descuento_pct=oferta.descuento_pct,
                margen_pct=round(margen, 2),
                stock_disponible=oferta.stock_disponible,
                horario_validez=oferta.horario_validez,
                activa=oferta.activa
            )
            self.oferta_repo.save(o_orm)
        except Exception:
            pass
        return oferta

    def listar_comercios(self) -> List[Comercio]:
        return list(self.comercios.values())

    def listar_ofertas(self) -> List[Oferta]:
        return list(self.ofertas.values())

    def obtener_cupones_usuario(self, msisdn: str) -> List[Dict[str, Any]]:
        """Retorna todos los cupones asociados a un usuario Movilnet."""
        CazadorInvariants.validar_msisdn_movilnet(msisdn)
        if self.cupon_repo:
            cupones_orm = self.cupon_repo.get_by_user(msisdn)
            return [c.to_dict() for c in cupones_orm]
        return [
            c.model_dump() for c in self.cupones.values()
            if c.usuario_msisdn == msisdn
        ]

    def obtener_historial_billing(self, msisdn: str) -> List[Dict[str, Any]]:
        """Retorna el historial de débitos Carrier Billing para un número Movilnet."""
        CazadorInvariants.validar_msisdn_movilnet(msisdn)
        if self.billing_repo:
            txs_orm = self.billing_repo.get_by_msisdn(msisdn)
            return [tx.to_dict() for tx in txs_orm]
        return [
            tx for tx in self.transacciones.values()
            if tx.get("msisdn") == msisdn
        ]

    def obtener_resumen_metricas(self) -> Dict[str, Any]:
        canjeados = sum(1 for c in self.cupones.values() if c.estado == EstadoCupon.CANJEADO)
        emitidos = len(self.cupones)
        return {
            "total_comercios": len(self.comercios),
            "total_ofertas": len(self.ofertas),
            "total_cupones_emitidos": emitidos,
            "total_cupones_canjeados": canjeados,
            "total_transacciones_billing": len(self.transacciones),
            "tasa_canje_pct": round((canjeados / emitidos * 100.0), 2) if emitidos > 0 else 0.0
        }

    # ==============================================================================
    # MÉTODOS REA CLEAN-ROOM: REGLAS AVANZADAS Y QR COMPACTO TIPO CASHEA
    # ==============================================================================

    def evaluar_regla_promocion_avanzada(
        self,
        rule: AdvancedPromotionRule,
        cantidad_solicitada: int = 1,
        monto_cesta_ves: float = 0.0,
        hora_actual_str: Optional[str] = None
    ) -> RuleEvaluationResult:
        """Evalúa una regla de descuento avanzada clean-room garantizando margen >= 35%."""
        return ReaCleanRoomDealsEngine.evaluate_rule(
            rule=rule,
            cantidad_solicitada=cantidad_solicitada,
            monto_cesta_ves=monto_cesta_ves,
            hora_actual_str=hora_actual_str
        )

    def generar_qr_compacto_cashea(self, deal_id: str, msisdn: str, totp_token: str) -> str:
        """Genera payload QR compacto de alta velocidad para terminales POS."""
        secret_str = self.vault_engine.secret.decode("utf-8") if isinstance(self.vault_engine.secret, bytes) else str(self.vault_engine.secret)
        return CompactQRCodec.encode(
            deal_id=deal_id,
            msisdn=msisdn,
            totp_token=totp_token,
            secret_key=secret_str
        )

    def verificar_qr_compacto_cashea(self, compact_qr: str, terminal_id: str = "pos-caja-default") -> Dict[str, Any]:
        """Decodifica y verifica la firma y tasa de terminal del QR compacto."""
        self.anti_collusion_sentinel.audit_terminal_rate(terminal_id)
        secret_str = self.vault_engine.secret.decode("utf-8") if isinstance(self.vault_engine.secret, bytes) else str(self.vault_engine.secret)
        return CompactQRCodec.decode(compact_qr, secret_str)
