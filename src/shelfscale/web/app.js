/* ShelfScale page. Plain JavaScript, no build step.
   Every score shown comes from the service; nothing here scores a food.
   Arithmetic here is display only (scaling a value to a chosen portion,
   rounding for reading) and never feeds a score. */
"use strict";

const STORE = "shelfscale.recipe.v1";
const MATCHES = "shelfscale.matches.v1";
const UNITS = "shelfscale.units.v1";
const RANGE = "shelfscale.range.v1";
const view = () => document.getElementById("view");

/* ---------- small helpers ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

function fmt(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
  const v = Number(value);
  let d;
  if (unit === "kJ" || unit === "kcal" || unit === "mg" || unit === "%") d = 0;
  else if (Math.abs(v) >= 100) d = 0;
  else if (Math.abs(v) >= 10) d = 1;
  else d = 2;
  return v.toLocaleString("en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });
}
const grams = (g) => `${fmt(g, Math.abs(g) >= 10 ? "kJ" : "g")} g`;

async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (_) { /* fall through */ }
  if (!res.ok) {
    const wait = res.headers.get("Retry-After");
    const msg = (data && data.error) || `The service answered ${res.status}.`;
    throw new Error(wait ? `${msg} Try again in ${wait} s.` : msg);
  }
  return data;
}

/* ---------- storage: this browser only ---------- */
function read(key, fallback) {
  try { const v = JSON.parse(localStorage.getItem(key) || "null"); return v ?? fallback; } catch (_) { return fallback; }
}
function write(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* private mode */ } }

let recipe = read(STORE, null);
if (!recipe || !Array.isArray(recipe.ingredients)) recipe = { name: "", servings: 1, ingredients: [], fvn_percent: null, free_sugars_g: null };
function saveRecipe() {
  write(STORE, recipe);
  const n = recipe.ingredients.length;
  const badge = document.getElementById("tab-count");
  if (badge) badge.textContent = n ? String(n) : "";
}
const matches = () => read(MATCHES, []);
function keepMatch(record) {
  const all = matches().filter((m) => m.query.toLowerCase() !== record.query.toLowerCase());
  all.push(record);
  write(MATCHES, all);
}
const unitKeys = (foodId) => (read(UNITS, {})[foodId] || []);
function keepUnit(foodId, key) {
  const all = read(UNITS, {});
  all[foodId] = Array.from(new Set([...(all[foodId] || []), key]));
  write(UNITS, all);
}

/* ---------- provenance sheet ---------- */
let sources = [];
const srcButton = (card, text) => {
  if (!card) return "";
  sources.push(card);
  return `<button class="src" type="button" data-src="${sources.length - 1}">${esc(text || card.label)}</button>`;
};
function openSheet(html) {
  document.getElementById("sheet-body").innerHTML = html;
  const sheet = document.getElementById("sheet");
  sheet.hidden = false;
  sheet.querySelector(".sheet-close").focus();
}
function closeSheet() { document.getElementById("sheet").hidden = true; }
function sourceHtml(card) {
  if (card.html) return card.html;
  const rows = [
    ["Dataset", card.dataset], ["Edition", card.edition], ["Publisher", card.publisher],
    ["Period", card.period], ["Where in the source", card.locator], ["Rights", card.rights],
    ["Citation", card.citation], ["Record", card.observation_id], ["Replaces", card.supersedes],
    ["Detail", card.detail], ["Note", card.note],
  ].filter(([, v]) => v);
  const link = card.url ? `<p><a href="${esc(card.url)}" rel="noopener" target="_blank">Open the source</a></p>` : "";
  return `<h2 id="sheet-title">${esc(card.label)}</h2><dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>${link}`;
}

/* ---------- laws and the two-law ticket ---------- */
const INPUT_WORDS = { fruit_veg_nuts_percent: "fruit, veg and nuts %", fvn_percent: "fruit, veg and nuts %", free_sugars_g: "free sugars",
  fvns_g: "fruit, veg, nuts and seeds", fibre: "fibre", fibre_aoac_g: "AOAC fibre", energy_kj: "energy",
  saturated_fat_g: "saturates", total_sugars_g: "sugars", sodium_mg: "sodium", protein_g: "protein", salt_g: "salt" };
const needWord = (m) => { const k = m.split(" (")[0].split(":")[0].trim(); return INPUT_WORDS[k] || k.replace(/_/g, " "); };
const ROLE_TITLE = { today: "Today's law", coming: "When the law changes", past: "Past law" };
const lawName = (law) => `${law.name.replace("UK Nutrient Profiling Model", "NPM")} ${law.version}`;
const lawStatus = (law) => `${lawName(law)}, ${law.status_text}`;

function ordered(models) {
  const rank = { today: 0, coming: 1, past: 2 };
  return Object.values(models).filter((m) => m && m.law).sort((a, b) => rank[a.law.role] - rank[b.law.role]);
}

function half(model, cls) {
  const law = model.law;
  const head = `<div class="law"><strong>${esc(ROLE_TITLE[law.role] || law.role)}</strong>${esc(lawStatus(law))}</div>`;
  if (model.scorable) {
    const less = model.less_healthy;
    return `<div class="half ${cls}">${head}
      <div class="score" aria-label="Score ${model.score}">${model.score}</div>
      <div class="verdict"><span class="mark" aria-hidden="true">${less ? "&#9632;" : "&#9633;"}</span> ${less ? "Less healthy" : "Not less healthy"}</div>
      ${model.total_a !== undefined ? `<div class="points">${model.total_a} A points, ${model.total_c} C points${model.protein_counted === false ? ". Protein not counted" : ""}</div>` : ""}
    </div>`;
  }
  let why = "";
  if (model.applicable === false) why = model.reason;
  else if (model.missing_inputs) why = "Needs " + model.missing_inputs.map(needWord).join(", ") + ".";
  return `<div class="half ${cls} unscored">${head}<div class="score">No score yet</div><p class="why">${esc(why)}</p></div>`;
}

function ticket(assessment, { hero = false } = {}) {
  const [first, second] = ordered(assessment.models);
  const flips = assessment.verdict_changes_under_2018 === true;
  let key;
  if (flips) key = "The ticket tears: this product's verdict changes when the law changes.";
  else if (assessment.verdict_changes_under_2018 === false) key = "The ticket holds: the same verdict under both laws.";
  else key = "One law cannot score this yet, so a change of verdict cannot be checked.";
  return `<div class="dual-wrap${hero ? " hero" : ""}">
    ${flips ? '<div class="stamp" aria-hidden="true">Verdict flips</div>' : ""}
    <div class="dual${flips ? " flips" : ""}" role="group" aria-label="Scores under two laws">
      ${half(first, "law-now")}${half(second, "law-2018")}
    </div>
    <p class="flip-key">${esc(key)}</p>
  </div>`;
}

function quote(assessment, release) {
  const parts = ordered(assessment.models).map((m) => m.scorable
    ? `score ${m.score}, ${m.less_healthy ? "less healthy" : "not less healthy"}, under ${lawStatus(m.law)}`
    : `no score under ${lawStatus(m.law)}`);
  return `<p class="quote"><span class="muted">Quote as:</span> ${esc(parts.join("; "))}. Data release ${esc(release)}.</p>`;
}

function yours(c) {
  const parts = [];
  if (c && c.fvn_percent !== undefined) parts.push(`fruit, veg and nuts ${fmt(c.fvn_percent, "g")}%`);
  if (c && c.free_sugars_g !== undefined) parts.push(`free sugars ${fmt(c.free_sugars_g, "g")} g per 100 g`);
  return parts.length ? `<p class="flip-key">Scored with figures you entered: ${esc(parts.join(", "))}. ShelfScale has not checked them.</p>` : "";
}

const LEVEL = { green: "Low", amber: "Medium", red: "High" };
function lights(tl, label) {
  if (!tl || !tl.colours) return tl && tl.not_assessed ? `<p class="note">${esc(tl.not_assessed)}</p>` : "";
  const order = [["fat", "Fat"], ["saturates", "Saturates"], ["sugars", "Sugars"], ["salt", "Salt"]];
  return `<div class="lights" role="list" aria-label="${esc(label)}">${order.map(([k, name]) => {
    const c = tl.colours[k];
    if (!c) return `<div class="light" role="listitem"><b>${name}</b><span class="lvl">No value</span></div>`;
    const by = c.decided_by === "per_portion" ? "<br>red by the per-portion rule" : "";
    return `<div class="light ${esc(c.colour)}" role="listitem"><b>${name}</b><span class="lvl">${LEVEL[c.colour] || esc(c.colour)}</span>
      <span class="amt">${fmt(c.per_100g, "g")} g per 100 g${by}</span></div>`;
  }).join("")}</div>`;
}

