/* Light / dark. Starts with the system setting; once the toggle is used, that choice is remembered on every page. */
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
  function saved() {
    var t; try { t = localStorage.getItem("theme"); } catch (e) {}
    if (t !== "light" && t !== "dark") { var m = /nmbtheme=(light|dark)/.exec(window.name || ""); t = m && m[1]; }
    return t === "light" || t === "dark" ? t : null;
  }
  /* keep every page and tab in step: back/forward cache restores, other tabs */
  function sync() {
    var t = saved(); if (!t || t === root.getAttribute("data-theme")) return;
    root.setAttribute("data-theme", t);
    var btn = document.getElementById("theme-toggle"); if (btn) label(btn);
  }
  window.addEventListener("pageshow", sync);
  window.addEventListener("storage", sync);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) sync(); });

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    label(btn);
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      function apply() {
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (e) {}
        /* fallback for browsers that give every local file its own storage (opening the files directly) */
        try { window.name = (window.name || "").replace(/nmbtheme=\w+;?/, "") + "nmbtheme=" + next + ";"; } catch (e) {}
        label(btn);
      }
      /* soft crossfade, whatever the motion setting */
      if (document.startViewTransition) document.startViewTransition(apply); else apply();
    });
  });
})();
