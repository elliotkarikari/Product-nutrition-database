/* ShelfScale page. Plain JavaScript, no build step.
   Every score shown comes from the service; nothing here scores a food.
   Arithmetic here is display only (scaling a value to a chosen portion,
   rounding for reading) and never feeds a score. */
"use strict";

const OLD = "uk-npm-2004/05";
const NEW = "uk-npm-2018";
const STORE = "shelfscale.recipe.v1";
const view = () => document.getElementById("view");

/* ---------- small helpers ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

function fmt(value, unit) {
  if (value === null || value === undefined || Number.isNaN(value)) return "";
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

/* ---------- recipe storage (this browser only) ---------- */
function loadRecipe() {
  try {
    const r = JSON.parse(localStorage.getItem(STORE) || "null");
    if (r && Array.isArray(r.ingredients)) return r;
  } catch (_) { /* storage unavailable or damaged */ }
  return { name: "", servings: 1, ingredients: [], fvn_percent: null, free_sugars_g: null };
}
let recipe = loadRecipe();
function saveRecipe() {
  try { localStorage.setItem(STORE, JSON.stringify(recipe)); } catch (_) { /* private mode: keep in memory */ }
  const n = recipe.ingredients.length;
  document.getElementById("tab-count").textContent = n ? String(n) : "";
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
  if (card.kind === "contributions") return card.html;
  const rows = [
    ["Dataset", card.dataset], ["Edition", card.edition], ["Publisher", card.publisher],
    ["Period", card.period], ["Where in the source", card.locator], ["Rights", card.rights],
    ["Citation", card.citation], ["Record", card.observation_id], ["Replaces", card.supersedes],
    ["Detail", card.detail], ["Note", card.note],
  ].filter(([, v]) => v);
  const link = card.url ? `<p><a href="${esc(card.url)}" rel="noopener" target="_blank">Open the source file</a></p>` : "";
  return `<h2 id="sheet-title">${esc(card.label)}</h2><dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>${link}`;
}

/* ---------- the dual-law ticket ---------- */
function half(model, cls, title, sub) {
  if (model && model.scorable) {
    const less = model.less_healthy;
    return `<div class="half ${cls}">
      <div class="law"><strong>${esc(title)}</strong>${esc(sub)}</div>
      <div class="score" aria-label="Score ${model.score}">${model.score}</div>
      <div class="verdict"><span class="mark" aria-hidden="true">${less ? "&#9632;" : "&#9633;"}</span> ${less ? "Less healthy" : "Not less healthy"}</div>
      <div class="points">${model.total_a} A points, ${model.total_c} C points${model.protein_counted === false ? ". Protein not counted" : ""}</div>
    </div>`;
  }
  let why = "";
  if (model && model.applicable === false) why = model.reason;
  else if (model && model.missing_inputs) why = "Needs: " + model.missing_inputs.map((m) => m.split(" (")[0].split(":")[0].replace(/_/g, " ")).join(", ") + ".";
  return `<div class="half ${cls} unscored">
    <div class="law"><strong>${esc(title)}</strong>${esc(sub)}</div>
    <div class="score">Not scored</div>
    <p class="why">${esc(why)}</p>
  </div>`;
}
function dualTicket(assessment) {
  const m = assessment.models;
  const flips = assessment.verdict_changes_under_2018 === true;
  let key;
  if (flips) key = "Torn ticket: the verdict changes when the 2018 model comes in.";
  else if (assessment.verdict_changes_under_2018 === false) key = "Whole ticket: the same verdict under both models.";
  else key = "One model cannot score this yet, so a change of verdict cannot be checked.";
  return `<div class="dual-wrap">
    ${flips ? '<div class="stamp" aria-hidden="true">Verdict flips</div>' : ""}
    <div class="dual${flips ? " flips" : ""}" role="group" aria-label="Scores under two models">
      ${half(m[OLD], "law-now", "Today's law", "NPM 2004/05, in force")}
      ${half(m[NEW], "law-2018", "The 2018 model", "Shadow score, not in force")}
    </div>
    <p class="flip-key">${esc(key)}</p>
  </div>`;
}