/* ---------- as sold: the unit and its band ---------- */
function bandHtml(sold) {
  const u = sold.unit;
  if (!u) return "";
  const b = sold.band;
  const ranged = u.low_g !== u.high_g;
  let table = "";
  if (b && b.available) {
    const ends = [["low", "Light end"], ["typical", "Typical"], ["high", "Heavy end"]].filter(([k]) => b.ends[k] && (ranged || k === "typical"));
    const rows = [["energy_kj", "Energy", "kJ"], ["fat", "Fat", "g"], ["saturates", "Saturates", "g"], ["sugars", "Sugars", "g"], ["salt", "Salt", "g"]];
    table = `<table class="figures band"><thead><tr><th>Per unit</th>${ends.map(([k, l]) => `<th>${l}<br><span class="u">${grams(b.ends[k].grams)}</span></th>`).join("")}</tr></thead><tbody>
      ${rows.map(([k, label, unit]) => `<tr><th scope="row">${label}</th>${ends.map(([e]) => {
        const amount = b.ends[e].amounts[k];
        const colour = b.ends[e].colours[k];
        const crosses = b.crosses.includes(k);
        return `<td class="n${crosses ? " cross" : ""}">${amount === null ? "" : fmt(amount, unit)}<span class="u">${unit}</span>${colour ? `<span class="tag ${colour}">${LEVEL[colour]}</span>` : ""}</td>`;
      }).join("")}</tr>`).join("")}
    </tbody></table>
    ${b.crosses.length ? `<div class="flag"><strong>The band crosses a line</strong>${esc(b.crosses.join(", "))} changes colour across this weight range, because a unit over 100 g is also checked against the per-portion red limits. Both ends are shown; the per-100 g verdict does not move.</div>` : `<p class="note">The colours hold across the whole range. ${esc(b.rule)}</p>`}`;
  }
  return `<div class="unit">
    <p class="unit-line"><span class="unit-big">${ranged ? `${grams(u.low_g)} to ${grams(u.high_g)}` : grams(u.typical_g)}</span>
    <span class="unit-what">One ${esc(u.label)}${ranged ? `, typical ${grams(u.typical_g)}` : ""}</span></p>
    <p class="note">${esc(u.basis)}. ${esc(u.spread)} ${u.source ? srcButton(u.source, u.source.label) : ""}${u.link === "user_confirmed" ? " You confirmed this is the same food." : ""}</p>
    ${table}
  </div>`;
}

function soldHtml(food) {
  const sold = food.as_sold;
  const sale = sold.sale;
  let lead;
  if (sold.kind === "loose") lead = `Sold loose${sale && sale.sale_format ? ` (${esc(sale.sale_format)})` : ""}. No pack, no declared weight and no label to copy, so the unit below comes from weighed evidence.`;
  else if (sold.kind === "packaged") lead = "Packaged. Scored as the unit on the shelf, at the weight you declared.";
  else if (sale) lead = `Sold as: ${esc(sale.sale_format || "not recorded")}.`;
  else lead = "How this food is sold is not on record.";
  const proposals = (sold.proposed_units || []).map((u) => `<li class="ticket proposal"><span><strong>${esc(u.label)}</strong>: ${grams(u.low_g)} to ${grams(u.high_g)} from ${u.n} purchase${u.n > 1 ? "s" : ""}, ${esc(u.source.label)}. ${srcButton(u.source, "Source")}</span>
      <button class="btn ticket" type="button" data-unit="${esc(u.key)}">Confirm it is this food</button></li>`).join("");
  return `<section class="panel ticket sold" aria-labelledby="sold-h">
    <h2 id="sold-h">As sold</h2>
    <p>${lead} ${sale ? srcButton(sale.source, "Sale format source") : ""}</p>
    ${bandHtml(sold)}
    ${sold.note ? `<p class="note">${esc(sold.note)}</p>` : ""}
    ${proposals ? `<h3>Possible unit evidence</h3><p class="small">The sampling reports name this food differently. A person has not yet confirmed the link, so it is not used until you do.</p><ul class="proposals">${proposals}</ul>` : ""}
    <div class="inline-form">
      <div class="field"><label for="packg">Packaged? Declared pack weight (g)</label><input class="input num" id="packg" type="number" inputmode="decimal" min="0.1" step="any" value="${esc(foodState.pack)}"></div>
      <button class="btn btn-ghost" type="button" data-act="set-pack">Use pack weight</button>
    </div>
  </section>`;
}

/* ---------- search ---------- */
let searchCtl = null;
async function runSearch(q, target, mode) {
  if (searchCtl) searchCtl.abort();
  searchCtl = new AbortController();
  const box = document.getElementById(target);
  if (!box) return;
  if (q.trim().length < 2) { box.innerHTML = ""; return; }
  try {
    const res = await fetch(`/ui/search?q=${encodeURIComponent(q)}`, { signal: searchCtl.signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Search did not work. Try again.");
    const items = data.results.map((r) => {
      const meta = [`CoFID ${r.code}`, r.overlay ? "official overlay values" : "", r.portions ? `${r.portions} unit weight${r.portions > 1 ? "s" : ""}` : ""].filter(Boolean).join(", ");
      if (mode === "add") {
        return `<li class="result ticket"><span class="name">${esc(r.name)}</span><span class="meta">${esc(meta)}</span>
          <button class="btn ticket act" type="button" data-add="${esc(r.food_id)}" data-name="${esc(r.name)}">Add</button></li>`;
      }
      const base = mode === "score" ? "#/score/" : "#/food/";
      return `<li><a class="result ticket" href="${base}${encodeURIComponent(r.food_id)}"><span class="name">${esc(r.name)}</span><span class="meta">${esc(meta)}</span></a></li>`;
    }).join("");
    const empty = !data.results.length && data.note ? `<p class="note">${esc(data.note)} For a product with its own label, score it from your own figures on <a href="#/range">Score your range</a>.</p>` : "";
    box.innerHTML = (items ? `<ul class="results">${items}</ul>` : "") + (data.results.length && data.note ? `<p class="note">${esc(data.note)}</p>` : "") + empty;
  } catch (e) {
    if (e.name !== "AbortError") box.innerHTML = `<p class="note">${esc(e.message)}</p>`;
  }
}
function wireSearch(id, target, mode) {
  const input = document.getElementById(id);
  const go = debounce(() => runSearch(input.value, target, mode), 200);
  ["input", "search", "change"].forEach((evt) => input.addEventListener(evt, go));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); runSearch(input.value, target, mode); } });
}

/* ---------- Home: the data first ---------- */
/* Drafted for Elliot's review (data-first round, 2026-11-06); not settled copy. */
const HERO = "The foods sold in the UK, as they are sold: what they weigh, what is in them, and where every number came from.";
const HERO_LEDE = "ShelfScale Open is a public data release built on the UK's official food tables. Browse it here, download every file without an account, and use it to score a product under today's law and the law that is coming.";
const COUNT_KEYS = ["foods", "foods_with_as_sold_unit", "sources_in_register"];
const whole = (n) => Number(n).toLocaleString("en-GB");

function countsHtml(release) {
  /* Every number here is the release block of GET /api, unchanged. */
  const values = { foods: release.foods, foods_with_as_sold_unit: release.foods_with_as_sold_unit,
    sources_in_register: release.sources_in_register };
  return `<dl class="counts">${COUNT_KEYS.map((k) => `<div class="count-cell">
      <dt>${esc(release.labels[k])}</dt><dd><span class="count-big">${whole(values[k])}</span>
      <span class="count-rel">Data release ${esc(release.data_release)}</span></dd></div>`).join("")}</dl>`;
}

function filesBrief(manifest) {
  return `<ul class="file-brief">${manifest.files.map((f) => `<li><a href="/download/${encodeURIComponent(f.name)}" download>${esc(f.name)}</a>
    <span class="muted small">${whole(f.rows)} rows</span></li>`).join("")}
    <li><a href="/download/release_manifest.json" download>release_manifest.json</a> <span class="muted small">counts, checksums, attribution</span></li></ul>`;
}

function citationHtml(manifest, id) {
  return `<div class="cite"><p class="small muted">Cite this release as:</p>
    <p class="cite-text" id="${id}">${esc(manifest.citation)}</p>
    <button class="btn btn-ghost" type="button" data-copy="${id}">Copy the citation</button> <span class="note" id="${id}-status" role="status"></span></div>`;
}

