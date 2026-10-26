/* Aplica tema y tamaño de texto antes del primer pintado para evitar parpadeos. */
(function () {
  try {
    var s = JSON.parse(localStorage.getItem('estudio:v1') || '{}');
    var ui = s.ui || {};
    var root = document.documentElement;
    var theme = ui.theme || 'auto';
    root.dataset.theme = theme;
    if (ui.scale) root.style.fontSize = (ui.scale * 100) + '%';
    var light = theme === 'light' || (theme === 'auto' && window.matchMedia('(prefers-color-scheme: light)').matches);
    var meta = document.getElementById('meta-theme');
    if (meta) meta.setAttribute('content', light ? '#f4f6fa' : '#0b1020');
  } catch (e) { /* sin almacenamiento */ }
})();
