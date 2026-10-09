/* ============================================================
   GENOMIND — Aplicación principal
   SPA sin dependencias: rutas, estado, agentes y visualización.
   ============================================================ */
"use strict";

/* ------------------------------ Utilidades ------------------------------ */
const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
const state = {
  diseases: [], snpsByDisease: {}, genotypes: {}, selectedDiseases: new Set(["T2D"]),
  foods: [], regions: [], compare: new Set(), sigmaTool: "summary",
  lastPRS: null, lastGX: null,
};

function pct(v, digits = 1) { return (v * 100).toFixed(digits) + "%"; }
function esc(s) {
  return String(s).replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
let toastTimer;
function toast(msg, isError) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.toggle("error", !!isError);
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 4200);
}
function openModal(html) {
  $("#modalContent").innerHTML = html;
  const root = $("#modalRoot");
  root.classList.remove("hidden");
  root.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}
function closeModal() {
  const root = $("#modalRoot");
  root.classList.add("hidden");
  root.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}
document.addEventListener("click", (e) => {
  if (e.target.matches("[data-close-modal]")) closeModal();
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

function parseNumbers(str) {
  return String(str || "").split(/[,;\s]+/).filter(Boolean).map(Number).filter(Number.isFinite);
}
function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

/* ------------------------------ Router ------------------------------ */
const VIEWS = ["home", "genoma", "vida", "alimentos", "estadistica", "atlas", "ciencia"];
function navTo(view) {
  if (!VIEWS.includes(view)) view = "home";
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  $$("#mainNav .tab").forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (location.hash !== `#/${view}`) history.pushState(null, "", `#/${view}`);
}
function routeFromHash() {
  const view = (location.hash.replace("#/", "") || "home").split("?")[0];
  navTo(VIEWS.includes(view) ? view : "home");
}
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-view]");
  if (el && !el.classList.contains("tab")) { e.preventDefault(); navTo(el.dataset.view); }
  const tab = e.target.closest("#mainNav .tab");
  if (tab) { e.preventDefault(); navTo(tab.dataset.view); }
});
window.addEventListener("popstate", routeFromHash);

/* ------------------------- Canvas ADN (hero) ------------------------- */
function startDNA() {
  const canvas = $("#dnaCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let W, H, dpr, t = 0, raf;
  const particles = [];

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 1.6);
    W = canvas.clientWidth; H = canvas.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function initParticles() {
    particles.length = 0;
    const n = Math.min(34, Math.floor(W / 30));
    for (let i = 0; i < n; i++) {
      particles.push({
        x: Math.random() * W, y: Math.random() * H, r: Math.random() * 2 + 0.8,
        vy: (Math.random() * 0.25 + 0.08), a: Math.random() * 0.5 + 0.12,
        hue: Math.random() > 0.5 ? "34,211,238" : "52,211,153",
      });
    }
  }
  function helixFrame(tick) {
    const amp = Math.min(H * 0.16, 120);
    const midY = H * 0.52;
    const speed = 0.011;
    const xStart = -60, xEnd = W + 60;
    const nodesA = [], nodesB = [];
    for (let x = xStart; x <= xEnd; x += 12) {
      const p = (x - xStart) / (xEnd - xStart);
      const phase = p * Math.PI * 6 + tick * speed * 60;
      nodesA.push([x, midY + Math.sin(phase) * amp]);
      nodesB.push([x, midY + Math.sin(phase + Math.PI) * amp]);
    }
    /* peldaños */
    ctx.lineWidth = 1.4;
    for (let i = 0; i < nodesA.length; i += 3) {
      const [ax, ay] = nodesA[i], [bx, by] = nodesB[i];
      const grad = ctx.createLinearGradient(ax, ay, bx, by);
      grad.addColorStop(0, "rgba(34,211,238,.35)");
      grad.addColorStop(1, "rgba(52,211,153,.35)");
      ctx.strokeStyle = grad;
      ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(bx, by); ctx.stroke();
    }
    /* hebras */
    function strand(nodes, color, glow) {
      ctx.beginPath();
      nodes.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
      ctx.strokeStyle = glow;
      ctx.lineWidth = 5; ctx.stroke();
      ctx.strokeStyle = color; ctx.lineWidth = 2.2; ctx.stroke();
    }
    strand(nodesA, "rgba(34,211,238,.8)", "rgba(34,211,238,.12)");
    strand(nodesB, "rgba(52,211,153,.8)", "rgba(52,211,153,.12)");
    /* nucleótidos */
    nodesA.forEach(([x, y], i) => { if (i % 3 === 0) dot(x, y, "rgba(34,211,238,.9)"); });
    nodesB.forEach(([x, y], i) => { if (i % 3 === 0) dot(x, y, "rgba(52,211,153,.9)"); });
    function dot(x, y, c) { ctx.beginPath(); ctx.arc(x, y, 2.6, 0, 7); ctx.fillStyle = c; ctx.fill(); }
    /* partículas */
    particles.forEach((p) => {
      if (!reduced) { p.y -= p.vy; if (p.y < -8) { p.y = H + 8; p.x = Math.random() * W; } }
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 7);
      ctx.fillStyle = `rgba(${p.hue},${p.a})`; ctx.fill();
    });
  }
  function loop() {
    ctx.clearRect(0, 0, W, H);
    helixFrame(t++);
    if (!document.hidden) raf = requestAnimationFrame(loop);
  }
  window.addEventListener("resize", () => { resize(); initParticles(); });
  resize(); initParticles();
  if (reduced) { helixFrame(0); return; }
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !raf) loop();
    else if (document.hidden) { cancelAnimationFrame(raf); raf = null; }
  });
  loop();
}

