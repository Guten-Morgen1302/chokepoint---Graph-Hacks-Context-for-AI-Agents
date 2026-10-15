// Chokepoint front end. Every number on the card comes from tool JSON (ENG-8).
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const state = { finding: "F-1", findings: [], cy: null, display: null, p0: null, final: null, source: null, opener: null };

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || r.statusText);
  return body;
}

function banner(text) { const b = $("#banner"); b.hidden = !text; b.textContent = text || ""; }

async function boot() {
  if (window.BOOT.error) { banner("Graph unavailable: " + window.BOOT.error); return; }
  if (window.BOOT.readonly) banner("You're viewing a shared read-only copy (demo is busy). Decisions won't be saved.");
  $("#graph-mode").textContent = window.BOOT.graph;
  const f = await api("/api/findings");
  state.findings = f.findings;
  const chips = $("#finding-chips");
  chips.innerHTML = "";
  for (const x of f.findings) {
    const b = document.createElement("button");
    b.textContent = `Triage ${x.id}`;
    b.onclick = () => { selectFinding(x.id); triage(); };
    chips.appendChild(b);
  }
  selectFinding("F-1");
  refreshDecisions();
}

function selectFinding(id) {
  const f = state.findings.find((x) => x.id === id) || { id, title: "" };
  state.finding = id;
  $("#finding-id").textContent = id;
  $("#finding-title").textContent = f.title;
  $("#finding-meta").textContent = f.at ? `${f.severity} · ${f.at.slice(0, 16).replace("T", " ")}` : "";
  $("#triage").textContent = `Triage ${id}`;
}

function resetCard() {
  $("#hero").className = "hero muted";
  $("#hero").textContent = "Finding attack paths…";
  for (const id of ["#proof", "#why", "#metrics"]) $(id).textContent = "";
  $("#proof").className = "proof";
  $("#trail").innerHTML = "";
  $("#plan").innerHTML = "";
  $("#tickets").innerHTML = "";
  $("#narrative").hidden = true;
  $("#narrative").innerHTML = "";
}

function triage(question) {
  if (state.source) state.source.close();
  resetCard();
  $("#triage").disabled = true;
  const url = `/api/triage?finding=${encodeURIComponent(state.finding)}` + (question ? `&q=${encodeURIComponent(question)}` : "");
  const es = new EventSource(url);
  state.source = es;
  es.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.evidence) renderEvidence(ev.evidence);
    if (ev.type === "baseline") onBaseline(ev.data);
    else if (ev.type === "tool") onTool(ev);
    else if (ev.type === "final") { onFinal(ev); es.close(); $("#triage").disabled = false; }
  };
  es.onerror = () => { es.close(); $("#triage").disabled = false; if (!state.final) banner("Connection lost. Press Triage to retry."); };
  state.final = null;
}

// The model writes light Markdown; render bold, code and bullets only, after escaping.
const md = (t) => esc(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, '<span class="mono">$1</span>')
  .replace(/^\s*[*-] /gm, "• ").replace(/\n{2,}/g, "\n");

const planCost = (p) => `Revoke ${p.grants.length} grant${p.grants.length === 1 ? "" : "s"} · cost ${p.cost}`;

function onBaseline(b) {
  if (!b.ok) { $("#hero").textContent = `Couldn't analyse ${state.finding}: ${b.error}`; return; }
  const paths = b.paths.data, p0 = b.p0.data;
  state.p0 = p0; state.display = paths.display;
  if (!paths.crown_jewels_reachable.length) {
    $("#hero").textContent = `No crown jewel is reachable from ${state.finding}.`;
    return;
  }
  $("#hero").className = "hero muted";
  if (!p0.revocable) {
    $("#hero").innerHTML = `No revocable fix<span class="sub">Every route passes through an accepted or non-revocable grant.</span>`;
  } else {
    $("#hero").innerHTML = `Cheapest: ${esc(planCost(p0))}<span class="sub">Agent checking company records…</span>`;
  }
  $("#metrics").textContent = `${paths.crown_jewels_reachable.length} jewels reachable · ${paths.independent_routes ?? "∞"} independent routes · shortest: ${paths.shortest_route_grants} grants · cheapest: cost ${p0.cost} · revoke everything the identity holds: cost ${paths.naive_cost}`;
  $("#metrics").title = paths.routes_note;
  addTrail(`<span class="mono">P0</span> · cost ${p0.cost} · cheapest cut (algo.maxFlow)`, "");
  renderPlan(p0);
  drawGraph(paths.display, p0.grants.map((g) => g.id), state.accepted || []);
  renderRouteList(paths.display, p0.grants.map((g) => g.id));
}

