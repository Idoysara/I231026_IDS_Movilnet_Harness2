/**
 * pwa.js — Motor Lógico y de Interacción de Mi Movilnet PWA
 * Proyecto: AI_Movilnet_300926 — Telecomunicaciones Movilnet C.A.
 * Autonomía: Antigravity Nivel 5 Mobile Client
 */

(function () {
  'use strict';

  // =========================================================================
  // GESTIÓN DEL SISTEMA DE TEMAS TRI-MODAL (LIGHT / MEDIUM / DARK)
  // =========================================================================
  window.setPwaTheme = function (theme) {
    var valid = ['light', 'medium', 'dark'];
    if (!valid.includes(theme)) theme = 'light';

    document.documentElement.setAttribute('data-theme', theme);
    if (document.body) {
      document.body.className = document.body.className.replace(/\btheme-\S+/g, '').trim() + ' theme-' + theme;
    }
    localStorage.setItem('movilnet_pwa_theme', theme);

    // Actualizar botones de la interfaz
    var buttons = document.querySelectorAll('.theme-btn');
    buttons.forEach(function (btn) {
      var isTarget = btn.getAttribute('data-theme-target') === theme;
      btn.classList.toggle('active', isTarget);
      btn.setAttribute('aria-pressed', isTarget ? 'true' : 'false');
    });

    // Actualizar meta theme-color para navegadores móviles
    var themeColors = {
      light: '#002B49',
      medium: '#16202D',
      dark: '#05080C'
    };
    var metaTheme = document.querySelector('meta[name="theme-color"]');
    if (metaTheme) {
      metaTheme.setAttribute('content', themeColors[theme] || '#002B49');
    }
  };

  // Sincronizar estado inicial al cargar DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      var current = localStorage.getItem('movilnet_pwa_theme') || 'light';
      window.setPwaTheme(current);
    });
  } else {
    var current = localStorage.getItem('movilnet_pwa_theme') || 'light';
    window.setPwaTheme(current);
  }

  // Configuración de Endpoints
  const CONFIG = {
    balanceEndpoint: '/api/v1/subscribers/balance',
    c2pEndpoint: '/api/v1/payments/c2p',
    agentEndpoint: '/api/v1/agents/customer-care/process',
    plansEndpoint: '/api/v1/catalog/plans',
    banksEndpoint: '/api/v1/banks',
    defaultPhone: '04160000001',
    defaultCid: 'V-10000001'
  };

  // Elementos DOM
  const DOM = {
    phoneBadge: document.getElementById('pwa-phone-badge'),
    planName: document.getElementById('pwa-plan-name'),
    balanceVes: document.getElementById('pwa-balance-ves'),
    balanceUsd: document.getElementById('pwa-balance-usd'),
    quotaFill: document.getElementById('pwa-quota-fill'),
    quotaText: document.getElementById('pwa-quota-text'),
    cutoffDate: document.getElementById('pwa-cutoff-date'),
    
    // C2P Form
    c2pForm: document.getElementById('pwa-c2p-form'),
    bankSelect: document.getElementById('c2p-bank-select'),
    amountInput: document.getElementById('c2p-amount-input'),
    phoneInput: document.getElementById('c2p-phone-input'),
    cidInput: document.getElementById('c2p-cid-input'),
    otpInput: document.getElementById('c2p-otp-input'),
    c2pSubmitBtn: document.getElementById('c2p-submit-btn'),
    c2pFeedback: document.getElementById('c2p-feedback'),

    // Chat
    chatForm: document.getElementById('pwa-chat-form'),
    chatMessages: document.getElementById('pwa-chat-messages'),
    chatInput: document.getElementById('pwa-chat-input'),
    chatSendBtn: document.getElementById('pwa-chat-send')
  };

  // Identificador de sesión persistente para memoria conversacional multi-turno
  let chatSessionId = sessionStorage.getItem('movilnet_pwa_session_id');
  if (!chatSessionId) {
    chatSessionId = 'sess-pwa-' + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem('movilnet_pwa_session_id', chatSessionId);
  }

  // Algoritmo de Detección de Dispositivo (Heurística de Triple Señal W3C)
  function detectClientDevice() {
    const ua = navigator.userAgent || '';
    const maxTouch = navigator.maxTouchPoints || 0;
    const width = window.innerWidth;
    const height = window.innerHeight;
    const isTouch = maxTouch > 0;

    let deviceType = 'Laptop / Computadora de Escritorio';
    let osFamily = 'Desconocido';
    let hardwareModel = 'PC/Mac';

    if (/Android/i.test(ua)) {
      osFamily = 'Android';
      if (/Tablet/i.test(ua) || (width >= 600 && width < 1024 && isTouch)) {
        deviceType = 'Tablet Android';
        hardwareModel = 'Tablet';
      } else {
        deviceType = 'Smartphone Android';
        hardwareModel = 'Teléfono Móvil';
      }
    } else if (/iPhone/i.test(ua)) {
      osFamily = 'iOS';
      deviceType = 'Smartphone iPhone (Apple)';
      hardwareModel = 'iPhone';
    } else if (/iPad/i.test(ua) || (navigator.platform === 'MacIntel' && maxTouch > 1)) {
      osFamily = 'iPadOS';
      deviceType = 'Tablet iPad (Apple)';
      hardwareModel = 'iPad';
    } else if (/Macintosh|Mac OS X/i.test(ua)) {
      osFamily = 'macOS';
      deviceType = 'Computadora Laptop / Mac';
      hardwareModel = 'Mac';
    } else if (/Windows NT/i.test(ua)) {
      osFamily = 'Windows';
      deviceType = 'Computadora Laptop / PC Windows';
      hardwareModel = 'PC Windows';
    } else if (/Linux/i.test(ua)) {
      osFamily = 'Linux';
      deviceType = 'Computadora / Estación Linux';
      hardwareModel = 'Linux Desktop';
    }

    if (deviceType.includes('Laptop') && isTouch && width <= 1024) {
      deviceType = 'Dispositivo Híbrido / Tablet';
    }

    return {
      device_type: deviceType,
      os_family: osFamily,
      hardware_model: hardwareModel,
      is_touch: isTouch,
      screen_resolution: `${width}x${height}`,
      pixel_ratio: window.devicePixelRatio || 1
    };
  }

  const clientDeviceInfo = detectClientDevice();

  // Coordenadas cacheadas en segundo plano (para no bloquear el click/Enter)
  let cachedCoords = { latitude: 10.4806, longitude: -66.9036 };
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (pos && pos.coords) {
          cachedCoords.latitude = pos.coords.latitude;
          cachedCoords.longitude = pos.coords.longitude;
        }
      },
      () => {},
      { timeout: 3000, enableHighAccuracy: false }
    );
  }

  /**
   * Registro del Service Worker oficial
   */
  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/ui/pwa/sw.js', { scope: '/ui/pwa/' })
        .then((reg) => {
          console.log('[PWA] Service Worker registrado con éxito en scope:', reg.scope);
        })
        .catch((err) => {
          console.warn('[PWA] Falla al registrar Service Worker:', err.message);
        });
    }
  }

  /**
   * Formateo numérico en moneda venezolana
   */
  function formatMoney(amount, decimals = 2) {
    if (isNaN(amount) || amount === null) return '0,00';
    return Number(amount).toLocaleString('es-VE', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  /**
   * Consulta OCS de Saldo y Cuota en O(1) Fast-Path
   */
  async function loadSubscriberBalance(phone = CONFIG.defaultPhone, cid = CONFIG.defaultCid) {
    try {
      const res = await fetch(CONFIG.balanceEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msisdn: phone, cid: cid })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (DOM.planName) DOM.planName.textContent = data.plan_name || 'PLAN INTELIPLAN 10GB';
      if (DOM.balanceVes) DOM.balanceVes.textContent = `Bs. ${formatMoney(data.balance_ves)}`;
      if (DOM.balanceUsd) DOM.balanceUsd.textContent = `≈ $${formatMoney(data.balance_usd_equiv)} USD`;
      if (DOM.phoneBadge) DOM.phoneBadge.textContent = data.msisdn || phone;

      // Cálculo de cuota 4GMAX
      const totalMb = data.total_quota_mb || 10240;
      const remainingMb = data.remaining_data_mb !== undefined ? data.remaining_data_mb : 6144;
      const consumedPct = totalMb > 0 ? Math.min(100, Math.max(0, Math.round(((totalMb - remainingMb) / totalMb) * 100))) : 0;
      const remainingGb = (remainingMb / 1024).toFixed(1);
      const totalGb = (totalMb / 1024).toFixed(0);

      if (DOM.quotaFill) DOM.quotaFill.style.width = `${100 - consumedPct}%`;
      if (DOM.quotaText) DOM.quotaText.textContent = `${remainingGb} GB disponibles de ${totalGb} GB`;
      if (DOM.cutoffDate) DOM.cutoffDate.textContent = data.billing_cutoff_date || 'Próximo corte: 28 del mes';

    } catch (err) {
      console.warn('[PWA] Error cargando balance OCS:', err.message);
      // Fallback visual para offline
      if (DOM.balanceVes) DOM.balanceVes.textContent = 'Bs. 150,00';
      if (DOM.balanceUsd) DOM.balanceUsd.textContent = '≈ $4,07 USD';
      if (DOM.quotaFill) DOM.quotaFill.style.width = '60%';
      if (DOM.quotaText) DOM.quotaText.textContent = '6.0 GB disponibles de 10 GB';
    }
  }

  /**
   * Cargar catálogo de bancos SUDEBAN para C2P
   */
  async function loadBanks() {
    try {
      const res = await fetch(CONFIG.banksEndpoint);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (DOM.bankSelect && Array.isArray(data.banks)) {
        DOM.bankSelect.innerHTML = '<option value="">Seleccione su banco emisor...</option>';
        data.banks.forEach((b) => {
          const opt = document.createElement('option');
          opt.value = b.bank_code;
          opt.textContent = `${b.bank_code} - ${b.bank_name}`;
          DOM.bankSelect.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn('[PWA] Fallback catálogo de bancos:', err.message);
      if (DOM.bankSelect) {
        DOM.bankSelect.innerHTML = `
          <option value="0102">0102 - Banco de Venezuela</option>
          <option value="0134">0134 - Banesco</option>
          <option value="0105">0105 - Mercantil</option>
          <option value="0108">0108 - Banco Provincial</option>
        `;
      }
    }
  }

  /**
   * Procesamiento de Pago Móvil C2P
   */
  async function handleC2PSubmit(e) {
    e.preventDefault();
    if (!DOM.c2pSubmitBtn) return;

    DOM.c2pSubmitBtn.disabled = true;
    DOM.c2pSubmitBtn.innerHTML = '<span>Procesando con SUDEBAN...</span>';
    if (DOM.c2pFeedback) DOM.c2pFeedback.innerHTML = '';

    const payload = {
      reference_id: `PWA-${Date.now().toString().slice(-8)}`,
      msisdn: DOM.phoneInput ? DOM.phoneInput.value.trim() : CONFIG.defaultPhone,
      bank_code: DOM.bankSelect ? DOM.bankSelect.value : '0102',
      amount_ves: DOM.amountInput ? parseFloat(DOM.amountInput.value) : 100.0,
      payer_cid: DOM.cidInput ? DOM.cidInput.value.trim() : CONFIG.defaultCid,
      otp_token: DOM.otpInput ? DOM.otpInput.value.trim() : '123456'
    };

    try {
      const res = await fetch(CONFIG.c2pEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await res.json();
      if (res.ok && result.success) {
        if (DOM.c2pFeedback) {
          DOM.c2pFeedback.innerHTML = `
            <div style="background: var(--pwa-success-bg); color: var(--pwa-success); padding: 12px; border-radius: 8px; font-size: 0.85rem; margin-top: 10px;">
              <strong>✅ ¡Recarga C2P Exitosa!</strong><br/>
              Referencia: <code>${result.reference_id}</code><br/>
              Monto Acreditado: <strong>Bs. ${formatMoney(result.amount_ves)}</strong><br/>
              Nuevo Saldo: <strong>Bs. ${formatMoney(result.new_balance_ves)}</strong>
            </div>
          `;
        }
        // Actualizar saldo inmediatamente
        loadSubscriberBalance(payload.msisdn, payload.payer_cid);
      } else {
        throw new Error(result.message || 'No fue posible conciliar el pago.');
      }
    } catch (err) {
      if (DOM.c2pFeedback) {
        DOM.c2pFeedback.innerHTML = `
          <div style="background: var(--pwa-danger-bg); color: var(--pwa-danger); padding: 12px; border-radius: 8px; font-size: 0.85rem; margin-top: 10px;">
            <strong>⚠️ Error en Pasarela C2P:</strong> ${err.message}
          </div>
        `;
      }
    } finally {
      DOM.c2pSubmitBtn.disabled = false;
      DOM.c2pSubmitBtn.innerHTML = '<span>⚡ Confirmar Pago Móvil C2P</span>';
    }
  }

  /**
   * Formateador liviano de Markdown para el chat (negritas, cursivas, saltos de línea y viñetas)
   */
  function formatChatText(raw) {
    if (!raw) return '';
    // Escapar HTML básico
    let safe = raw
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Negritas (*texto*)
    safe = safe.replace(/\*([^\*]+)\*/g, '<strong>$1</strong>');
    // Código (`codigo`)
    safe = safe.replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.06);padding:2px 4px;border-radius:4px;font-family:monospace;">$1</code>');
    // Cursivas (_texto_)
    safe = safe.replace(/_([^_]+)_/g, '<em>$1</em>');
    // Saltos de línea
    safe = safe.replace(/\n/g, '<br>');
    return safe;
  }

  let isChatSending = false;

  /**
   * Enviar consulta al Agente N1 de Customer Care
   */
  async function sendChatMessage() {
    if (isChatSending) return;
    if (!DOM.chatInput || !DOM.chatMessages) return;
    const text = DOM.chatInput.value.trim();
    if (!text) return;

    isChatSending = true;
    if (DOM.chatSendBtn) {
      DOM.chatSendBtn.disabled = true;
      DOM.chatSendBtn.innerText = '...';
      DOM.chatSendBtn.style.opacity = '0.6';
    }
    if (DOM.chatInput) {
      DOM.chatInput.disabled = true;
    }

    // Agregar mensaje del usuario
    const userMsg = document.createElement('div');
    userMsg.className = 'pwa-msg user';
    userMsg.textContent = text;
    DOM.chatMessages.appendChild(userMsg);
    DOM.chatInput.value = '';
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;

    // Indicador temporal
    const typingMsg = document.createElement('div');
    typingMsg.className = 'pwa-msg assistant';
    typingMsg.innerHTML = '<em>Consultando asistente Movilnet...</em>';
    DOM.chatMessages.appendChild(typingMsg);
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;

    try {
      const res = await fetch(CONFIG.agentEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: chatSessionId,
          text: text,
          msisdn: CONFIG.defaultPhone,
          channel: 'web',
          latitude: cachedCoords.latitude,
          longitude: cachedCoords.longitude,
          device_info: clientDeviceInfo
        })
      });

      const data = await res.json();
      const rawReply = data.response_text || 'Entendido. ¿En qué más le podemos colaborar con su línea Movilnet?';
      typingMsg.innerHTML = formatChatText(rawReply);

      // Renderizar Botones Interactivos y Ganchos de Conversión (Funnel Marketing)
      if (data.interactive_options && data.interactive_options.length > 0) {
        const btnContainer = document.createElement('div');
        btnContainer.style.display = 'flex';
        btnContainer.style.flexWrap = 'wrap';
        btnContainer.style.gap = '8px';
        btnContainer.style.marginTop = '10px';

        data.interactive_options.forEach((opt) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'pwa-action-chip';
          btn.style.background = opt.id.includes('c2p') || opt.id.includes('funnel') ? 'var(--pwa-primary, #002B49)' : '#f0f4f8';
          btn.style.color = opt.id.includes('c2p') || opt.id.includes('funnel') ? '#ffffff' : '#002B49';
          btn.style.border = '1px solid rgba(0,43,73,0.2)';
          btn.style.borderRadius = '16px';
          btn.style.padding = '6px 12px';
          btn.style.fontSize = '0.78rem';
          btn.style.cursor = 'pointer';
          btn.style.fontWeight = '600';
          btn.innerText = opt.title;

          btn.onclick = () => {
            if (opt.id.includes('c2p') || opt.id.includes('funnel') || opt.id.includes('recharge')) {
              // Conducir al embudo de conversión C2P con One-Click Checkout
              const c2pSec = document.getElementById('sec-c2p');
              if (c2pSec) {
                c2pSec.scrollIntoView({ behavior: 'smooth' });
                if (data.metadata && data.metadata.marketing_funnel && data.metadata.marketing_funnel.prefill_data) {
                  const pre = data.metadata.marketing_funnel.prefill_data;
                  if (pre.amount_ves && DOM.amountInput) {
                    DOM.amountInput.value = pre.amount_ves;
                  }
                }
                if (DOM.otpInput) DOM.otpInput.focus();
              }
            } else {
              if (DOM.chatInput) {
                DOM.chatInput.value = opt.title;
                sendChatMessage();
              }
            }
          };
          btnContainer.appendChild(btn);
        });
        typingMsg.appendChild(btnContainer);
      }
    } catch (err) {
      typingMsg.innerHTML = 'En este momento estamos procesando su solicitud en modo de contingencia. Su línea se encuentra activa.';
    } finally {
      isChatSending = false;
      if (DOM.chatSendBtn) {
        DOM.chatSendBtn.disabled = false;
        DOM.chatSendBtn.innerText = 'Enviar';
        DOM.chatSendBtn.style.opacity = '1';
      }
      if (DOM.chatInput) {
        DOM.chatInput.disabled = false;
        DOM.chatInput.focus();
      }
      DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
    }
  }

  /**
   * Inicialización PWA
   */
  function init() {
    registerServiceWorker();
    loadSubscriberBalance();
    loadBanks();

    if (DOM.c2pForm) {
      DOM.c2pForm.addEventListener('submit', handleC2PSubmit);
    }

    // Vinculación canónica del formulario de chat (maneja botón submit y Enter nativamente)
    if (DOM.chatForm) {
      DOM.chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        e.stopPropagation();
        sendChatMessage();
      });
    }

    if (DOM.chatInput) {
      DOM.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          sendChatMessage();
        }
      });
    }

    console.log('✅ [Mi Movilnet PWA] Cliente de Autoservicio Móvil Inicializado.');

    // Inicializar listeners de WhatsApp y Telegram
    setupExternalSimulators();
  }

  /**
   * Selector Dinámico de Formato de Pantalla (Celular vs Tablet)
   */
  window.setAppDeviceMode = function (modalId, mode) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return;
    const win = modalEl.querySelector('.pwa-app-window');
    const btnPhone = modalEl.querySelector('#btn-mode-phone');
    const btnTablet = modalEl.querySelector('#btn-mode-tablet');

    if (win) {
      if (mode === 'tablet') {
        win.classList.remove('device-phone');
        win.classList.add('device-tablet');
        if (btnPhone) btnPhone.classList.remove('active');
        if (btnTablet) btnTablet.classList.add('active');
      } else {
        win.classList.remove('device-tablet');
        win.classList.add('device-phone');
        if (btnTablet) btnTablet.classList.remove('active');
        if (btnPhone) btnPhone.classList.add('active');
      }
    }
  };

  /**
   * Conmutador dinámico de abonado de prueba para simulación
   */
  window.switchPwaSubscriber = function (phone) {
    if (!phone) return;
    CONFIG.defaultPhone = phone;
    if (DOM.phoneInput) DOM.phoneInput.value = phone;
    if (DOM.phoneBadge) DOM.phoneBadge.textContent = phone;
    loadSubscriberBalance(phone, CONFIG.defaultCid);
    console.log('📱 [PWA] Conmutado a abonado de prueba:', phone);
  };

  /**
   * Despachador de consultas de prueba predefinidas (1-Click Tester)
   */
  window.sendQuickPrompt = function (app, text) {
    if (app === 'whatsapp') {
      const inp = document.getElementById('wa-chat-input');
      const form = document.getElementById('wa-chat-form');
      if (inp && form) {
        inp.value = text;
        form.dispatchEvent(new Event('submit'));
      }
    } else if (app === 'chat') {
      const inp = document.getElementById('modal-chat-input');
      const form = document.getElementById('modal-chat-form');
      if (inp && form) {
        inp.value = text;
        form.dispatchEvent(new Event('submit'));
      }
    } else if (app === 'telegram') {
      const inp = document.getElementById('tg-chat-input');
      const form = document.getElementById('tg-chat-form');
      if (inp && form) {
        inp.value = text;
        form.dispatchEvent(new Event('submit'));
      }
    }
  };

  /**
   * Gestor de Ventanas y Modales PWA Multi-App
   */
  window.openPwaApp = function (appId) {
    if (appId === 'c2p') {
      const c2pSec = document.getElementById('sec-c2p');
      if (c2pSec) {
        c2pSec.scrollIntoView({ behavior: 'smooth' });
        if (DOM.amountInput) DOM.amountInput.focus();
      }
      return;
    }

    const modalId = `modal-app-${appId}`;
    const modalEl = document.getElementById(modalId);
    if (modalEl) {
      modalEl.classList.add('active');
      modalEl.classList.add('open');
      modalEl.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';

      // Enfoque automático al campo de entrada según aplicación
      if (appId === 'chat') {
        const inp = document.getElementById('modal-chat-input');
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (appId === 'whatsapp') {
        const inp = document.getElementById('wa-chat-input');
        if (inp) setTimeout(() => inp.focus(), 150);
      } else if (appId === 'telegram') {
        const inp = document.getElementById('tg-chat-input');
        if (inp) setTimeout(() => inp.focus(), 150);
      }
    }
  };

  window.closePwaApp = function (appId) {
    const modalId = `modal-app-${appId}`;
    const modalEl = document.getElementById(modalId);
    if (modalEl) {
      modalEl.classList.remove('active');
      modalEl.classList.remove('open');
      modalEl.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
  };

  // Cerrar modal al hacer click en el fondo semitransparente
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('pwa-modal-backdrop') && (e.target.classList.contains('active') || e.target.classList.contains('open'))) {
      e.target.classList.remove('active');
      e.target.classList.remove('open');
      e.target.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    }
  });

  /**
   * Manejador de Simulación Interactiva para WhatsApp y Telegram
   */
  function setupExternalSimulators() {
    // 1. WhatsApp Chat
    const waForm = document.getElementById('wa-chat-form');
    const waInput = document.getElementById('wa-chat-input');
    const waMessages = document.getElementById('wa-chat-messages');

    if (waForm && waInput && waMessages) {
      waForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = waInput.value.trim();
        if (!text) return;

        // Render mensaje de usuario (estilo verde WhatsApp)
        const userDiv = document.createElement('div');
        userDiv.className = 'chat-bubble user';
        userDiv.innerText = text;
        waMessages.appendChild(userDiv);
        waInput.value = '';
        waMessages.scrollTop = waMessages.scrollHeight;

        // Indicador bot
        const botDiv = document.createElement('div');
        botDiv.className = 'chat-bubble bot';
        botDiv.innerHTML = '<em>Escribiendo...</em>';
        waMessages.appendChild(botDiv);
        waMessages.scrollTop = waMessages.scrollHeight;

        try {
          const resp = await fetch(CONFIG.agentEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: text,
              message: text,
              query: text,
              session_id: 'wa-' + chatSessionId,
              channel: 'whatsapp',
              msisdn: CONFIG.defaultPhone,
              device_info: clientDeviceInfo
            })
          });
          const data = await resp.json();
          const reply = data.response_text || data.reply || 'Mensaje recibido en WhatsApp Movilnet.';
          botDiv.innerHTML = formatChatText(reply);

          // Renderizar botones interactivos oficiales de WhatsApp
          if (data.interactive_options && data.interactive_options.length > 0) {
            const btnWrap = document.createElement('div');
            btnWrap.style.cssText = 'display:flex; flex-wrap:wrap; gap:6px; margin-top:8px;';
            data.interactive_options.forEach((opt) => {
              const btn = document.createElement('button');
              btn.type = 'button';
              btn.style.cssText = 'background:#E7FCE3; border:1px solid #25D366; color:#075E54; border-radius:14px; padding:5px 10px; font-size:0.75rem; cursor:pointer; font-weight:600;';
              btn.innerText = opt.title;
              btn.onclick = () => {
                if (opt.id.includes('c2p') || opt.id.includes('recharge')) {
                  closePwaApp('whatsapp');
                  openPwaApp('c2p');
                } else {
                  waInput.value = opt.title;
                  waForm.dispatchEvent(new Event('submit'));
                }
              };
              btnWrap.appendChild(btn);
            });
            botDiv.appendChild(btnWrap);
          }
        } catch (err) {
          botDiv.innerHTML = 'Error al conectar con el asistente de WhatsApp. Por favor intenta de nuevo.';
        }
        waMessages.scrollTop = waMessages.scrollHeight;
      });
    }

    // 2. Telegram Chat
    const tgForm = document.getElementById('tg-chat-form');
    const tgInput = document.getElementById('tg-chat-input');
    const tgMessages = document.getElementById('tg-chat-messages');

    if (tgForm && tgInput && tgMessages) {
      tgForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = tgInput.value.trim();
        if (!text) return;

        // Render mensaje de usuario (estilo azul/verde Telegram)
        const userDiv = document.createElement('div');
        userDiv.className = 'chat-bubble user';
        userDiv.innerText = text;
        tgMessages.appendChild(userDiv);
        tgInput.value = '';
        tgMessages.scrollTop = tgMessages.scrollHeight;

        // Indicador bot
        const botDiv = document.createElement('div');
        botDiv.className = 'chat-bubble bot';
        botDiv.innerHTML = '<em>escribiendo...</em>';
        tgMessages.appendChild(botDiv);
        tgMessages.scrollTop = tgMessages.scrollHeight;

        try {
          const resp = await fetch(CONFIG.agentEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: text,
              message: text,
              query: text,
              session_id: 'tg-' + chatSessionId,
              channel: 'telegram',
              msisdn: CONFIG.defaultPhone,
              device_info: clientDeviceInfo
            })
          });
          const data = await resp.json();
          const reply = data.response_text || data.reply || 'Mensaje procesado en Telegram Bot.';
          botDiv.innerHTML = reply.replace(/\n/g, '<br/>');
        } catch (err) {
          botDiv.innerHTML = 'Error de conexión con @MovilnetAtencionBot.';
        }
        tgMessages.scrollTop = tgMessages.scrollHeight;
      });
    }

    // 3. Ventana Independiente Asistente Virtual Movilnet (Simulador Móvil/Tablet)
    const modalChatForm = document.getElementById('modal-chat-form');
    const modalChatInput = document.getElementById('modal-chat-input');
    const modalChatMessages = document.getElementById('modal-chat-messages');

    if (modalChatForm && modalChatInput && modalChatMessages) {
      modalChatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = modalChatInput.value.trim();
        if (!text) return;

        // Burbuja usuario
        const userMsg = document.createElement('div');
        userMsg.className = 'chat-bubble user';
        userMsg.style.cssText = 'background:#002B49; color:#FFFFFF; align-self:flex-end; border-radius:12px; padding:10px 14px; font-size:0.86rem; max-width:85%;';
        userMsg.textContent = text;
        modalChatMessages.appendChild(userMsg);
        modalChatInput.value = '';
        modalChatMessages.scrollTop = modalChatMessages.scrollHeight;

        // Indicador asistente
        const typingMsg = document.createElement('div');
        typingMsg.className = 'chat-bubble bot';
        typingMsg.style.cssText = 'background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:10px 14px; font-size:0.86rem; color:#0F172A; max-width:85%;';
        typingMsg.innerHTML = '<em>Consultando asistente Movilnet...</em>';
        modalChatMessages.appendChild(typingMsg);
        modalChatMessages.scrollTop = modalChatMessages.scrollHeight;

        try {
          const res = await fetch(CONFIG.agentEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              session_id: chatSessionId,
              text: text,
              message: text,
              query: text,
              msisdn: CONFIG.defaultPhone,
              channel: 'pwa-app-window',
              latitude: cachedCoords.latitude,
              longitude: cachedCoords.longitude,
              device_info: clientDeviceInfo
            })
          });

          const data = await res.json();
          const rawReply = data.response_text || data.reply || 'Entendido. ¿En qué más le podemos colaborar con su línea Movilnet?';
          typingMsg.innerHTML = formatChatText(rawReply);

          // Botones interactivos (Funnel Marketing)
          if (data.interactive_options && data.interactive_options.length > 0) {
            const btnWrap = document.createElement('div');
            btnWrap.style.cssText = 'display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;';
            data.interactive_options.forEach((opt) => {
              const btn = document.createElement('button');
              btn.type = 'button';
              btn.style.cssText = 'background:#F1F5F9; border:1px solid #CBD5E1; color:#002B49; border-radius:16px; padding:6px 12px; font-size:0.78rem; cursor:pointer; font-weight:600;';
              btn.innerText = opt.title;
              btn.onclick = () => {
                if (opt.id.includes('c2p') || opt.id.includes('recharge') || opt.id.includes('funnel')) {
                  closePwaApp('chat');
                  openPwaApp('c2p');
                } else {
                  modalChatInput.value = opt.title;
                  modalChatForm.dispatchEvent(new Event('submit'));
                }
              };
              btnWrap.appendChild(btn);
            });
            typingMsg.appendChild(btnWrap);
          }
        } catch (err) {
          typingMsg.innerHTML = 'Estamos procesando su solicitud en modo contingencia. Su línea se encuentra activa.';
        }
        modalChatMessages.scrollTop = modalChatMessages.scrollHeight;
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
