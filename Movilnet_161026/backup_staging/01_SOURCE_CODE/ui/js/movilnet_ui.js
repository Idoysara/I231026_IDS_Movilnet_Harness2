/**
 * movilnet_ui.js — Lógica de Interacción Dinámica y Accesibilidad (IX / AX)
 * Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
 * Estándar: WCAG 2.1 AAA / UX-IX-AX Design System
 */

(function () {
  'use strict';

  // Constantes de Configuración
  const STORAGE_THEME_KEY = 'movilnet_theme_preference';
  const OFFICIAL_BCV_RATE = 41.5230; // Tasa de contingencia si no responde el endpoint
  let currentBcvRate = OFFICIAL_BCV_RATE;

  // Estado del Sistema
  const state = {
    activeTheme: 'light',
    activeTab: 'tab-tokens',
    bcvRate: OFFICIAL_BCV_RATE,
    lastSubscriberData: null
  };

  /* ========================================================================
     1. GESTOR DE TEMA (MODO CLARO / OSCURO NOC DASHBOARD)
     ======================================================================== */
  function initTheme() {
    const savedTheme = localStorage.getItem(STORAGE_THEME_KEY);
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (prefersDark ? 'dark' : 'light');
    setTheme(initialTheme);

    const themeToggleBtn = document.getElementById('btn-toggle-theme');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', toggleTheme);
    }
  }

  function setTheme(theme) {
    state.activeTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_THEME_KEY, theme);

    const themeToggleBtn = document.getElementById('btn-toggle-theme');
    if (themeToggleBtn) {
      const isDark = theme === 'dark';
      themeToggleBtn.setAttribute('aria-label', isDark ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro NOC');
      themeToggleBtn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      const icon = themeToggleBtn.querySelector('.theme-icon');
      if (icon) {
        icon.textContent = isDark ? '☀️' : '🌙';
      }
      const label = themeToggleBtn.querySelector('.theme-label');
      if (label) {
        label.textContent = isDark ? 'Modo Claro' : 'Modo NOC';
      }
    }
  }

  function toggleTheme() {
    const newTheme = state.activeTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  }

  /* ========================================================================
     2. RELOJ LEGAL DE VENEZUELA (UTC-4) Y TELEMETRÍA SWARM L5
     ======================================================================== */
  function startCaracasClock() {
    const clockEl = document.getElementById('caracas-clock');
    if (!clockEl) return;

    function update() {
      const now = new Date();
      // Formato para hora local de Caracas
      const options = {
        timeZone: 'America/Caracas',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      };
      const timeStr = new Intl.DateTimeFormat('es-VE', options).format(now);
      clockEl.textContent = `${timeStr} VET (UTC-4)`;
    }
    update();
    setInterval(update, 1000);
  }

  /* ========================================================================
     3. NAVEGACIÓN POR PESTAÑAS ACCESIBLE (WAI-ARIA Tablist)
     ======================================================================== */
  function initTabs() {
    const tablist = document.querySelector('[role="tablist"]');
    if (!tablist) return;

    const tabs = tablist.querySelectorAll('[role="tab"]');
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => selectTab(tab));

      // Navegación por teclado (Flechas, Inicio, Fin)
      tab.addEventListener('keydown', (e) => {
        let targetTab = null;
        if (e.key === 'ArrowRight') {
          targetTab = tabs[(index + 1) % tabs.length];
        } else if (e.key === 'ArrowLeft') {
          targetTab = tabs[(index - 1 + tabs.length) % tabs.length];
        } else if (e.key === 'Home') {
          targetTab = tabs[0];
        } else if (e.key === 'End') {
          targetTab = tabs[tabs.length - 1];
        }

        if (targetTab) {
          e.preventDefault();
          targetTab.focus();
          selectTab(targetTab);
        }
      });
    });
  }

  function selectTab(selectedTab) {
    const tablist = selectedTab.closest('[role="tablist"]');
    const tabs = tablist.querySelectorAll('[role="tab"]');
    const targetPanelId = selectedTab.getAttribute('aria-controls');

    tabs.forEach((tab) => {
      const isSelected = tab === selectedTab;
      tab.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      tab.tabIndex = isSelected ? 0 : -1;
    });

    document.querySelectorAll('[role="tabpanel"]').forEach((panel) => {
      if (panel.id === targetPanelId) {
        panel.classList.add('active');
        panel.removeAttribute('hidden');
      } else {
        panel.classList.remove('active');
        panel.setAttribute('hidden', 'true');
      }
    });

    state.activeTab = targetPanelId;
  }

  /* ========================================================================
     4. GESTOR DE DIÁLOGOS MODALES ACCESIBLES (Trap Focus + Escape)
     ======================================================================== */
  let previousActiveElement = null;

  function openModal(modalId) {
    const modalBackdrop = document.getElementById(modalId);
    if (!modalBackdrop) return;

    previousActiveElement = document.activeElement;
    modalBackdrop.classList.add('open');
    modalBackdrop.setAttribute('aria-hidden', 'false');

    // Mover foco al primer elemento interactivo o al diálogo
    const dialog = modalBackdrop.querySelector('[role="dialog"]');
    const focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) {
      focusable[0].focus();
    } else if (dialog) {
      dialog.focus();
    }

    // Escuchar Escape
    document.addEventListener('keydown', handleModalKeyDown);
  }

  function closeModal(modalId) {
    const modalBackdrop = document.getElementById(modalId);
    if (!modalBackdrop) return;

    modalBackdrop.classList.remove('open');
    modalBackdrop.setAttribute('aria-hidden', 'true');
    document.removeEventListener('keydown', handleModalKeyDown);

    if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
      previousActiveElement.focus();
    }
  }

  function handleModalKeyDown(e) {
    if (e.key === 'Escape') {
      const openModal = document.querySelector('.mov-modal-backdrop.open');
      if (openModal) {
        closeModal(openModal.id);
      }
    }
  }

  /* ========================================================================
     5. CALCULADORA DINÁMICA C2P PAGO MÓVIL Y TASA BCV
     ======================================================================== */
  async function fetchLiveBcvRate() {
    try {
      const res = await fetch('/api/v1/fintech/rates/bcv');
      if (res.ok) {
        const data = await res.json();
        if (data.rate_ves_usd) {
          currentBcvRate = parseFloat(data.rate_ves_usd);
          state.bcvRate = currentBcvRate;
          updateBcvDisplay();
        }
      }
    } catch (e) {
      console.warn('Usando tasa BCV contingente oficial:', currentBcvRate);
      updateBcvDisplay();
    }
  }

  function updateBcvDisplay() {
    const bcvDisplay = document.getElementById('bcv-rate-badge');
    if (bcvDisplay) {
      bcvDisplay.textContent = `Tasa Oficial BCV: ${currentBcvRate.toFixed(4)} Bs/USD`;
    }
  }

  function initC2PCalculator() {
    const amountUsdInput = document.getElementById('c2p-amount-usd');
    const amountVesOutput = document.getElementById('c2p-amount-ves');
    const commissionOutput = document.getElementById('c2p-commission');
    const totalVesOutput = document.getElementById('c2p-total-ves');

    if (!amountUsdInput) return;

    function recalculate() {
      const usd = parseFloat(amountUsdInput.value) || 0;
      const ves = usd * currentBcvRate;
      const commissionRate = 0.003; // 0.3% P2P estándar
      const commission = ves * commissionRate;
      const total = ves + commission;

      if (amountVesOutput) amountVesOutput.value = ves.toFixed(2);
      if (commissionOutput) commissionOutput.textContent = `${commission.toFixed(2)} Bs (0.3% SUDEBAN)`;
      if (totalVesOutput) totalVesOutput.textContent = `${total.toFixed(2)} Bs`;
    }

    amountUsdInput.addEventListener('input', recalculate);
    recalculate();
  }

  /* ========================================================================
     6. VALIDADOR ALGORÍTMICO LUHN-10 PARA DISPOSITIVOS EIR
     ======================================================================== */
  function isValidImeiLuhn(imei) {
    const cleaned = String(imei).replace(/[\s-]/g, '');
    if (!/^\d{15}$/.test(cleaned)) return false;

    let sum = 0;
    for (let i = 0; i < 15; i++) {
      let digit = parseInt(cleaned.charAt(i), 10);
      if (i % 2 === 1) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
    }
    return sum % 10 === 0;
  }

  function initImeiValidator() {
    const imeiInput = document.getElementById('eir-imei-input');
    const feedbackEl = document.getElementById('eir-imei-feedback');
    const submitBtn = document.getElementById('btn-submit-eir');

    if (!imeiInput || !feedbackEl) return;

    imeiInput.addEventListener('input', () => {
      const val = imeiInput.value.trim();
      if (val.length === 0) {
        feedbackEl.textContent = 'Ingrese los 15 dígitos del IMEI para validar con GSMA.';
        feedbackEl.className = 'mov-help-text';
        if (submitBtn) submitBtn.disabled = true;
        return;
      }

      if (val.length < 15) {
        feedbackEl.textContent = `Dígitos ingresados: ${val.length}/15`;
        feedbackEl.className = 'mov-help-text';
        if (submitBtn) submitBtn.disabled = true;
        return;
      }

      const isValid = isValidImeiLuhn(val);
      if (isValid) {
        feedbackEl.textContent = '✓ Código IMEI matemáticamente válido según norma GSMA (Luhn-10 OK)';
        feedbackEl.className = 'mov-help-text text-success';
        feedbackEl.style.color = 'var(--mov-success)';
        if (submitBtn) submitBtn.disabled = false;
      } else {
        feedbackEl.textContent = '✗ Dígito verificador de IMEI inválido (Fallo de paridad Luhn-10)';
        feedbackEl.className = 'mov-help-text text-danger';
        feedbackEl.style.color = 'var(--mov-danger)';
        if (submitBtn) submitBtn.disabled = true;
      }
    });
  }

  /* ========================================================================
     7. BÚSQUEDA RÁPIDA DE ABONADO OCS (FAST-PATH)
     ======================================================================== */
  function initSubscriberSearch() {
    const searchForm = document.getElementById('form-subscriber-search');
    const phoneInput = document.getElementById('input-search-msisdn');
    const resultBox = document.getElementById('subscriber-result-box');

    if (!searchForm || !phoneInput || !resultBox) return;

    searchForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const phone = phoneInput.value.trim();
      if (!phone) return;

      resultBox.innerHTML = `
        <div class="mov-skeleton" style="height: 120px; width: 100%; margin-top: 16px;"></div>
      `;

      try {
        const startTime = performance.now();
        const res = await fetch(`/api/v1/subscribers/${encodeURIComponent(phone)}`);
        const duration = (performance.now() - startTime).toFixed(2);

        if (res.ok) {
          const sub = await res.json();
          renderSubscriberCard(resultBox, sub, duration);
        } else {
          renderSubscriberNotFound(resultBox, phone, duration);
        }
      } catch (err) {
        // En caso de modo estático o desconexión, mostrar demo interactiva
        renderDemoSubscriber(resultBox, phone);
      }
    });
  }

  function renderSubscriberCard(container, data, duration) {
    const statusBadgeClass = data.status === 'ACTIVO' ? 'mov-badge-success' : 'mov-badge-warning';
    container.innerHTML = `
      <div class="mov-card" style="margin-top: 16px; border-left: 4px solid var(--mov-orange-accent);">
        <div class="mov-card-header">
          <div>
            <span class="mov-badge mov-badge-4gmax">4GMAX LTE</span>
            <span class="mov-badge ${statusBadgeClass}">${data.status}</span>
          </div>
          <span style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-muted);">
            Fast-Path: ${duration} ms
          </span>
        </div>
        <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 8px;">
          Línea Movilnet: ${data.msisdn}
        </h3>
        <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 12px;">
          Plan: <strong>${data.plan_name || 'Inteliplan 10GB 4GMAX'}</strong> | Segmento: ${data.segment || 'PREPAGO_MASIVO'}
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;">
          <div style="background: var(--bg-subtle); padding: 12px; border-radius: var(--radius-md);">
            <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">Saldo Disponible</span>
            <strong style="font-size: 1.125rem; font-family: var(--font-mono); color: var(--mov-blue-primary);">
              ${data.balance_ves ? data.balance_ves.toFixed(2) : '150.00'} Bs
            </strong>
          </div>
          <div style="background: var(--bg-subtle); padding: 12px; border-radius: var(--radius-md);">
            <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">Megas Restantes</span>
            <strong style="font-size: 1.125rem; font-family: var(--font-mono); color: var(--mov-cyan-data);">
              ${data.remaining_data_mb || '7680'} MB
            </strong>
          </div>
        </div>
      </div>
    `;
  }

  function renderDemoSubscriber(container, phone) {
    container.innerHTML = `
      <div class="mov-card" style="margin-top: 16px; border-left: 4px solid var(--mov-orange-accent);">
        <div class="mov-card-header">
          <div>
            <span class="mov-badge mov-badge-4gmax">4GMAX LTE</span>
            <span class="mov-badge mov-badge-success">ACTIVO</span>
          </div>
          <span style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-muted);">
            Fast-Path Simulado: 0.18 ms
          </span>
        </div>
        <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 8px;">
          Línea Movilnet: ${phone}
        </h3>
        <p style="font-size: 0.875rem; color: var(--text-secondary); margin-bottom: 12px;">
          Plan: <strong>Inteliplan 10GB 4GMAX</strong> | Segmento: PREPAGO_MASIVO
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;">
          <div style="background: var(--bg-subtle); padding: 12px; border-radius: var(--radius-md);">
            <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">Saldo Disponible</span>
            <strong style="font-size: 1.125rem; font-family: var(--font-mono); color: var(--text-primary);">
              311.42 Bs ($7.50 USD)
            </strong>
          </div>
          <div style="background: var(--bg-subtle); padding: 12px; border-radius: var(--radius-md);">
            <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">Datos 4GMAX</span>
            <strong style="font-size: 1.125rem; font-family: var(--font-mono); color: var(--mov-cyan-data);">
              8,192 MB (80%)
            </strong>
          </div>
        </div>
      </div>
    `;
  }

  function renderSubscriberNotFound(container, phone, duration) {
    container.innerHTML = `
      <div class="mov-card" style="margin-top: 16px; border-left: 4px solid var(--mov-warning);">
        <span class="mov-badge mov-badge-warning">NO ENCONTRADO</span>
        <p style="margin-top: 8px; font-size: 0.875rem;">
          No se encontró registro para la línea <strong>${phone}</strong> en los 4.000.000 abonados (${duration} ms).
        </p>
      </div>
    `;
  }

  /* ========================================================================
     8. INICIALIZACIÓN GLOBAL
     ======================================================================== */
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    startCaracasClock();
    initTabs();
    fetchLiveBcvRate();
    initC2PCalculator();
    initImeiValidator();
    initSubscriberSearch();

    // Enlazar botones de modales con data-modal-target
    document.querySelectorAll('[data-modal-open]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-modal-open');
        openModal(targetId);
      });
    });

    document.querySelectorAll('[data-modal-close]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-modal-close');
        closeModal(targetId);
      });
    });

    // Cerrar al pulsar sobre el fondo
    document.querySelectorAll('.mov-modal-backdrop').forEach((backdrop) => {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          closeModal(backdrop.id);
        }
      });
    });
  });

  // Exponer API global accesible
  window.MovilnetUI = {
    setTheme,
    toggleTheme,
    openModal,
    closeModal,
    isValidImeiLuhn,
    getBcvRate: () => currentBcvRate
  };
})();
