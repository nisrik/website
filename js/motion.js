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
    el.style.setProperty("--d", Math.min(i * 70, 560) + "ms");
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
  document.querySelectorAll(".b a[href], .c-body p a[href], .c-body dd a[href], .c-sub a[href]").forEach(function (a) {
    if (a.hasAttribute("data-link") || /[↓→↗]\s*$/.test(a.textContent)) return;
    var u; try { u = new URL(a.getAttribute("href"), location.href); } catch (e) { return; }
    var internal = u.origin === location.origin || inside.test(u.hostname) || u.protocol === "file:";
    a.setAttribute("data-link", internal ? "int" : "ext");
  });

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