function addTrail(html, cls) {
  const li = document.createElement("li");
  li.className = cls;
  li.innerHTML = html;
  $("#trail").appendChild(li);
}

function citeLinks(ids) {
  return (ids || []).map((id) => {
    const t = id.startsWith("doc:") ? "doc" : id.startsWith("msg:") ? "msg" : id.startsWith("SEC-") ? "ticket" : "node";
    return `<span class="cite" data-cite="${esc(id)}">${t} · ${esc(id.replace(/^(doc|msg):/, ""))}</span>`;
  }).join(", ");
}

function onTool(ev) {
  const r = ev.result, a = ev.input || {};
  if (ev.name === "explain_grant" && r.ok) {
    addTrail(`Read company records for ${r.data.grants.length} grants`, "muted");
  } else if (ev.name === "what_if") {
    if (!r.ok) addTrail(`▲ rejected: ${esc(r.error.replace(/^\w+: /, ""))}`, "rej");
    else addTrail(`<span class="mono">${r.data.plan_id}</span> · cost ${r.data.cost} · keep ${esc((a.keep || []).join(", "))} because ${citeLinks(a.cites)}`, "");
  } else if (ev.name === "choose_plan") {
    if (!r.ok) addTrail(`✗ ${esc(r.error)}`, "x");
  } else if (ev.name === "record_decision" && r.ok && r.data.status === "proposed") {
    addTrail(`▲ Agent proposes accepting risk on ${esc(r.data.draft.grant_id)}`, "rej");
  } else if (ev.name === "draft_tickets" && r.ok) {
    renderTickets(r.data.tickets);
  } else if (!r.ok) {
    addTrail(`▲ ${esc(ev.name)}: ${esc(r.error)}`, "rej");
  }
}

function onFinal(ev) {
  state.final = ev;
  if (ev.status === "error") {
    $("#hero").className = "hero"; $("#hero").textContent = ev.error.startsWith("graph unavailable") ? "Graph unavailable" : "Something went wrong";
    $("#why").textContent = ev.error; return;
  }
  const p0 = state.p0;
  let plan, why = "";
  if (ev.status === "chosen") {
    plan = ev.plan;
    const extra = p0 ? plan.cost - p0.cost : 0;
    why = extra > 0 ? `+${extra} cost · ${esc(ev.reason)} ${citeLinks(ev.cites)}` : `Cheapest plan checked against company records: ${esc(ev.reason || "no conflicts found")}`;
    $("#hero").className = "hero";
    $("#hero").innerHTML = `Agent's plan: ${esc(planCost(plan))}`;
    if (p0 && plan.plan_id !== "P0") addTrail(`<span class="mono">P0</span> · cost ${p0.cost} · ✗ not chosen`, "x");
    addTrail(`<span class="mono">${plan.plan_id}</span> · cost ${plan.cost} · ✓ chosen`, "ok");
  } else {
    const fb = ev.fallback || {};
    plan = fb.plan;
    $("#hero").className = "hero";
    if (!plan) { $("#hero").textContent = "No plan available"; return; }
    $("#hero").innerHTML = plan.revocable ? `Cheapest plan: ${esc(planCost(plan))}` : "No revocable fix";
    why = `○ Not reviewed by agent · ${esc(fb.reason)}`;
    if (!$("#trail").children.length || $("#trail").textContent.trim() === "") addTrail("Not reviewed. The plan above is the cheapest verified fix.", "muted");
  }
  if (plan.revocable) {
    const ok = plan.severed;
    $("#proof").className = ok ? "proof" : "proof bad";
    $("#proof").innerHTML = ok ? `✓ Severed: 0 routes remain (<span class="mono">${esc(plan.proof)}</span>)` : `✗ Plan ${esc(plan.plan_id)} does not sever (<span class="mono">${esc(plan.proof || "unverified")}</span>)`;
  }
  if (!plan.unique && plan.tie_reason) why += `${why ? " · " : ""}1 of 2 equally cheap plans · chosen: ${esc(plan.tie_reason)}`;
  if (ev.note && ev.status === "chosen") why += ` <span class="meta">(agent stopped early: ${esc(ev.note)})</span>`;
  $("#why").innerHTML = why;
  if (ev.narrative || ev.question) {
    const n = $("#narrative");
    n.hidden = false;
    const empty = ev.status === "fallback" ? `The agent is offline (${ev.fallback?.reason || "unavailable"}), so only the graph answer above is shown.` : "(no answer text)";
    n.innerHTML = (ev.question ? `<span class="q">You asked: ${esc(ev.question)}</span>` : "") + md(ev.narrative || empty);
  }
  if (ev.unverified_numbers && ev.unverified_numbers.length) $("#why").innerHTML += ` <span class="meta" title="The narrative mentions numbers not in the evidence">⚠ narrative may be inaccurate</span>`;
  renderPlan(plan);
  drawGraph(state.display, plan.grants.map((g) => g.id), [...(plan.kept || []), ...(state.accepted || [])]);
  renderRouteList(state.display, plan.grants.map((g) => g.id));
  for (const p of ev.proposals || []) renderProposal(p);
  bindCites();
}

