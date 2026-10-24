/**
 * noc_dashboard.js — Lógica de Telemetría en Tiempo Real para el NOC/CCO Movilnet
 * Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
 * Autonomía: Antigravity Nivel 5 Swarm Telemetry
 */

(function () {
  'use strict';

  // Configuración de Polling y Endpoints
  const CONFIG = {
    metricsEndpoint: '/api/v1/metrics/live',
    statusEndpoint: '/api/v1/noc/status',
    pollIntervalMs: 5000,
    requestTimeoutMs: 4000
  };

  // Elementos DOM Claves
  const DOM = {
    clockTime: document.getElementById('noc-clock-time'),
    clockDate: document.getElementById('noc-clock-date'),
    refreshBtn: document.getElementById('btn-manual-refresh'),
    connectionStatusText: document.getElementById('noc-conn-status-text'),
    connectionPulse: document.getElementById('noc-conn-pulse'),
    
    // Top KPIs
    kpiTotalSubs: document.getElementById('kpi-total-subs'),
    kpiActiveLines: document.getElementById('kpi-active-lines'),
    kpiC2PRechargeVes: document.getElementById('kpi-c2p-ves'),
    kpiC2PRechargeUsd: document.getElementById('kpi-c2p-usd'),
    kpiSwarmSla: document.getElementById('kpi-swarm-sla'),
    kpiBcvRate: document.getElementById('kpi-bcv-rate'),

    // Swarm Cards
    agentN1Lat: document.getElementById('agent-n1-lat'),
    agentN1Tps: document.getElementById('agent-n1-tps'),
    agentN2Lat: document.getElementById('agent-n2-lat'),
    agentN2Tps: document.getElementById('agent-n2-tps'),
    agentN3Lat: document.getElementById('agent-n3-lat'),
    agentN3Locks: document.getElementById('agent-n3-locks'),
    agentN4Lat: document.getElementById('agent-n4-lat'),
    agentN4Ret: document.getElementById('agent-n4-ret'),

    // Security Table
    securityTbody: document.getElementById('noc-security-tbody'),

    // Banks Table
    banksTbody: document.getElementById('noc-banks-tbody'),

    // Radio Network
    coreAvail: document.getElementById('net-core-avail'),
    enodebCount: document.getElementById('net-enodeb-count'),
    netThroughput: document.getElementById('net-throughput'),
    netTraffic: document.getElementById('net-traffic'),
    conatelIndex: document.getElementById('net-conatel-index')
  };

  /**
   * Actualiza el reloj oficial de operaciones VET (-0400).
   */
  function updateClock() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    if (DOM.clockTime) {
      DOM.clockTime.textContent = `${hours}:${minutes}:${seconds} VET`;
    }

    if (DOM.clockDate) {
      const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
      DOM.clockDate.textContent = now.toLocaleDateString('es-VE', options).toUpperCase();
    }
  }

  /**
   * Formatea números grandes con separadores de miles y decimales venezolanos.
   */
  function formatNumber(num, decimals = 0) {
    if (num === null || num === undefined || isNaN(num)) return '--';
    return Number(num).toLocaleString('es-VE', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  /**
   * Renderiza los datos de telemetría en la UI del Dashboard.
   */
  function renderMetrics(data) {
    if (!data) return;

    // 1. Top KPIs
    if (data.subscribers_kpis) {
      const sub = data.subscribers_kpis;
      if (DOM.kpiTotalSubs) DOM.kpiTotalSubs.textContent = formatNumber(sub.total_installed_base);
      if (DOM.kpiActiveLines) DOM.kpiActiveLines.textContent = formatNumber(sub.active_subscribers);
    }

    // 2. Control Financiero C2P
    if (data.fintech_c2p_control) {
      const fin = data.fintech_c2p_control;
      if (DOM.kpiC2PRechargeVes) DOM.kpiC2PRechargeVes.textContent = `Bs. ${formatNumber(fin.today_total_recharge_ves, 2)}`;
      if (DOM.kpiC2PRechargeUsd) DOM.kpiC2PRechargeUsd.textContent = `≈ $${formatNumber(fin.today_total_usd_equivalent, 2)}`;
      if (DOM.kpiBcvRate) DOM.kpiBcvRate.textContent = `${formatNumber(fin.bcv_rate, 2)} Bs/$`;

      // Tabla de Bancos
      if (DOM.banksTbody && Array.isArray(fin.top_banks)) {
        DOM.banksTbody.innerHTML = '';
        fin.top_banks.forEach((b) => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><strong>${b.bank}</strong></td>
            <td><span class="noc-badge info">${b.share_pct}%</span></td>
            <td><span class="noc-badge success">ONLINE</span></td>
          `;
          DOM.banksTbody.appendChild(tr);
        });
      }
    }

    // 3. Enjambre Swarm Nivel 5
    if (data.swarm_orchestration) {
      const swarm = data.swarm_orchestration;
      if (DOM.kpiSwarmSla) DOM.kpiSwarmSla.textContent = `${swarm.global_sla_compliance}%`;

      if (swarm.agents) {
        const ag = swarm.agents;
        if (ag.N1_CUSTOMER_CARE) {
          if (DOM.agentN1Lat) DOM.agentN1Lat.textContent = `${ag.N1_CUSTOMER_CARE.latency_avg_ms.toFixed(3)} ms`;
          if (DOM.agentN1Tps) DOM.agentN1Tps.textContent = `${ag.N1_CUSTOMER_CARE.tps} TPS`;
        }
        if (ag.N2_FINTECH_C2P) {
          if (DOM.agentN2Lat) DOM.agentN2Lat.textContent = `${ag.N2_FINTECH_C2P.latency_avg_ms.toFixed(3)} ms`;
          if (DOM.agentN2Tps) DOM.agentN2Tps.textContent = `${ag.N2_FINTECH_C2P.tps} TPS`;
        }
        if (ag.N3_EMERGENCY_EIR) {
          if (DOM.agentN3Lat) DOM.agentN3Lat.textContent = `${ag.N3_EMERGENCY_EIR.latency_avg_ms.toFixed(3)} ms`;
          if (DOM.agentN3Locks) DOM.agentN3Locks.textContent = `${ag.N3_EMERGENCY_EIR.active_blacklist_locks} Bloqueos`;
        }
        if (ag.N4_RETENTION_CHURN) {
          if (DOM.agentN4Lat) DOM.agentN4Lat.textContent = `${ag.N4_RETENTION_CHURN.latency_avg_ms.toFixed(3)} ms`;
          if (DOM.agentN4Ret) DOM.agentN4Ret.textContent = `${ag.N4_RETENTION_CHURN.retention_success_pct}%`;
        }
      }
    }

    // 4. Red Radioeléctrica 4GMAX
    if (data.network_telemetry) {
      const net = data.network_telemetry;
      if (DOM.coreAvail) DOM.coreAvail.textContent = `${net.core_availability_pct}%`;
      if (DOM.enodebCount) DOM.enodebCount.textContent = formatNumber(net.active_enodeb_sites);
      if (DOM.netThroughput) DOM.netThroughput.textContent = `${net.average_throughput_mbps} Mbps`;
      if (DOM.netTraffic) DOM.netTraffic.textContent = `${net.peak_traffic_gbps} Gbps`;
      if (DOM.conatelIndex) DOM.conatelIndex.textContent = `${net.conatel_quality_index}/100`;
    }

    // 5. Tabla de Incidentes de Seguridad Recientes
    if (DOM.securityTbody && Array.isArray(data.recent_events)) {
      DOM.securityTbody.innerHTML = '';
      data.recent_events.forEach((ev) => {
        const tr = document.createElement('tr');
        let badgeClass = 'info';
        if (ev.severity === 'CRITICAL') badgeClass = 'danger';
        else if (ev.severity === 'WARNING') badgeClass = 'warning';

        tr.innerHTML = `
          <td><span style="font-family: monospace;">${ev.timestamp}</span></td>
          <td><strong>${ev.event}</strong></td>
          <td><span style="font-family: monospace;">${ev.msisdn}</span></td>
          <td><span class="noc-badge ${badgeClass}">${ev.status}</span></td>
        `;
        DOM.securityTbody.appendChild(tr);
      });
    }

    // Estado Conexión
    if (DOM.connectionStatusText) DOM.connectionStatusText.textContent = 'TELEMETRÍA EN VIVO (ACTIVA)';
    if (DOM.connectionPulse) DOM.connectionPulse.style.backgroundColor = 'var(--noc-status-green)';
  }

  /**
   * Petición asíncrona hacia el backend de métricas.
   */
  async function fetchLiveMetrics() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONFIG.requestTimeoutMs);

      const response = await fetch(CONFIG.metricsEndpoint, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const json = await response.json();
      renderMetrics(json);
    } catch (err) {
      console.warn('[NOC Dashboard] Error recuperando métricas en vivo:', err.message);
      if (DOM.connectionStatusText) DOM.connectionStatusText.textContent = 'MODO LOCAL DE CONTINGENCIA';
      if (DOM.connectionPulse) DOM.connectionPulse.style.backgroundColor = 'var(--noc-status-amber)';
    }
  }

  /**
   * Inicialización del Dashboard.
   */
  function init() {
    // Actualizar reloj cada 1s
    updateClock();
    setInterval(updateClock, 1000);

    // Fetch inicial de métricas
    fetchLiveMetrics();

    // Polling recurrente
    setInterval(fetchLiveMetrics, CONFIG.pollIntervalMs);

    // Botón de refresco manual accesible
    if (DOM.refreshBtn) {
      DOM.refreshBtn.addEventListener('click', () => {
        DOM.refreshBtn.disabled = true;
        DOM.refreshBtn.innerHTML = '<span>Sincronizando...</span>';
        fetchLiveMetrics().finally(() => {
          setTimeout(() => {
            DOM.refreshBtn.disabled = false;
            DOM.refreshBtn.innerHTML = '<span>⚡ Sincronizar Ahora</span>';
          }, 600);
        });
      });
    }

    console.log('✅ [NOC Dashboard] Consola Ejecutiva Inicializada (WCAG 2.1 AAA - Swarm L5).');
  }

  // Arranque seguro según estado del documento
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