/* ------------------------------ Inicio ------------------------------ */
async function initHome() {
  try {
    const [health, agents] = await Promise.all([API.health(), API.agents()]);
    $$("[data-stat]").forEach((el) => {
      const k = el.dataset.stat;
      if (health[k] != null) el.textContent = health[k];
    });
    $("#agentsGrid").innerHTML = agents.map((a, i) => {
      const palettes = [
        ["rgba(34,211,238,.14)", "#22d3ee"], ["rgba(167,139,250,.14)", "#a78bfa"],
        ["rgba(52,211,153,.14)", "#34d399"], ["rgba(251,191,36,.14)", "#fbbf24"],
        ["rgba(248,113,113,.14)", "#f87171"],
      ];
      const [bg, fg] = palettes[i % palettes.length];
      return `<div class="agent-card">
        <div class="agent-icon" style="background:${bg};color:${fg}">${a.name.slice(0, 2)}</div>
        <h3>${esc(a.name)}</h3>
        <div class="agent-role">${esc(a.role)}</div>
        <p>${esc(a.specialty)}</p>
        <p class="agent-method">${esc(a.method)}</p>
      </div>`;
    }).join("");
  } catch (e) {
    toast(e.message, true);
  }
}

/* --------------------------- Genoma (GENETIX) --------------------------- */
async function initGenoma() {
  if (!state.diseases.length) {
    state.diseases = await API.diseases();
  }
  renderDiseaseChips();
  await renderGenoEditor();
}

function renderDiseaseChips() {
  const box = $("#diseaseChips");
  box.innerHTML = state.diseases.map((d) =>
    `<button class="chip ${state.selectedDiseases.has(d.code) ? "on" : ""}" data-disease="${d.code}"
      title="${esc(d.description_es)}">${esc(d.name_es)}</button>`).join("");
  $$(".chip", box).forEach((chip) => chip.addEventListener("click", async () => {
    const code = chip.dataset.disease;
    if (state.selectedDiseases.has(code)) state.selectedDiseases.delete(code);
    else state.selectedDiseases.add(code);
    renderDiseaseChips();
    await renderGenoEditor();
  }));
  $("#btnAnalyzePRS").disabled = state.selectedDiseases.size === 0;
}

async function renderGenoEditor() {
  const box = $("#genoEditor");
  if (!state.selectedDiseases.size) {
    box.innerHTML = '<p class="muted" style="padding:16px">Selecciona al menos una enfermedad para editar genotipos.</p>';
    return;
  }
  const codes = [...state.selectedDiseases];
  for (const code of codes) {
    if (!state.snpsByDisease[code]) {
      state.snpsByDisease[code] = await API.diseaseSnps(code);
    }
  }
  const rows = [];
  for (const code of codes) {
    const disease = state.diseases.find((d) => d.code === code);
    rows.push(`<tr><td colspan="5" style="background:rgba(34,211,238,.06);font-weight:600;color:var(--cyan)">${esc(disease.name_es)} — riesgo poblacional de referencia: ${pct(disease.baseline_risk)}</td></tr>`);
    state.snpsByDisease[code].forEach((s) => {
      const gt = state.genotypes[s.rsid] || "";
      rows.push(`<tr>
        <td><span class="gene-name">${esc(s.gene)}</span><br><span class="rsid">${s.rsid}</span></td>
        <td><span class="or-badge">OR ${s.odds_ratio}</span></td>
        <td title="${esc(s.note || "")}">${s.note ? esc(s.note.slice(0, 46)) + (s.note.length > 46 ? "…" : "") : "—"}</td>
        <td>
          <select data-rsid="${s.rsid}" data-risk="${s.risk_allele}" data-other="${s.other_allele}" aria-label="Genotipo de ${s.rsid}">
            <option value="">— sin dato —</option>
            <option value="${s.other_allele}${s.other_allele}" ${gt === s.other_allele + s.other_allele ? "selected" : ""}>${s.other_allele}${s.other_allele} (0 alelos riesgo)</option>
            <option value="${s.risk_allele}${s.other_allele}" ${gt === s.risk_allele + s.other_allele ? "selected" : ""}>${s.risk_allele}${s.other_allele} (1)</option>
            <option value="${s.risk_allele}${s.risk_allele}" ${gt === s.risk_allele + s.risk_allele ? "selected" : ""}>${s.risk_allele}${s.risk_allele} (2)</option>
          </select>
        </td>
        <td style="font-size:.76rem;color:var(--muted)">${s.study || ""}</td>
      </tr>`);
    });
  }
  box.innerHTML = `<table class="table geno-table" style="min-width:700px">
    <thead><tr><th>Variantes</th><th>Efecto</th><th>Nota</th><th>Tu genotipo</th><th>Fuente</th></tr></thead>
    <tbody>${rows.join("")}</tbody></table>`;
  $$("select[data-rsid]", box).forEach((sel) => sel.addEventListener("change", () => {
    if (sel.value) state.genotypes[sel.dataset.rsid] = sel.value;
    else delete state.genotypes[sel.dataset.rsid];
  }));
}

async function randomProfile(enriched) {
  try {
    const payload = { diseases: [...state.selectedDiseases], simulated: true, seed: Math.floor(Math.random() * 99999), enriched };
    const res = await API.batchPRS(payload);
    state.genotypes = res.genotypes_used;
    await renderGenoEditor();
    toast(enriched ? "Perfil de alto riesgo generado." : "Perfil aleatorio generado.");
  } catch (e) { toast(e.message, true); }
}