function yours(c) {
  const parts = [];
  if (c && c.fvn_percent !== undefined) parts.push(`fruit, veg and nuts ${fmt(c.fvn_percent, "g")}%`);
  if (c && c.free_sugars_g !== undefined) parts.push(`free sugars ${fmt(c.free_sugars_g, "g")} g per 100 g`);
  return parts.length ? `<p class="flip-key">Scored with your figures: ${esc(parts.join(", "))}. ShelfScale has not checked them.</p>` : "";
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

/* ---------- Look up ---------- */
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
    if (!res.ok) throw new Error(data.error || "Search failed.");
    const items = data.results.map((r) => {
      const meta = [`CoFID ${r.code}`, r.overlay ? "official overlay values" : "", r.portions ? `${r.portions} portion weight${r.portions > 1 ? "s" : ""}` : ""].filter(Boolean).join(", ");
      if (mode === "add") {
        return `<li class="result ticket"><span class="name">${esc(r.name)}</span><span class="meta">${esc(meta)}</span>
          <button class="btn ticket act" type="button" data-add="${esc(r.food_id)}" data-name="${esc(r.name)}">Add</button></li>`;
      }
      return `<li><a class="result ticket" href="#/food/${encodeURIComponent(r.food_id)}"><span class="name">${esc(r.name)}</span><span class="meta">${esc(meta)}</span></a></li>`;
    }).join("");
    box.innerHTML = (items ? `<ul class="results">${items}</ul>` : "") + (data.note ? `<p class="note">${esc(data.note)}</p>` : "");
  } catch (e) {
    if (e.name !== "AbortError") box.innerHTML = `<p class="note">${esc(e.message)}</p>`;
  }
}

function renderLookup() {
  view().innerHTML = `<section class="scene">
    <div class="backtype" aria-hidden="true">Two laws</div>
    <div class="hero-search">
      <h1>One food. Two laws.</h1>
      <p>Every food is scored under the nutrient profiling law in force today and under the 2018 model that may replace it. Search the UK composition tables, see both verdicts, then build a recipe and print its label.</p>
      <div class="searchbox field">
        <label for="q">Search CoFID 2021 foods</label>
        <input class="input" id="q" type="search" autocomplete="off" placeholder="For example: raisins, butter, flour" enterkeyhint="search">
      </div>
      <div id="found"></div>
      <figure class="keyticket" aria-label="How to read a score ticket">
        <div class="dual-wrap">
          <div class="stamp" aria-hidden="true">Verdict flips</div>
          <div class="dual flips">
            <div class="half law-now"><div class="law"><strong>Today's law</strong>NPM 2004/05, in force</div>
              <p class="keytext">The score that decides advertising and promotions now.</p></div>
            <div class="half law-2018"><div class="law"><strong>The 2018 model</strong>Shadow score, not in force</div>
              <p class="keytext">The score the same food gets if the 2018 model is adopted.</p></div>
          </div>
        </div>
        <figcaption class="flip-key">How to read it. Every food gets one ticket with both scores. When the ticket tears, the verdict changes between the two laws.</figcaption>
      </figure>
    </div>
  </section>`;
  const input = document.getElementById("q");
  const go = debounce(() => runSearch(input.value, "found", "view"), 220);
  input.addEventListener("input", go);
  input.focus({ preventScroll: true });
}

/* ---------- Food ---------- */
const foodState = { id: null, portion: null, fvn: "", fs: "", data: null };

function scaled(value, g) { return value === null || value === undefined ? null : value * g / 100; }

function panelTable(food, portionG) {
  const rows = food.panel.map((p) => {
    const sub = p.label.startsWith("of which");
    let v100;
    if (p.value === null) v100 = `<span class="muted">${p.value_kind === "present_not_quantified" ? "present, amount unknown (N)" : "not given"}</span>`;
    else if (p.value_kind === "trace") v100 = "trace";
    else v100 = `${fmt(p.value, p.unit)}<span class="u">${esc(p.unit)}</span>`;
    const per = portionG && p.value !== null && p.value_kind === "number" ? `${fmt(scaled(p.value, portionG), p.unit)}<span class="u">${esc(p.unit)}</span>` : (p.value_kind === "trace" ? "trace" : "");
    return `<tr class="${sub ? "sub" : ""}"><th scope="row">${esc(p.label)}<span class="srcrow">${srcButton(p.source)}</span></th>
      <td class="n">${v100}</td>${portionG ? `<td class="n">${per}</td>` : ""}</tr>`;
  }).join("");
  const basis = food.panel.some((p) => p.basis === "per_100ml") ? "Per 100 ml" : "Per 100 g";
  return `<table class="figures"><thead><tr><th>Nutrient</th><th>${basis}</th>${portionG ? `<th>Per portion, ${grams(portionG)}</th>` : ""}</tr></thead><tbody>${rows}</tbody></table>`;
}

