/* Shared behaviour for every explainer page.
 *
 * To add a page:
 *   1. Copy any existing page as a starting point.
 *   2. Add one line to PAGES below. The nav on every page updates.
 *
 * Helpers this file provides:
 *   <a class="L">L608</a> or <a class="L">L608–613</a>  -> link to those lines of the demo XML on GitHub
 *   <a class="term" data-term="joiner">Joiner</a>       -> link + hover card from glossary-data.js
 *   Site.renderCode(el, lines, {highlight: [608]})        -> code block with real XML line numbers
 *   Site.tabs(container)                                  -> simple accessible tabs
 */
(function () {
  "use strict";

  var PAGES = [
    { href: "index.html", title: "Overview" },
    { href: "glossary.html", title: "Glossary" },
    { href: "input.html", title: "The input XML" },
    { href: "example.html", title: "One mapping, end to end" },
    { href: "steps.html", title: "The 5 steps" },
    { href: "decisions.html", title: "Decisions" },
    { href: "process-log.html", title: "Process log" }
  ];

  var XML_URL = "https://github.com/infinitelambda/flowline-pwc-demo/blob/main/FLOWLINE_DEMO_JAFFLESHOP.xml";

  function renderNav() {
    var nav = document.getElementById("site-nav");
    if (!nav) return;
    var here = location.pathname.split("/").pop() || "index.html";
    PAGES.forEach(function (p) {
      var a = document.createElement("a");
      a.href = p.href;
      a.textContent = p.title;
      if (p.href === here) a.setAttribute("aria-current", "page");
      nav.appendChild(a);
    });
  }

  function linkLines(root) {
    (root || document).querySelectorAll("a.L:not([href])").forEach(function (a) {
      var nums = a.textContent.match(/\d+/g);
      if (!nums) return;
      var frag = "#L" + nums[0] + (nums[1] ? "-L" + nums[1] : "");
      a.href = XML_URL + frag;
      a.target = "_blank";
      a.rel = "noopener";
      a.title = "Open these lines of the demo XML on GitHub";
    });
  }

  var tip;
  function glossaryById(id) {
    var list = window.GLOSSARY || [];
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }
  function showTip(a) {
    var g = glossaryById(a.dataset.term);
    if (!g) return;
    if (!tip) { tip = document.createElement("div"); tip.className = "term-tip"; document.body.appendChild(tip); }
    tip.innerHTML = "";
    var b = document.createElement("b"); b.textContent = g.term; tip.appendChild(b);
    tip.appendChild(document.createTextNode(g.def));
    var r = a.getBoundingClientRect();
    tip.style.display = "block";
    var left = Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - 316);
    tip.style.left = Math.max(window.scrollX + 8, left) + "px";
    tip.style.top = (window.scrollY + r.bottom + 6) + "px";
  }
  function hideTip() { if (tip) tip.style.display = "none"; }
  function linkTerms(root) {
    (root || document).querySelectorAll("a.term[data-term]").forEach(function (a) {
      if (!a.getAttribute("href")) a.href = "glossary.html#" + a.dataset.term;
      a.addEventListener("mouseenter", function () { showTip(a); });
      a.addEventListener("focus", function () { showTip(a); });
      a.addEventListener("mouseleave", hideTip);
      a.addEventListener("blur", hideTip);
    });
  }

  /* lines: array of [lineNumber, text]. lineNumber may be null for an elision row ("…"). */
  function renderCode(el, lines, opts) {
    opts = opts || {};
    var hl = opts.highlight || [];
    el.innerHTML = "";
    el.classList.add("code");
    lines.forEach(function (pair) {
      var row = document.createElement("span");
      row.className = "row" + (hl.indexOf(pair[0]) >= 0 ? " hl" : "");
      var ln = document.createElement("span");
      ln.className = "ln";
      ln.textContent = pair[0] == null ? "…" : String(pair[0]);
      row.appendChild(ln);
      row.appendChild(document.createTextNode(pair[1]));
      el.appendChild(row);
    });
  }

  function tabs(container) {
    var buttons = container.querySelectorAll('[role="tab"]');
    function select(btn) {
      buttons.forEach(function (b) {
        var on = b === btn;
        b.setAttribute("aria-selected", on ? "true" : "false");
        var panel = document.getElementById(b.getAttribute("aria-controls"));
        if (panel) panel.hidden = !on;
      });
    }
    buttons.forEach(function (b) { b.addEventListener("click", function () { select(b); }); });
    if (buttons.length) select(buttons[0]);
  }

  /* Plain text in, DOM fragment out: "L161–180" style refs become XML line links. */
  function textWithLines(text) {
    var frag = document.createDocumentFragment();
    var re = /L\d+(?:[–-]\d+)?/g, last = 0, m;
    while ((m = re.exec(text))) {
      frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      var a = document.createElement("a");
      a.className = "L";
      a.textContent = m[0];
      frag.appendChild(a);
      last = m.index + m[0].length;
    }
    frag.appendChild(document.createTextNode(text.slice(last)));
    var wrap = document.createElement("span");
    wrap.appendChild(frag);
    linkLines(wrap);
    return wrap;
  }

  /* Let long identifiers (s_FL_JS_STAGING_FULL) wrap after underscores instead of mid-word. */
  function breakAtUnderscores(root) {
    (root || document).querySelectorAll(".flow-node .t").forEach(function (el) {
      if (el.dataset.wbr || el.children.length) return;
      var parts = el.textContent.split("_");
      el.textContent = "";
      parts.forEach(function (p, i) {
        el.appendChild(document.createTextNode(p + (i < parts.length - 1 ? "_" : "")));
        if (i < parts.length - 1) el.appendChild(document.createElement("wbr"));
      });
      el.dataset.wbr = "1";
    });
  }

  window.Site = {
    renderCode: renderCode, tabs: tabs, linkLines: linkLines, linkTerms: linkTerms,
    textWithLines: textWithLines, breakAtUnderscores: breakAtUnderscores, XML_URL: XML_URL
  };

  document.addEventListener("DOMContentLoaded", function () {
    renderNav();
    linkLines();
    linkTerms();
    breakAtUnderscores();
    document.querySelectorAll(".tabs-group").forEach(tabs);
  });
})();
