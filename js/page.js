/* Every page: highlight the current section in the side list, parallax on the cover image, colour on touch devices. */
(function () {
  "use strict";
  var ids = [].map.call(document.querySelectorAll(".c-sec[id]"), function (s) { return s.id; });
  if (ids.length && window.NMB) NMB.spy(ids, ".toc a[data-spy-link]", "data-spy-link");
  if (window.NMB) NMB.grainOnTouch();

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