async function loadFood(id) {
  const p = new URLSearchParams();
  if (foodState.portion) p.set("portion_g", String(foodState.portion));
  if (foodState.fvn !== "") p.set("fvn_percent", foodState.fvn);
  if (foodState.fs !== "") p.set("free_sugars_g", foodState.fs);
  return api(`/ui/food/${encodeURIComponent(id)}?${p}`);
}

async function renderFood(id) {
  if (foodState.id !== id) Object.assign(foodState, { id, portion: null, fvn: "", fs: "", data: null });
  sources = [];
  if (!foodState.data) view().innerHTML = `<section class="scene"><p class="note">Loading the food.</p></section>`;
  let food;
  try { food = await loadFood(id); } catch (e) {
    view().innerHTML = `<section class="scene"><h1 class="headline">Food not loaded</h1><p>${esc(e.message)}</p><p><a class="btn ticket" href="#/">Search again</a></p></section>`;
    return;
  }
  if (foodState.portion === null) {
    // Default to a portion someone would eat in one go; tiny unit weights stay one tap away.
    const first = food.portions.find((x) => x.tappable && x.grams >= 10);
    if (first) { foodState.portion = first.grams; food = await loadFood(id).catch(() => food); }
  }
  foodState.data = food;
  const a = food.assessment;
  const g = foodState.portion;
  const tappable = food.portions.filter((x) => x.tappable);
  const listed = food.portions.filter((x) => !x.tappable);
  const chip = (label, value, sub) => `<button class="chip ticket" type="button" data-portion="${value}" aria-pressed="${g === value}">${esc(label)}<small>${esc(sub)}</small></button>`;
  const old = a.models[OLD], neu = a.models[NEW];
  const needsFvn = !old.scorable && (old.missing_inputs || []).some((m) => m.startsWith("fruit_veg_nuts_percent"));
  const fsMissing = neu && neu.scorable === false && neu.applicable !== false;
  const caller = food.caller_supplied || {};

  view().innerHTML = `<section class="scene">
    <div class="backtype" aria-hidden="true">${esc(food.name)}</div>
    <h1 class="headline">${esc(food.name)}</h1>
    <p class="muted small">CoFID ${esc(food.code)}, group ${esc(food.group)}. ${esc(food.description || "")}</p>
    ${dualTicket(a)}
    ${yours(food.caller_supplied)}
    <div class="band">
      <div>
        <h2 class="small muted">Portion</h2>
        <div class="chips">
          ${tappable.map((p) => chip(p.label, p.grams, grams(p.grams))).join("")}
          ${chip("Per 100 g only", 0, "no portion")}
        </div>
        <div class="inline-form noprint">
          <div class="field"><label for="pg">Or weigh it (g)</label><input class="input num" id="pg" type="number" inputmode="decimal" min="0.1" step="any" value="${g && !tappable.some((p) => p.grams === g) ? g : ""}"></div>
          <button class="btn btn-ghost" type="button" data-act="set-portion">Use this weight</button>
        </div>
        ${tappable.length ? `<p class="note">Portion weights: ${tappable.map((p) => srcButton(p.source, `${p.label}, ${p.source.label}`)).join(" ")}</p>` : `<p class="note">No portion weight is on record for this food. Weigh it, or use per 100 g.</p>`}
        ${listed.length ? `<p class="note">Also printed, not offered as one tap: ${listed.map((p) => `${esc(p.label)} ${esc(p.weight_text)} ${srcButton(p.source, "why")}`).join("; ")}</p>` : ""}
      </div>
      ${food.as_sold ? `<div class="flag"><strong>As sold, not made up</strong>${esc(food.as_sold.text)}</div>` : ""}
      ${(needsFvn || fsMissing || caller.fvn_percent !== undefined || caller.free_sugars_g !== undefined) ? `<div class="panel ticket">
        <h2>Your figures</h2>
        <p class="small">CoFID cannot supply these. Anything you enter is labelled as yours in the result.</p>
        <div class="inline-form">
          ${needsFvn || caller.fvn_percent !== undefined ? `<div class="field"><label for="fvn">Fruit, veg and nuts (% of weight)</label><input class="input num" id="fvn" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(foodState.fvn)}"></div>` : ""}
          ${fsMissing || caller.free_sugars_g !== undefined ? `<div class="field"><label for="fs">Free sugars (g per 100 g)</label><input class="input num" id="fs" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(foodState.fs)}"></div>` : ""}
          <button class="btn ticket" type="button" data-act="apply-figures">Score with these</button>
        </div>
        ${fsMissing && neu.free_sugars_note ? `<p class="note">${esc(neu.free_sugars_note)}</p>` : ""}
      </div>` : ""}
      <div class="band two">
        <div class="panel ticket">
          <h2>What is in it</h2>
          ${panelTable(food, g)}
          ${food.salt_from_sodium ? `<p class="note">Salt for traffic lights and scores is sodium x 2.5.</p>` : ""}
          ${food.overlay_values.length ? `<h3>Also measured by an official overlay</h3><table class="figures"><tbody>${food.overlay_values.map((o) => `<tr><th scope="row">${esc(o.label)}<span class="srcrow">${srcButton(o.source)}</span></th><td class="n">${o.value === null ? esc(o.value_text) : `${fmt(o.value, o.unit)}<span class="u">${esc(o.unit)}</span>`}</td></tr>`).join("")}</tbody></table>` : ""}
        </div>
        <div class="panel ticket">
          <h2>Front of pack</h2>
          ${lights(a.traffic_lights, "Traffic lights")}
          ${a.traffic_lights && a.traffic_lights.portion_rule_applied ? `<p class="note">The portion is over 100 g, so the per-portion red rule was checked.</p>` : ""}
          <h3>Add to your recipe</h3>
          <div class="inline-form">
            <div class="field"><label for="addg">Weight (g)</label><input class="input num" id="addg" type="number" inputmode="decimal" min="0.1" step="any" value="${g || 100}"></div>
            <button class="btn ticket" type="button" data-act="add-food">Add to recipe</button>
          </div>
        </div>
      </div>
      <p class="note">${esc(food.evidence_note)} Data release ${esc(food.data_release)}.</p>
    </div>
  </section>`;
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
  const flag = lastResult && lastResult.ingredients.find((x) => x.food_id === item.food_id && x.as_sold);
  return `<li class="ing ticket" data-index="${index}">
    <div class="ing-top"><span class="ing-name">${esc(item.name)}</span>
      <button class="btn btn-ghost" type="button" data-remove="${index}" aria-label="Remove ${esc(item.name)}">Remove</button></div>
    <div class="ing-row">
      <div class="field"><label for="g${index}">Grams as used</label>
        <input class="input num" id="g${index}" type="number" inputmode="decimal" min="0.1" step="any" value="${esc(item.grams)}" data-grams="${index}"></div>
      <div class="chips" data-chips="${index}"></div>
    </div>
    <p class="note${flag ? "" : " hidden"}" data-flag="${esc(item.food_id)}"><strong>As sold.</strong> This is the powder or concentrate as sold. Weigh it dry and add any water or milk as its own ingredient. The score treats it as sold, not made up.</p>
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
  view().innerHTML = `<section class="scene">
    <div class="backtype" aria-hidden="true">${esc(recipe.name || "Recipe")}</div>
    <h1 class="headline">${esc(recipe.name || "Your recipe")}</h1>
    <div id="result-hero"></div>
    <div class="band">
      <div class="inline-form">
        <div class="field"><label for="rname">Recipe name</label><input class="input" id="rname" type="text" maxlength="120" value="${esc(recipe.name)}" placeholder="Name it for the label"></div>
        <div class="field"><label>Servings</label><div class="stepper">
          <button class="btn ticket" type="button" data-act="less" aria-label="Fewer servings">&minus;</button>
          <output id="servings" aria-live="polite">${recipe.servings}</output>
          <button class="btn ticket" type="button" data-act="more" aria-label="More servings">+</button></div></div>
      </div>
      ${items.length ? `<ul class="ingredients">${items.map(ingredientHtml).join("")}</ul>` : `<div class="panel ticket empty"><h2>No ingredients yet</h2><p>Search below and add what goes in. Weights stay in this browser only.</p></div>`}
      <div class="adder panel ticket">
        <div class="field"><label for="addq">Add an ingredient</label><input class="input" id="addq" type="search" autocomplete="off" placeholder="Search CoFID foods" enterkeyhint="search"></div>
        <div id="addfound"></div>
      </div>
      <div id="result-detail"></div>
      ${items.length ? `<p><button class="btn btn-ghost" type="button" data-act="clear">Start a new recipe</button></p>` : ""}
    </div>
  </section>`;
  const q = document.getElementById("addq");
  q.addEventListener("input", debounce(() => runSearch(q.value, "addfound", "add"), 220));
  paintResult();
  paintChips();
  recalc();
}

function contributionsCard(name, label, unit) {
  const rows = (lastResult.contributions[name] || []);
  const html = `<h2 id="sheet-title">${esc(label)} in this recipe</h2>
    <p class="small">Each ingredient's value per 100 g, scaled by its weight. Then the sum is divided by the total raw weight, ${grams(lastResult.total_g)}.</p>
    <table class="figures"><thead><tr><th>Ingredient</th><th>Per 100 g</th><th>In recipe</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><th scope="row">${esc(r.name)}, ${grams(r.grams)}<span class="srcrow muted small">${esc(r.source.label)}, ${esc(r.source.observation_id)}</span></th><td class="n">${fmt(r.per_100g, unit)}</td><td class="n">${fmt(r.amount, unit)}<span class="u">${esc(unit)}</span></td></tr>`).join("")}
    </tbody></table>`;
  return { kind: "contributions", label, html };
}