async function analyzePRS() {
  const btn = $("#btnAnalyzePRS");
  btn.disabled = true; btn.textContent = "Calculando…";
  try {
    const hasManual = Object.keys(state.genotypes).length > 0;
    const res = await API.batchPRS({
      diseases: [...state.selectedDiseases],
      genotypes: hasManual ? state.genotypes : {},
      simulated: !hasManual, seed: 42,
    });
    state.lastPRS = res;
    renderPRS(res);
    if (!hasManual) toast("Sin genotipos manuales: se usó un perfil aleatorio (agéntalo en la tabla).");
  } catch (e) {
    toast(e.message, true);
  } finally {
    btn.disabled = false; btn.textContent = "Analizar panel";
  }
}

function renderPRS(res) {
  const box = $("#prsResults");
  box.innerHTML = res.results.map((r) => {
    const top = r.contributions.slice(0, 4).map((c) =>
      `<div class="top-snp"><span><b>${esc(c.gene)}</b> <span class="rsid">${c.rsid}</span> · ${esc(c.genotype)}</span><span style="color:${c.log_contribution >= 0 ? "var(--red)" : "var(--emerald)"}">${c.log_contribution >= 0 ? "+" : ""}${c.log_contribution.toFixed(3)}</span></div>`).join("");
    return `<div class="result-card">
      <div class="cat">${esc(r.category)}</div>
      <h3>${esc(r.name_es)}</h3>
      <div class="gauge-wrap" data-gauge></div>
      <div class="risk-nums">
        <div class="risk-num"><b style="color:${Charts.riskColor(r.rr)}">×${r.rr}</b><span>riesgo vs media</span></div>
        <div class="risk-num"><b>${Math.round(r.percentile)}</b><span>percentil PRS</span></div>
        <div class="risk-num"><b>${pct(r.abs_risk)}</b><span>riesgo estimado</span></div>
      </div>
      <div style="font-size:.78rem;color:var(--muted);margin-bottom:6px">Referencia: ${pct(r.baseline_risk)} (${r.n_used}/${r.n_total} SNPs usados)</div>
      ${top}
    </div>`;
  }).join("");
  res.results.forEach((r, i) => {
    const el = $(`#prsResults .result-card:nth-child(${i + 1}) [data-gauge]`);
    Charts.gauge({
      el, value: r.abs_risk, max: 0.5, color: Charts.riskColor(r.rr),
      label: pct(r.abs_risk), sublabel: "riesgo estimado",
    });
  });
  const note = $("#prsDisclaimer");
  note.hidden = false;
  note.textContent = res.disclaimer;
  box.insertAdjacentHTML("beforeend",
    `<div class="result-card" style="display:flex;flex-direction:column;justify-content:center;gap:10px;border-color:var(--emerald)">
      <h3 style="color:var(--emerald)">Informe</h3>
      <p class="small muted">Descarga el análisis completo en JSON para tu investigación o compártelo con tu equipo.</p>
      <div class="btn-row">
        <button class="btn btn-ghost btn-sm" onclick="downloadJSON(state.lastPRS, 'genomind_prs_report.json')">Descargar informe</button>
        <button class="btn btn-primary btn-sm" data-view="vida">Llevar a Gen × Ambiente →</button>
      </div>
    </div>`);
}

/* --------------------------- Gen × Ambiente --------------------------- */
async function initVida() {
  if (!state.regions.length) state.regions = await API.regions();
  const sel = $("#regionSelect");
  sel.innerHTML = '<option value="">— Sin región (sin PM2.5) —</option>' +
    state.regions.map((r) => `<option value="${r.id}">${esc(r.name)} (PM2.5 ${r.pm25})</option>`).join("");
  $("#lifestyleForm").addEventListener("submit", (e) => { e.preventDefault(); analyzeGX(); });
}

async function analyzeGX(useSimulated) {
  const form = $("#lifestyleForm");
  const data = Object.fromEntries(new FormData(form).entries());
  const payload = {
    genotypes: Object.keys(state.genotypes).length && !useSimulated ? state.genotypes : {},
    simulated: useSimulated || !Object.keys(state.genotypes).length,
    seed: 42,
    lifestyle: {
      smoking: data.smoking, activity: data.activity, diet: data.diet,
      servings_fv: parseInt(data.servings_fv || "3", 10),
      alcohol: data.alcohol, sleep: data.sleep, stress: data.stress,
      weight_kg: data.weight_kg ? parseFloat(data.weight_kg) : null,
      height_cm: data.height_cm ? parseFloat(data.height_cm) : null,
    },
    region_id: data.region_id || null,
  };
  try {
    const res = await API.geneEnvironment(payload);
    state.lastGX = res;
    state.lastGX._lifestyle = payload.lifestyle;
    renderGX(res);
    if (!$("#gxDiseases").scrollIntoView) return;
  } catch (e) { toast(e.message, true); }
}