async function renderHome() {
  sources = [];
  view().innerHTML = `<section class="scene home">
    <div class="backtype" aria-hidden="true">ABCDF<br>GHJMO<br>PQSW</div>
    <div class="home-head">
      <p class="kicker">ShelfScale Open data</p>
      <h1 class="headline home-title">${esc(HERO)}</h1>
    </div>
    <section class="groups-hero ticket" aria-labelledby="groups-h">
      <p class="lede">${esc(HERO_LEDE)}</p>
      <div id="counts"><p class="note">Loading the release counts.</p></div>
      <h2 id="groups-h" class="groups-title">Browse the foods by group</h2>
      <ol class="groups" id="groups"><li class="note">Loading the food groups.</li></ol>
      <div class="searchbox field">
        <label for="q">Or find a food by name or CoFID code</label>
        <input class="input" id="q" type="search" autocomplete="off" placeholder="For example: raisins, butter, onions" enterkeyhint="search">
      </div>
      <div id="found"></div>
    </section>
    <div class="home-panels">
      <section class="panel ticket" aria-labelledby="dl-h">
        <p class="eyebrow">Download the data</p>
        <h2 id="dl-h">The whole release as CSV</h2>
        <p class="small">No account and no key. Generated from the same data the service uses.</p>
        <div id="dlbrief"><p class="note">Loading the release files.</p></div>
        <p><a class="btn ticket" href="#/download">All files and how to cite them</a></p>
      </section>
      <section class="panel ticket can-do" aria-labelledby="can-h">
        <p class="eyebrow">One thing the data can do</p>
        <h2 id="can-h">Score a product under today's law and the law that is coming</h2>
        <div id="example"><p class="note">Loading a worked example from the service.</p></div>
        <p><a class="btn ticket" href="#/score">Score a product</a></p>
      </section>
    </div>
  </section>`;
  wireSearch("q", "found", "view");
  const [summary, groupList, manifest, food] = await Promise.allSettled([
    api("/api"), api("/ui/groups"), api("/download/release_manifest.json"), api("/ui/food/14-393?free_sugars_g=0")]);
  const put = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
  if (summary.status === "fulfilled") put("counts", countsHtml(summary.value.release));
  else put("counts", `<p class="note">The counts did not load: ${esc(summary.reason.message)}</p>`);
  if (groupList.status === "fulfilled") {
    put("groups", groupList.value.groups.map((g) => `<li><a class="group-link" href="#/browse/${encodeURIComponent(g.code)}">
      <span class="group-name">${esc(g.name)}</span><span class="group-n">${whole(g.foods)} foods</span></a></li>`).join(""));
  } else put("groups", `<li class="note">The food groups did not load: ${esc(groupList.reason.message)}</li>`);
  if (manifest.status === "fulfilled") {
    put("dlbrief", `<p class="small">Release <strong>${esc(manifest.value.data_release)}</strong></p>${filesBrief(manifest.value)}${citationHtml(manifest.value, "cite-home")}`);
  } else put("dlbrief", `<p class="note">The release files did not load: ${esc(manifest.reason.message)}</p>`);
  if (food.status === "fulfilled") {
    const f = food.value;
    sources = [];
    put("example", `<p class="example-label">Worked example, live from the service: <a href="#/score/14-393">${esc(f.name)}</a></p>
      ${ticket(f.assessment)}
      <p class="small example-note">Free sugars are entered as 0 g, as for whole dried fruit with nothing added. That one figure is entered, and labelled as entered; CoFID records total sugars only. Every other number is CoFID 2021, ${srcButton(f.panel[0].source, "with its source")}.</p>`);
    revealTear();
  } else put("example", `<p class="note">The worked example did not load: ${esc(food.reason.message)}</p>`);
}

/* ---------- Browse: one food group ---------- */
async function renderGroup(code) {
  sources = [];
  view().innerHTML = `<section class="scene"><p class="note">Loading the group.</p></section>`;
  let g;
  try { g = await api(`/ui/group/${encodeURIComponent(code)}`); } catch (e) {
    view().innerHTML = `<section class="scene"><h1 class="headline">This group did not load</h1><p>${esc(e.message)}</p><p><a class="btn ticket" href="#/">Back to the data</a></p></section>`;
    return;
  }
  view().innerHTML = `<section class="scene browse">
    <div class="backtype" aria-hidden="true">${esc(g.name)}</div>
    <p class="kicker"><a href="#/">All groups</a></p>
    <h1 class="headline">${esc(g.name)}</h1>
    <p class="lede">${whole(g.foods)} foods in CoFID 2021, in ${g.subgroups.length} group${g.subgroups.length === 1 ? "" : "s"}. Data release ${esc(g.data_release)}. Each food opens with what it weighs as sold, what is in it and where each value came from.</p>
    <nav class="sub-jump" aria-label="Groups in ${esc(g.name)}">${g.subgroups.map((s) => `<a href="#/browse/${encodeURIComponent(code)}" data-jump="sg-${esc(s.code)}">${esc(s.name)} <span class="muted">${s.foods.length}</span></a>`).join("")}</nav>
    ${g.subgroups.map((s) => `<section class="panel ticket subgroup" id="sg-${esc(s.code)}" aria-labelledby="sgh-${esc(s.code)}">
      <h2 id="sgh-${esc(s.code)}">${esc(s.name)} <span class="muted small">CoFID group ${esc(s.code)}, ${s.foods.length} food${s.foods.length === 1 ? "" : "s"}</span></h2>
      <ul class="food-list">${s.foods.map((f) => `<li><a href="#/food/${encodeURIComponent(f.food_id)}">${esc(f.name)}</a>${f.portions ? `<span class="muted small"> ${f.portions} unit weight${f.portions > 1 ? "s" : ""}</span>` : ""}</li>`).join("")}</ul>
    </section>`).join("")}
  </section>`;
}

/* ---------- Score a product ---------- */
function renderScoreStart() {
  sources = [];
  view().innerHTML = `<section class="scene score-start">
    <div class="backtype" aria-hidden="true">Score</div>
    <h1 class="headline">Score a product</h1>
    <p class="lede">Pick a food from the data and see its score under the law in force today and under the 2018 model that may replace it, with the source of every number behind both.</p>
    <div class="paths">
      <div class="path ticket">
        <h2>From ShelfScale reference data</h2>
        <div class="searchbox field">
          <label for="sq">Find the food by name or CoFID code</label>
          <input class="input" id="sq" type="search" autocomplete="off" placeholder="For example: raisins, butter, onions" enterkeyhint="search">
        </div>
        <div id="sfound"></div>
      </div>
      <a class="path ticket go" href="#/range"><h2>From your own figures</h2><p>Your product has its own label? Score it, or a whole range, from your per 100 g figures.</p><span class="btn ticket">Score your range</span></a>
      <a class="path ticket go" href="#/recipe"><h2>From a recipe</h2><p>Add what goes in by weight. Get both scores and a UK nutrition declaration to print.</p><span class="btn ticket">Start a recipe</span></a>
    </div>
  </section>`;
  wireSearch("sq", "sfound", "score");
}

/* ---------- Download the data ---------- */
const kb = (bytes) => (bytes >= 1048576 ? `${fmt(bytes / 1048576, "g")} MB` : `${whole(Math.ceil(bytes / 1024))} KB`);

async function renderDownloads() {
  sources = [];
  view().innerHTML = `<section class="scene downloads"><div class="backtype" aria-hidden="true">CSV</div>
    <h1 class="headline">Download the data</h1><div id="dl"><p class="note">Loading the release.</p></div></section>`;
  let m;
  try { m = await api("/download/release_manifest.json"); } catch (e) {
    document.getElementById("dl").innerHTML = `<p class="note">The release did not load: ${esc(e.message)}</p>`;
    return;
  }
  const decisions = m.match_decision_categories;
  document.getElementById("dl").innerHTML = `
    <p class="lede">The whole release as CSV files. No account and no key. Every file is generated from the same data the service and its API use, so a number you download is the number the page shows.</p>
    <section class="panel ticket release-id">
      <p class="eyebrow">Data release</p>
      <p class="release-string">${esc(m.data_release)}</p>
      ${citationHtml(m, "cite-dl")}
    </section>
    <div class="table-wrap"><table class="figures files">
      <thead><tr><th>File</th><th>What is in it</th><th>Rows</th><th>Size</th><th>SHA-256</th></tr></thead>
      <tbody>${m.files.map((f) => `<tr><th scope="row"><a href="/download/${encodeURIComponent(f.name)}" download>${esc(f.name)}</a></th>
        <td>${esc(f.description)}</td><td class="n">${whole(f.rows)}</td><td class="n">${kb(f.bytes)}</td><td><code class="sha">${esc(f.sha256)}</code></td></tr>`).join("")}
        <tr><th scope="row"><a href="/download/release_manifest.json" download>release_manifest.json</a></th><td colspan="4">Row counts, checksums, the laws and their status, and the attribution for every source.</td></tr>
      </tbody></table></div>
    <div class="band two">
      <section class="panel ticket">
        <h2>Match decisions</h2>
        <p class="small">match_decisions.csv holds every decision that links a source record to a CoFID food, as recorded.</p>
        <ul class="gaps">${decisions.map((c) => `<li><strong>${esc(c.description)}</strong>: ${c.rows ? `${whole(c.rows)} rows` : esc(c.statement)}</li>`).join("")}</ul>
      </section>
      <section class="panel ticket">
        <h2>Sources and rights</h2>
        <ul class="gaps">${m.attribution.map((a) => `<li><strong>${esc(a.dataset)}</strong>${a.edition ? `, ${esc(a.edition)}` : ""}. ${esc(a.licence)}${a.extraction ? ` Extraction: ${esc(a.extraction)}.` : ""}${a.attribution ? `<br><span class="small">${esc(a.attribution)}</span>` : ""}</li>`).join("")}</ul>
        <p class="small">${m.not_included.map(esc).join(" ")}</p>
      </section>
    </div>
    <p class="note">One food at a time: every food page has its own CSV, built from what that page shows. Laws in this release: ${m.laws.map((l) => esc(lawStatus(l))).join("; ")}.</p>`;
}

/* ---------- Food ---------- */
const foodState = { id: null, portion: null, fvn: "", fs: "", pack: "", data: null, scoreFirst: false };