function renderPlan(p) {
  const ul = $("#plan");
  ul.innerHTML = "";
  if (!p.revocable) { ul.innerHTML = `<li>Blocking: ${esc((p.blocking || []).join(", "))}</li>`; return; }
  if (!p.unique && p.alternative) {
    const alt = document.createElement("li");
    alt.className = "alt";
    alt.textContent = `Equally cheap alternative: ${p.alternative.map((g) => g.id).join(", ")}`;
    queueMicrotask(() => ul.appendChild(alt));
  }
  for (const g of p.grants) {
    const li = document.createElement("li");
    li.innerHTML = `<div class="row"><span class="gname">${esc(g.name)}</span><span class="mono">${esc(g.id)}</span>
      <button class="link" data-explain="${esc(g.id)}">Why does this exist?</button>
      <button class="link" data-accept="${esc(g.id)}">Accept risk…</button></div>
      <div class="costline">cost ${g.cost} = base 1 + used ${g.uses_30d}×/30d (+${g.cost - 1}) · breaks: ${p.services_broken.length ? esc(p.services_broken.join(", ")) : "none on record"}</div>`;
    ul.appendChild(li);
  }
  for (const g of p.kept_grants || []) {
    if ((state.accepted || []).includes(g.id)) continue;
    const li = document.createElement("li");
    li.className = "kept";
    li.innerHTML = `<div class="row"><span class="gname">Kept: ${esc(g.name)}</span><span class="mono">${esc(g.id)}</span>
      <button class="link" data-explain="${esc(g.id)}">Why does this exist?</button>
      <button class="link" data-accept="${esc(g.id)}">Accept risk…</button></div>
      <div class="costline">not revoked · record why it stays, with a review date</div>`;
    ul.appendChild(li);
  }
  ul.querySelectorAll("[data-explain]").forEach((b) => (b.onclick = () => openProvenance(b.dataset.explain, b)));
  ul.querySelectorAll("[data-accept]").forEach((b) => (b.onclick = () => openAcceptForm(b.closest("li"), { grant_id: b.dataset.accept })));
}

function renderTickets(ts) {
  $("#tickets").innerHTML = ts.map((t) => `<div class="ticket"><div class="row"><strong>${esc(t.title)}</strong> <button class="link" data-copy>Copy</button></div><pre>${esc(t.body)}</pre></div>`).join("");
  $("#tickets").querySelectorAll("[data-copy]").forEach((b) => (b.onclick = () => navigator.clipboard.writeText(b.closest(".ticket").querySelector("pre").textContent)));
}

function renderProposal(d) {
  const li = [...$("#plan").children].find((x) => x.querySelector(`[data-accept="${d.grant_id}"]`)) || $("#plan").appendChild(document.createElement("li"));
  openAcceptForm(li, d, true);
}