function renderGX(res) {
  $("#lifestyleEmpty").classList.add("hidden");
  const box = $("#lifestyleResults");
  box.classList.remove("hidden");

  const labels = Object.keys(res.lifestyle_scores);
  Charts.radar({ el: $("#lifestyleRadar"), labels, values: labels.map((k) => res.lifestyle_scores[k]) });

  const bmi = $("#bmiBadge");
  if (res.bmi) {
    const cls = res.bmi.category === "normal" || res.bmi.category === "bajo" ? "ok" : (res.bmi.category === "sobrepeso" ? "warn" : "bad");
    bmi.className = `bmi-badge ${cls}`;
    bmi.textContent = `IMC ${res.bmi.value} — ${res.bmi.label}`;
  } else {
    bmi.className = "bmi-badge ok hidden";
  }

  const totalReducible = res.diseases.reduce((s, d) => s + d.reducible_points, 0);
  const avgReducible = res.diseases.length ? (res.diseases.reduce((s, d) => s + d.reducible_fraction_pct, 0) / res.diseases.length) : 0;
  $("#gxSummary").innerHTML = `
    <p>Tu perfil de vida deja <span class="big">${Math.round(avgReducible)}%</span> de riesgo evitable en promedio.</p>
    ${res.region ? `<p class="small muted">Región: <b>${esc(res.region.name)}</b> · PM2.5 ${res.region.pm25} µg/m³ · ${res.region.pm25 <= 15 ? "dentro de" : "por encima de"} el rango tolerable OMS</p>` : ""}`;

  $("#gxDiseases").innerHTML = res.diseases.map((d) => {
    const maxBar = Math.max(d.abs_combined, d.abs_optimized, 0.02);
    const recs = (d.recommendations || []).map((r) =>
      `<div class="rec-item ${r.priority === "critica" ? "crit" : ""}">
        <h4>${esc(r.title)}</h4>${esc(r.detail)}<span class="rec-src">Fuente: ${esc(r.evidence)}</span>
      </div>`).join("");
    const inters = (d.interactions || []).map((i) =>
      `<div class="interaction-item"><b>Interacción gen-ambiente:</b> ${esc(i.detail)} <span class="rec-src">${esc(i.source)}</span></div>`).join("");
    const mults = (d.multipliers_used || []).map((m) => `<span class="pill info" title="${esc(m.option)}">${esc(m.factor)}</span>`).join(" ");
    return `<div class="gx-card">
      <div class="cat">${esc(d.category)}</div>
      <h3>${esc(d.name_es)}</h3>
      <div class="gx-bars">
        <div class="gx-bar-row"><span>Hoy: ${pct(d.abs_combined)}</span>
          <div class="gx-bar"><i class="now" style="width:${(d.abs_combined / maxBar) * 100}%"></i></div></div>
        <div class="gx-bar-row"><span>Optimizado:</span>
          <div class="gx-bar"><i class="opt" style="width:${(d.abs_optimized / maxBar) * 100}%"></i></div></div>
      </div>
      <div class="reducible">↓ Reducible: ${pct(d.reducible_points)} puntos (${d.reducible_fraction_pct}% del riesgo actual)</div>
      <div class="chip-row">${mults}</div>
      ${inters}
      ${recs || '<p class="muted small">Sin recomendaciones específicas: tu perfil ya es óptimo para esta enfermedad.</p>'}
    </div>`;
  }).join("") + `<div class="result-card" style="display:flex;flex-direction:column;justify-content:center;gap:10px;border-color:var(--emerald)">
      <h3 style="color:var(--emerald)">Informe completo</h3>
      <div class="btn-row">
        <button class="btn btn-ghost btn-sm" onclick="downloadJSON(state.lastGX, 'genomind_genxambiente.json')">Descargar JSON</button>
        <button class="btn btn-ghost btn-sm" onclick="openSaveProfileModal()">Guardar perfil</button>
        <button class="btn btn-primary btn-sm" data-view="alimentos">Mejorar mi dieta →</button>
      </div>
    </div>`;
  $("#gxDiseases").insertAdjacentHTML("beforeend", `<p class="legal-note">${esc(res.disclaimer)}</p>`);
}

/* --------------------------- Perfiles --------------------------- */
async function openSaveProfileModal() {
  if (!state.lastGX) { toast("Primero ejecuta un análisis Gen × Ambiente.", true); return; }
  openModal(`
    <h3>Guardar perfil</h3>
    <p class="muted small">Se guarda el genotipo, tu estilo de vida y el resultado del análisis en la base local SQLite.</p>
    <label class="field" style="margin-top:12px"><span>Nombre del perfil</span>
      <input id="profileNameInput" placeholder="Ej: Perfil demostrativo — sin datos reales"></label>
    <div class="btn-row" style="margin-top:14px">
      <button class="btn btn-primary" id="btnConfirmSave">Guardar</button>
    </div>`);
  $("#btnConfirmSave").addEventListener("click", async () => {
    const name = $("#profileNameInput").value.trim();
    if (!name) { toast("Escribe un nombre.", true); return; }
    try {
      await API.saveProfile({
        name,
        genotypes: state.lastGX.genotypes_used || {},
        lifestyle: state.lastGX._lifestyle || {},
        results: { diseases: state.lastGX.diseases || [] },
      });
      closeModal();
      toast("Perfil guardado en la base de datos.");
    } catch (e) { toast(e.message, true); }
  });
}

async function openProfilesModal() {
  let profiles = [];
  try { profiles = await API.listProfiles(); } catch (e) { toast(e.message, true); return; }
  const list = profiles.length
    ? profiles.map((p) => `
      <div class="basket-item">
        <span><b>${esc(p.name)}</b><br><span class="cat">${esc(p.created_at)}</span></span>
        <span class="btn-row">
          <button class="btn btn-ghost btn-sm" onclick="loadProfile(${p.id})">Cargar</button>
          <button class="btn btn-danger btn-sm" onclick="removeProfile(${p.id}, this)">Eliminar</button>
        </span>
      </div>`).join("")
    : '<p class="muted">Sin perfiles guardados. Analiza en Gen × Ambiente y pulsa "Guardar perfil".</p>';
  openModal(`<h3>Perfiles guardados</h3>${list}`);
}

