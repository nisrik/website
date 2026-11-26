/* Home: keep the background video playing (some browsers need muted set from script), and the Pause / Play control. */
(function () {
  "use strict";
  var v = document.querySelector(".hero-video"), btn = document.querySelector(".hero-pause");
  if (!v) return;
  v.muted = true;
  var p = v.play(); if (p && p.catch) p.catch(function () {});
  if (window.NMB) NMB.grainOnTouch();
  if (!btn) return;
  btn.addEventListener("click", function () {
    if (v.paused) { v.play(); btn.classList.remove("paused"); btn.setAttribute("aria-label", "Pause the background video"); }
    else { v.pause(); btn.classList.add("paused"); btn.setAttribute("aria-label", "Play the background video"); }
  });
})();