function openAcceptForm(li, d, proposed = false) {
  li.querySelector(".form")?.remove();
  const rb = d.review_by || new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);
  const f = document.createElement("div");
  f.className = "form";
  f.innerHTML = `${proposed ? '<div class="meta" style="color:var(--warn)">▲ Proposed by agent · not saved</div>' : ""}
    <label>Why can't this be revoked?<textarea name="rationale" aria-describedby="err-${d.grant_id}">${esc(d.rationale || "")}</textarea></label>
    <label>Review by${proposed ? " (agent suggested)" : ""}<input type="date" name="review_by" value="${esc(rb)}"></label>
    <div><span class="meta">Sources</span> <div class="srcchips">${(d.cites || []).map((c) => `<button type="button" data-src="${esc(c)}" aria-label="Remove ${esc(c)}">${esc(c)} ×</button>`).join("")}</div>
      <label>Add source<input name="addsrc" placeholder="type a ticket/doc id, e.g. SEC-305"></label></div>
    <div class="err" id="err-${d.grant_id}" role="alert"></div>
    <div><button class="primary" data-confirm>${proposed ? "Confirm acceptance" : "Save"}</button> <button class="link" data-discard>Discard</button></div>`;
  li.appendChild(f);
  f.querySelectorAll("[data-src]").forEach((b) => (b.onclick = () => b.remove()));
  f.querySelector("[data-discard]").onclick = () => f.remove();
  f.querySelector("[data-confirm]").onclick = async () => {
    const cites = [...f.querySelectorAll("[data-src]")].map((b) => b.dataset.src)
      .concat(f.querySelector("[name=addsrc]").value.split(",").map((s) => s.trim()).filter(Boolean));
    try {
      await api("/api/decisions", { method: "POST", body: JSON.stringify({ grant_id: d.grant_id, disposition: "ACCEPT_RISK", rationale: f.querySelector("textarea").value, review_by: f.querySelector("[name=review_by]").value, cites }) });
      f.remove();
      toast(`Accepted risk on ${d.grant_id}. Re-run triage to see the plan route around it.`);
      refreshDecisions();
    } catch (e) { f.querySelector(".err").textContent = e.message; }
  };
}

async function refreshDecisions() {
  const { decisions } = await api("/api/decisions");
  const active = decisions.filter((d) => !["SUPERSEDED", "WITHDRAWN"].includes(d.badge));
  state.accepted = decisions.filter((d) => d.status === "ACTIVE" && d.disposition === "ACCEPT_RISK").map((d) => d.grant_id);
  $("#memory-chip").textContent = `Memory: ${active.length} decision${active.length === 1 ? "" : "s"}`;
  const ul = $("#decisions");
  if (!decisions.length) { ul.innerHTML = `<li class="muted">No decisions yet. Accept a risk on any grant to remember it.</li>`; return; }
  const glyph = { HOLDS: "●", NEEDS_REVIEW: "▲", STALE: "○", SUPERSEDED: "○", WITHDRAWN: "○" };
  const label = (d) => {
    if (d.badge === "NEEDS_REVIEW" && d.reasons.includes("new_jewels")) return `NEEDS REVIEW · now also reaches ${d.new_jewels.join(", ")}`;
    if (d.badge === "NEEDS_REVIEW") return "NEEDS REVIEW · review date passed";
    if (d.badge === "STALE" && d.reasons.includes("grant_removed")) return "STALE · the grant no longer exists";
    if (d.badge === "STALE") return "STALE · cited source removed";
    if (d.badge === "HOLDS" && d.reasons.includes("exposure_shrank")) return "HOLDS · exposure shrank";
    return d.badge;
  };
  ul.innerHTML = decisions.map((d) => `<li><span class="badge b-${d.badge}">${glyph[d.badge] || ""} ${esc(label(d))}</span>
    <div>${esc(d.disposition)} on <span class="mono">${esc(d.grant_id)}</span> · review by ${esc(d.review_by || "—")}</div>
    <div class="meta">${esc(d.rationale)} · ${citeLinks(d.cited_ids)}</div></li>`).join("");
  bindCites();
}