async function loadProfile(id) {
  try {
    const p = await API.getProfile(id);
    state.genotypes = p.genotypes || {};
    closeModal();
    await renderGenoEditor();
    toast(`Perfil "${p.name}" cargado en el editor.`);
  } catch (e) { toast(e.message, true); }
}

async function removeProfile(id, btn) {
  try {
    await API.deleteProfile(id);
    btn.closest(".basket-item").remove();
    toast("Perfil eliminado.");
  } catch (e) { toast(e.message, true); }
}

/* --------------------------- Alimentos (NUTRIX) --------------------------- */
const FOOD_CATS = () => [...new Set(state.foods.map((f) => f.category))];
async function initAlimentos() {
  if (!state.foods.length) state.foods = await API.foods();
  const catSel = $("#foodCategory");
  catSel.innerHTML = '<option value="">Todas las categorías</option>' +
    FOOD_CATS().map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  ["foodSearch", "foodCategory", "foodCost"].forEach((id) =>
    $("#" + id).addEventListener("input", renderFoodsTable));
  $("#btnBasket").addEventListener("click", async () => {
    openModal('<h3>Cesta vital</h3><p class="muted">Optimizando nutrientes por costo…</p>');
    const b = await API.basket(parseInt($("#foodCost").value || "0", 10) || null);
    renderBasket(b);
  });
  renderFoodsTable();
}

function renderFoodsTable() {
  const q = $("#foodSearch").value.trim().toLowerCase();
  const cat = $("#foodCategory").value;
  const maxCost = $("#foodCost").value ? parseInt($("#foodCost").value, 10) : null;
  const rows = state.foods.filter((f) =>
    (!q || f.name.toLowerCase().includes(q)) &&
    (!cat || f.category === cat) &&
    (!maxCost || f.cost_index <= maxCost));
  $("#foodsBody").innerHTML = rows.map((f) => {
    const giCls = f.glycemic_index ? (f.glycemic_index <= 55 ? "ok" : f.glycemic_index <= 70 ? "mid" : "bad") : "info";
    const costPill = f.cost_index <= 1 ? "ok" : f.cost_index <= 3 ? "mid" : "bad";
    const gi = f.glycemic_index || "—";
    return `<tr>
      <td><b>${esc(f.name)}</b><br><span class="muted small">${esc(f.region)}</span></td>
      <td class="muted">${esc(f.category)}</td>
      <td class="num">${f.kcal}</td><td class="num">${f.protein_g} g</td>
      <td class="num">${f.fiber_g} g</td>
      <td class="num"><span class="pill ${giCls}">${gi}</span></td>
      <td class="num">${f.sodium_mg} mg</td>
      <td class="num"><span class="pill ${costPill}">{"$".repeat(f.cost_index)}</span></td>
      <td class="num"><div class="score-bar"><i style="width:${f.health_score}%"></i></div> ${f.health_score}</td>
      <td class="chk"><input type="checkbox" data-compare="${f.id}" ${state.compare.has(f.id) ? "checked" : ""} aria-label="Comparar ${esc(f.name)}"></td>
    </tr>`;
  }).join("") || '<tr><td colspan="10" class="muted" style="text-align:center;padding:24px">Sin resultados.</td></tr>';
  $$("[data-compare]", $("#foodsBody")).forEach((chk) => chk.addEventListener("change", () => {
    const id = parseInt(chk.dataset.compare, 10);
    if (chk.checked) {
      if (state.compare.size >= 4) { chk.checked = false; toast("Máximo 4 alimentos para comparar.", true); return; }
      state.compare.add(id);
    } else state.compare.delete(id);
    if (state.compare.size >= 2) compareFoods();
    else $("#comparePanel").classList.add("hidden");
  }));
}

async function compareFoods() {
  const res = await API.compareFoods([...state.compare]);
  const panel = $("#comparePanel");
  panel.classList.remove("hidden");
  const nutrients = [
    ["kcal", "kcal", false], ["protein_g", "Proteína", true], ["fiber_g", "Fibra", true],
    ["glycemic_index", "Índ. glucémico", false], ["sodium_mg", "Sodio", false],
    ["sugar_g", "Azúcar", false], ["potassium_mg", "Potasio", true],
    ["cost_index", "Costo", false], ["water_l", "Agua (L)", false],
  ];
  panel.innerHTML = `
    <h3 class="panel-title">Comparación</h3>
    <div class="compare-grid">${res.foods.map((f) => `
      <div class="compare-item">
        <h4>${esc(f.name)}</h4>
        <div class="pill ${f.health_score >= 70 ? "ok" : f.health_score >= 45 ? "mid" : "bad"}" style="margin-bottom:8px">Salud: ${f.health_score}/100</div>
        <div class="pill ${f.glycemic_class === "bajo" ? "ok" : f.glycemic_class === "medio" ? "mid" : "bad"}" style="margin-bottom:10px">IG: ${f.glycemic_index || "n/a"} (${f.glycemic_class})</div>
        ${nutrients.map(([k, lab, better]) => {
          const max = Math.max(...res.foods.map((x) => x[k] || 0), 0.0001);
          const w = ((f[k] || 0) / max) * 100;
          return `<div class="compare-bar-row"><span>${lab}</span><div class="compare-bar"><i style="width:${w}%;${res.best_per_nutrient[k] === f[k] && better ? "background:linear-gradient(90deg,#34d399,#2dd4bf)" : ""}"></i></div><span style="text-align:right">${f[k] ?? "—"}</span></div>`;
        }).join("")}
      </div>`).join("")}
    <div class="insight-box">${esc(res.insight)}</div>
    <p class="muted small" style="margin-top:10px">Los mejores valores por nutriente se destacan en verde. Costo: 1 = muy barato, 5 = caro. Agua: litros por kg producidos.</p>`;
}

