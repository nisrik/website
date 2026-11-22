/* Mobile menu, and the header that hides on scroll down and returns on scroll up. */
(function () {
  var hdr = document.getElementById('hdr'), lastY = window.scrollY, tick = false;
  if (hdr) hdr.classList.toggle('scrolled', window.scrollY > 8);
  if (hdr) window.addEventListener('scroll', function () {
    if (tick) return; tick = true;
    requestAnimationFrame(function () {
      var y = window.scrollY;
      hdr.classList.toggle('scrolled', y > 8);
      hdr.classList.toggle('hide', y > lastY && y > 160 && !document.body.classList.contains('menu-open'));
      lastY = y; tick = false;
    });
  }, { passive: true });
  var b = document.getElementById('burger'), m = document.getElementById('menu');
  if (!b || !m) return;
  function set(open) {
    b.setAttribute('aria-expanded', open); b.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.body.classList.toggle('menu-open', open);
    if (open) { m.hidden = false; requestAnimationFrame(function () { m.classList.add('on'); }); }
    else { m.classList.remove('on'); setTimeout(function () { if (!document.body.classList.contains('menu-open')) m.hidden = true; }, 300); }
  }
  b.addEventListener('click', function () { set(!document.body.classList.contains('menu-open')); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
  window.matchMedia('(min-width: 800px)').addEventListener('change', function (e) { if (e.matches) set(false); });
})();