function panelTable(food, portionG) {
  const rows = food.panel.map((p) => {
    const sub = p.label.startsWith("of which");
    let v100;
    if (p.value === null) v100 = `<span class="muted">${p.value_kind === "present_not_quantified" ? "present, amount unknown (N)" : "not given"}</span>`;
    else if (p.value_kind === "trace") v100 = "trace";
    else v100 = `${fmt(p.value, p.unit)}<span class="u">${esc(p.unit)}</span>`;
    const per = portionG && p.value !== null && p.value_kind === "number" ? `${fmt(p.value * portionG / 100, p.unit)}<span class="u">${esc(p.unit)}</span>` : (p.value_kind === "trace" ? "trace" : "");
    return `<tr class="${sub ? "sub" : ""}"><th scope="row">${esc(p.label)}<span class="srcrow">${srcButton(p.source)}</span></th>
      <td class="n">${v100}</td>${portionG ? `<td class="n">${per}</td>` : ""}</tr>`;
  }).join("");
  const basis = food.panel.some((p) => p.basis === "per_100ml") ? "Per 100 ml" : "Per 100 g";
  return `<table class="figures"><thead><tr><th>Nutrient</th><th>${basis}</th>${portionG ? `<th>Per ${grams(portionG)}</th>` : ""}</tr></thead><tbody>${rows}</tbody></table>`;
}

/* The query that sets what a food page shows; the page and its CSV use the same one. */
function foodParams(id) {
  const p = new URLSearchParams();
  if (foodState.portion) p.set("portion_g", String(foodState.portion));
  if (foodState.fvn !== "") p.set("fvn_percent", foodState.fvn);
  if (foodState.fs !== "") p.set("free_sugars_g", foodState.fs);
  if (foodState.pack !== "") p.set("pack_g", foodState.pack);
  const keys = unitKeys(id);
  if (keys.length) p.set("unit", keys.join(","));
  return p;
}

async function loadFood(id) {
  return api(`/ui/food/${encodeURIComponent(id)}?${foodParams(id)}`);
}

function foodCsvHref(id) {
  const p = foodParams(id).toString();
  return `/download/food/${encodeURIComponent(id)}.csv${p ? `?${p}` : ""}`;
}