function renderBasket(b) {
  openModal(`
    <h3>Cesta vital — nutrición al costo mínimo</h3>
    <p class="muted small" style="margin-bottom:14px">${esc(b.message)}</p>
    ${b.items.map((i) => `<div class="basket-item"><span><b>${esc(i.name)}</b><br><span class="cat">${esc(i.category)} · ${"jq ".repeat(0)}costo ${i.cost_index}/5</span></span><span class="pill info">${esc((i.note || "").slice(0, 46))}${(i.note || "").length > 46 ? "…" : ""}</span></div>`).join("")}
    <div class="kv-grid" style="margin-top:18px">
      <div class="kv"><b>${b.estimated_daily.protein_g} g</b><span>Proteína (${b.coverage.protein_pct}% del objetivo)</span></div>
      <div class="kv"><b>${b.estimated_daily.fiber_g} g</b><span>Fibra (${b.coverage.fiber_pct}% del objetivo)</span></div>
      <div class="kv"><b>${b.estimated_daily.kcal} kcal</b><span>Energía aproximada</span></div>
      <div class="kv"><b>${b.estimated_daily.water_l} L</b><span>Huella hídrica</span></div>
    </div>
    <p class="muted small" style="margin-top:14px">Objetivos: 50 g de proteína y 25 g de fibra al día (referencia adulto ~70 kg). Elaborada con los alimentos de menor costo del catálogo${$("#foodCost").value ? " (filtro de costo aplicado)" : ""}.</p>`);
}

/* --------------------------- Estadística (SIGMA) --------------------------- */
const SIGMA_TOOLS = {
  summary: {
    title: "Estadística descriptiva",
    fields: [{ name: "values", label: "Valores (separados por coma, espacio o línea)", type: "textarea", placeholder: "23, 25, 31, 22, 28, 30, 24" }],
    build: (f) => ({ values: parseNumbers(f.values) }),
  },
  ttest: {
    title: "t-test (Welch o pareado)",
    fields: [
      { name: "a", label: "Grupo A", type: "textarea", placeholder: "5.1, 4.9, 5.3, 5.0, 5.2" },
      { name: "b", label: "Grupo B", type: "textarea", placeholder: "4.6, 4.4, 4.8, 4.5, 4.7" },
      { name: "paired", label: "Muestras pareadas", type: "checkbox" },
    ],
    build: (f) => ({ a: parseNumbers(f.a), b: parseNumbers(f.b), paired: !!f.paired }),
  },
  mannwhitney: {
    title: "U de Mann-Whitney (no paramétrica)",
    fields: [
      { name: "a", label: "Grupo A", type: "textarea", placeholder: "…" },
      { name: "b", label: "Grupo B", type: "textarea", placeholder: "…" },
    ],
    build: (f) => ({ a: parseNumbers(f.a), b: parseNumbers(f.b) }),
  },
  chisq: {
    title: "Chi-cuadrado de independencia",
    fields: [{
      name: "table", label: "Tabla de contingencia (una fila por línea, columnas separadas por coma)", type: "textarea",
      placeholder: "20, 30\n50, 10",
    }],
    build: (f) => ({
      table: String(f.table).split(/\n+/).filter(Boolean)
        .map((row) => row.split(",").map(Number).filter(Number.isFinite)),
    }),
  },
  or: {
    title: "Odds Ratio (tabla 2×2)",
    fields: [{
      name: "cells", label: "Celdas a b c d (caso-expuesto, control-expuesto, caso-no expuesto, control-no expuesto)",
      type: "text", placeholder: "688, 650, 21, 59",
    }],
    build: (f) => {
      const n = parseNumbers(f.cells);
      if (n.length !== 4) throw new Error("Se requieren exactamente 4 valores: a, b, c, d.");
      return { a: n[0], b: n[1], c: n[2], d: n[3] };
    },
  },
  correlation: {
    title: "Correlación de Pearson o Spearman",
    fields: [
      { name: "x", label: "Variable X", type: "textarea", placeholder: "1, 2, 3, 4, 5" },
      { name: "y", label: "Variable Y", type: "textarea", placeholder: "10.2, 11.1, 12.6, 13.9, 15.3" },
      { name: "method", label: "Método", type: "select", options: [["pearson", "Pearson"], ["spearman", "Spearman"]] },
    ],
    build: (f) => ({ x: parseNumbers(f.x), y: parseNumbers(f.y), method: f.method }),
  },
  anova: {
    title: "ANOVA de una vía",
    fields: [{
      name: "groups", label: "Grupos — formato: Nombre: v1, v2, v3 (un grupo por línea)", type: "textarea",
      placeholder: "Control: 10, 11, 12, 13\nDosis1: 20, 21, 19, 22\nDosis2: 30, 29, 31, 32",
    }],
    build: (f) => {
      const groups = {};
      String(f.groups).split(/\n+/).filter(Boolean).forEach((line) => {
        const [name, vals] = line.split(":");
        if (name && vals) groups[name.trim()] = parseNumbers(vals);
      });
      return { groups };
    },
  },
  power: {
    title: "Tamaño de muestra (dos medias)",
    fields: [
      { name: "effect_d", label: "Tamaño del efecto d de Cohen (0.2 pequeño, 0.5 medio, 0.8 grande)", type: "text", placeholder: "0.5" },
      { name: "alpha", label: "Alfa", type: "text", placeholder: "0.05" },
      { name: "power", label: "Potencia deseada", type: "text", placeholder: "0.8" },
    ],
    build: (f) => ({
      effect_d: parseFloat(f.effect_d), alpha: parseFloat(f.alpha || "0.05"),
      power: parseFloat(f.power || "0.8"),
    }),
  },
  dataset: {
    title: "Análisis automático de CSV",
    fields: [
      { name: "csv_text", label: "Pega tu CSV (primera fila: encabezados)", type: "csv" },
      { name: "group_col", label: "Columna de agrupación (opcional)", type: "text", placeholder: "grupo" },
      { name: "value_col", label: "Columna numérica a contrastar (opcional)", type: "text", placeholder: "peso" },
    ],
    build: (f) => ({ csv_text: f.csv_text, group_col: f.group_col || null, value_col: f.value_col || null }),
  },
};