const REQUIRED = ["energy_kj", "fat_g", "saturated_fat_g", "total_sugars_g", "protein_g", "sodium_mg"];
function paintResult() {
  const hero = document.getElementById("result-hero");
  const detail = document.getElementById("result-detail");
  if (!hero || !detail) return;
  sources = [];
  if (resultError) { hero.innerHTML = `<div class="flag"><strong>Not calculated</strong>${esc(resultError)}</div>`; detail.innerHTML = ""; return; }
  if (!lastResult) { hero.innerHTML = ""; detail.innerHTML = ""; return; }
  const r = lastResult;
  const a = r.assessment;
  const old = a.models[OLD], neu = a.models[NEW];
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
  hero.innerHTML = `${dualTicket(a)}${yours(mine)}
    <p class="muted small">${grams(r.total_g)} in all, ${r.servings} serving${r.servings > 1 ? "s" : ""} of ${grams(r.serving_g)}. ${esc(r.yield_note)}</p>`;
  detail.innerHTML = `
    <div class="panel ticket">
      <h2>Your figures</h2>
      <p class="small">CoFID cannot supply these for a recipe. What you enter is labelled as yours.</p>
      <div class="inline-form">
        <div class="field"><label for="rfvn">Fruit, veg and nuts (% of weight)</label><input class="input num" id="rfvn" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(recipe.fvn_percent ?? "")}"></div>
        <div class="field"><label for="rfs">Free sugars (g per 100 g)</label><input class="input num" id="rfs" type="number" inputmode="decimal" min="0" max="100" step="any" value="${esc(recipe.free_sugars_g ?? "")}"></div>
      </div>
      ${fvnNeeded ? `<p class="note">Today's law needs this. Fruit, vegetable and nut ingredients make up ${fmt(known.share_of_weight_percent, "%")}% of the weight; the rest have no value under the group rule, so ShelfScale will not assume one.</p>` : ""}
      ${r.fruit_veg_nuts.source === "derived_from_ingredients" ? `<p class="note">Fruit, veg and nuts: ${fmt(r.fruit_veg_nuts.value, "%")}%, worked out from the ingredients by group.</p>` : ""}
      ${neu.free_sugars_note ? `<p class="note">${esc(neu.free_sugars_note)}</p>` : ""}
    </div>
    ${r.review_flags.length ? `<div class="flag"><strong>Check before relying on it</strong>${r.review_flags.map((f) => `${esc(f.ingredient)}: ${esc(f.reason)}`).join("<br>")}</div>` : ""}
    <div class="band two">
      <div class="panel ticket">
        <h2>Per 100 g and per serving</h2>
        <table class="figures"><thead><tr><th>Nutrient</th><th>Per 100 g</th><th>Per serving, ${grams(r.serving_g)}</th></tr></thead><tbody>
        ${rows.map(([k, label, unit]) => {
          const v = r.per_100g[k];
          const card = contributionsCard(k, label, unit);
          sources.push(card);
          const btn = `<button class="src" type="button" data-src="${sources.length - 1}">Where from</button>`;
          if (v === undefined) return `<tr><th scope="row">${esc(label)}<span class="srcrow">${btn}</span></th><td class="n muted" colspan="2">not recorded for every ingredient</td></tr>`;
          return `<tr class="${label.startsWith("of which") ? "sub" : ""}"><th scope="row">${esc(label)}<span class="srcrow">${btn}</span></th><td class="n">${fmt(v, unit)}<span class="u">${unit}</span></td><td class="n">${fmt(r.per_serving[k], unit)}<span class="u">${unit}</span></td></tr>`;
        }).join("")}
        </tbody></table>
        <p class="note">These are the CoFID values the scores use. The label converts them to the declaration's conventions.</p>
      </div>
      <div class="panel ticket">
        <h2>Front of pack, per serving</h2>
        ${a.traffic_lights ? lights(a.traffic_lights, "Traffic lights") : `<p class="note">Traffic lights need fat, saturates, sugars and salt for every ingredient.</p>`}
        ${a.traffic_lights ? `<p class="note">Colours follow per 100 g; a serving over 100 g is also checked against the per-portion red limits. Serving: ${grams(r.serving_g)}.</p>` : ""}
        <p><a class="btn ticket" href="#/label">Get the label</a></p>
      </div>
    </div>`;
  const keep = (id, field) => {
    const el = document.getElementById(id);
    el.addEventListener("change", () => { recipe[field] = el.value === "" ? null : el.value; saveRecipe(); recalc(); });
  };
  keep("rfvn", "fvn_percent");
  keep("rfs", "free_sugars_g");
  document.querySelectorAll("[data-flag]").forEach((el) => {
    const sold = r.ingredients.some((x) => x.food_id === el.dataset.flag && x.as_sold);
    el.classList.toggle("hidden", !sold);
  });
}

/* ---------- Label ---------- */
function declRows(r) {
  const L = r.label;
  const pick = (side, key) => L[side].find((x) => x.key === key);
  const cell = (row) => row.display === null ? "n/a" : `${row.display} ${row.unit}`;
  const lines = [
    ["Energy", (s) => `${cell(pick(s, "energy_kj"))} / ${cell(pick(s, "energy_kcal"))}`, false],
    ["Fat", (s) => cell(pick(s, "fat_g")), false],
    ["of which saturates", (s) => cell(pick(s, "saturates_g")), true],
    ["Carbohydrate", (s) => cell(pick(s, "carbohydrate_g")), false],
    ["of which sugars", (s) => cell(pick(s, "sugars_g")), true],
    ["Protein", (s) => cell(pick(s, "protein_g")), false],
    ["Salt", (s) => cell(pick(s, "salt_g")), false],
  ];
  return lines.map(([name, f, sub]) => ({ name, sub, per100: f("per_100g"), serving: f("per_serving") }));
}

async function renderLabel() {
  sources = [];
  if (recipe.ingredients.length && !lastResult) {
    view().innerHTML = `<section class="scene"><p class="note">Calculating the recipe.</p></section>`;
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
  view().innerHTML = `<section class="scene">
    <div class="backtype noprint" aria-hidden="true">Label</div>
    <h1 class="headline noprint">${esc(r.name || "Your recipe")}</h1>
    <div class="decl" id="decl">
      <table>
        <caption>Nutrition</caption>
        <thead><tr><th>Typical values</th><th>Per 100 g</th><th>Per portion (${esc(grams(r.serving_g))})</th></tr></thead>
        <tbody>${rows.map((x) => `<tr class="${x.sub ? "sub" : ""}"><td>${esc(x.name)}</td><td>${esc(x.per100)}</td><td>${esc(x.serving)}</td></tr>`).join("")}</tbody>
        <tfoot><tr><td colspan="3">This pack makes ${r.servings} portion${r.servings > 1 ? "s" : ""}. ${esc(L.statement)}</td></tr></tfoot>
      </table>
    </div>
    <div class="label-actions noprint">
      <button class="btn ticket" type="button" data-act="print">Print the label</button>
      <button class="btn ticket" type="button" data-act="copy">Copy as text</button>
      <span id="copied" class="note" role="status"></span>
    </div>
    <div class="panel ticket noprint">
      <h2>How these figures were made</h2>
      <p class="small">Carbohydrate and sugars are converted from CoFID's monosaccharide equivalents to weight, protein is total nitrogen x 6.25, and energy uses the Regulation's factors, all as the CoFID user guide sets out. ${esc(L.method)}.</p>
      <p class="small">Rounding: ${esc(L.rounding)}. Per 100 g and per portion are rounded separately from unrounded values.</p>
      ${missing.length ? `<div class="flag"><strong>Not declared</strong>${missing.map((k) => `${esc(k.replace(/_g$/, "").replace(/_/g, " "))}: not recorded for ${esc(L.missing[k].join(", "))}`).join("<br>")}</div>` : ""}
      ${excl.length ? `<div class="flag"><strong>Energy leaves out</strong>${excl.map(([part, names]) => `${esc(part)} for ${esc(names.join(", "))}, because CoFID records no value`).join("<br>")}</div>` : ""}
      <p class="small">${esc(r.yield_note)} Data release ${esc(r.data_release)}.</p>
    </div>
  </section>`;
}

function labelText() {
  const r = lastResult;
  const rows = declRows(r);
  return [`Nutrition${r.name ? `: ${r.name}` : ""}`, `Typical values\tPer 100 g\tPer portion (${grams(r.serving_g)})`,
    ...rows.map((x) => `${x.sub ? "  " : ""}${x.name}\t${x.per100}\t${x.serving}`),
    `This pack makes ${r.servings} portion${r.servings > 1 ? "s" : ""}. ${r.label.statement}`].join("\n");
}

/* ---------- routing and events ---------- */
function route() {
  const hash = location.hash || "#/";
  let tab = "lookup";
  closeSheet();
  if (hash.startsWith("#/food/")) renderFood(decodeURIComponent(hash.slice(7)));
  else if (hash === "#/recipe") { tab = "recipe"; renderRecipe(); }
  else if (hash === "#/label") { tab = "label"; renderLabel(); }
  else renderLookup();
  document.querySelectorAll(".tabs a").forEach((a) => {
    if (a.dataset.tab === tab) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  window.scrollTo(0, 0);
}

function addIngredient(food_id, name, g) {
  recipe.ingredients.push({ food_id, name, grams: g });
  saveRecipe();
}

document.addEventListener("click", async (ev) => {
  const t = ev.target.closest("button, [data-close]");
  if (!t) return;
  if (t.hasAttribute("data-close")) { closeSheet(); return; }
  if (t.dataset.src !== undefined) { openSheet(sourceHtml(sources[Number(t.dataset.src)])); return; }
  if (t.dataset.portion !== undefined) {
    foodState.portion = Number(t.dataset.portion) || 0;
    if (!foodState.portion) foodState.portion = 0;
    renderFood(foodState.id); return;
  }
  if (t.dataset.add) {
    const ps = await portionsFor(t.dataset.add);
    const usual = ps.find((p) => p.grams >= 10);
    addIngredient(t.dataset.add, t.dataset.name, usual ? usual.grams : 100);
    renderRecipe();
    const idx = recipe.ingredients.length - 1;
    const el = document.getElementById(`g${idx}`);
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
    case "set-portion": {
      const v = Number(document.getElementById("pg").value);
      if (v > 0) { foodState.portion = v; renderFood(foodState.id); }
      break;
    }
    case "apply-figures": {
      const f = document.getElementById("fvn"), s = document.getElementById("fs");
      if (f) foodState.fvn = f.value;
      if (s) foodState.fs = s.value;
      renderFood(foodState.id);
      break;
    }
    case "add-food": {
      const v = Number(document.getElementById("addg").value);
      if (v > 0 && foodState.data) { addIngredient(foodState.data.food_id, foodState.data.name, v); location.hash = "#/recipe"; }
      break;
    }
    case "less": case "more": {
      recipe.servings = Math.min(1000, Math.max(1, recipe.servings + (t.dataset.act === "more" ? 1 : -1)));
      document.getElementById("servings").textContent = recipe.servings;
      saveRecipe(); recalc(); break;
    }
    case "clear":
      if (window.confirm("Start a new recipe? This removes the current one from this browser.")) {
        recipe = { name: "", servings: 1, ingredients: [], fvn_percent: null, free_sugars_g: null };
        lastResult = null; saveRecipe(); renderRecipe();
      }
      break;
    case "print": window.print(); break;
    case "copy": {
      const text = labelText();
      const status = document.getElementById("copied");
      try { await navigator.clipboard.writeText(text); status.textContent = "Copied."; }
      catch (_) {
        const ta = document.createElement("textarea");
        ta.value = text; document.body.appendChild(ta); ta.select();
        status.textContent = document.execCommand("copy") ? "Copied." : "Copy is blocked here. Select the label and copy it.";
        ta.remove();
      }
      break;
    }
    default: break;
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