async function renderFood(id, { scoreFirst = false } = {}) {
  foodState.scoreFirst = scoreFirst;
  if (foodState.id !== id) Object.assign(foodState, { id, portion: null, fvn: "", fs: "", pack: "", data: null });
  sources = [];
  if (!foodState.data) view().innerHTML = `<section class="scene"><p class="note">Loading the product.</p></section>`;
  let food;
  try { food = await loadFood(id); } catch (e) {
    view().innerHTML = `<section class="scene"><h1 class="headline">This food did not load</h1><p>${esc(e.message)}</p><p><a class="btn ticket" href="#/">Back to the data</a></p></section>`;
    return;
  }
  if (foodState.portion === null) {
    const unit = food.as_sold && food.as_sold.unit;
    const first = food.portions.find((x) => x.tappable && x.grams >= 10);
    const pick = unit ? unit.typical_g : (first ? first.grams : null);
    if (pick) { foodState.portion = pick; food = await loadFood(id).catch(() => food); }
  }
  foodState.data = food;
  sources = [];
  const a = food.assessment;
  const g = foodState.portion;
  const tappable = food.portions.filter((x) => x.tappable);
  const listed = food.portions.filter((x) => !x.tappable);
  const chip = (label, value, sub) => `<button class="chip ticket" type="button" data-portion="${value}" aria-pressed="${g === value}">${esc(label)}<small>${esc(sub)}</small></button>`;
  const models = ordered(a.models);
  const needsFvn = models.some((m) => !m.scorable && (m.missing_inputs || []).some((x) => x.startsWith("fruit_veg_nuts_percent")));
  const neu = a.models["uk-npm-2018"];
  const fsMissing = neu && neu.scorable === false && neu.applicable !== false;
  const caller = food.caller_supplied || {};

  const figuresForm = (needsFvn || fsMissing || caller.fvn_percent !== undefined || caller.free_sugars_g !== undefined) ? `
        <h3>Your figures</h3>
        <p class="small">CoFID cannot supply these. What you enter is labelled as yours wherever the score appears.</p>
        <div class="inline-form">
          ${needsFvn || caller.fvn_percent !== undefined ? `<div class="field"><label for="fvn">Fruit, veg and nuts (% of weight)</label><input class="input num" id="fvn" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(foodState.fvn)}"></div>` : ""}
          ${fsMissing || caller.free_sugars_g !== undefined ? `<div class="field"><label for="fs">Free sugars (g per 100 g)</label><input class="input num" id="fs" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(foodState.fs)}"></div>` : ""}
          <button class="btn ticket" type="button" data-act="apply-figures">Score with these</button>
        </div>
        ${fsMissing && neu.free_sugars_note ? `<p class="note">${esc(neu.free_sugars_note)}</p>` : ""}` : "";
  const scorePanel = `<section class="panel score-panel" id="score" aria-labelledby="score-h">
      <p class="eyebrow">Score this food</p>
      <h2 id="score-h">Under today's law and the law that is coming</h2>
      ${ticket(a)}
      ${yours(caller)}
      ${quote(a, food.data_release)}
      ${figuresForm}
      <h3>Front of pack</h3>
      ${lights(a.traffic_lights, "Traffic lights")}
      ${a.traffic_lights && a.traffic_lights.portion_rule_applied ? `<p class="note">The unit is over 100 g, so the per-portion red limits were checked too.</p>` : ""}
    </section>`;
  const composition = `<section class="panel ticket">
          <h2>What is in it</h2>
          <div class="chips">
            ${tappable.map((p) => chip(p.label, p.grams, grams(p.grams))).join("")}
            ${chip("Per 100 g only", 0, "no unit")}
          </div>
          <div class="inline-form">
            <div class="field"><label for="pg">Or weigh one (g)</label><input class="input num" id="pg" type="number" inputmode="decimal" min="0.1" step="any" value="${g && !tappable.some((p) => p.grams === g) ? Math.round(g * 10) / 10 : ""}"></div>
            <button class="btn btn-ghost" type="button" data-act="set-portion">Use this weight</button>
          </div>
          ${panelTable(food, g)}
          ${food.salt_from_sodium ? `<p class="note">Salt for colours and scores is sodium x 2.5.</p>` : ""}
          ${tappable.length ? `<p class="note">Unit weights: ${tappable.map((p) => srcButton(p.source, `${p.label}, ${p.source.label}`)).join(" ")}</p>` : ""}
          ${listed.length ? `<p class="note">Also printed, not offered as one tap: ${listed.map((p) => `${esc(p.label)} ${esc(p.weight_text)} ${srcButton(p.source, "why")}`).join("; ")}</p>` : ""}
          ${food.overlay_values.length ? `<h3>Also measured by an official overlay</h3><table class="figures"><tbody>${food.overlay_values.map((o) => `<tr><th scope="row">${esc(o.label)}<span class="srcrow">${srcButton(o.source)}</span></th><td class="n">${o.value === null ? esc(o.value_text) : `${fmt(o.value, o.unit)}<span class="u">${esc(o.unit)}</span>`}</td></tr>`).join("")}</tbody></table>` : ""}
        </section>`;
  const recipePanel = `<section class="panel ticket">
          <h2>Use it in a recipe</h2>
          <div class="inline-form">
            <div class="field"><label for="addg">Weight (g)</label><input class="input num" id="addg" type="number" inputmode="decimal" min="0.1" step="any" value="${g ? Math.round(g * 10) / 10 : 100}"></div>
            <button class="btn ticket" type="button" data-act="add-food">Add to recipe</button>
          </div>
        </section>`;
  const record = `
      ${food.powder ? `<div class="flag"><strong>As sold, not made up</strong>${esc(food.powder.text)}</div>` : ""}
      <div class="band two">
        ${soldHtml(food)}
        ${composition}
      </div>`;
  view().innerHTML = `<section class="scene food">
    <div class="backtype" aria-hidden="true">${esc(food.name)}</div>
    <p class="kicker">${scoreFirst ? `<a href="#/score">Score a product</a>` : `<a href="#/browse/${encodeURIComponent((food.group || "").slice(0, 1))}">${esc(food.group_name || "Food group")}</a>`}</p>
    <h1 class="headline">${esc(food.name)}</h1>
    <p class="muted small desc">CoFID ${esc(food.code)}, group ${esc(food.group)}. ${esc(food.description || "")}</p>
    <div class="band">
      ${scoreFirst ? scorePanel + record : record + scorePanel}
      <div class="band two">
        ${recipePanel}
        <section class="panel ticket">
          <h2>This food as data</h2>
          <p class="small">Its identity, weights, composition with sources, and both scores with their laws, as this page shows them now.</p>
          <p><a class="btn ticket" href="${esc(foodCsvHref(food.food_id))}" download>Download this food as CSV</a></p>
          <p class="small">${scoreFirst ? `<a href="#/food/${encodeURIComponent(food.food_id)}">Open the full record</a>` : `<a href="#/score/${encodeURIComponent(food.food_id)}">Open the score view</a>`}</p>
        </section>
      </div>
      <p class="note">${esc(food.evidence_note)} Data release ${esc(food.data_release)}.</p>
    </div>
  </section>`;
  revealTear();
}

/* ---------- Your range (bulk) ---------- */
const COLUMNS = ["name", "code", "free_sugars_g", "fvn_percent", "pack_g", "energy_kj", "fat_g", "saturated_fat_g",
  "total_sugars_g", "salt_g", "sodium_mg", "protein_g", "fibre_aoac_g", "fibre_nsp_g", "fruit_veg_nuts_percent", "fvns_g", "is_drink"];
let lastRun = null;

function parseCsv(text) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i += 1; } else if (ch === '"') quoted = false; else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i += 1; row.push(cell); rows.push(row); row = []; cell = ""; }
    else cell += ch;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim() !== ""));
}

function toRows(text) {
  const lines = text.trim();
  if (!lines) return [];
  const table = parseCsv(lines);
  const header = table[0].map((h) => h.trim().toLowerCase());
  if (header.includes("name") || header.includes("code")) {
    return table.slice(1).map((cells) => {
      // CoFID names contain commas. An unquoted name in the first column spills into extra
      // cells; join the overflow back into the name rather than misreading the row.
      const extra = cells.length - header.length;
      const r = header[0] === "name" && extra > 0 ? [cells.slice(0, extra + 1).join(","), ...cells.slice(extra + 1)] : cells;
      const row = {};
      header.forEach((h, i) => {
        const v = (r[i] || "").trim();
        if (!COLUMNS.includes(h) || v === "") return;
        if (h === "name" || h === "code") row[h] = v;
        else if (h === "is_drink") row[h] = /^(1|y|yes|true)$/i.test(v);
        else row[h] = Number(v);
      });
      return row;
    });
  }
  return lines.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
    .map((l) => (/^\d{2}-\d{3,4}(@row\d+)?$/.test(l) ? { code: l } : { name: l }));
}

function verdictCell(m) {
  if (!m.scorable) return `<td class="vcell none"><span class="vscore">No score</span><span class="vword">needs ${esc(m.missing.length ? m.missing.map(needWord).join(", ") : "an input")}</span></td>`;
  return `<td class="vcell"><span class="vscore">${m.score}</span><span class="vword"><span aria-hidden="true">${m.less_healthy ? "&#9632;" : "&#9633;"}</span> ${m.less_healthy ? "less healthy" : "not less healthy"}</span></td>`;
}

/* Which of the two modes scored a row. Read from the service's own row: a row with no
   CoFID food was scored from the visitor's figures. */
function scoredFrom(r) {
  if (!r.resolved.food_id) return "Your figures";
  const own = Object.keys(r.caller_supplied || {}).map(needWord);
  return `ShelfScale reference data${own.length ? `, with your ${own.join(" and ")}` : ""}`;
}

function rowHtml(r, laws) {
  const order = laws.map((l) => l.model);
  const flips = r.verdict_changes_under_2018 === true;
  const sold = r.as_sold;
  const unit = sold.unit;
  const unitCell = !unit && sold.proposed_units && r.resolved.food_id ? `<a href="#/food/${encodeURIComponent(r.resolved.food_id)}">Confirm a unit weight</a>` : unit ? `${grams(unit.low_g)}${unit.low_g !== unit.high_g ? ` to ${grams(unit.high_g)}` : ""}${sold.band && sold.band.crosses && sold.band.crosses.length ? `<br><span class="tag red">${esc(sold.band.crosses.join(", "))} crosses</span>` : ""}` : "";
  const srcCard = { label: "Where this row came from", html: `<h2 id="sheet-title">${esc(r.input)}</h2><dl>
      <dt>Scored from</dt><dd>${esc(scoredFrom(r))}</dd>
      <dt>Matched to</dt><dd>${esc(r.resolved.name)}${r.resolved.code ? ` (CoFID ${esc(r.resolved.code)})` : ""}</dd>
      <dt>How</dt><dd>${esc(r.resolved.basis)}</dd><dt>Values from</dt><dd>${esc(r.sources.join(", "))}</dd>
      ${Object.keys(r.caller_supplied || {}).length ? `<dt>You entered</dt><dd>${esc(Object.entries(r.caller_supplied).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(", "))}</dd>` : ""}
      ${ordered(r.models).map((m) => `<dt>${esc(ROLE_TITLE[m.law.role])}</dt><dd>${esc(lawStatus(m.law))}: ${m.scorable ? `score ${m.score}` : esc(m.missing.join("; "))}</dd>`).join("")}
      <dt>Sold as</dt><dd>${esc(sold.kind)}${sold.sale_format ? `, ${esc(sold.sale_format)}` : ""}${unit ? `; unit ${esc(unit.label)}, ${esc(unit.spread)}` : ""}</dd></dl>` };
  return `<tr class="${flips ? "flip-row" : ""}">
    <th scope="row"><span class="pname">${esc(r.input)}</span>${flips ? '<span class="torn" title="Verdict flips">Flips</span>' : ""}
      <span class="pmeta">${esc(r.resolved.name)}${sold.kind === "loose" ? ", sold loose" : ""}</span>
      <span class="mode-tag">Scored from: ${esc(scoredFrom(r))}</span>${srcButton(srcCard, "Receipts")}</th>
    ${order.map((id) => verdictCell(r.models[id])).join("")}
    <td class="n">${unitCell}</td>
  </tr>`;
}

function renderRange() {
  sources = [];
  const saved = read(RANGE, "");
  view().innerHTML = `<section class="scene range">
    <div class="backtype" aria-hidden="true">Range</div>
    <h1 class="headline">Score your range</h1>
    <p class="lede">Bring your whole range. Paste one product per line, or upload a spreadsheet saved as CSV. Products whose verdict flips come first.</p>
    <div class="modes">
      <div class="mode ticket"><h2>From your own figures</h2><p class="small">Give your label values per 100 g. The row is scored from your figures, and says so.</p></div>
      <div class="mode ticket"><h2>From ShelfScale reference data</h2><p class="small">Give a CoFID name or code. The row is scored from CoFID values and their sources, and says so.</p></div>
    </div>
    <div class="panel ticket">
      <div class="field"><label for="rows">Products, one per line, or CSV with a header row</label>
        <textarea class="input area" id="rows" rows="8" spellcheck="false" placeholder="Raisins, dried&#10;Jaffa cakes&#10;11-886">${esc(saved)}</textarea></div>
      <div class="inline-form">
        <div class="field"><label for="csv">Or upload a CSV</label><input class="input file" id="csv" type="file" accept=".csv,text/csv"></div>
        <button class="btn ticket" type="button" data-act="run-range">Score the range</button>
        <button class="btn btn-ghost" type="button" data-act="template">Download a CSV template</button>
      </div>
      <p class="note">CSV columns: name or code; optional free_sugars_g, fvn_percent and pack_g; or your own label figures per 100 g (energy_kj, fat_g, saturated_fat_g, total_sugars_g, salt_g, protein_g, fibre_aoac_g, fruit_veg_nuts_percent). The 2018 model needs a free sugars figure for each row; total sugars are never used instead.</p>
    </div>
    <div id="run"></div>
  </section>`;
  if (lastRun) paintRun();
}

async function runRange() {
  const text = document.getElementById("rows").value;
  write(RANGE, text);
  const rows = toRows(text);
  const box = document.getElementById("run");
  if (!rows.length) { box.innerHTML = `<p class="note">Add at least one product first.</p>`; return; }
  box.innerHTML = `<p class="note">Scoring ${rows.length} row${rows.length > 1 ? "s" : ""}.</p>`;
  try { lastRun = await api("/ui/bulk", { rows, confirmed: matches() }); paintRun(); }
  catch (e) { box.innerHTML = `<div class="flag"><strong>Not scored</strong>${esc(e.message)}</div>`; }
}

function paintRun() {
  const box = document.getElementById("run");
  if (!box || !lastRun) return;
  sources = [];
  const r = lastRun;
  const s = r.summary;
  const laws = r.laws.slice().sort((a, b) => ({ today: 0, coming: 1, past: 2 }[a.role] - { today: 0, coming: 1, past: 2 }[b.role]));
  box.innerHTML = `
    <div class="run-head">
      <p class="run-big">${s.verdict_changes_under_2018}<span> verdict${s.verdict_changes_under_2018 === 1 ? "" : "s"} flip</span></p>
      <p class="small">${r.rows.filter((x) => !x.resolved.food_id).length} scored from your figures, ${r.rows.filter((x) => x.resolved.food_id).length} from ShelfScale reference data.</p>
      <p class="small">${s.scored} of ${s.received} scored. ${s.gaps} gap${s.gaps === 1 ? "" : "s"}, ${s.errors} row error${s.errors === 1 ? "" : "s"}, ${s.loose} sold loose. Data release ${esc(r.data_release)}.</p>
      <div class="label-actions noprint">
        <button class="btn ticket" type="button" data-act="export-csv">Export CSV</button>
        <button class="btn ticket" type="button" data-act="export-text">Copy as text</button>
        <span id="exported" class="note" role="status"></span>
      </div>
    </div>
    ${r.rows.length ? `<div class="table-wrap"><table class="figures run"><thead><tr><th>Product</th>${laws.map((l) => `<th>${esc(ROLE_TITLE[l.role])}<br><span class="u">${esc(lawStatus(l))}</span></th>`).join("")}<th>Unit as sold</th></tr></thead>
      <tbody>${r.rows.map((x) => rowHtml(x, laws)).join("")}</tbody></table></div>` : ""}
    ${r.gaps.length ? `<section class="panel ticket"><h2>Gaps</h2><p class="small">These rows were not scored. Nothing is guessed: confirm a match, give the CoFID code, or score them from your label figures.</p>
      <ul class="gaps">${r.gaps.map((g) => `<li><strong>${esc(g.input)}</strong>: ${esc(g.reason)} ${g.candidates.length ? `<button class="btn btn-ghost" type="button" data-match="${esc(g.input)}">Find a match</button>` : ""}</li>`).join("")}</ul></section>` : ""}
    ${r.errors.length ? `<section class="panel ticket"><h2>Rows to fix</h2><ul class="gaps">${r.errors.map((e) => `<li>Row ${e.index + 1}${e.input ? ` (${esc(e.input)})` : ""}: ${esc(e.error)}</li>`).join("")}</ul></section>` : ""}
    <p class="note">${esc(r.rule)}</p>`;
}

function exportRows() {
  const r = lastRun;
  const laws = r.laws;
  const head = ["product", "status", "scored_from", "matched_cofid_code", "matched_name", "match_basis",
    ...laws.flatMap((l) => [`${l.model} score`, `${l.model} verdict`, `${l.model} law`]),
    "verdict_changes", "sold_as", "unit_low_g", "unit_high_g", "unit_basis", "values_from", "you_entered", "reason", "data_release"];
  const out = [head];
  r.rows.forEach((x) => out.push([x.input, "scored", scoredFrom(x), x.resolved.code || "", x.resolved.name, x.resolved.basis,
    ...laws.flatMap((l) => { const m = x.models[l.model]; return [m.scorable ? m.score : "", m.scorable ? (m.less_healthy ? "less healthy" : "not less healthy") : `not scored: ${m.missing.join("; ")}`, lawStatus(l)]; }),
    x.verdict_changes_under_2018 === null ? "unknown" : String(x.verdict_changes_under_2018), x.as_sold.kind,
    x.as_sold.unit ? x.as_sold.unit.low_g.toFixed(1) : "", x.as_sold.unit ? x.as_sold.unit.high_g.toFixed(1) : "",
    x.as_sold.unit ? x.as_sold.unit.basis : "", x.sources.join("; "),
    Object.entries(x.caller_supplied || {}).map(([k, v]) => `${k}=${v}`).join("; "), "", r.data_release]));
  r.gaps.forEach((g) => out.push([g.input, "gap", "not scored", "", "", "", ...laws.flatMap(() => ["", "", ""]), "", "", "", "", "", "", "", g.reason, r.data_release]));
  r.errors.forEach((e) => out.push([e.input || `row ${e.index + 1}`, "error", "not scored", "", "", "", ...laws.flatMap(() => ["", "", ""]), "", "", "", "", "", "", "", e.error, r.data_release]));
  return out;
}
const csvCell = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));

async function openMatch(name) {
  openSheet(`<h2 id="sheet-title">Match "${esc(name)}"</h2><p class="note">Looking for candidates.</p>`);
  let r;
  try { r = await api("/ui/match", { name }); } catch (e) { document.getElementById("sheet-body").innerHTML += `<p class="note">${esc(e.message)}</p>`; return; }
  const engine = r.engine.engine === "jev"
    ? `Candidates found by shared words, then scored by Jev (${esc(r.engine.model)}) as the probability that each is the same food. Above ${r.thresholds.propose_at} a candidate is proposed; below ${r.thresholds.abstain_below} it is set aside. Thresholds: ${esc(r.thresholds.basis)}`
    : `Candidates found by shared words only. ${esc(r.engine.reason)}`;
  const items = r.candidates.map((c, i) => `<li class="ticket cand ${c.verdict}">
      <span><strong>${esc(c.name)}</strong> <span class="muted small">CoFID ${esc(c.code)}, group ${esc(c.group)}</span><br>
      <span class="small">${c.probability === null ? `possible match, word overlap ${fmt(c.retrieval_score, "g")}` : `${c.verdict === "proposed" ? "proposed" : c.verdict === "abstain" ? "unlikely" : "possible"}, Jev probability ${fmt(c.probability, "g")}`}</span></span>
      <button class="btn ticket" type="button" data-confirm="${i}">This is it</button></li>`).join("");
  window.__match = r;
  document.getElementById("sheet-body").innerHTML = `<h2 id="sheet-title">Match "${esc(name)}"</h2>
    <p class="small">${engine}</p>
    <p class="small"><strong>${esc(r.rule)}</strong></p>
    ${items ? `<ol class="cands">${items}</ol>` : `<p class="note">No CoFID food shares a word with this name. Score it from your own label figures instead.</p>`}
    <p class="small">None of these? Close this and leave the row as a gap, or score it from your label figures.</p>`;
}

/* ---------- Recipe ---------- */
let lastResult = null;
let resultError = null;
const portionCache = {};

async function portionsFor(id) {
  if (!portionCache[id]) {
    try { portionCache[id] = (await api(`/ui/food/${encodeURIComponent(id)}`)).portions.filter((p) => p.tappable); }
    catch (_) { portionCache[id] = []; }
  }
  return portionCache[id];
}

async function calculate() {
  const valid = recipe.ingredients.filter((i) => Number(i.grams) > 0);
  if (!valid.length) { lastResult = null; resultError = null; paintResult(); return; }
  const body = { name: recipe.name || null, servings: recipe.servings, ingredients: valid.map((i) => ({ food_id: i.food_id, grams: Number(i.grams) })) };
  if (recipe.fvn_percent !== null && recipe.fvn_percent !== "") body.fvn_percent = Number(recipe.fvn_percent);
  if (recipe.free_sugars_g !== null && recipe.free_sugars_g !== "") body.free_sugars_g = Number(recipe.free_sugars_g);
  try { lastResult = await api("/ui/recipe", body); resultError = null; }
  catch (e) { resultError = e.message; }
  paintResult();
}
const recalc = debounce(calculate, 320);

function ingredientHtml(item, index) {
  return `<li class="ing ticket" data-index="${index}">
    <div class="ing-top"><span class="ing-name">${esc(item.name)}</span>
      <button class="btn btn-ghost" type="button" data-remove="${index}" aria-label="Remove ${esc(item.name)}">Remove</button></div>
    <div class="ing-row">
      <div class="field"><label for="g${index}">Grams as used</label>
        <input class="input num" id="g${index}" type="number" inputmode="decimal" min="0.1" step="any" value="${esc(item.grams)}" data-grams="${index}"></div>
      <div class="chips" data-chips="${index}"></div>
    </div>
    <p class="note hidden" data-flag="${esc(item.food_id)}"><strong>As sold.</strong> This is the powder or concentrate as sold. Weigh it dry and add any water or milk as its own ingredient. The score treats it as sold, not made up.</p>
  </li>`;
}

async function paintChips() {
  for (const [index, item] of recipe.ingredients.entries()) {
    const box = document.querySelector(`[data-chips="${index}"]`);
    if (!box) continue;
    const ps = await portionsFor(item.food_id);
    box.innerHTML = ps.map((p) => `<button class="chip ticket" type="button" data-tap="${index}" data-g="${p.grams}" aria-pressed="${Number(item.grams) === p.grams}">${esc(p.label)}<small>${grams(p.grams)}, ${esc(p.source.label)}</small></button>`).join("");
  }
}

function renderRecipe() {
  sources = [];
  const items = recipe.ingredients;
  view().innerHTML = `<section class="scene recipe">
    <div class="backtype low" aria-hidden="true">${esc(recipe.name || "Recipe")}</div>
    <h1 class="headline">${esc(recipe.name || "Your recipe")}</h1>
    <p class="lede">For a small producer the recipe is the product. Add what goes in, by weight as used, and see the finished product under both laws.</p>
    <div id="result-hero"></div>
    <div class="band">
      <div class="inline-form">
        <div class="field grow"><label for="rname">Product name</label><input class="input" id="rname" type="text" maxlength="120" value="${esc(recipe.name)}" placeholder="Name it for the label"></div>
        <div class="field"><label>Portions it makes</label><div class="stepper">
          <button class="btn ticket" type="button" data-act="less" aria-label="Fewer portions">&minus;</button>
          <output id="servings" aria-live="polite">${recipe.servings}</output>
          <button class="btn ticket" type="button" data-act="more" aria-label="More portions">+</button></div></div>
      </div>
      ${items.length ? `<ul class="ingredients">${items.map(ingredientHtml).join("")}</ul>` : `<div class="panel ticket empty"><h2>No ingredients yet</h2><p>Search below and add what goes in. The recipe stays in this browser only.</p></div>`}
      <div class="adder panel ticket">
        <div class="field"><label for="addq">Add an ingredient</label><input class="input" id="addq" type="search" autocomplete="off" placeholder="Search CoFID foods" enterkeyhint="search"></div>
        <div id="addfound"></div>
      </div>
      <div id="result-detail"></div>
      ${items.length ? `<p><button class="btn btn-ghost" type="button" data-act="clear">Start a new recipe</button></p>` : ""}
    </div>
  </section>`;
  wireSearch("addq", "addfound", "add");
  paintResult();
  paintChips();
  recalc();
}

const REQUIRED = ["energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g", "protein_g", "sodium_mg"];
function contributionsCard(name, label, unit) {
  const rows = (lastResult.contributions[name] || []);
  return { label, html: `<h2 id="sheet-title">${esc(label)} in this recipe</h2>
    <p class="small">Each ingredient's value per 100 g, scaled by its weight, then divided by the total raw weight, ${grams(lastResult.total_g)}.</p>
    <table class="figures"><thead><tr><th>Ingredient</th><th>Per 100 g</th><th>In recipe</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><th scope="row">${esc(r.name)}, ${grams(r.grams)}<span class="srcrow muted small">${esc(r.source.label)}, ${esc(r.source.observation_id)}</span></th><td class="n">${fmt(r.per_100g, unit)}</td><td class="n">${fmt(r.amount, unit)}<span class="u">${esc(unit)}</span></td></tr>`).join("")}
    </tbody></table>` };
}

