const $ = (id) => document.getElementById(id);

let graphNetwork = null;
let federationGraphNetwork = null;

const DOMAIN_META = {
  sourcing: {
    label: "sourcing",
    team: "procurement",
    className: "domain-sourcing",
    query: "components_by_supplier",
    edge: "SUPPLIED_BY",
  },
  ebom: {
    label: "ebom",
    team: "engineering",
    className: "domain-ebom",
    query: "products_by_components",
    edge: "USED_IN",
  },
  routing: {
    label: "routing",
    team: "manufacturing",
    className: "domain-routing",
    query: "processes_by_components",
    edge: "INPUT_OF",
  },
};

const DOMAIN_EXAMPLES = {
  sourcing: [
    { title: "SUP-002 components", supplier_id: "SUP-002", desc: "All parts supplied by SUP-002 (sourcing graph only)." },
    { title: "SUP-001 high risk", supplier_id: "SUP-001", desc: "Components from Nihon Steel — procurement view." },
  ],
  ebom: [
    { title: "COMP-103 products", component_ids: ["COMP-103"], desc: "Which finished goods use COMP-103 (ebom only)." },
    { title: "Multiple parts", component_ids: ["COMP-100", "COMP-103"], desc: "Component → product links for two IDs." },
  ],
  routing: [
    { title: "COMP-103 processes", component_ids: ["COMP-103"], desc: "Manufacturing processes that consume COMP-103." },
    { title: "Work centers", component_ids: ["COMP-100", "COMP-101"], desc: "Routing graph for two components." },
  ],
};

const AGENT_EXAMPLES = [
  {
    title: "German brass supplier disruption",
    goal:
      "Our German brass supplier might face a port strike next month. Which finished products and component parts should we worry about?",
    intent:
      "Test whether the agent can identify a supplier from country and material alone, then quantify BOM exposure when that supply line fails.",
    exploration:
      "Resolve clues (Germany + brass → Euro Brass GmbH) → bom_supplier_impact → sourcing SUPPLIED_BY rows joined to ebom USED_IN for affected components and finished goods.",
  },
  {
    title: "Servo motor drive shaft trace",
    goal:
      "The servo motor drive product relies on a drive shaft part. Can you trace how that component connects through the bill of materials to the finished assembly?",
    intent:
      "Test whether the agent maps everyday part and product names to graph entities without explicit COMP-xxx / PROD-xxx IDs.",
    exploration:
      "Infer drive shaft and Servo Motor Drive from the question → bom_supply_path → traverse ebom/routing edges (USED_IN, INPUT_OF, PRODUCED_BY) between the two nodes.",
  },
  {
    title: "Brass valve shortage",
    goal:
      "We're short on brass valve-related parts. Find similar components in our catalog and show which suppliers feed them.",
    intent:
      "Test multi-hop reasoning: semantic similarity first, then upstream supplier linkage — not a single pre-known part ID.",
    exploration:
      "Resolve brass valve-like parts via component master text search (name/material) → bom_supplier_impact or catalog impact queries on matched component IDs.",
  },
];

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

function showError(elId, message) {
  const el = $(elId);
  if (!message) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = message;
}

