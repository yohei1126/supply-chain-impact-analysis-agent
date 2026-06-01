const $ = (id) => document.getElementById(id);

let graphNetwork = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const text = await res.text();
  let body = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { detail: text };
    }
  }
  if (!res.ok) {
    const detail = body?.detail ?? res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function setReadyStatus(ok) {
  const el = $("status-ready");
  if (ok) {
    el.textContent = "Ready";
    el.classList.add("ok");
    el.classList.remove("warn");
  } else {
    el.textContent = "Unavailable";
    el.classList.add("warn");
    el.classList.remove("ok");
  }
}

async function refreshStatus() {
  try {
    await api("/health");
    setReadyStatus(true);
  } catch {
    setReadyStatus(false);
  }
}

function showError(message) {
  const el = $("error");
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
}

function renderEvidence(evidence) {
  const list = $("evidence-list");
  list.innerHTML = "";
  if (!evidence?.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "No evidence statements for this question.";
    list.appendChild(li);
    return;
  }
  for (const item of evidence) {
    const li = document.createElement("li");
    li.textContent = item.claim ?? "";
    list.appendChild(li);
  }
}

function renderFindings(findings) {
  const list = $("findings-list");
  list.innerHTML = "";
  if (!findings?.length) {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "No specific findings for this question.";
    list.appendChild(li);
    return;
  }
  for (const item of findings) {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  }
}

async function runAnalysis() {
  const goal = $("goal").value.trim();
  if (!goal) {
    showError("Enter a question first.");
    return;
  }

  const btn = $("run-btn");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  showError("");

  try {
    const body = await api("/v1/agent/run", {
      method: "POST",
      body: JSON.stringify({ goal, mode: "auto" }),
    });

    $("explanation").textContent = body.explanation || "No summary available.";
    renderFindings(body.findings);
    renderEvidence(body.evidence);
    renderGraphView(body.graph_view);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze";
  }
}

function renderGraphView(graphView) {
  const container = $("graph-network");
  const caption = $("graph-caption");
  const view = graphView || {};
  const nodes = view.nodes || [];
  const edges = view.edges || [];

  if (!nodes.length) {
    caption.textContent =
      "No map for this question yet. Try a supplier (SUP-xxx) or path (COMP-xxx to PROD-xxx) example.";
    if (graphNetwork) {
      graphNetwork.destroy();
      graphNetwork = null;
    }
    container.innerHTML = "";
    return;
  }

  caption.textContent = `${view.node_count} items in your supply chain view (${view.seed_count} directly related to your question).`;

  if (typeof vis === "undefined") {
    container.textContent = "Map viewer failed to load.";
    return;
  }

  const visNodes = new vis.DataSet(
    nodes.map((n) => ({
      id: n.id,
      label: n.display?.split("\n")[0] || n.entity_id,
      title: n.title,
      color: {
        background: n.color,
        border: n.seed ? "#f5f0e6" : n.color,
        highlight: { background: n.color, border: "#fff" },
      },
      borderWidth: n.seed ? 3 : 1,
      font: { color: "#e8edf4", size: 12 },
    }))
  );
  const visEdges = new vis.DataSet(
    edges.map((e, i) => ({
      id: i,
      from: e.from,
      to: e.to,
      label: e.label,
      arrows: e.arrows || "to",
      font: { color: "#8b9cb3", size: 10, align: "middle" },
      color: { color: "#4a5a6e", highlight: "#e8a838" },
    }))
  );

  if (graphNetwork) {
    graphNetwork.destroy();
  }
  container.style.height = "100%";
  graphNetwork = new vis.Network(
    container,
    { nodes: visNodes, edges: visEdges },
    {
      layout: { hierarchical: { enabled: true, direction: "LR", sortMethod: "directed" } },
      physics: { enabled: false },
      interaction: { hover: true, tooltipDelay: 100 },
      edges: { smooth: { type: "cubicBezier" } },
    }
  );
}

function bindQueryExamples() {
  document.querySelectorAll(".query-example").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("goal").value = btn.dataset.goal ?? "";
      document.querySelectorAll(".query-example").forEach((el) => el.classList.remove("is-selected"));
      btn.classList.add("is-selected");
      $("goal").focus();
    });
  });
}

$("run-btn").addEventListener("click", runAnalysis);
bindQueryExamples();
refreshStatus();

window.addEventListener("resize", () => {
  if (graphNetwork) graphNetwork.redraw();
});
