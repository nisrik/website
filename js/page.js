/* Every page: highlight the current section in the side list, parallax on the cover image, colour on touch devices. */
(function () {
  "use strict";
  var ids = [].map.call(document.querySelectorAll(".c-sec[id]"), function (s) { return s.id; });
  if (ids.length && window.NMB) NMB.spy(ids, ".toc a[data-spy-link]", "data-spy-link");
  if (window.NMB) NMB.grainOnTouch();

  /* side list: smooth scroll to the section (done in script so it also works when the system asks for reduced motion) */
  function topOffset() { return (parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 0); }
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest('.toc a[href^="#"]');
    if (!a || ev.defaultPrevented || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button) return;
    var t = document.getElementById(a.getAttribute("href").slice(1));
    if (!t) return;
    ev.preventDefault();
    var from = window.pageYOffset, to = Math.max(0, t.getBoundingClientRect().top + from - topOffset() + 1);
    var dist = Math.abs(to - from), dur = Math.min(1100, 450 + dist * 0.25), start = null;
    function ease(x) { return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
    function step(now) {
      if (start === null) start = now;
      var k = Math.min(1, (now - start) / dur);
      window.scrollTo(0, from + (to - from) * ease(k));
      if (k < 1) requestAnimationFrame(step);
    }
    document.documentElement.style.scrollBehavior = "auto";   /* don't let CSS smoothing fight the animation */
    requestAnimationFrame(function (n) { step(n); });
    try { history.pushState(null, "", "#" + t.id); } catch (e) {}
    setTimeout(function () { document.documentElement.style.scrollBehavior = ""; }, dur + 50);
  });

  var cover = document.querySelector(".parallax img");
  if (!cover || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  var frame = cover.parentNode, ticking = false;
  function update() {
    var r = frame.getBoundingClientRect(), vh = window.innerHeight || 1;
    if (r.bottom > 0 && r.top < vh) {
      var p = (r.top + r.height / 2 - vh / 2) / vh;
      cover.style.transform = "translate3d(0," + (p * -9).toFixed(2) + "%,0)";
    }
    ticking = false;
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  window.addEventListener("resize", update);
  update();
})();
