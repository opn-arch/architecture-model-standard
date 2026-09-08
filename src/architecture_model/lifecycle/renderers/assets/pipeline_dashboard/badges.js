// Pipeline Dashboard — node cards + badge rendering.
// Reads state from <script id="pipeline-state"> and populates #pipeline-root.
// Vanilla ES2020; no build step.

(function () {
  "use strict";

  const stateEl = document.getElementById("pipeline-state");
  const root = document.getElementById("pipeline-root");
  if (!stateEl || !root) return;

  let state;
  try {
    state = JSON.parse(stateEl.textContent || "{}");
  } catch (e) {
    console.error("pipeline-state: invalid JSON", e);
    return;
  }

  const nodes = Array.isArray(state.nodes) ? state.nodes : [];
  const badgeMap = state.badges && typeof state.badges === "object" ? state.badges : {};

  // Threshold classifiers ---------------------------------------------------
  function classifyValidation(score) {
    if (typeof score !== "number") return null;
    if (score >= 85) return "badge--ok";
    if (score >= 60) return "badge--warn";
    return "badge--error";
  }
  function classifyFailureRate(rate) {
    if (typeof rate !== "number") return null;
    if (rate >= 0.10) return "badge--error";
    if (rate >= 0.02) return "badge--warn";
    return "badge--ok";
  }

  function makeBadge(label, cls) {
    const b = document.createElement("span");
    b.className = "badge" + (cls ? " " + cls : "");
    b.textContent = label;
    return b;
  }

  function renderBadges(container, nodeBadges) {
    if (!nodeBadges || typeof nodeBadges !== "object") return;
    const wrap = document.createElement("div");
    wrap.className = "badges";

    const vs = nodeBadges.validation_score;
    const vsCls = classifyValidation(vs);
    if (vsCls) wrap.appendChild(makeBadge("val " + vs, vsCls));

    const inv = nodeBadges.invocations_7d;
    if (typeof inv === "number") {
      wrap.appendChild(makeBadge("inv7d " + inv, ""));
      const fr = nodeBadges.failure_rate_7d;
      const frCls = classifyFailureRate(fr);
      if (frCls && inv > 0) {
        wrap.appendChild(makeBadge("fail " + (fr * 100).toFixed(1) + "%", frCls));
      }
    }

    if (wrap.childNodes.length) container.appendChild(wrap);
  }

  // Node card render --------------------------------------------------------
  function renderCard(node) {
    const card = document.createElement("div");
    const kind = (node.kind || "").toLowerCase();
    card.className = "node-card node-card--" + kind;
    card.dataset.nodeId = node.id;

    const idEl = document.createElement("div");
    idEl.className = "node-card__id";
    idEl.textContent = node.id;
    card.appendChild(idEl);

    const nameEl = document.createElement("div");
    nameEl.className = "node-card__name";
    nameEl.textContent = node.name || node.id;
    card.appendChild(nameEl);

    const kindEl = document.createElement("div");
    kindEl.className = "node-card__kind";
    kindEl.textContent = node.kind || "";
    card.appendChild(kindEl);

    renderBadges(card, badgeMap[node.id]);

    card.addEventListener("click", function () {
      if (window.__pipelineDrilldown && typeof window.__pipelineDrilldown.open === "function") {
        window.__pipelineDrilldown.open(node);
      }
    });

    return card;
  }

  // Mount all cards ---------------------------------------------------------
  const frag = document.createDocumentFragment();
  nodes.forEach(function (n) { frag.appendChild(renderCard(n)); });
  root.appendChild(frag);
})();