function parseComponentIds(raw) {
  return raw
    .split(/[,\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function bindModeTabs() {
  const tabs = document.querySelectorAll(".mode-tab");
  const panels = document.querySelectorAll(".mode-panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const panelId = tab.getAttribute("aria-controls");
      tabs.forEach((t) => {
        const active = t === tab;
        t.classList.toggle("is-active", active);
        t.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach((p) => {
        const active = p.id === panelId;
        p.classList.toggle("is-active", active);
        p.hidden = !active;
      });
      if (panelId === "panel-federation") {
        refitGraphNetwork(federationGraphNetwork, "federation-graph-network");
      } else if (panelId === "panel-agent") {
        refitGraphNetwork(graphNetwork, "graph-network");
      }
      window.dispatchEvent(new Event("resize"));
    });
  });
}

function refitGraphNetwork(network, containerId) {
  if (!network) return;
  const container = $(containerId);
  if (!container) return;
  requestAnimationFrame(() => {
    network.redraw();
    network.fit({ animation: false });
  });
}

function syncDomainParams() {
  const graphId = $("domain-graph").value;
  const isSourcing = graphId === "sourcing";
  $("domain-param-supplier").hidden = !isSourcing;
  $("domain-param-components").hidden = isSourcing;
  renderDomainExamples(graphId);
}

function renderAgentExamples() {
  const container = $("agent-examples");
  container.innerHTML = "";
  for (const ex of AGENT_EXAMPLES) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "query-example agent-example";
    btn.dataset.goal = ex.goal;
    btn.innerHTML = `
      <span class="query-example-title">${ex.title}</span>
      <span class="query-example-meta query-example-intent">
        <span class="meta-label">Intent</span>
        ${ex.intent}
      </span>
      <span class="query-example-meta query-example-explore">
        <span class="meta-label">Expected exploration</span>
        ${ex.exploration}
      </span>
    `;
    btn.addEventListener("click", () => {
      $("goal").value = ex.goal;
      document.querySelectorAll(".agent-example").forEach((el) => el.classList.remove("is-selected"));
      btn.classList.add("is-selected");
      $("goal").focus();
    });
    container.appendChild(btn);
  }
}

function renderDomainExamples(graphId) {
  const container = $("domain-examples");
  container.innerHTML = "";
  for (const ex of DOMAIN_EXAMPLES[graphId] || []) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "query-example domain-example";
    btn.innerHTML = `
      <span class="query-example-title">${ex.title}</span>
      <span class="query-example-desc">${ex.desc}</span>
    `;
    btn.addEventListener("click", () => {
      $("domain-graph").value = graphId;
      syncDomainParams();
      if (ex.supplier_id) $("domain-supplier-id").value = ex.supplier_id;
      if (ex.component_ids) $("domain-component-ids").value = ex.component_ids.join(", ");
      document.querySelectorAll(".domain-example").forEach((el) => el.classList.remove("is-selected"));
      btn.classList.add("is-selected");
    });
    container.appendChild(btn);
  }
}

