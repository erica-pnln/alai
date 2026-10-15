/* Kabaybay AI — UI motion: word-stagger, scroll-reveal, pointer tilt.
   Idempotent + resilient: re-scans after Streamlit re-renders. */
(function () {
  if (window.__kbMotion) return;
  window.__kbMotion = true;

  function boot() {
    var doc = document;
    var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;
    doc.documentElement.classList.add('kb-anim');
    var lastPageTitle = null;

    var WORD_TARGETS = '.home-hero-heading, .main h1, .verse-of-day-ref, .featured-study-topic, .home-section-heading, .home-hero-sub, .home-hero-kicker';
    var REVEAL_TARGETS = '.home-hero, .verse-of-day, .featured-study, .jump-help, .notice, .page-title-container, div[data-testid="stVerticalBlockBorderWrapper"]';
    var FADE_TARGETS = '.scripture-card, .result-card, .passage-summary';
    var TILT_TARGETS = '.home-hero, .verse-of-day, .featured-study, .scripture-card, .result-card';

    var io = ('IntersectionObserver' in window) ? new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('kb-in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' }) : null;

    function inView(el) {
      var r = el.getBoundingClientRect();
      return r.top < (window.innerHeight * 0.94) && r.bottom > 0;
    }

    function splitWords(el) {
      if (el.getAttribute('data-kb-split') === '1') return;
      var hasElement = false, i;
      for (i = 0; i < el.childNodes.length; i++) {
        if (el.childNodes[i].nodeType === 1) { hasElement = true; break; }
      }
      if (hasElement) return; /* skip nodes with markup (e.g. <sup> verse numbers) */
      var text = el.textContent.replace(/\s+/g, ' ').trim();
      if (!text) return;
      var parts = text.split(' ');
      var frag = doc.createDocumentFragment();
      for (i = 0; i < parts.length; i++) {
        var s = doc.createElement('span');
        s.className = 'kb-word';
        s.textContent = parts[i];
        s.style.transitionDelay = (i * 24) + 'ms';
        frag.appendChild(s);
        frag.appendChild(doc.createTextNode(' '));
      }
      el.textContent = '';
      el.appendChild(frag);
      el.setAttribute('data-kb-split', '1');
    }

    function reveal(el, cls) {
      if (!el.classList.contains(cls)) el.classList.add(cls);
      if (io) io.observe(el); else el.classList.add('kb-in');
    }

    function scan() {
      var pageTitle = doc.querySelector('.page-title-container h1, .main h1, .main h2');
      if (pageTitle) {
        var titleText = pageTitle.textContent.trim();
        if (lastPageTitle === null) {
          lastPageTitle = titleText;
        } else if (titleText && titleText !== lastPageTitle) {
          lastPageTitle = titleText;
          var pageContent = doc.querySelector('[data-testid="stMainBlockContainer"]');
          if (pageContent) {
            pageContent.classList.remove('mark-page-transition');
            void pageContent.offsetWidth;
            pageContent.classList.add('mark-page-transition');
            setTimeout(function () {
              pageContent.classList.remove('mark-page-transition');
            }, 320);
          }
        }
      }

      var i, list;
      list = doc.querySelectorAll(WORD_TARGETS);
      for (i = 0; i < list.length; i++) splitWords(list[i]);

      list = doc.querySelectorAll('.kb-word');
      for (i = 0; i < list.length; i++) {
        if (inView(list[i])) list[i].classList.add('kb-in');
        else if (io) io.observe(list[i]);
      }

      list = doc.querySelectorAll(REVEAL_TARGETS);
      for (i = 0; i < list.length; i++) reveal(list[i], 'kb-reveal');

      list = doc.querySelectorAll(FADE_TARGETS);
      for (i = 0; i < list.length; i++) reveal(list[i], 'kb-fade');

      list = doc.querySelectorAll(TILT_TARGETS);
      for (i = 0; i < list.length; i++) if (!list[i].classList.contains('kb-tilt')) list[i].classList.add('kb-tilt');
    }

    /* Pointer tilt (delegated — bound once) */
    if (!window.__kbTilt) {
      window.__kbTilt = true;
      doc.addEventListener('pointermove', function (e) {
        if (e.pointerType === 'touch') return;
        var t = e.target;
        var card = t && t.closest ? t.closest('.kb-tilt') : null;
        if (!card) return;
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = 'perspective(1000px) rotateX(' + (-py * 1).toFixed(2) + 'deg) rotateY(' + (px * 1.2).toFixed(2) + 'deg) translateY(-1px)';
      }, { passive: true });
      doc.addEventListener('pointerout', function (e) {
        if (e.pointerType === 'touch') return;
        var t = e.target;
        var card = t && t.closest ? t.closest('.kb-tilt') : null;
        if (card && (!e.relatedTarget || !card.contains(e.relatedTarget))) card.style.transform = '';
      }, { passive: true });
    }

    scan();

    /* Re-scan when Streamlit re-renders content */
    var pending = null;
    if ('MutationObserver' in window) {
      new MutationObserver(function () {
        if (pending) return;
        pending = setTimeout(function () { pending = null; scan(); }, 120);
      }).observe(doc.body, { childList: true, subtree: true });
    }
    var ticks = 0;
    var iv = setInterval(function () { scan(); if (++ticks > 25) clearInterval(iv); }, 400);
  }

  function ready(fn) {
    if (document.readyState !== 'loading') setTimeout(fn, 0);
    else document.addEventListener('DOMContentLoaded', fn);
  }
  ready(boot);
})();