async function openProvenance(gid, opener) {
  state.opener = opener;
  const d = $("#drawer");
  d.hidden = false;
  $("#drawer-title").textContent = `Why does ${gid} exist?`;
  $("#drawer-body").innerHTML = "<p class='muted'>Loading…</p>";
  $("#drawer-title").focus();
  try {
    const r = await api(`/api/explain/${encodeURIComponent(gid)}`);
    const g = r.data.grants[0];
    const pol = g.policy.status === "violation"
      ? `<p class="violation">■ POLICY VIOLATION · ${g.policy.docs.map((x) => esc(`${x.title} ${x.section}`)).join(", ")} allows only ${esc(g.policy.allowed.join(", "))}</p>`
      : g.policy.status === "ok" ? `<p class="meta">Policy: allowed by ${esc(g.policy.docs.join(", "))}</p>` : `<p class="meta">No policy on record</p>`;
    const t = g.ticket;
    $("#drawer-body").innerHTML = `<h3>${esc(g.name)}</h3>${pol}
      <p>${t ? `Ticket <strong>${esc(t.id)}</strong>: ${esc(t.title)}<br>requested by ${esc(t.requester || "—")} · approved by ${esc(t.approver || "—")}` : ""}</p>
      ${t ? `<div class="quote">“${esc(t.untrusted_text)}”<div class="src">ticket · ${esc(t.id)}</div></div>` : ""}
      ${g.gaps.map((x) => `<p class="gap">${esc(x)}</p>`).join("")}
      <p class="meta">Owner: ${esc(g.owner_team || "—")} · granted by ${esc(g.granted_by || "—")} · used ${g.uses_30d}×/30d · last used ${esc(g.last_used || "—")}</p>
      <h3>What the company says about it</h3>
      ${g.mentions.map((m) => `<div class="quote" id="q-${esc(m.source_id)}">“${esc(m.untrusted_text)}”<div class="src">${esc(m.type.toLowerCase())} · ${esc(m.title || m.source_id)} ${esc(m.section || "")} ${m.author ? "· " + esc(m.author) : ""}</div></div>`).join("") || "<p class='muted'>Nothing on record.</p>"}
      <h3>Who knows about it</h3><div id="who-knows" class="meta">…</div>`;
    const wk = await api(`/api/who_knows/${encodeURIComponent(g.holder.id)}`);
    $("#who-knows").innerHTML = (wk.data.people || []).map((p) => `${esc(p.name)} (${p.sources})`).join(" · ") || "No one on record";
  } catch (e) { $("#drawer-body").innerHTML = `<p class="gap">Couldn't load provenance — ${esc(e.message)}</p>`; }
}

function bindCites() {
  document.querySelectorAll("[data-cite]").forEach((c) => {
    c.tabIndex = 0;
    c.setAttribute("role", "link");
    c.onclick = () => openSource(c.dataset.cite, c);
    c.onkeydown = (e) => { if (e.key === "Enter") openSource(c.dataset.cite, c); };
  });
}

async function openSource(id, opener) {
  state.opener = opener;
  $("#drawer").hidden = false;
  $("#drawer-title").textContent = id;
  $("#drawer-body").innerHTML = "<p class='muted'>Loading…</p>";
  $("#drawer-title").focus();
  try {
    const s = await api(`/api/source/${encodeURIComponent(id)}`);
    $("#drawer-title").textContent = s.title ? `${s.title} ${s.section || ""}` : id;
    $("#drawer-body").innerHTML = `<div class="quote">“${esc(s.text)}”<div class="src">${esc((s.type || "").toLowerCase())} · ${esc(s.id)}${s.author ? " · " + esc(s.author) : ""}</div></div>`;
  } catch (e) { $("#drawer-body").innerHTML = `<p class="gap">Source not found: ${esc(e.message)}</p>`; }
}

function closeDrawer() { $("#drawer").hidden = true; state.opener?.focus(); }

function renderEvidence(list) {
  $("#evidence-summary").textContent = `${list.length} queries · ${list.filter((e) => /MAX_FLOW/.test(e.name)).length} algo.maxFlow · ${list.reduce((a, e) => a + e.ms, 0).toFixed(1)} ms`;
  $("#evidence-list").innerHTML = list.map((e) => `<li><strong>${esc(e.label || e.name)}</strong> <span class="meta">${esc(e.name)} · ${e.rows} rows · ${e.ms} ms</span><pre>${esc(e.cypher)}${Object.keys(e.params || {}).length ? "\n// params " + esc(JSON.stringify(e.params)) : ""}</pre></li>`).join("");
}

