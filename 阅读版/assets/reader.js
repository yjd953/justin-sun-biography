(function () {
  'use strict';
  var root = document.documentElement;
  var toc = document.getElementById('toc');
  var open = document.getElementById('open-menu');
  var current = document.getElementById('current');
  var theme = document.getElementById('theme');
  var size = 19;
  var night = false;
  try {
    size = Math.max(16, Math.min(26, Number(localStorage.getItem('book-size')) || 19));
    night = localStorage.getItem('book-night') === 'true';
  } catch (ignore) {}
  function persist() {
    try {
      localStorage.setItem('book-size', String(size));
      localStorage.setItem('book-night', String(night));
    } catch (ignore) {}
  }
  function apply() {
    root.style.setProperty('--body-size', size + 'px');
    root.classList.toggle('night', night);
    theme.textContent = night ? '日读' : '夜读';
    theme.setAttribute('aria-pressed', String(night));
  }
  function menu(show) {
    toc.classList.toggle('open', show);
    open.setAttribute('aria-expanded', String(show));
  }
  function jumpTo(target) {
    root.style.scrollBehavior = 'auto';
    target.scrollIntoView({ block: 'start' });
  }
  document.getElementById('smaller').addEventListener('click', function () {
    size = Math.max(16, size - 1);
    apply();
    persist();
  });
  document.getElementById('larger').addEventListener('click', function () {
    size = Math.min(26, size + 1);
    apply();
    persist();
  });
  theme.addEventListener('click', function () {
    night = !night;
    apply();
    persist();
  });
  open.addEventListener('click', function () { menu(!toc.classList.contains('open')); });
  document.getElementById('close-menu').addEventListener('click', function () { menu(false); });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') menu(false);
  });
  document.querySelectorAll('.toc a[href^="#"]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      var target = document.getElementById(link.getAttribute('href').slice(1));
      if (!target) return;
      event.preventDefault();
      menu(false);
      history.pushState(null, '', link.getAttribute('href'));
      jumpTo(target);
      updateCurrent();
    });
  });
  document.querySelectorAll('sup a').forEach(function (link) {
    link.addEventListener('click', function () {
      var target = document.getElementById(link.getAttribute('href').slice(1));
      var details = target && target.querySelector('details');
      if (details) details.open = true;
    });
  });
  var headings = Array.from(document.querySelectorAll('main h2[id],main h3[id]'));
  var links = Array.from(document.querySelectorAll('.toc nav a'));
  var ticking = false;
  function updateCurrent() {
    var active = null;
    headings.forEach(function (heading) {
      if (heading.getBoundingClientRect().top <= 180) active = heading;
    });
    current.textContent = active ? active.textContent : '流量与筹码';
    links.forEach(function (link) {
      link.classList.toggle('active', !!active && link.getAttribute('href') === '#' + active.id);
    });
    ticking = false;
  }
  window.addEventListener('scroll', function () {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(updateCurrent);
    }
  }, { passive: true });
  if (location.hash) {
    var initialTarget = document.getElementById(location.hash.slice(1));
    if (initialTarget) {
      jumpTo(initialTarget);
      if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function () {
          jumpTo(initialTarget);
          updateCurrent();
        });
      }
    }
  }
  apply();
  updateCurrent();
})();