function renderTable(theadId, tbodyId, rows) {
  const thead = $(theadId);
  const tbody = $(tbodyId);
  thead.innerHTML = "";
  tbody.innerHTML = "";

  if (!rows?.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 3;
    td.className = "muted";
    td.textContent = "No rows returned.";
    tr.appendChild(td);
    tbody.appendChild(tr);
    return;
  }

  const columns = Object.keys(rows[0]);
  const headRow = document.createElement("tr");
  for (const col of columns) {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);

  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const col of columns) {
      const td = document.createElement("td");
      const val = row[col];
      td.textContent = val == null ? "" : typeof val === "object" ? JSON.stringify(val) : String(val);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

function renderDomainQuerySpec(query) {
  const block = $("domain-query-block");
  const dl = $("domain-query-spec");
  const expr = $("domain-query-expression");

  if (!query) {
    block.hidden = true;
    return;
  }

  const rows = [
    ["Graph", query.graph_id],
    ["Owner team", query.owner_team],
    ["Query spec", query.query_spec],
    ["Ontology", query.ontology_source],
    ["Engine", query.engine],
    ["Language", query.language],
    ["Scope", query.scope],
  ];

  dl.innerHTML = "";
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value ?? "";
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  const params = document.createElement("dd");
  params.className = "query-params";
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(query.parameters, null, 2);
  params.appendChild(pre);
  const dt = document.createElement("dt");
  dt.textContent = "Parameters";
  dl.appendChild(dt);
  dl.appendChild(params);

  expr.textContent = query.cypher || "";

  block.hidden = false;
}

function renderDomainResult(body) {
  const result = body.result;
  const meta = DOMAIN_META[result.graph_id] || {};
  const badge = $("domain-result-badge");
  badge.hidden = false;
  badge.className = `domain-badge ${meta.className || ""}`;
  badge.textContent = `${result.graph_id} · ${result.query_name}`;

  $("domain-summary").textContent = result.summary;
  $("domain-summary").classList.remove("muted");
  renderDomainQuerySpec(body.query);
  renderTable("domain-table-head", "domain-table-body", result.rows);
  $("domain-table-wrap").hidden = false;
}

async function runDomainQuery() {
  const graphId = $("domain-graph").value;
  const btn = $("domain-run-btn");
  btn.disabled = true;
  btn.textContent = "Querying…";
  showError("domain-error", "");

  const payload = { graph_id: graphId };
  if (graphId === "sourcing") {
    payload.supplier_id = $("domain-supplier-id").value.trim();
  } else {
    payload.component_ids = parseComponentIds($("domain-component-ids").value);
  }

  try {
    const body = await api("/v1/federation/domain-query", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderDomainResult(body);
  } catch (err) {
    showError("domain-error", err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run domain query";
  }
}

function severityClass(severity) {
  if (severity === "high") return "severity-high";
  if (severity === "medium") return "severity-medium";
  return "severity-low";
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderFederationSteps(domainQueries, joinPlan) {
  const container = $("federation-steps");
  container.innerHTML = "";

  for (const step of joinPlan || []) {
    const match = domainQueries.find((q) => q.graph_id === step.graph_id);
    const meta = DOMAIN_META[step.graph_id] || {};
    const card = document.createElement("article");
    card.className = `step-card ${meta.className || ""}`;
    card.innerHTML = `
      <header class="step-card-head">
        <span class="step-num">Step ${step.step}</span>
        <span class="domain-badge ${meta.className || ""}">${step.graph_id}</span>
        <span class="step-edge">${step.edge}</span>
      </header>
      <p class="step-desc">${step.description}</p>
      <p class="step-bridge">Bridge: <code>${step.bridge}</code></p>
      ${
        match
          ? `<p class="step-summary">${match.summary}</p>
             <p class="step-meta">${match.row_count} row(s) · <code>${match.query_name}</code></p>
             <details class="step-cypher-block">
               <summary>Cypher query</summary>
               <pre class="step-cypher">${escapeHtml(match.cypher || "")}</pre>
             </details>`
          : `<p class="step-summary muted">No data</p>`
      }
    `;
    container.appendChild(card);
  }
}

function renderProblems(problems) {
  const list = $("problems-list");
  list.innerHTML = "";
  if (!problems?.length) {
    list.innerHTML = '<li class="muted">No problems identified.</li>';
    return;
  }
  for (const p of problems) {
    const li = document.createElement("li");
    li.className = severityClass(p.severity);
    li.innerHTML = `<span class="severity-tag">${p.severity}</span> ${p.message}`;
    list.appendChild(li);
  }
}

function renderMitigations(mitigations) {
  const list = $("mitigations-list");
  list.innerHTML = "";
  if (!mitigations?.length) {
    list.innerHTML = '<li class="muted">No mitigations suggested.</li>';
    return;
  }
  for (const m of mitigations) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="owner-tag">${m.owner_team}</span> ${m.action}`;
    list.appendChild(li);
  }
}

async function runFederation() {
  const supplierId = $("federation-supplier-id").value.trim();
  if (!supplierId) {
    showError("federation-error", "Enter a supplier ID.");
    return;
  }

  const btn = $("federation-run-btn");
  btn.disabled = true;
  btn.textContent = "Federating…";
  showError("federation-error", "");

  try {
    const body = await api("/v1/federation/analyze", {
      method: "POST",
      body: JSON.stringify({ supplier_id: supplierId }),
    });

    $("federation-placeholder").hidden = true;
    $("federation-results").hidden = false;

    const scoreEl = $("impact-score");
    scoreEl.hidden = false;
    scoreEl.textContent = `impact score ${body.impact_score}`;

    renderFederationSteps(body.domain_queries, body.join_plan);
    renderProblems(body.problems);
    renderMitigations(body.mitigations);
    renderTable("federated-table-head", "federated-table-body", body.federated_rows);
    renderGraphView(body.graph_view, "federation-graph-network", "federation-graph-caption", "federation");
  } catch (err) {
    showError("federation-error", err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run federation";
  }
}

function renderEvidence(evidence) {
  const list = $("evidence-list");
  list.innerHTML = "";
  if (!evidence?.length) {
    list.innerHTML = '<li class="muted">No evidence statements for this question.</li>';
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
    list.innerHTML = '<li class="muted">No specific findings for this question.</li>';
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
    showError("error", "Enter a question first.");
    return;
  }

  const btn = $("run-btn");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  showError("error", "");

  try {
    const body = await api("/v1/agent/run", {
      method: "POST",
      body: JSON.stringify({ goal, mode: "auto" }),
    });

    $("explanation").textContent = body.explanation || "No summary available.";
    renderFindings(body.findings);
    renderEvidence(body.evidence);
    renderGraphView(body.graph_view, "graph-network", "graph-caption", "agent");
  } catch (err) {
    showError("error", err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze";
  }
}

function renderGraphView(graphView, containerId, captionId, mode) {
  const container = $(containerId);
  const caption = $(captionId);
  const view = graphView || {};
  const nodes = view.nodes || [];
  const edges = view.edges || [];

  const isFederation = mode === "federation";
  let networkRef = isFederation ? federationGraphNetwork : graphNetwork;

  if (!nodes.length) {
    caption.textContent = isFederation
      ? "No federated map for this supplier — try SUP-001 or SUP-002 after seeding domain graphs."
      : view.seed_count > 0
        ? "Graph data is missing or stale. Re-seed Neo4j, then retry: uv run python scripts/seed_complex_bom.py --reset"
        : "No map for this question yet. Try a supplier (SUP-xxx) or path example.";
    if (networkRef) {
      networkRef.destroy();
      if (isFederation) federationGraphNetwork = null;
      else graphNetwork = null;
    }
    container.innerHTML = "";
    return;
  }

  caption.textContent = `${view.node_count} items (${view.seed_count} directly related).`;

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

  if (networkRef) networkRef.destroy();

  if (isFederation) {
    container.style.minHeight = "280px";
    container.style.height = "280px";
  } else {
    container.style.minHeight = "240px";
    container.style.height = "240px";
  }

  const network = new vis.Network(
    container,
    { nodes: visNodes, edges: visEdges },
    {
      layout: { hierarchical: { enabled: true, direction: "LR", sortMethod: "directed" } },
      physics: { enabled: false },
      interaction: { hover: true, tooltipDelay: 100 },
      edges: { smooth: { type: "cubicBezier" } },
    }
  );

  if (isFederation) federationGraphNetwork = network;
  else graphNetwork = network;

  refitGraphNetwork(network, containerId);
}

function bindExamples() {
  document.querySelectorAll(".federation-example").forEach((btn) => {
    btn.addEventListener("click", () => {
      $("federation-supplier-id").value = btn.dataset.supplier ?? "";
      document.querySelectorAll(".federation-example").forEach((el) => el.classList.remove("is-selected"));
      btn.classList.add("is-selected");
    });
  });
}

$("domain-graph").addEventListener("change", syncDomainParams);
$("domain-run-btn").addEventListener("click", runDomainQuery);
$("federation-run-btn").addEventListener("click", runFederation);
$("run-btn").addEventListener("click", runAnalysis);

bindModeTabs();
renderAgentExamples();
bindExamples();
syncDomainParams();
refreshStatus();

window.addEventListener("resize", () => {
  if (graphNetwork) graphNetwork.redraw();
  if (federationGraphNetwork) federationGraphNetwork.redraw();
});