function drawGraph(display, cutIds, keptIds) {
  if (!display || !window.cytoscape) return;
  if (window.cytoscapeDagre && !state.dagreReg) { cytoscape.use(window.cytoscapeDagre); state.dagreReg = true; }
  const els = [
    ...display.nodes.map((n) => ({ data: { id: n.id, label: n.name, kind: n.finding ? "finding" : n.jewel ? "jewel" : "node" } })),
    ...display.edges.map((e) => {
      const st = cutIds.includes(e.grant) ? "cut" : keptIds.includes(e.grant) ? "kept" : e.grant ? "grant" : "structural";
      const base = e.grant ? `${e.grant} ${e.kind}` : "";
      return { data: { id: e.id, source: e.source, target: e.target, state: st,
        label: st === "cut" ? `✂ ${base}` : st === "kept" ? `kept · ${base}` : base } };
    }),
  ];
  if (state.cy) state.cy.destroy();
  state.cy = cytoscape({
    container: $("#graph"), elements: els,
    layout: { name: window.cytoscapeDagre ? "dagre" : "breadthfirst", rankDir: "LR", rankSep: 110, nodeSep: 50, edgeSep: 20 },
    style: [
      { selector: "node", style: { "background-color": "#15181C", width: 28, height: 28, label: "data(label)", "font-family": "IBM Plex Sans", "font-size": 13, color: "#15181C", "text-valign": "bottom", "text-margin-y": 6 } },
      { selector: "node[kind='jewel']", style: { shape: "rectangle", width: 32, height: 32, "background-color": "#B42318" } },
      { selector: "node[kind='finding']", style: { shape: "diamond", width: 32, height: 32 } },
      { selector: "edge", style: { width: 1.5, "line-color": "#5B636E", "target-arrow-color": "#5B636E", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", "font-size": 11, "font-family": "IBM Plex Mono", color: "#5B636E", "text-rotation": "autorotate", "text-background-color": "#fff", "text-background-opacity": 1 } },
      { selector: "edge[state='structural']", style: { width: 1, "line-color": "#E3E5E8", "target-arrow-color": "#E3E5E8" } },
      { selector: "edge[state='cut']", style: { width: 3, "line-color": "#2443D9", "target-arrow-color": "#2443D9", "line-style": "dashed", "line-dash-pattern": [6, 4], color: "#2443D9" } },
      { selector: "edge[state='kept']", style: { width: 2, "line-color": "#B54708", "target-arrow-color": "#B54708", color: "#B54708" } },
    ],
  });
}

function renderRouteList(display, cutIds) {
  if (!display) return;
  const out = display.edges.filter((e) => e.grant).map((e) => `<li>${esc(e.source)} → ${esc(e.target)} <span class="mono">${esc(e.grant)}</span>${cutIds.includes(e.grant) ? " ✂ cut" : ""}</li>`);
  $("#route-list").innerHTML = out.join("");
}

function toast(t) { $("#toast").textContent = t; }

document.addEventListener("DOMContentLoaded", () => {
  boot().catch((e) => banner(e.message));
  $("#triage").onclick = () => triage();
  $("#ask-btn").onclick = () => { const q = $("#ask").value.trim(); if (q) { triage(q); $("#ask").value = ""; } };
  $("#ask").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#ask-btn").click(); });
  $("#drawer-close").onclick = closeDrawer;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#drawer").hidden) closeDrawer(); if (e.key === "e" && document.activeElement === document.body) $("#evidence").open = !$("#evidence").open; });
  $("#as-list").onclick = () => { const l = $("#route-list"); l.hidden = !l.hidden; };
  $("#new-session").onclick = () => {
    if (state.source) state.source.close();
    state.source = null; state.p0 = null; state.final = null; state.display = null;
    if (state.cy) { state.cy.destroy(); state.cy = null; }
    $("#route-list").innerHTML = "";
    $("#evidence-list").innerHTML = ""; $("#evidence-summary").textContent = "no queries yet";
    $("#triage").disabled = false;
    resetCard();
    $("#hero").textContent = "New session. Memory is loaded from the graph.";
    refreshDecisions();
  };
  $("#reset").onclick = async () => { await api("/api/reset", { method: "POST" }); location.reload(); };
  document.querySelectorAll("[data-event]").forEach((b) => (b.onclick = async () => {
    try { const r = await api(`/api/event/${b.dataset.event}`, { method: "POST" }); toast(`Applied: ${r.title}.` + (r.ingested ? ` Ingested 1 message · ${r.ingested.mentions} mentions (pre-extracted, not live).` : "") + " Re-run triage."); refreshDecisions(); }
    catch (e) { toast(e.message); }
  }));
});
