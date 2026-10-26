/* Sitio de estudio: progreso local, filtros, navegación y herramientas. Sin dependencias. */
(() => {
  'use strict';

  const KEY = 'estudio:v1';
  const DASH_KEY = 'cv_study_checks_v1';
  const SCALES = [0.9, 1, 1.12, 1.25, 1.4];
  const THEMES = ['auto', 'light', 'dark'];
  const THEME_LABEL = { auto: 'Automático', light: 'Claro', dark: 'Oscuro' };
  const FILTER_LABEL = { all: 'Todos', pending: 'Pendientes', done: 'Hechos' };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // ---------- Estado persistente ----------
  let state = load();
  function load() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY) || '{}');
      return { checks: s.checks || {}, open: s.open || {}, scroll: s.scroll || {}, ui: s.ui || {} };
    } catch (e) {
      return { checks: {}, open: {}, scroll: {}, ui: {} };
    }
  }
  function loadDashChecks() {
    try { return JSON.parse(localStorage.getItem(DASH_KEY) || '{}'); } catch (e) { return {}; }
  }
  function saveDashCheck(syncKey, val) {
    if (!syncKey) return;
    try {
      const map = loadDashChecks();
      if (val === null) delete map[syncKey];
      else map[syncKey] = !!val;
      localStorage.setItem(DASH_KEY, JSON.stringify(map));
    } catch (e) {}
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* almacenamiento no disponible */ }
  }

  const docs = $$('.doc');
  const tabs = $$('.tab');
  const drawer = $('#drawer');
  const scrim = $('#scrim');
  const btnMenu = $('#btn-menu');
  let activeDoc = null;

  // ---------- Tema y tamaño de texto ----------
  function effectiveTheme() {
    const t = state.ui.theme || 'auto';
    if (t !== 'auto') return t;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  function applyTheme() {
    const t = state.ui.theme || 'auto';
    document.documentElement.dataset.theme = t;
    const meta = $('#meta-theme');
    if (meta) meta.setAttribute('content', effectiveTheme() === 'light' ? '#f4f6fa' : '#0b1020');
    $('#theme-label').textContent = 'Tema: ' + THEME_LABEL[t];
  }
  function applyScale() {
    const s = state.ui.scale || 1;
    document.documentElement.style.fontSize = (s * 100) + '%';
  }
  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', applyTheme);

  // ---------- Progreso ----------
  function taskDone(input) {
    const id = input.dataset.id;
    const syncKey = input.dataset.syncKey;
    const dashMap = loadDashChecks();
    if (syncKey && syncKey in dashMap) {
      state.checks[id] = !!dashMap[syncKey];
      return !!dashMap[syncKey];
    }
    if (id in state.checks) {
      if (syncKey) saveDashCheck(syncKey, state.checks[id]);
      return !!state.checks[id];
    }
    return input.dataset.default === '1';
  }
  function applyChecks() {
    $$('.task-check').forEach((input) => {
      const done = taskDone(input);
      input.checked = done;
      input.closest('.task').classList.toggle('done', done);
    });
  }
  function refresh() {
    let gDone = 0;
    let gTotal = 0;
    docs.forEach((doc) => {
      $$('.sec', doc).forEach((sec) => {
        const boxes = $$('.task-check', sec);
        const done = boxes.filter((b) => b.checked).length;
        sec.dataset.total = boxes.length;
        sec.dataset.done = done;
        sec.dataset.pending = boxes.length - done;
        const badge = $('.sec-count', sec);
        badge.hidden = boxes.length === 0;
        badge.textContent = done + '/' + boxes.length;
        badge.classList.toggle('complete', boxes.length > 0 && done === boxes.length);
      });
      const all = $$('.task-check', doc);
      const done = all.filter((b) => b.checked).length;
      const pct = all.length ? Math.round((done / all.length) * 100) : 0;
      $('.fill', doc).style.setProperty('--p', pct);
      $('.doc-pct', doc).textContent = pct + '%';
      const tab = $('.tab[data-doc="' + doc.dataset.doc + '"] .n');
      if (tab) tab.textContent = done + '/' + all.length;
      gDone += done;
      gTotal += all.length;
    });
    $('#global-pct').textContent = (gTotal ? Math.round((gDone / gTotal) * 100) : 0) + '%';
    buildToc();
  }

  // ---------- Índice de secciones ----------
  function buildToc() {
    const list = $('#toc');
    list.textContent = '';
    if (!activeDoc) return;
    $$('.sec', activeDoc).forEach((sec) => {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '#' + sec.id;
      const name = document.createElement('span');
      name.textContent = $('.sec-title', sec).textContent;
      a.appendChild(name);
      if (Number(sec.dataset.total) > 0) {
        const mini = document.createElement('span');
        mini.className = 'mini';
        mini.textContent = sec.dataset.done + '/' + sec.dataset.total;
        a.appendChild(mini);
      }
      li.appendChild(a);
      list.appendChild(li);
    });
  }

  // ---------- Secciones abiertas / filtro ----------
  function applyOpenState() {
    const filtering = document.body.dataset.filter !== 'all';
    docs.forEach((doc) => {
      const secs = $$('.sec', doc);
      const hasSaved = secs.some((s) => s.id in state.open);
      secs.forEach((sec, idx) => {
        if (filtering) sec.open = true;
        else if (hasSaved) sec.open = !!state.open[sec.id];
        else sec.open = idx === firstPendingIndex(secs) || sec.hasAttribute('data-open-default');
      });
    });
  }
  function firstPendingIndex(secs) {
    const idx = secs.findIndex((s) => Number(s.dataset.pending) > 0);
    return idx === -1 ? 0 : idx;
  }
  function setFilter(mode) {
    state.ui.filter = mode;
    save();
    document.body.dataset.filter = mode;
    $$('[data-filter-btn]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.filterBtn === mode)));
    applyOpenState();
  }

  // ---------- Navegación entre documentos ----------
  function showDoc(id, { restoreScroll = true } = {}) {
    if (activeDoc) state.scroll[activeDoc.dataset.doc] = Math.round(window.scrollY);
    const next = docs.find((d) => d.dataset.doc === id) || docs[0];
    activeDoc = next;
    docs.forEach((d) => { d.hidden = d !== next; });
    tabs.forEach((t) => {
      if (t.dataset.doc === next.dataset.doc) {
        t.setAttribute('aria-current', 'page');
        try { t.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' }); } catch (e) {}
      } else {
        t.removeAttribute('aria-current');
      }
    });
    $$('[data-nav-doc]').forEach((b) => {
      if (b.dataset.navDoc === next.dataset.doc) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });
    $('#top-doc').textContent = $('h1', next).textContent;
    state.ui.doc = next.dataset.doc;
    save();
    buildToc();
    if ($('#q-study') && $('#q-study').value.trim()) runSearch($('#q-study').value);
    if (restoreScroll) {
      const y = state.scroll[next.dataset.doc] || 0;
      window.scrollTo({ top: y, behavior: 'instant' });
    }
  }

  function route() {
    const hash = decodeURIComponent(location.hash.replace('#', ''));
    const sec = hash ? document.getElementById(hash) : null;
    if (sec && sec.classList.contains('sec')) {
      showDoc(sec.closest('.doc').dataset.doc, { restoreScroll: false });
      sec.open = true;
      sec.scrollIntoView({ block: 'start' });
    } else if (hash && docs.some((d) => d.dataset.doc === hash)) {
      showDoc(hash);
    } else if (!activeDoc) {
      showDoc(state.ui.doc || docs[0].dataset.doc);
    }
  }

  // ---------- Menú lateral ----------
  const isDesktop = () => window.matchMedia('(min-width: 1024px)').matches;
  function openDrawer() {
    drawer.classList.add('open');
    scrim.hidden = false;
    btnMenu.setAttribute('aria-expanded', 'true');
    document.body.classList.add('no-scroll');
    $('#btn-close').focus();
  }
  function closeDrawer({ focusMenu = true } = {}) {
    if (isDesktop()) return;
    drawer.classList.remove('open');
    scrim.hidden = true;
    btnMenu.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('no-scroll');
    if (focusMenu) btnMenu.focus();
  }

  // ---------- Avisos ----------
  let toastTimer;
  function toast(msg) {
    const el = $('#toast');
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
  }

  // ---------- Siguiente pendiente ----------
  function goNext() {
    const next = $$('.task:not(.done)', activeDoc).find((t) => t.offsetParent !== null || t.closest('details:not([open])'));
    if (!next) { toast('No quedan tareas pendientes en este documento'); return; }
    const sec = next.closest('details.sec');
    if (sec) sec.open = true;
    next.scrollIntoView({ block: 'center', behavior: 'smooth' });
    next.classList.remove('flash');
    void next.offsetWidth;
    next.classList.add('flash');
  }

  // ---------- Flashcards (Active Recall), Audio (TTS) y Cronómetro + Wake Lock ----------
  function enhanceQuotes() {
    $$('.doc blockquote:not(.callout)').forEach((bq) => {
      if ($('.quote-tools', bq)) return;
      const body = document.createElement('div');
      body.className = 'quote-body';
      while (bq.firstChild) body.appendChild(bq.firstChild);

      const tools = document.createElement('div');
      tools.className = 'quote-tools';

      const btnRecall = document.createElement('button');
      btnRecall.type = 'button';
      btnRecall.className = 'quote-btn';
      btnRecall.dataset.quoteAction = 'recall';
      btnRecall.setAttribute('aria-pressed', 'false');
      btnRecall.textContent = '👁️ Ensayar';

      const btnTts = document.createElement('button');
      btnTts.type = 'button';
      btnTts.className = 'quote-btn';
      btnTts.dataset.quoteAction = 'tts';
      btnTts.setAttribute('aria-pressed', 'false');
      btnTts.textContent = '🔊 Escuchar';

      const btnTimer = document.createElement('button');
      btnTimer.type = 'button';
      btnTimer.className = 'quote-btn';
      btnTimer.dataset.quoteAction = 'timer';
      btnTimer.textContent = '⏱️ Medir tiempo';

      tools.appendChild(btnRecall);
      tools.appendChild(btnTts);
      tools.appendChild(btnTimer);

      const hint = document.createElement('div');
      hint.className = 'recall-hint';
      hint.textContent = '👆 Recita tu respuesta en voz alta y toca aquí para verificar';

      bq.appendChild(tools);
      bq.appendChild(body);
      bq.appendChild(hint);
    });
  }

  function toggleGlobalRecall() {
    const active = document.body.classList.toggle('recall-mode');
    $$('blockquote.is-blurred, blockquote.is-revealed').forEach((bq) => {
      bq.classList.remove('is-blurred', 'is-revealed');
      const btn = $('[data-quote-action="recall"]', bq);
      if (btn) {
        btn.setAttribute('aria-pressed', String(active));
        btn.textContent = active ? '👁️ Mostrar' : '👁️ Ensayar';
      }
    });
    ['#bnav-recall', '#drawer-recall-btn'].forEach((sel) => {
      const b = $(sel);
      if (b) b.setAttribute('aria-pressed', String(active));
    });
    toast(active ? 'Modo Memoria activo: guiones ocultos para ensayar' : 'Modo Memoria desactivado');
  }

  let activeSpeechBtn = null;
  function stopSpeech() {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (activeSpeechBtn) {
      activeSpeechBtn.setAttribute('aria-pressed', 'false');
      activeSpeechBtn.textContent = '🔊 Escuchar';
      activeSpeechBtn = null;
    }
  }
  function speakQuote(bq, btn) {
    if (!('speechSynthesis' in window)) {
      toast('Tu navegador no soporta lectura de voz');
      return;
    }
    if (activeSpeechBtn === btn) {
      stopSpeech();
      return;
    }
    stopSpeech();
    const body = $('.quote-body', bq) || bq;
    const text = body.innerText.replace(/["“”]/g, '').trim();
    if (!text) return;

    const utter = new SpeechSynthesisUtterance(text);
    const isEnglish = /\b(Hi, I'm|Throughout my career|Currently, I'm|Full Stack Engineer)\b/i.test(text);
    utter.lang = isEnglish ? 'en-US' : 'es-MX';
    utter.rate = 1.02;
    activeSpeechBtn = btn;
    btn.setAttribute('aria-pressed', 'true');
    btn.textContent = '⏹️ Detener';
    utter.onend = () => stopSpeech();
    utter.onerror = () => stopSpeech();
    window.speechSynthesis.speak(utter);
  }

  // ---------- Cronómetro de Pitch + Screen Wake Lock ----------
  let timerId = null;
  let timerSec = 0;
  let wakeLock = null;

  async function requestWakeLock() {
    if (!('wakeLock' in navigator)) return;
    try {
      if (!wakeLock) {
        wakeLock = await navigator.wakeLock.request('screen');
        const badge = $('#wake-badge');
        if (badge) badge.hidden = false;
        wakeLock.addEventListener('release', () => {
          wakeLock = null;
          if (badge) badge.hidden = true;
        });
      }
    } catch (e) { /* no disponible o rechazado */ }
  }
  function releaseWakeLock() {
    if (wakeLock) {
      wakeLock.release().catch(() => {});
      wakeLock = null;
    }
    const badge = $('#wake-badge');
    if (badge) badge.hidden = true;
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && timerId) requestWakeLock();
  });

  function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
  }
  function renderTimer() {
    const clock = $('#timer-clock');
    const hint = $('#timer-hint');
    const dot = $('#timer-dot');
    const playBtn = $('#timer-play-btn');
    const bnavLabel = $('#bnav-timer-label');
    const bnavBtn = $('#bnav-timer');
    const formatted = formatTime(timerSec);
    if (clock) {
      clock.textContent = formatted;
      clock.classList.remove('zone-good', 'zone-warn', 'zone-over');
      if (timerSec >= 60 && timerSec <= 90) clock.classList.add('zone-good');
      else if (timerSec > 90 && timerSec <= 150) clock.classList.add('zone-warn');
      else if (timerSec > 150) clock.classList.add('zone-over');
    }
    if (hint) {
      if (timerSec < 60) hint.textContent = 'Meta pitch: 60s–90s';
      else if (timerSec <= 90) hint.textContent = '✅ Ventana ideal (60–90s)';
      else if (timerSec <= 150) hint.textContent = '⚡ Ventana STAR (1.5–2.5m)';
      else hint.textContent = '⚠️ >2:30m: sintetiza y cierra';
    }
    if (dot) dot.classList.toggle('running', !!timerId);
    if (playBtn) playBtn.textContent = timerId ? 'Pausar' : 'Reanudar';
    if (bnavLabel) bnavLabel.textContent = (!$('#timer-bar').hidden && (timerId || timerSec > 0)) ? formatted : 'Reloj';
    if (bnavBtn) bnavBtn.setAttribute('aria-pressed', String(!$('#timer-bar').hidden));
  }
  function startTimer({ reset = false } = {}) {
    const bar = $('#timer-bar');
    if (bar) bar.hidden = false;
    if (reset) timerSec = 0;
    if (!timerId) {
      timerId = setInterval(() => {
        timerSec += 1;
        renderTimer();
      }, 1000);
    }
    requestWakeLock();
    renderTimer();
  }
  function pauseTimer() {
    if (timerId) {
      clearInterval(timerId);
      timerId = null;
    }
    renderTimer();
  }
  function closeTimer() {
    pauseTimer();
    timerSec = 0;
    releaseWakeLock();
    const bar = $('#timer-bar');
    if (bar) bar.hidden = true;
    renderTimer();
  }

  // ---------- Buscador instantáneo ----------
  function norm(str) {
    return (str || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }
  function toggleSearch(force) {
    const bar = $('#search-bar');
    const input = $('#q-study');
    if (!bar || !input) return;
    const open = typeof force === 'boolean' ? force : bar.hidden;
    bar.hidden = !open;
    ['#btn-top-search', '#bnav-search'].forEach((sel) => {
      const b = $(sel);
      if (b) {
        b.setAttribute('aria-expanded', String(open));
        b.setAttribute('aria-pressed', String(open));
      }
    });
    if (open) {
      input.focus();
      input.select();
    } else {
      input.value = '';
      runSearch('');
    }
  }
  function runSearch(rawQuery) {
    const q = norm(rawQuery.trim());
    const countEl = $('#search-count');
    if (!q) {
      $$('.sec').forEach((s) => s.classList.remove('search-hidden'));
      tabs.forEach((t) => t.classList.remove('has-hit'));
      if (countEl) countEl.hidden = true;
      applyOpenState();
      return;
    }
    let activeHits = 0;
    docs.forEach((doc) => {
      let docHits = 0;
      $$('.sec', doc).forEach((sec) => {
        const match = norm(sec.innerText).includes(q);
        if (doc === activeDoc) {
          sec.classList.toggle('search-hidden', !match);
          if (match) {
            sec.open = true;
            activeHits += 1;
          }
        }
        if (match) docHits += 1;
      });
      const tab = $('.tab[data-doc="' + doc.dataset.doc + '"]');
      if (tab) tab.classList.toggle('has-hit', docHits > 0 && doc !== activeDoc);
    });
    if (countEl) {
      countEl.hidden = false;
      countEl.textContent = activeHits + (activeHits === 1 ? ' sección' : ' secciones');
    }
  }

  // ---------- Respaldo y restauración de progreso ----------
  const dlg = $('#dlg-sync');
  function exportCode() {
    return 'ESTUDIO1:' + btoa(JSON.stringify({ v: 1, checks: state.checks }));
  }
  function importCode(raw) {
    const text = raw.trim().replace(/^ESTUDIO1:/, '');
    const data = JSON.parse(atob(text));
    if (!data || typeof data.checks !== 'object') throw new Error('formato');
    state.checks = data.checks;
    save();
    applyChecks();
    refresh();
  }

  // ---------- Eventos ----------
  document.addEventListener('change', (e) => {
    const input = e.target.closest('.task-check');
    if (!input) return;
    state.checks[input.dataset.id] = input.checked;
    saveDashCheck(input.dataset.syncKey, input.checked);
    input.closest('.task').classList.toggle('done', input.checked);
    save();
    refresh();
  });

  window.addEventListener('storage', (e) => {
    if (e.key === KEY || e.key === DASH_KEY) {
      state = load();
      applyChecks();
      refresh();
    }
  });

  const qInput = $('#q-study');
  if (qInput) {
    qInput.addEventListener('input', () => runSearch(qInput.value));
    qInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') toggleSearch(false);
    });
  }

  document.addEventListener('click', (e) => {
    const navDocBtn = e.target.closest('[data-nav-doc]');
    if (navDocBtn) {
      location.hash = '#' + navDocBtn.dataset.navDoc;
      showDoc(navDocBtn.dataset.navDoc);
      closeDrawer({ focusMenu: false });
      return;
    }

    const quoteAction = e.target.closest('[data-quote-action]');
    if (quoteAction) {
      const bq = quoteAction.closest('blockquote');
      const act = quoteAction.dataset.quoteAction;
      if (act === 'recall') {
        const globalMode = document.body.classList.contains('recall-mode');
        if (globalMode) {
          const revealed = bq.classList.toggle('is-revealed');
          quoteAction.setAttribute('aria-pressed', String(!revealed));
          quoteAction.textContent = revealed ? '👁️ Ocultar' : '👁️ Mostrar';
        } else {
          const blurred = bq.classList.toggle('is-blurred');
          quoteAction.setAttribute('aria-pressed', String(blurred));
          quoteAction.textContent = blurred ? '👁️ Mostrar' : '👁️ Ensayar';
        }
      } else if (act === 'tts') {
        speakQuote(bq, quoteAction);
      } else if (act === 'timer') {
        startTimer({ reset: true });
        toast('⏱️ Cronómetro iniciado (meta: 60s–90s)');
      }
      return;
    }

    const blurredClick = e.target.closest('blockquote.is-blurred .quote-body, blockquote.is-blurred .recall-hint, body.recall-mode blockquote:not(.callout):not(.is-revealed) .quote-body, body.recall-mode blockquote:not(.callout):not(.is-revealed) .recall-hint');
    if (blurredClick) {
      const bq = blurredClick.closest('blockquote');
      const btn = $('[data-quote-action="recall"]', bq);
      if (document.body.classList.contains('recall-mode')) {
        bq.classList.add('is-revealed');
        if (btn) { btn.setAttribute('aria-pressed', 'false'); btn.textContent = '👁️ Ocultar'; }
      } else {
        bq.classList.remove('is-blurred');
        if (btn) { btn.setAttribute('aria-pressed', 'false'); btn.textContent = '👁️ Ensayar'; }
      }
      return;
    }

    const summary = e.target.closest('.sec > summary');
    if (summary) {
      const sec = summary.parentElement;
      setTimeout(() => {
        if (document.body.dataset.filter === 'all') { state.open[sec.id] = sec.open; save(); }
      });
      return;
    }
    const filterBtn = e.target.closest('[data-filter-btn]');
    if (filterBtn) { setFilter(filterBtn.dataset.filterBtn); return; }
    if (e.target.closest('#toc a')) { closeDrawer({ focusMenu: false }); return; }

    const action = e.target.closest('[data-action]');
    if (!action) return;
    switch (action.dataset.action) {
      case 'next': goNext(); break;
      case 'toggle-recall': toggleGlobalRecall(); closeDrawer({ focusMenu: false }); break;
      case 'toggle-timer': {
        const bar = $('#timer-bar');
        if (bar && bar.hidden) {
          startTimer({ reset: timerSec === 0 });
          toast('⏱️ Cronómetro activo + Pantalla encendida');
        } else {
          closeTimer();
        }
        closeDrawer({ focusMenu: false });
        break;
      }
      case 'timer-play': {
        if (timerId) pauseTimer();
        else startTimer({ reset: false });
        break;
      }
      case 'timer-reset': {
        startTimer({ reset: true });
        break;
      }
      case 'timer-close': closeTimer(); break;
      case 'toggle-search': toggleSearch(); break;
      case 'clear-search': toggleSearch(false); break;
      case 'expand': $$('.sec', activeDoc).forEach((s) => { s.open = true; }); break;
      case 'collapse': $$('.sec', activeDoc).forEach((s) => { s.open = false; }); break;
      case 'bigger': case 'smaller': {
        const i = SCALES.indexOf(state.ui.scale || 1);
        const j = Math.min(SCALES.length - 1, Math.max(0, (i === -1 ? 1 : i) + (action.dataset.action === 'bigger' ? 1 : -1)));
        state.ui.scale = SCALES[j];
        save(); applyScale();
        toast('Tamaño de texto: ' + Math.round(SCALES[j] * 100) + '%');
        break;
      }
      case 'theme': {
        const i = THEMES.indexOf(state.ui.theme || 'auto');
        state.ui.theme = THEMES[(i + 1) % THEMES.length];
        save(); applyTheme();
        break;
      }
      case 'sync': {
        $('#sync-text').value = exportCode();
        dlg.showModal();
        break;
      }
      case 'copy': {
        const ta = $('#sync-text');
        const done = () => toast('Código copiado');
        if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(ta.value).then(done, () => { ta.select(); });
        else { ta.select(); document.execCommand('copy'); done(); }
        break;
      }
      case 'import': {
        try { importCode($('#sync-text').value); dlg.close(); toast('Progreso restaurado'); }
        catch (err) { toast('Código no válido'); }
        break;
      }
      case 'close-dialog': dlg.close(); break;
      case 'reset-doc': {
        if (!confirm('¿Reiniciar el progreso de este documento?')) break;
        $$('.task-check', activeDoc).forEach((i) => {
          delete state.checks[i.dataset.id];
          saveDashCheck(i.dataset.syncKey, null);
        });
        save(); applyChecks(); refresh();
        toast('Progreso del documento reiniciado');
        break;
      }
      default: break;
    }
  });

  btnMenu.addEventListener('click', openDrawer);
  $('#btn-close').addEventListener('click', () => closeDrawer());
  scrim.addEventListener('click', () => closeDrawer());
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && drawer.classList.contains('open')) closeDrawer(); });
  window.addEventListener('hashchange', route);
  window.matchMedia('(min-width: 1024px)').addEventListener('change', () => closeDrawer({ focusMenu: false }));

  let scrollTimer;
  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      if (activeDoc) { state.scroll[activeDoc.dataset.doc] = Math.round(window.scrollY); save(); }
    }, 250);
  }, { passive: true });

  // ---------- Inicio ----------
  applyTheme();
  applyScale();
  enhanceQuotes();
  applyChecks();
  refresh();
  document.body.dataset.filter = state.ui.filter || 'all';
  $$('[data-filter-btn]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.filterBtn === document.body.dataset.filter)));
  route();
  applyOpenState();
  buildToc();

  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
    window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
  }
})();