function renderSigmaForm() {
  const tool = SIGMA_TOOLS[state.sigmaTool];
  $("#sigmaResult").innerHTML = "";
  $$(".sigma-tab").forEach((t) => t.classList.toggle("active", t.dataset.tool === state.sigmaTool));
  const fieldsHtml = tool.fields.map((f) => {
    if (f.type === "textarea" || f.type === "csv") {
      return `<label class="field" style="grid-column:1/-1"><span>${f.label}</span>
        <textarea id="sigmaCsv" name="${f.name}" placeholder="${f.placeholder || ""}" style="min-height:${f.type === "csv" ? 160 : 90}px"></textarea></label>`;
    }
    if (f.type === "select") {
      return `<label class="field"><span>${f.label}</span>
        <select name="${f.name}">${f.options.map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>`;
    }
    if (f.type === "checkbox") {
      return `<label class="field" style="flex-direction:row;align-items:center;gap:10px"><input type="checkbox" name="${f.name}" style="width:auto"> <span>${f.label}</span></label>`;
    }
    return `<label class="field"><span>${f.label}</span><input type="text" name="${f.name}" placeholder="${f.placeholder || ""}"></label>`;
  }).join("");
  $("#sigmaForm").innerHTML = `
    <h3 class="panel-title">${tool.title}</h3>
    <form id="sigmaInnerForm" class="form-grid">${fieldsHtml}
      <div class="field-actions"><button type="submit" class="btn btn-primary">Calcular</button></div>
    </form>`;
  $("#sigmaInnerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());
    try {
      const payload = tool.build(data);
      const res = await API.stats(state.sigmaTool, payload);
      renderSigmaResult(res);
    } catch (err) {
      $("#sigmaResult").innerHTML = `<div class="apa-out" style="color:var(--red);background:var(--red-soft);border-color:rgba(248,113,113,.3)">${esc(err.message)}</div>`;
    }
  });
}

function renderSigmaResult(res) {
  const box = $("#sigmaResult");
  if (res.error) {
    box.innerHTML = `<div class="apa-out" style="color:var(--red);background:var(--red-soft);border-color:rgba(248,113,113,.3)">${esc(res.error)}</div>`;
    return;
  }
  let html = "";
  if (!res.apa && res.mean != null && res.sd != null && res.n) {
    const icTxt = res.ci95_mean ? `, 95% IC [${res.ci95_mean.join(", ")}]` : "";
    res.apa = `M = ${res.mean}, SD = ${res.sd}${icTxt}, N = ${res.n}`;
  }
  if (res.apa) html += `<div class="apa-out">${esc(res.apa)}</div>`;
  if (res.apa_fisher) html += `<div class="apa-out" style="color:var(--violet)">${esc(res.apa_fisher)}</div>`;
  const show = (label, key) => res[key] != null && res[key] !== "" ?
    `<div class="kv"><b>${typeof res[key] === "number" ? res[key] : esc(String(res[key]))}</b><span>${label}</span></div>` : "";
  const generic = ["n", "mean", "sd", "median", "sem", "min", "max", "q1", "q3", "iqr", "skew", "kurtosis",
    "statistic", "p", "dof", "mean_diff", "cohen_d", "odds_ratio", "r", "r_squared",
    "eta_squared", "cramers_v", "effect_d", "alpha", "power",
    "n_per_group_1", "n_per_group_2", "fisher_p", "se", "cv_pct"];
  const labels = {
    n: "n", mean: "Media", sd: "Desv. estándar", median: "Mediana", sem: "Error estándar",
    min: "Mínimo", max: "Máximo", q1: "Q1", q3: "Q3", iqr: "IQR", skew: "Asimetría",
    kurtosis: "Curtosis", statistic: "Estadístico", p: "Valor p", dof: "gl",
    mean_diff: "Diferencia de medias", cohen_d: "d de Cohen", odds_ratio: "Odds Ratio",
    r: "r", r_squared: "R²", eta_squared: "η²", cramers_v: "V de Cramér",
    effect_d: "d de Cohen", alpha: "Alfa", power: "Potencia", n_per_group_1: "n por grupo 1",
    n_per_group_2: "n por grupo 2", fisher_p: "p exacta (Fisher)", se: "Error estándar", cv_pct: "CV %",
  };
  html += '<div class="kv-grid">' + generic.filter((k) => res[k] != null).map((k) => show(labels[k] || k, k)).join("") + "</div>";
  if (res.ci95) html += `<div class="kv-grid"><div class="kv"><b>[${res.ci95.map((x) => typeof x === "number" ? x.toFixed(3) : x).join(", ")}]</b><span>IC 95%</span></div></div>`;
  if (res.ci95_string) html += `<div class="apa-out" style="font-size:.9rem">OR = ${esc(res.ci95_string)}</div>`;
  if (res.summary && res.summary.ci95_mean) {
    html += `<div class="kv-grid"><div class="kv"><b>[${res.summary.ci95_mean.join(", ")}]</b><span>IC 95% de la media</span></div></div>`;
  }
  if (res.explanation) html += `<p class="muted small" style="margin-top:14px">${esc(res.explanation)}</p>`;
  if (res.warning_low_expected) html += `<p class="small" style="color:var(--amber);margin-top:12px">⚠ Frecuencias esperadas < 5: se aplicó la prueba exacta de Fisher.</p>`;
  if (res.group_test) {
    const gt = res.group_test;
    html += "<h3 class='panel-title' style='margin-top:18px'>Contraste entre grupos</h3>";
    if (gt.ttest) { html += `<div class="apa-out">${esc(gt.ttest.apa)}</div>`; html += `<div class="apa-out" style="color:var(--violet)">${esc(gt.mannwhitney.apa)}</div>`; }
    if (gt.anova) html += `<div class="apa-out">${esc(gt.anova.apa)}</div>`;
  }
  if (res.summaries) {
    html += "<h3 class='panel-title' style='margin-top:18px'>Resumen por columna</h3><div class='kv-grid'>";
    for (const [name, s] of Object.entries(res.summaries)) {
      html += `<div class="kv"><b>${esc(name)}: ${s.mean ?? "—"}</b><span>media ± ${s.sd ?? "?"} (n=${s.n})</span></div>`;
    }
    html += "</div>";
  }
  if (res.correlations && Object.keys(res.correlations).length) {
    html += "<h3 class='panel-title' style='margin-top:18px'>Correlaciones detectadas</h3><div class='kv-grid'>";
    for (const [pair, c] of Object.entries(res.correlations)) {
      html += `<div class="kv"><b>r = ${c.r}</b><span>${esc(pair)} (${esc(c.apa)})</span></div>`;
    }
    html += "</div>";
  }
  box.innerHTML = html;
}

