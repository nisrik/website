/* Shared helpers: DOM builder, reveal-on-scroll, current-section tracking. */
(function () {
  "use strict";
  var root = document.documentElement;
  root.classList.add("js");

  /* ---------- tiny DOM builder ---------- */
  function append(node, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { append(node, x); }); return; }
    node.appendChild(typeof c === "object" ? c : document.createTextNode(String(c)));
  }
  function h(tag, attrs) {
    var n = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v == null || v === false) return;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else n.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) append(n, arguments[i]);
    return n;
  }
  function pad(n) { return n < 10 ? "0" + n : String(n); }
  function safeUrl(u) { return /^(https?:\/\/|mailto:|images\/|syllabi\/|course\.html|index\.html|#)/i.test(u || "") ? u : ""; }

  /* ---------- reveal on scroll ---------- */
  var io = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" }) : null;

  function reveal(scope) {
    (scope || document).querySelectorAll(".rv, .w-host").forEach(function (n) {
      if (io) io.observe(n); else n.classList.add("in");
    });
  }

  /* split a heading into words that rise into place */
  function splitWords(node) {
    var text = node.textContent;
    node.textContent = "";
    node.setAttribute("aria-label", text);
    text.split(/\s+/).forEach(function (word, i, all) {
      var inner = h("span", { text: word, "aria-hidden": "true" });
      inner.style.transitionDelay = (i * 55) + "ms";
      node.appendChild(h("span", { class: "w" }, inner));
      if (i < all.length - 1) node.appendChild(document.createTextNode(" "));
    });
    node.classList.add("w-host");
  }

  /* ---------- current section tracking ---------- */
  function spy(sectionIds, linkSelector, attr) {
    if (!("IntersectionObserver" in window)) return;
    var links = {};
    document.querySelectorAll(linkSelector).forEach(function (a) { links[a.getAttribute(attr)] = a; });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        Object.keys(links).forEach(function (k) { links[k].classList.remove("is-current"); });
        var l = links[e.target.id];
        if (l) l.classList.add("is-current");
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    sectionIds.forEach(function (id) { var s = document.getElementById(id); if (s) obs.observe(s); });
  }

  /* ---------- touch devices: colour arrives when an index image is in view ---------- */
  function grainOnTouch() {
    if (!window.matchMedia("(hover: none)").matches || !("IntersectionObserver" in window)) return;
    var g = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.target.classList.toggle("in-view", e.intersectionRatio > 0.6); });
    }, { threshold: [0, 0.6, 1] });
    document.querySelectorAll(".grain-img").forEach(function (n) { g.observe(n); });
  }

  window.NMB = { h: h, pad: pad, safeUrl: safeUrl, reveal: reveal, splitWords: splitWords, spy: spy, grainOnTouch: grainOnTouch };
})();
