// Pipeline Dashboard — drill-down panel controller.
// Exposes window.__pipelineDrilldown = { open(node), close() }.
// Vanilla ES2020; offline-first (no network fetches).

(function () {
  "use strict";

  const panel = document.getElementById("pipeline-drilldown");
  const root = document.getElementById("pipeline-root");
  const stateEl = document.getElementById("pipeline-state");
  if (!panel) return;

  let badgeMap = {};
  if (stateEl) {
    try {
      const parsed = JSON.parse(stateEl.textContent || "{}");
      if (parsed && typeof parsed.badges === "object") badgeMap = parsed.badges;
    } catch (e) {
      // ignore; drilldown still works without badges
    }
  }

  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  function renderBadges(nodeId) {
    const badges = badgeMap[nodeId];
    if (!badges || typeof badges !== "object") return null;
    const wrap = el("div", "badges");
    Object.keys(badges).forEach(function (k) {
      const v = badges[k];
      const b = el("span", "badge", k + ": " + v);
      wrap.appendChild(b);
    });
    return wrap.childNodes.length ? wrap : null;
  }

  function populate(node) {
    panel.innerHTML = "";

    const closeBtn = el("button", "close-btn", "\u00d7");
    closeBtn.setAttribute("aria-label", "Close");
    closeBtn.addEventListener("click", api.close);
    panel.appendChild(closeBtn);

    panel.appendChild(el("h2", null, node.name || node.id));
    const meta = el("div", "node-card__id", node.id + " \u00b7 " + (node.kind || "unknown"));
    panel.appendChild(meta);

    const badges = renderBadges(node.id);
    if (badges) {
      const section = el("section", "badges-section");
      section.appendChild(el("h3", null, "Metrics"));
      section.appendChild(badges);
      panel.appendChild(section);
    }

    // Lessons — placeholder; future work loads lessons/<comp_id>.json lazily.
    const lessons = el("section", "lessons");
    lessons.appendChild(el("h3", null, "Lessons"));
    lessons.appendChild(el("div", "placeholder", "n/a"));
    panel.appendChild(lessons);

    // Open Issues — placeholder.
    const issues = el("section", "open-issues");
    issues.appendChild(el("h3", null, "Open Issues"));
    issues.appendChild(el("div", "placeholder", "n/a"));
    panel.appendChild(issues);
  }

  const api = {
    open: function (node) {
      if (!node) return;
      populate(node);
      panel.removeAttribute("hidden");
      if (root) root.classList.add("drilldown-open");
    },
    close: function () {
      panel.setAttribute("hidden", "");
      if (root) root.classList.remove("drilldown-open");
    },
  };

  window.__pipelineDrilldown = api;
})();