function paintResult() {
  const hero = document.getElementById("result-hero");
  const detail = document.getElementById("result-detail");
  if (!hero || !detail) return;
  sources = [];
  if (resultError) { hero.innerHTML = `<div class="flag"><strong>Not calculated</strong>${esc(resultError)}</div>`; detail.innerHTML = ""; return; }
  if (!lastResult) { hero.innerHTML = ""; detail.innerHTML = ""; return; }
  const r = lastResult;
  const a = r.assessment;
  const old = a.models["uk-npm-2004/05"];
  const neu = a.models["uk-npm-2018"];
  const fvnNeeded = !old.scorable && (old.missing_inputs || []).some((m) => m.startsWith("fruit_veg_nuts_percent"));
  const known = r.fruit_veg_nuts.known;
  const rows = [
    ["energy_kj", "Energy", "kJ"], ["fat_g", "Fat", "g"], ["saturated_fat_g", "of which saturates", "g"],
    ["total_sugars_g", "Total sugars", "g"], ["fibre_nsp_g", "Fibre (NSP)", "g"], ["fibre_aoac_g", "Fibre (AOAC)", "g"],
    ["protein_g", "Protein", "g"], ["sodium_mg", "Sodium", "mg"],
  ].filter(([k]) => k in r.per_100g || REQUIRED.includes(k));
  const mine = {};
  if (recipe.fvn_percent !== null && recipe.fvn_percent !== "") mine.fvn_percent = Number(recipe.fvn_percent);
  if (recipe.free_sugars_g !== null && recipe.free_sugars_g !== "") mine.free_sugars_g = Number(recipe.free_sugars_g);
  hero.innerHTML = `${ticket(a, { hero: true })}${yours(mine)}${quote(a, r.data_release)}
    <p class="muted small">${grams(r.total_g)} in all, ${r.servings} portion${r.servings > 1 ? "s" : ""} of ${grams(r.serving_g)}. ${esc(r.yield_note)}</p>`;
  detail.innerHTML = `
    <section class="panel ticket">
      <h2>Your figures</h2>
      <p class="small">CoFID cannot supply these for a recipe. What you enter is labelled as yours.</p>
      <div class="inline-form">
        <div class="field"><label for="rfvn">Fruit, veg and nuts (% of weight)</label><input class="input num" id="rfvn" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(recipe.fvn_percent ?? "")}"></div>
        <div class="field"><label for="rfs">Free sugars (g per 100 g)</label><input class="input num" id="rfs" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(recipe.free_sugars_g ?? "")}"></div>
        <button class="btn ticket" type="button" data-act="apply-recipe">Score with these</button>
      </div>
      ${fvnNeeded ? `<p class="note">Today's law needs this. Fruit, vegetable and nut ingredients make up ${fmt(known.share_of_weight_percent, "%")}% of the weight; the rest have no value under the group rule, so ShelfScale will not assume one.</p>` : ""}
      ${r.fruit_veg_nuts.source === "derived_from_ingredients" ? `<p class="note">Fruit, veg and nuts: ${fmt(r.fruit_veg_nuts.value, "%")}%, worked out from the ingredients by group.</p>` : ""}
      ${neu.free_sugars_note ? `<p class="note">${esc(neu.free_sugars_note)}</p>` : ""}
    </section>
    ${r.review_flags.length ? `<div class="flag"><strong>Check before relying on it</strong>${r.review_flags.map((f) => `${esc(f.ingredient)}: ${esc(f.reason)}`).join("<br>")}</div>` : ""}
    <div class="band two">
      <section class="panel ticket">
        <h2>Per 100 g and per portion</h2>
        <table class="figures"><thead><tr><th>Nutrient</th><th>Per 100 g</th><th>Per ${grams(r.serving_g)}</th></tr></thead><tbody>
        ${rows.map(([k, label, unit]) => {
          const v = r.per_100g[k];
          sources.push(contributionsCard(k, label, unit));
          const btn = `<button class="src" type="button" data-src="${sources.length - 1}">Where from</button>`;
          if (v === undefined) return `<tr><th scope="row">${esc(label)}<span class="srcrow">${btn}</span></th><td class="n muted" colspan="2">not recorded for every ingredient</td></tr>`;
          return `<tr class="${label.startsWith("of which") ? "sub" : ""}"><th scope="row">${esc(label)}<span class="srcrow">${btn}</span></th><td class="n">${fmt(v, unit)}<span class="u">${unit}</span></td><td class="n">${fmt(r.per_serving[k], unit)}<span class="u">${unit}</span></td></tr>`;
        }).join("")}
        </tbody></table>
        <div class="flag basis"><strong>Why the label shows different numbers</strong>These are the CoFID values the scores use. The label is worked out under the labelling rules: carbohydrate by weight, protein from nitrogen and the Regulation's energy factors. <a href="#/label?method">See how the label is worked out</a>.</div>
      </section>
      <section class="panel ticket">
        <h2>Front of pack, per portion</h2>
        ${a.traffic_lights ? lights(a.traffic_lights, "Traffic lights") : `<p class="note">Traffic lights need fat, saturates, sugars and salt for every ingredient.</p>`}
        ${a.traffic_lights ? `<p class="note">Colours follow per 100 g. A portion over 100 g is also checked against the per-portion red limits. Portion: ${grams(r.serving_g)}.</p>` : ""}
        <p><a class="btn ticket" href="#/label">Get the label</a></p>
      </section>
    </div>`;
  document.querySelectorAll("[data-flag]").forEach((el) => {
    el.classList.toggle("hidden", !r.ingredients.some((x) => x.food_id === el.dataset.flag && x.as_sold));
  });
  revealTear();
}

/* ---------- Label ---------- */
function declRows(r) {
  const L = r.label;
  const pick = (side, key) => L[side].find((x) => x.key === key);
  const cell = (row) => (row.display === null ? "n/a" : `${row.display} ${row.unit}`);
  return [
    ["Energy", (s) => `${cell(pick(s, "energy_kj"))} / ${cell(pick(s, "energy_kcal"))}`, false],
    ["Fat", (s) => cell(pick(s, "fat_g")), false],
    ["of which saturates", (s) => cell(pick(s, "saturates_g")), true],
    ["Carbohydrate", (s) => cell(pick(s, "carbohydrate_g")), false],
    ["of which sugars", (s) => cell(pick(s, "sugars_g")), true],
    ["Protein", (s) => cell(pick(s, "protein_g")), false],
    ["Salt", (s) => cell(pick(s, "salt_g")), false],
  ].map(([name, f, sub]) => ({ name, sub, per100: f("per_100g"), serving: f("per_serving") }));
}

async function renderLabel(focusMethod) {
  sources = [];
  if (recipe.ingredients.length && !lastResult) {
    view().innerHTML = `<section class="scene"><p class="note">Working out the recipe.</p></section>`;
    await calculate();
  }
  const r = lastResult;
  if (!r) {
    view().innerHTML = `<section class="scene"><div class="backtype" aria-hidden="true">Label</div>
      <h1 class="headline">No recipe to label yet</h1><p>Build a recipe first. The label is worked out from its ingredients.</p>
      <p><a class="btn ticket" href="#/recipe">Go to the recipe</a></p></section>`;
    return;
  }
  const rows = declRows(r);
  const L = r.label;
  const missing = Object.keys(L.missing);
  const excl = Object.entries(L.energy_excludes);
  view().innerHTML = `<section class="scene label">
    <div class="backtype noprint" aria-hidden="true">Label</div>
    <h1 class="headline noprint">${esc(r.name || "Your recipe")}</h1>
    <div class="print-sheet">
      <p class="print-name">${esc(r.name || "Your recipe")}</p>
      <div class="decl" id="decl">
        <table>
          <caption>Nutrition</caption>
          <thead><tr><th>Typical values</th><th>Per 100 g</th><th>Per portion (${esc(grams(r.serving_g))})</th></tr></thead>
          <tbody>${rows.map((x) => `<tr class="${x.sub ? "sub" : ""}"><td>${esc(x.name)}</td><td>${esc(x.per100)}</td><td>${esc(x.serving)}</td></tr>`).join("")}</tbody>
          <tfoot><tr><td colspan="3">This pack makes ${r.servings} portion${r.servings > 1 ? "s" : ""}. ${esc(L.statement)}</td></tr></tfoot>
        </table>
      </div>
      <p class="print-foot">Worked out with ShelfScale from CoFID 2021, data release ${esc(r.data_release)}.</p>
    </div>
    <div class="label-actions noprint">
      <button class="btn ticket" type="button" data-act="print">Print the label</button>
      <button class="btn ticket" type="button" data-act="copy">Copy as text</button>
      <span id="copied" class="note" role="status"></span>
    </div>
    <section class="panel ticket noprint" id="method" tabindex="-1">
      <h2>How these figures are worked out</h2>
      <p class="small">The label follows the labelling rules, not CoFID's own conventions. Carbohydrate and sugars are converted from CoFID's monosaccharide equivalents to weight, protein is total nitrogen x 6.25, and energy uses the Regulation's factors, all as the CoFID user guide sets out. That is why these figures differ from the recipe screen, which shows the values the scores use. ${esc(L.method)}.</p>
      <p class="small">Rounding: ${esc(L.rounding)}. Per 100 g and per portion are rounded separately from unrounded values.</p>
      ${missing.length ? `<div class="flag"><strong>Not declared</strong>${missing.map((k) => `${esc(k.replace(/_g$/, "").replace(/_/g, " "))}: not recorded for ${esc(L.missing[k].join(", "))}`).join("<br>")}</div>` : ""}
      ${excl.length ? `<div class="flag"><strong>Energy leaves out</strong>${excl.map(([part, names]) => `${esc(part)} for ${esc(names.join(", "))}, because CoFID records no value`).join("<br>")}</div>` : ""}
      <p class="small">${esc(r.yield_note)} Data release ${esc(r.data_release)}.</p>
    </section>
  </section>`;
  if (focusMethod) { const m = document.getElementById("method"); m.scrollIntoView(); m.focus({ preventScroll: true }); }
}

function labelText() {
  const r = lastResult;
  return [`Nutrition${r.name ? `: ${r.name}` : ""}`, `Typical values\tPer 100 g\tPer portion (${grams(r.serving_g)})`,
    ...declRows(r).map((x) => `${x.sub ? "  " : ""}${x.name}\t${x.per100}\t${x.serving}`),
    `This pack makes ${r.servings} portion${r.servings > 1 ? "s" : ""}. ${r.label.statement}`].join("\n");
}

/* ---------- the tear, once, when a flip appears ---------- */
function revealTear() {
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll(".dual.flips:not(.torn-in)").forEach((el) => {
    el.classList.add("tearing");
    requestAnimationFrame(() => requestAnimationFrame(() => { el.classList.add("torn-in"); el.classList.remove("tearing"); }));
  });
}

/* ---------- routing and events ---------- */
function route() {
  const hash = location.hash || "#/";
  let tab = "browse";
  closeSheet();
  if (hash.startsWith("#/food/")) renderFood(decodeURIComponent(hash.slice(7)));
  else if (hash.startsWith("#/browse/")) renderGroup(decodeURIComponent(hash.slice(9)));
  else if (hash.startsWith("#/score/")) { tab = "score"; renderFood(decodeURIComponent(hash.slice(8)), { scoreFirst: true }); }
  else if (hash === "#/score") { tab = "score"; renderScoreStart(); }
  else if (hash === "#/range") { tab = "range"; renderRange(); }
  else if (hash === "#/download") { tab = "download"; renderDownloads(); }
  else if (hash === "#/recipe") { tab = "score"; renderRecipe(); }
  else if (hash.startsWith("#/label")) { tab = "score"; renderLabel(hash.includes("method")); }
  else renderHome();
  document.querySelectorAll(".tabs a").forEach((a) => {
    if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  if (!hash.includes("method")) window.scrollTo(0, 0);
}

function addIngredient(food_id, name, g) {
  recipe.ingredients.push({ food_id, name, grams: g });
  saveRecipe();
}

function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function copyText(text, statusId) {
  const status = document.getElementById(statusId);
  try { await navigator.clipboard.writeText(text); status.textContent = "Copied."; }
  catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    status.textContent = document.execCommand("copy") ? "Copied." : "Copy is blocked here. Select the text and copy it.";
    ta.remove();
  }
}

document.addEventListener("click", async (ev) => {
  const t = ev.target.closest("button, [data-close]");
  if (!t) return;
  if (t.hasAttribute("data-close")) { closeSheet(); return; }
  if (t.dataset.copy) { copyText(document.getElementById(t.dataset.copy).textContent, `${t.dataset.copy}-status`); return; }
  if (t.dataset.src !== undefined) { openSheet(sourceHtml(sources[Number(t.dataset.src)])); return; }
  if (t.dataset.portion !== undefined) { foodState.portion = Number(t.dataset.portion) || 0; renderFood(foodState.id, { scoreFirst: foodState.scoreFirst }); return; }
  if (t.dataset.unit) { keepUnit(foodState.id, t.dataset.unit); foodState.portion = null; renderFood(foodState.id, { scoreFirst: foodState.scoreFirst }); return; }
  if (t.dataset.match) { openMatch(t.dataset.match); return; }
  if (t.dataset.confirm !== undefined) {
    const r = window.__match;
    const c = r.candidates[Number(t.dataset.confirm)];
    try {
      const record = await api("/ui/match/confirm", { query: r.query, food_id: c.food_id, engine: r.engine, probability: c.probability });
      keepMatch(record);
      closeSheet();
      if (document.getElementById("rows")) runRange();
    } catch (e) { document.getElementById("sheet-body").insertAdjacentHTML("beforeend", `<p class="note">${esc(e.message)}</p>`); }
    return;
  }
  if (t.dataset.add) {
    const ps = await portionsFor(t.dataset.add);
    const usual = ps.find((p) => p.grams >= 10);
    addIngredient(t.dataset.add, t.dataset.name, usual ? Math.round(usual.grams * 10) / 10 : 100);
    renderRecipe();
    const el = document.getElementById(`g${recipe.ingredients.length - 1}`);
    if (el) { el.focus(); el.select(); }
    return;
  }
  if (t.dataset.remove !== undefined) { recipe.ingredients.splice(Number(t.dataset.remove), 1); saveRecipe(); renderRecipe(); return; }
  if (t.dataset.tap !== undefined) {
    const i = Number(t.dataset.tap);
    recipe.ingredients[i].grams = Number(t.dataset.g);
    saveRecipe();
    document.getElementById(`g${i}`).value = t.dataset.g;
    t.parentElement.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === t)));
    recalc(); return;
  }
  switch (t.dataset.act) {
    case "set-portion": { const v = Number(document.getElementById("pg").value); if (v > 0) { foodState.portion = v; renderFood(foodState.id, { scoreFirst: foodState.scoreFirst }); } break; }
    case "set-pack": { const v = document.getElementById("packg").value; foodState.pack = Number(v) > 0 ? v : ""; foodState.portion = Number(v) > 0 ? Number(v) : null; renderFood(foodState.id, { scoreFirst: foodState.scoreFirst }); break; }
    case "apply-figures": {
      const f = document.getElementById("fvn"), s = document.getElementById("fs");
      if (f) foodState.fvn = f.value;
      if (s) foodState.fs = s.value;
      renderFood(foodState.id, { scoreFirst: foodState.scoreFirst }); break;
    }
    case "apply-recipe": {
      recipe.fvn_percent = document.getElementById("rfvn").value || null;
      recipe.free_sugars_g = document.getElementById("rfs").value || null;
      saveRecipe(); calculate(); break;
    }
    case "add-food": {
      const v = Number(document.getElementById("addg").value);
      if (v > 0 && foodState.data) { addIngredient(foodState.data.food_id, foodState.data.name, v); location.hash = "#/recipe"; }
      break;
    }
    case "less": case "more":
      recipe.servings = Math.min(1000, Math.max(1, recipe.servings + (t.dataset.act === "more" ? 1 : -1)));
      document.getElementById("servings").textContent = recipe.servings;
      saveRecipe(); recalc(); break;
    case "clear":
      if (window.confirm("Start a new recipe? This removes the current one from this browser.")) {
        recipe = { name: "", servings: 1, ingredients: [], fvn_percent: null, free_sugars_g: null };
        lastResult = null; saveRecipe(); renderRecipe();
      }
      break;
    case "run-range": runRange(); break;
    case "template":
      download("shelfscale-range-template.csv", `${COLUMNS.slice(0, 5).join(",")}\nRaisins, dried,,0,,\nJaffa cakes,,,,,\n,11-886,,,,\n`, "text/csv"); break;
    case "export-csv": download(`shelfscale-range-${new Date().toISOString().slice(0, 10)}.csv`, exportRows().map((r) => r.map(csvCell).join(",")).join("\n"), "text/csv");
      document.getElementById("exported").textContent = "Exported."; break;
    case "export-text": copyText(exportRows().map((r) => r.join("\t")).join("\n"), "exported"); break;
    case "print": window.print(); break;
    case "copy": copyText(labelText(), "copied"); break;
    default: break;
  }
});

document.addEventListener("click", (ev) => {
  const j = ev.target.closest("a[data-jump]");
  if (!j) return;
  ev.preventDefault();
  const el = document.getElementById(j.dataset.jump);
  if (el) el.scrollIntoView({ block: "start" });
});

document.addEventListener("change", async (ev) => {
  const t = ev.target;
  if (t.id === "csv" && t.files && t.files[0]) {
    const text = await t.files[0].text();
    document.getElementById("rows").value = text;
    runRange();
  }
});

document.addEventListener("input", (ev) => {
  const t = ev.target;
  if (t.dataset && t.dataset.grams !== undefined) {
    recipe.ingredients[Number(t.dataset.grams)].grams = t.value;
    saveRecipe();
    const chips = document.querySelector(`[data-chips="${t.dataset.grams}"]`);
    if (chips) chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(Number(c.dataset.g) === Number(t.value))));
    recalc();
  } else if (t.id === "rname") {
    recipe.name = t.value; saveRecipe();
    const h = document.querySelector(".headline");
    if (h) h.textContent = t.value || "Your recipe";
    const b = document.querySelector(".backtype");
    if (b) b.textContent = t.value || "Recipe";
    recalc();
  }
});

document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closeSheet(); });
window.addEventListener("hashchange", route);
document.addEventListener("DOMContentLoaded", () => { saveRecipe(); route(); });