function initSigma() {
  $$(".sigma-tab").forEach((tab) => tab.addEventListener("click", () => {
    state.sigmaTool = tab.dataset.tool;
    renderSigmaForm();
  }));
  renderSigmaForm();
}

/* --------------------------- Atlas (TERRA) --------------------------- */
async function initAtlas() {
  if (!state.regions.length) state.regions = await API.regions();
  const byPm = [...state.regions].sort((a, b) => b.pm25 - a.pm25);

  Charts.scatter({
    el: $("#atlasScatter"),
    points: state.regions.map((r) => ({ x: r.pm25, y: r.life_expectancy, label: r.name, pm25: r.pm25 })),
    xLabel: "PM2.5 anual (µg/m³) — guía OMS: 5", yLabel: "Esperanza de vida (años)",
  });

  const sel = $("#atlasRegionSelect");
  sel.innerHTML = state.regions.map((r) => `<option value="${r.id}">${esc(r.name)} — ${esc(r.country)}</option>`).join("");
  function detail() {
    const r = state.regions.find((x) => x.id === sel.value);
    if (!r) return;
    const cls = (v, warn) => (v <= warn ? "ok" : v <= warn * 2 ? "mid" : "bad");
    $("#atlasDetail").innerHTML = `
      <div class="atlas-detail-grid">
        <div class="kv"><b>${r.pm25} µg/m³</b><span>PM2.5 anual <span class="pill ${cls(r.pm25, 15)}">${(r.pm25 / 5).toFixed(1)}x guía OMS</span></span></div>
        <div class="kv"><b>${r.green_pct}%</b><span>Espacios verdes</span></div>
        <div class="kv"><b>${r.walkability}/100</b><span>Caminabilidad</span></div>
        <div class="kv"><b>${r.healthcare_index}/100</b><span>Acceso a salud</span></div>
        <div class="kv"><b>${r.life_expectancy} años</b><span>Esperanza de vida</span></div>
        <div class="kv"><b>${r.ncd_per100k}</b><span>Muertes ENT /100k/año</span></div>
      </div>
      <p class="region-note">${esc(r.note)}</p>`;
  }
  sel.addEventListener("change", detail);
  detail();

  $("#atlasBody").innerHTML = byPm.map((r) => {
    const pm = r.pm25 <= 15 ? "ok" : r.pm25 <= 35 ? "mid" : "bad";
    return `<tr>
      <td><b>${esc(r.name)}</b></td><td class="muted">${esc(r.country)}</td>
      <td class="num"><span class="pill ${pm}">${r.pm25}</span></td>
      <td class="num">${r.green_pct}%</td><td class="num">${r.walkability}</td>
      <td class="num">${r.healthcare_index}</td><td class="num">${r.life_expectancy}</td>
      <td class="num">${r.ncd_per100k}</td></tr>`;
  }).join("");
}

/* --------------------------- Arranque --------------------------- */
document.addEventListener("DOMContentLoaded", async () => {
  routeFromHash();
  startDNA();
  initSigma();
  initHome();
  initGenoma();
  initVida();
  initAlimentos().catch((e) => toast(e.message, true));
  initAtlas().catch((e) => toast(e.message, true));

  $("#btnRandomProfile").addEventListener("click", () => randomProfile(false));
  $("#btnEnrichedProfile").addEventListener("click", () => randomProfile(true));
  $("#btnClearGenotypes").addEventListener("click", async () => {
    state.genotypes = {};
    await renderGenoEditor();
    toast("Genotipos limpiados.");
  });
  $("#btnAnalyzePRS").addEventListener("click", analyzePRS);
  $("#btnSimGxESim").addEventListener("click", () => analyzeGX(true));
  $("#btnLoadProfile").addEventListener("click", openProfilesModal);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
});
