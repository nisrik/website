/* Light / dark. Saved choice wins; otherwise follows the system. */
(function () {
  var root = document.documentElement;
  function current() {
    return root.getAttribute("data-theme") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  }
  function label(btn) {
    var dark = current() === "dark", t = dark ? "Switch to light mode" : "Switch to dark mode";
    btn.title = t; btn.setAttribute("aria-label", t);
  }
  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    label(btn);
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      function apply() {
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (e) {}
        label(btn);
      }
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!document.startViewTransition) { apply(); return; }
      if (reduce) { document.startViewTransition(apply); return; }   /* soft crossfade only */
      /* the new theme opens as a circle from the toggle */
      var r = btn.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      var rad = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      root.classList.add("theming");
      var vt = document.startViewTransition(apply);
      vt.ready.then(function () {
        root.animate(
          { clipPath: ["circle(0px at " + x + "px " + y + "px)", "circle(" + rad + "px at " + x + "px " + y + "px)"] },
          { duration: 750, easing: "cubic-bezier(.65,0,.25,1)", pseudoElement: "::view-transition-new(root)" });
      });
      vt.finished.finally(function () { root.classList.remove("theming"); });
    });
  });
})();
