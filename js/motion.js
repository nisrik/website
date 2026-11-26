/* Motion shared by the Inquiry and course pages. Everything here is optional:
   if it doesn't run, the pages are complete, just still. */
(function () {
  "use strict";
  
  /* ---- 1. hairlines draw in as they reach the viewport ---- */
  var LINES = ".c-sec, .sub, .grp, .rows .row, .objectives li, .dl-list > div, .bullets li, .tbl .r, .link-list li, .c-top.ruled, .c-end, .objectives";
  var lines = [].slice.call(document.querySelectorAll(LINES));
  lines.forEach(function (el) {
    var sibs = el.parentNode ? [].filter.call(el.parentNode.children, function (c) { return c.matches(LINES); }) : [];
    var i = Math.max(0, sibs.indexOf(el));
    var dense = el.matches(".rows .row, .objectives li, .dl-list > div, .bullets li, .tbl .r, .link-list li");
    el.style.setProperty("--d", (dense ? Math.min(i * 24, 192) : Math.min(i * 70, 560)) + "ms");
    if (el.classList.contains("objectives")) [].forEach.call(el.children, function (li, n) { li.style.setProperty("--i", n); });
  });
  if (!("IntersectionObserver" in window)) lines.forEach(function (el) { el.classList.add("line-in"); });
  else {
    var lo = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("line-in"); lo.unobserve(e.target); } });
    }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });
    lines.forEach(function (el) { lo.observe(el); });
  }

  /* ---- links: mark inside-the-site (→) and outside (↗) ---- */
  var inside = /(^|\.)nonemoreblue\.com$/i;
  document.querySelectorAll(".c-pdf a[href]").forEach(function (a) { a.setAttribute("data-link", "dl"); });
  document.querySelectorAll(".b a[href], .c-body p a[href], .c-body dd a[href], .c-sub a[href], .tbl a[href], .c-samples h2 a[href], .hero-title a[href]").forEach(function (a) {
    if (a.hasAttribute("data-link") || /[↓→↗]\s*$/.test(a.textContent)) return;
    var u; try { u = new URL(a.getAttribute("href"), location.href); } catch (e) { return; }
    var internal = u.origin === location.origin || inside.test(u.hostname) || u.protocol === "file:";
    var kind = /\.pdf$/i.test(u.pathname) ? "dl" : (internal ? "int" : "ext");
    var n = a.nextSibling;
    if (n && n.nodeType === 3 && n.nodeValue.charAt(0) === ".") {
      /* link ends a sentence: the arrow comes after the full stop */
      var sp = document.createElement("span"); sp.className = "stop"; sp.setAttribute("data-link", kind); sp.textContent = ".";
      n.nodeValue = n.nodeValue.slice(1);
      a.parentNode.insertBefore(sp, n);
      a.setAttribute("data-stop", "");
    }
    a.setAttribute("data-link", kind);
  });

  /* ---- arrows that would wrap when they open: draw them over the gap instead, so the link never jumps from under the pointer ---- */
  function probeArrows() {
    var ts = document.querySelectorAll("a[data-link]:not([data-stop]), .stop[data-link]");
    ts.forEach(function (t) { t.removeAttribute("data-noshift"); });
    var before = [];
    ts.forEach(function (t) { var r = t.getClientRects(); before.push([r.length, r.length ? r[r.length - 1].top : 0]); });
    ts.forEach(function (t) { t.classList.add("probe"); });
    var flags = [];
    ts.forEach(function (t, i) { var r = t.getClientRects(); flags.push(r.length !== before[i][0] || (r.length && Math.abs(r[r.length - 1].top - before[i][1]) > 2)); });
    ts.forEach(function (t) { t.classList.remove("probe"); });
    ts.forEach(function (t, i) { if (flags[i]) t.setAttribute("data-noshift", ""); });
  }
  probeArrows();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(probeArrows);
  var pt; window.addEventListener("resize", function () { clearTimeout(pt); pt = setTimeout(probeArrows, 150); });

  /* ---- 11. page transitions: the clicked course title carries over ---- */
  var lastLink = null;
  document.addEventListener("click", function (e) { var a = e.target.closest && e.target.closest("a[href]"); lastLink = a && /(teaching|essays)\//.test(a.getAttribute("href")) ? a : null; }, true);
  window.addEventListener("pageswap", function (e) { if (e.viewTransition && lastLink) lastLink.style.viewTransitionName = "course-title"; });
  window.addEventListener("pagereveal", function (e) {
    if (!e.viewTransition) return;
    var t = document.querySelector(".c-title"); if (!t) return;
    t.style.viewTransitionName = "course-title"; document.documentElement.classList.add("vt-in");
    e.viewTransition.finished.finally(function () { t.style.viewTransitionName = ""; document.documentElement.classList.remove("vt-in"); });
  });
})();
