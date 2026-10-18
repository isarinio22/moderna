/* Your Tumor, Your Vaccine — interactive figures.
   Vanilla JS, no build step, no framework. Every chart is inline SVG drawn from
   the JSON the pipeline exported, so what you see is what the code produced. */
'use strict';

const DATA = {};
const FILES = ['manifest', 'funnel', 'epitopes', 'panels', 'construct', 'evidence'];

const GLOSSARY = {
  neoantigen: ['Neoantigen', 'A protein fragment that exists only because of a mutation in the tumor. Healthy cells never make it, which is what lets the immune system treat it as foreign.'],
  tcell: ['T cell', 'A white blood cell that inspects the fragments other cells display, and kills cells showing something it has been trained to recognise as wrong.'],
  hla: ['HLA', 'The molecules that hold protein fragments up on a cell surface for inspection. Yours are inherited and highly variable, and each one can only grip fragments of a particular shape.'],
  mrna: ['mRNA', 'A temporary instruction sheet copied from DNA. Cells read it to build a protein, then destroy it. A vaccine made this way never enters the cell nucleus and does not change your DNA.'],
  hazard: ['Hazard ratio', 'A comparison of how fast something is happening in two groups. 0.51 means that at any moment, the vaccine group was recurring at about half the rate of the other group.'],
  rfs: ['Recurrence-free survival', 'How long someone goes after surgery without the cancer coming back. It is not the same as how long they live.'],
  nnt: ['Number needed to treat', 'How many people would have to receive a treatment for one extra person to benefit. Smaller is better.'],
  checkpoint: ['Checkpoint inhibitor', 'A drug like pembrolizumab that blocks the "stand down" signal tumors use to switch off T cells. It does not teach the immune system anything; it stops the brakes being applied.'],
  affinity: ['Binding strength', 'How tightly a fragment is gripped by an HLA molecule, in nanomolar. Lower numbers mean a tighter grip and a better chance of being displayed.'],
  agreto: ['Mutant advantage', 'How much better the mutated fragment binds than its normal version. If both bind equally well, the immune system has no way to tell them apart, so it is a poor target.']
};

/* ---------- tiny helpers ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, kids = []) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k === 'text') n.textContent = v;
    else n.setAttribute(k, v);
  }
  (Array.isArray(kids) ? kids : [kids]).forEach(c => c && n.appendChild(c));
  return n;
};
const svg = (tag, attrs = {}, kids = []) => {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'text') n.textContent = v; else n.setAttribute(k, v);
  }
  (Array.isArray(kids) ? kids : [kids]).forEach(c => c && n.appendChild(c));
  return n;
};
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const pct = x => `${(x * 100).toFixed(1)}%`;
const fmt = (x, d = 2) => Number(x).toFixed(d);

/* A chart container that announces itself properly to a screen reader. */
function chart(width, height, label) {
  const s = svg('svg', {
    viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': label,
    preserveAspectRatio: 'xMidYMid meet'
  });
  s.appendChild(svg('title', { text: label }));
  return s;
}

/* ---------- tooltips ---------- */
function initTooltips() {
  const tip = $('#tip');
  let open = null;
  const show = (btn) => {
    const entry = GLOSSARY[btn.dataset.term];
    if (!entry) return;
    tip.innerHTML = '';
    tip.appendChild(el('span', { class: 't', text: entry[0] }));
    tip.appendChild(document.createTextNode(entry[1]));
    tip.dataset.open = 'true';
    tip.setAttribute('aria-hidden', 'false');
    const r = btn.getBoundingClientRect();
    const w = Math.min(336, window.innerWidth * 0.88);
    tip.style.width = w + 'px';
    let left = r.left + window.scrollX + r.width / 2 - w / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - w - 8));
    tip.style.left = left + 'px';
    tip.style.top = (r.bottom + window.scrollY + 8) + 'px';
    open = btn;
  };
  const hide = () => { tip.dataset.open = 'false'; tip.setAttribute('aria-hidden', 'true'); open = null; };

  document.addEventListener('click', e => {
    const btn = e.target.closest('.term');
    if (btn) { e.preventDefault(); open === btn ? hide() : show(btn); }
    else if (!e.target.closest('#tip')) hide();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') hide(); });
  document.addEventListener('mouseover', e => {
    const btn = e.target.closest('.term');
    if (btn && window.matchMedia('(hover: hover)').matches) show(btn);
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest('.term') && window.matchMedia('(hover: hover)').matches) hide();
  });
  document.querySelectorAll('.term').forEach(b => {
    b.setAttribute('type', 'button');
    b.setAttribute('aria-label', `${b.textContent}: show definition`);
  });
}

function initTheme() {
  const btn = $('#theme-toggle');
  const stored = (() => { try { return localStorage.getItem('theme'); } catch { return null; } })();
  if (stored) document.documentElement.dataset.theme = stored;
  btn.addEventListener('click', () => {
    const dark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const current = document.documentElement.dataset.theme || (dark ? 'dark' : 'light');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch { /* private mode */ }
    redraw();
  });
}

/* ================= figures ================= */

/* How the two drugs do different jobs. */
function drawConcept() {
  const W = 760, H = 210;
  const s = chart(W, H, 'Four steps: the tumor mutates, the vaccine teaches the immune system those mutations, T cells hunt for them, and a checkpoint inhibitor stops the tumor switching those T cells off.');
  const steps = [
    ['Tumor mutates', 'proteins change shape', css('--muted-series')],
    ['Vaccine teaches', 'those mutations, as wanted posters', css('--combo')],
    ['T cells hunt', 'now they know what to look for', css('--accent')],
    ['Brakes released', 'pembrolizumab stops the shutdown', css('--control')]
  ];
  const w = 172, gap = (W - steps.length * w) / (steps.length - 1);
  steps.forEach(([title, sub, colour], i) => {
    const x = i * (w + gap);
    s.appendChild(svg('rect', { x, y: 42, width: w, height: 112, rx: 14, fill: colour, opacity: .14, stroke: colour, 'stroke-width': 2 }));
    s.appendChild(svg('circle', { cx: x + 26, cy: 70, r: 14, fill: colour }));
    s.appendChild(svg('text', { x: x + 26, y: 75, 'text-anchor': 'middle', fill: '#fff', 'font-size': 15, 'font-weight': 700, text: String(i + 1) }));
    const titleSize = textWidth(title, 16, 700) > w - 26 ? 14.5 : 16;
    s.appendChild(svg('text', { x: x + 14, y: 108, fill: css('--fg'), 'font-size': titleSize, 'font-weight': 700, text: title }));
    wrapText(s, sub, x + 14, 128, w - 26, 13, css('--fg-muted'));
    if (i < steps.length - 1) {
      const ax = x + w + gap / 2;
      s.appendChild(svg('path', { d: `M${x + w + 5} 98 L${ax + 9} 98`, stroke: css('--rule'), 'stroke-width': 2.5, 'marker-end': 'url(#arrow)' }));
    }
  });
  const defs = svg('defs', {}, svg('marker', { id: 'arrow', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 5, markerHeight: 5, orient: 'auto' },
    svg('path', { d: 'M0 0 L10 5 L0 10 z', fill: css('--rule') })));
  s.insertBefore(defs, s.firstChild);
  mount('#fig-concept', s);
  $('#cap-concept').textContent = 'The vaccine and the antibody solve different problems. One teaches the immune system what to look for; the other stops the tumor switching it off. Neither alone is the whole story.';
}

/* Text measurement.
   getComputedTextLength() only works once an element is in the rendered
   document, and these charts are built detached and mounted afterwards -- it
   returns 0 and nothing ever wraps. A 2D canvas measures the same font without
   needing to be attached to anything. */
const _measureCtx = document.createElement('canvas').getContext('2d');
function textWidth(text, size, weight = 400) {
  _measureCtx.font = `${weight} ${size}px ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`;
  return _measureCtx.measureText(text).width;
}

function wrapText(parent, text, x, y, maxWidth, size, fill) {
  const words = text.split(' ');
  const lines = [];
  let line = [];
  words.forEach(word => {
    const candidate = [...line, word].join(' ');
    if (line.length && textWidth(candidate, size) > maxWidth) {
      lines.push(line.join(' '));
      line = [word];
    } else {
      line.push(word);
    }
  });
  if (line.length) lines.push(line.join(' '));
  lines.forEach((content, i) => {
    parent.appendChild(svg('text', {
      x, y: y + i * size * 1.3, fill, 'font-size': size, text: content
    }));
  });
  return lines.length;
}

/* Sliding window over a real selected epitope. */
let windowState = { idx: 0 };
function drawWindow() {
  const eps = DATA.epitopes.epitopes.filter(e => e.sel);
  const ep = eps[windowState.idx % eps.length];
  const W = 760, H = 210;
  const s = chart(W, H, `A protein from the gene ${ep.gene}. The mutation changes one letter, and every short fragment covering that letter becomes a possible target. The fragment shown is ${ep.mut}, which differs from the normal version ${ep.wt} at one position.`);

  const n = ep.mut.length;
  const boxW = Math.min(52, (W - 120) / (n + 1));
  const startX = (W - boxW * n) / 2;

  s.appendChild(svg('text', { x: W / 2, y: 24, 'text-anchor': 'middle', fill: css('--fg-muted'), 'font-size': 14, text: `${ep.gene} — position ${ep.pos} in the protein` }));

  [['normal', ep.wt, 48, css('--muted-series')], ['mutated', ep.mut, 118, css('--combo')]].forEach(([label, seq, y, colour]) => {
    s.appendChild(svg('text', { x: startX - 10, y: y + boxW * 0.62, 'text-anchor': 'end', fill: css('--fg-muted'), 'font-size': 12, text: label }));
    [...seq].forEach((ch, i) => {
      const isMut = i === ep.offset - 1;
      s.appendChild(svg('rect', {
        x: startX + i * boxW, y, width: boxW - 3, height: boxW, rx: 5,
        fill: isMut ? colour : 'none', opacity: isMut ? 1 : 1,
        stroke: isMut ? colour : css('--rule'), 'stroke-width': isMut ? 2 : 1
      }));
      s.appendChild(svg('text', {
        x: startX + i * boxW + (boxW - 3) / 2, y: y + boxW * 0.66, 'text-anchor': 'middle',
        'font-size': 17, 'font-weight': isMut ? 700 : 500,
        fill: isMut ? '#fff' : css('--fg'), 'font-family': 'ui-monospace, monospace', text: ch
      }));
    });
  });

  s.appendChild(svg('text', { x: W / 2, y: 196, 'text-anchor': 'middle', fill: css('--fg-muted'), 'font-size': 13.5,
    text: `one letter differs — and that is the entire basis of the target` }));
  mount('#fig-window', s);
  $('#cap-window').textContent = `A real example from the pipeline: ${ep.gene}, fragment ${ep.mut}, displayed by ${ep.allele.replace('HLA-','HLA ')}. It binds at ${ep.nm} nM; the normal version binds at ${ep.wt_nm ?? '—'} nM.`;

  const ctr = $('#window-controls');
  if (!ctr.childElementCount) {
    const seg = el('div', { class: 'seg', role: 'group', 'aria-label': 'Choose an example fragment' });
    const prev = el('button', { type: 'button', text: '‹ previous' });
    const next = el('button', { type: 'button', text: 'another example ›' });
    prev.onclick = () => { windowState.idx = (windowState.idx - 1 + eps.length) % eps.length; drawWindow(); };
    next.onclick = () => { windowState.idx = (windowState.idx + 1) % eps.length; drawWindow(); };
    seg.append(prev, next);
    ctr.appendChild(seg);
  }
}

/* How much the chosen set changes with HLA type. */
function drawPanels() {
  const p = DATA.panels;
  const names = Object.keys(p.panels).sort();
  const pretty = n => n.replace('common_', '').replace('_', ' ');

  $('#panel-stats').innerHTML = '';
  const total = p.panels[names[0]].selected.length;
  [[p.overlap.shared_by_all, `of ${total} targets shared by all three`],
   [total - p.overlap.shared_by_all, 'change with immune type'],
   [names.length, 'HLA sets compared']
  ].forEach(([v, k]) => {
    $('#panel-stats').appendChild(el('div', { class: 'stat' }, [
      el('div', { class: 'v', text: String(v) }), el('div', { class: 'k', text: k })
    ]));
  });

  const W = 760, rowH = 60, H = names.length * rowH + 62;
  const s = chart(W, H, `Each row is one set of HLA types. Of ${total} targets chosen for each, only ${p.overlap.shared_by_all} are shared by all three sets, from the identical tumor.`);
  const all = new Set();
  names.forEach(n => p.panels[n].selected.forEach(e => all.add(e.id)));
  const ids = [...all].sort();
  const cellW = (W - 150) / ids.length;

  names.forEach((name, r) => {
    const y = 34 + r * rowH;
    const chosen = new Set(p.panels[name].selected.map(e => e.id));
    s.appendChild(svg('text', { x: 0, y: y + 18, fill: css('--fg'), 'font-size': 15, 'font-weight': 650, text: pretty(name) }));
    s.appendChild(svg('text', { x: 0, y: y + 36, fill: css('--fg-muted'), 'font-size': 12, text: `${chosen.size} targets` }));
    ids.forEach((id, i) => {
      const inAll = names.every(n => p.panels[n].selected.some(e => e.id === id));
      s.appendChild(svg('rect', {
        x: 150 + i * cellW, y: y + 2, width: Math.max(1.5, cellW - 1.2), height: 26, rx: 2,
        fill: chosen.has(id) ? (inAll ? css('--accent') : css('--combo')) : css('--rule'),
        opacity: chosen.has(id) ? 1 : .35
      }));
    });
  });
  s.appendChild(svg('text', { x: 150, y: H - 10, fill: css('--fg-muted'), 'font-size': 12.5, text: `each column is one possible target — ${ids.length} distinct targets across all three sets` }));
  mount('#fig-panels', s);

  const pairs = Object.entries(p.overlap.pairwise)
    .map(([k, v]) => `${pretty(k.split('|')[0])} and ${pretty(k.split('|')[1])} share ${v}`).join('; ');
  $('#cap-panels').textContent = `Green marks a target chosen for every HLA set; orange marks one chosen for only some. ${pairs}. The tumor is identical in all three runs — only the immune genetics differ.`;
  $('#hla-assumption').innerHTML = `<strong>An assumption, not a result.</strong> ${DATA.manifest.hla.assumption}`;
}

const REASON_LABELS = {
  gate_presentation_percentile: 'would not be displayed well enough',
  gate_affinity: 'binds too weakly to be held up',
  rank_cutoff: 'outscored by other fragments',
  mutation_cap: 'another fragment from the same mutation scored higher',
  gene_cap: 'already two fragments from this gene',
  mutation_type_excluded: 'not a simple protein change',
  variant_type_excluded: 'not a single-letter change',
  not_a_simple_substitution: 'not a simple protein change',
  duplicate_call: 'the same mutation listed twice',
  over_max_mutations: 'beyond the per-sample limit',
  no_gene_symbol: 'no gene name',
  unparseable_record: 'the record could not be read',
  no_accession: 'no protein sequence could be found',
  mismatch: 'the protein sequence disagreed with the mutation',
  position_out_of_range: 'the position falls outside the protein',
  no_sequence: 'no protein sequence available',
  sequence_too_short: 'the protein is shorter than the fragment'
};
const reasonLabel = r => REASON_LABELS[r] || r.replace(/_/g, ' ');

/* The narrowing, with the discards. */
function drawFunnel() {
  const root = $('#funnel');
  root.innerHTML = '';
  const max = Math.max(...DATA.funnel.map(s => Math.max(s.n_in, s.n_out)));
  const scale = v => Math.max(2, (Math.log10(v + 1) / Math.log10(max + 1)) * 100);

  DATA.funnel.forEach(step => {
    const reasons = Object.entries(step.reasons).sort((a, b) => b[1] - a[1]);
    const lost = step.n_in - step.n_out;
    const wrapEl = el('div', { class: 'funnel-step' });
    wrapEl.appendChild(el('div', {}, [
      el('strong', { text: step.step }),
      el('span', { class: 'funnel-meta', text: ` — ${step.label}` })
    ]));
    const bar = el('div', { class: 'funnel-bar' });
    bar.appendChild(el('div', {
      class: 'funnel-fill',
      style: `width:${scale(step.n_out)}%`,
      text: step.n_out.toLocaleString()
    }));
    wrapEl.appendChild(bar);
    const meta = el('div', { class: 'funnel-meta' });
    if (lost > 0 && reasons.length) {
      meta.textContent = `${lost.toLocaleString()} discarded — ` +
        reasons.slice(0, 3).map(([r, c]) => `${c.toLocaleString()} ${reasonLabel(r)}`).join('; ');
    } else if (step.n_out > step.n_in) {
      meta.textContent = `each mutation produces many overlapping fragments`;
    } else {
      meta.textContent = `${step.n_in.toLocaleString()} in, ${step.n_out.toLocaleString()} out`;
    }
    wrapEl.appendChild(meta);
    root.appendChild(wrapEl);
  });
}

/* Live re-ranking. */
const weights = { presentation: 0.40, agretopicity: 0.25, expression: 0.25, quality: 0.10 };
const WEIGHT_LABELS = {
  presentation: ['Will it be displayed?', 'affinity'],
  agretopicity: ['Better than normal?', 'agreto'],
  expression: ['Is the gene switched on?', null],
  quality: ['Is the peptide awkward?', null]
};

function drawWeights() {
  const root = $('#weights');
  if (root.childElementCount) return;
  Object.entries(WEIGHT_LABELS).forEach(([key, [label, term]]) => {
    const row = el('div', { class: 'slider-row' });
    const name = el('label', { for: `w-${key}` });
    name.appendChild(document.createTextNode(label));
    if (term) {
      const b = el('button', { class: 'term', type: 'button', 'data-term': term, text: ' \u24D8' });
      b.setAttribute('aria-label', `${label}: show definition`);
      name.appendChild(b);
    }
    const input = el('input', {
      type: 'range', id: `w-${key}`, min: '0', max: '100', step: '5',
      value: String(Math.round(weights[key] * 100))
    });
    const out = el('span', { class: 'n', text: pct(weights[key]) });
    input.addEventListener('input', () => {
      weights[key] = Number(input.value) / 100;
      out.textContent = pct(weights[key]);
      drawRanking();
    });
    row.append(name, input, out);
    root.appendChild(row);
  });
}

function drawRanking() {
  const sum = Object.values(weights).reduce((a, b) => a + b, 0) || 1;
  const scored = DATA.epitopes.epitopes.map(e => ({
    ...e,
    live: (e.c.presentation * weights.presentation + e.c.agretopicity * weights.agretopicity
         + e.c.expression * weights.expression + e.c.quality * weights.quality) / sum
  }));
  // Mirror the pipeline: gated candidates can never be chosen, one per mutation.
  const eligible = scored.filter(e => !e.why_not || !e.why_not.startsWith('gate'));
  eligible.sort((a, b) => b.live - a.live || a.gene.localeCompare(b.gene) || a.id.localeCompare(b.id));
  const seenMut = new Set(), seenGene = new Map(), top = [];
  for (const e of eligible) {
    const mutId = e.id.split('|')[0];
    if (seenMut.has(mutId)) continue;
    if ((seenGene.get(e.gene) || 0) >= 2) continue;
    seenMut.add(mutId); seenGene.set(e.gene, (seenGene.get(e.gene) || 0) + 1);
    top.push(e);
    if (top.length === 34) break;
  }

  const t = $('#epitope-table');
  t.innerHTML = '';
  t.appendChild(el('caption', { class: 'sr-only', text: 'The thirty-four fragments selected under the current weighting' }));
  const head = el('tr');
  ['#', 'gene', 'fragment', 'normal', 'displayed by', 'binding (nM)', 'mutant advantage', 'score']
    .forEach((h, i) => head.appendChild(el('th', { class: i >= 5 ? 'num' : '', scope: 'col', text: h })));
  t.appendChild(el('thead', {}, head));

  const body = el('tbody');
  top.slice(0, 12).forEach((e, i) => {
    const row = el('tr', { class: 'sel' });
    row.append(
      el('td', { class: 'num', text: String(i + 1) }),
      el('td', { text: e.gene }),
      el('td', { class: 'mono', html: highlight(e.mut, e.offset) }),
      el('td', { class: 'mono', text: e.wt }),
      el('td', { text: e.allele.replace('HLA-', '') }),
      el('td', { class: 'num', text: e.nm == null ? '—' : fmt(e.nm, 0) }),
      el('td', { class: 'num', text: e.agreto == null ? '—' : `${fmt(e.agreto, 1)}×` }),
      el('td', { class: 'num', text: fmt(e.live, 3) })
    );
    body.appendChild(row);
  });
  t.appendChild(body);

  const changed = top.slice(0, 34).filter(e => !e.sel).length;
  $('#cap-rank').textContent =
    `Showing the top 12 of 34, chosen from ${DATA.epitopes.total_candidates.toLocaleString()} candidates. `
    + `The highlighted letter is the mutation. "Mutant advantage" is how much more tightly the mutated fragment binds than the normal one — above 1 is good, around 1 means the immune system may not be able to tell them apart. `
    + (changed ? `Under this weighting, ${changed} of the 34 differ from the pipeline's default choice.` : `This weighting reproduces the pipeline's default choice exactly.`);
}

function highlight(seq, offset) {
  return [...seq].map((ch, i) =>
    i === offset - 1 ? `<strong style="color:var(--combo)">${ch}</strong>` : ch).join('');
}

/* The construct, as a clickable map. */
function drawConstruct() {
  const c = DATA.construct;
  const map = $('#construct-map');
  map.innerHTML = '';
  const colours = {
    cap: css('--accent'), utr: css('--control'), kozak: css('--muted-series'),
    epitope: css('--combo'), linker: css('--rule'), stop: css('--muted-series'),
    polya: css('--warn')
  };
  c.blocks.filter(b => b.nt > 0).forEach(b => {
    const btn = el('button', {
      type: 'button',
      style: `flex:${b.nt} 0 0;background:${colours[b.kind] || css('--rule')}`,
      title: `${b.name} — ${b.nt} nt`,
      'aria-label': `${b.name}, ${b.nt} nucleotides`
    });
    btn.onclick = () => showBlock(b);
    map.appendChild(btn);
  });
  const cap = c.blocks.find(b => b.kind === 'cap');
  $('#cap-construct').textContent =
    `${c.total_nt.toLocaleString()} letters in total, ${c.cds_nt.toLocaleString()} of them coding for the 34 fragments. `
    + `Select any region to read what it does. The 5' cap is drawn as a label with no width because it is a chemical modification, not a letter.`;
  showBlock(c.blocks.find(b => b.kind === 'epitope') || c.blocks[0]);
  $('#construct-disclaimer').innerHTML = `<strong>Conceptual only.</strong> ${c.disclaimer}`;
  if (cap) $('#block-detail').dataset.capNote = cap.note;
}

function showBlock(b) {
  const d = $('#block-detail');
  d.innerHTML = '';
  d.appendChild(el('h3', { text: b.name }));
  d.appendChild(el('p', { style: 'margin:.2rem 0 .6rem;color:var(--fg-muted);font-size:.88rem',
    text: `${b.nt.toLocaleString()} nucleotides${b.aa ? ` · protein: ${b.aa}` : ''}` }));
  d.appendChild(el('p', { style: 'margin:0', text: b.note }));
}

/* Kaplan–Meier curves. */
function drawKM() {
  const ev = DATA.evidence;
  const W = 760, H = 420, M = { t: 18, r: 18, b: 50, l: 58 };
  const maxT = 66;
  const x = t => M.l + (t / maxT) * (W - M.l - M.r);
  const y = s => M.t + (1 - s) * (H - M.t - M.b);

  const s = chart(W, H, `Kaplan-Meier curves of recurrence-free survival over five years. The vaccine plus antibody group stays higher throughout, ending at about ${pct(ev.landmarks.at(-1).combo)} compared with ${pct(ev.landmarks.at(-1).control)} for the antibody alone.`);

  for (let g = 0; g <= 100; g += 25) {
    s.appendChild(svg('line', { x1: M.l, x2: W - M.r, y1: y(g / 100), y2: y(g / 100), stroke: css('--rule'), 'stroke-width': 1, 'stroke-dasharray': g === 0 ? '' : '3 4' }));
    s.appendChild(svg('text', { x: M.l - 8, y: y(g / 100) + 4, 'text-anchor': 'end', fill: css('--fg-muted'), 'font-size': 13, text: `${g}%` }));
  }
  for (let t = 0; t <= maxT; t += 12) {
    s.appendChild(svg('text', { x: x(t), y: H - M.b + 18, 'text-anchor': 'middle', fill: css('--fg-muted'), 'font-size': 13, text: String(t) }));
  }
  s.appendChild(svg('text', { x: (W + M.l) / 2, y: H - 8, 'text-anchor': 'middle', fill: css('--fg-muted'), 'font-size': 13.5, text: 'months since treatment started' }));

  [['control', css('--control')], ['combo', css('--combo')]].forEach(([arm, colour]) => {
    const c = ev.curves[arm];
    let d = `M${x(0)} ${y(1)}`;
    let prev = 1;
    c.t.forEach((t, i) => {
      if (t > maxT) return;
      d += ` L${x(t)} ${y(prev)} L${x(t)} ${y(c.s[i])}`;
      prev = c.s[i];
    });
    d += ` L${x(maxT)} ${y(prev)}`;
    // Colour alone is not an accessible encoding: these two differ in hue but
    // sit close in lightness, so the control arm is also dashed.
    s.appendChild(svg('path', {
      d, fill: 'none', stroke: colour, 'stroke-width': 2.6, 'stroke-linejoin': 'round',
      ...(arm === 'control' ? { 'stroke-dasharray': '7 3' } : {})
    }));
  });

  // Mark the five-year gap, which is the headline.
  const last = ev.landmarks.at(-1);
  s.appendChild(svg('line', { x1: x(60), x2: x(60), y1: y(last.combo), y2: y(last.control), stroke: css('--accent'), 'stroke-width': 2, 'stroke-dasharray': '4 3' }));
  s.appendChild(svg('text', { x: x(60) - 8, y: y((last.combo + last.control) / 2) + 4, 'text-anchor': 'end', fill: css('--accent'), 'font-size': 13.5, 'font-weight': 700, text: `${fmt(last.per_100, 0)} per 100` }));

  mount('#fig-km', s);
  $('#cap-km').textContent =
    `Reconstructed from the trial's published summary table. At five years, ${pct(last.combo)} of the vaccine group were still recurrence-free against ${pct(last.control)} of the antibody-only group. `
    + `Hazard ratio ${fmt(ev.reconstruction.hr, 3)} (95% confidence interval ${fmt(ev.reconstruction.ci[0], 3)} to ${fmt(ev.reconstruction.ci[1], 3)}); the trial published ${fmt(ev.cuts.find(c => c.name === 'year5').hr, 3)}.`;

  const legend = $('#km-legend');
  legend.innerHTML = '';
  [['vaccine + pembrolizumab', css('--combo'), false], ['pembrolizumab alone', css('--control'), true]]
    .forEach(([label, colour, dashed]) => {
      const key = svg('svg', { width: 26, height: 12, 'aria-hidden': 'true' });
      key.appendChild(svg('line', {
        x1: 0, y1: 6, x2: 26, y2: 6, stroke: colour, 'stroke-width': 3,
        ...(dashed ? { 'stroke-dasharray': '7 3' } : {})
      }));
      legend.appendChild(el('li', {}, [key, el('span', { text: label })]));
    });

  const t = $('#at-risk');
  t.innerHTML = '';
  t.appendChild(el('caption', { class: 'sr-only', text: 'Number of patients still being followed at each timepoint' }));
  const times = ev.curves.combo.n_risk.map(r => r.t);
  const head = el('tr', {}, el('th', { scope: 'col', text: 'still being followed' }));
  times.forEach(tm => head.appendChild(el('th', { class: 'num', scope: 'col', text: String(tm) })));
  t.appendChild(el('thead', {}, head));
  const body = el('tbody');
  [['vaccine + pembrolizumab', 'combo'], ['pembrolizumab alone', 'control']].forEach(([label, arm]) => {
    const row = el('tr', {}, el('th', { scope: 'row', text: label }));
    ev.curves[arm].n_risk.forEach(r => row.appendChild(el('td', { class: 'num', text: String(r.n) })));
    body.appendChild(row);
  });
  t.appendChild(body);
}

/* 100 people, at a chosen timepoint. */
let landmarkIdx = 4;
function drawIconArrays() {
  const ev = DATA.evidence;
  const ctr = $('#landmark-controls');
  if (!ctr.childElementCount) {
    const seg = el('div', { class: 'seg', role: 'group', 'aria-label': 'Choose a timepoint' });
    ev.landmarks.forEach((lm, i) => {
      const b = el('button', { type: 'button', text: lm.months === 60 ? '5 years' : `${lm.months} months` });
      b.setAttribute('aria-pressed', String(i === landmarkIdx));
      b.onclick = () => {
        landmarkIdx = i;
        [...seg.children].forEach((c, j) => c.setAttribute('aria-pressed', String(j === i)));
        drawIconArrays();
      };
      seg.appendChild(b);
    });
    ctr.appendChild(seg);
  }

  const lm = ev.landmarks[landmarkIdx];
  const root = $('#icon-arrays');
  root.innerHTML = '';
  const grid = el('div', { style: 'display:grid;gap:1.75rem;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr))' });

  [['vaccine + pembrolizumab', lm.combo, css('--combo')],
   ['pembrolizumab alone', lm.control, css('--control')]].forEach(([label, value, colour]) => {
    const n = Math.round(value * 100);
    const box = el('div');
    box.appendChild(el('h3', { style: 'margin-bottom:.1rem;font-size:1rem', text: label }));
    box.appendChild(el('p', { style: `margin:.1rem 0 .7rem;font-size:1.6rem;font-weight:740;color:${colour}`, text: `${n} of 100` }));
    const people = el('div', { class: 'people', role: 'img',
      'aria-label': `${n} out of 100 people still cancer-free at ${lm.months} months` });
    for (let i = 0; i < 100; i++) {
      const on = i < n;
      const fig = svg('svg', { viewBox: '0 0 10 20', 'aria-hidden': 'true' });
      fig.appendChild(svg('circle', { cx: 5, cy: 4, r: 3, fill: on ? colour : css('--rule') }));
      fig.appendChild(svg('path', { d: 'M5 8 C1.5 8 0.8 11 0.8 14 L0.8 19 L9.2 19 L9.2 14 C9.2 11 8.5 8 5 8 Z', fill: on ? colour : css('--rule') }));
      people.appendChild(fig);
    }
    box.appendChild(people);
    box.appendChild(el('p', { style: 'font-size:.85rem;color:var(--fg-muted);margin-top:.5rem',
      text: `still cancer-free at ${lm.months === 60 ? 'five years' : `${lm.months} months`}` }));
    grid.appendChild(box);
  });
  root.appendChild(grid);

  const direction = lm.per_100 >= 0 ? 'more' : 'fewer';
  $('#nnt-note').innerHTML =
    `<strong>${fmt(Math.abs(lm.per_100), 0)} ${direction} people per 100</strong> were cancer-free at `
    + `${lm.months === 60 ? 'five years' : `${lm.months} months`} — but the trial was small, so that figure is `
    + `uncertain: somewhere between ${fmt(lm.ci_low_per_100, 0)} and ${fmt(lm.ci_high_per_100, 0)} per 100. `
    + `Put another way, the <button class="term" type="button" data-term="nnt">number needed to treat</button> is ${lm.nnt}.`;
}

/* The caveats, as expandable detail. */
function drawExplainers() {
  const root = $('#explainers');
  root.innerHTML = '';
  const order = ['small_sample', 'open_label', 'one_sided_alpha', 'nominal_p_values',
                 'rfs_is_not_survival', 'hazard_ratio', 'number_needed_to_treat',
                 'proportional_hazards', 'reconstruction_limits', 'phase_3'];
  order.forEach(key => {
    const e = DATA.evidence.explainers[key];
    if (!e) return;
    const d = el('details', { class: 'card', style: 'margin-bottom:.6rem' });
    d.appendChild(el('summary', { style: 'cursor:pointer;font-weight:670', text: e.title }));
    d.appendChild(el('p', { style: 'margin-top:.75rem', text: e.plain }));
    if (e.caveats.length) {
      const ul = el('ul', { style: 'margin:.5rem 0;padding-left:1.1rem;color:var(--fg-muted);font-size:.93rem' });
      e.caveats.forEach(c => ul.appendChild(el('li', { text: c })));
      d.appendChild(ul);
    }
    d.appendChild(el('p', { style: 'font-size:.84rem;color:var(--fg-muted);margin:.5rem 0 0',
      text: `More precisely: ${e.technical} Source: ${e.sources.join('; ')}` }));
    root.appendChild(d);
  });
  $('#verdict').textContent = DATA.evidence.verdict;
}

/* How close the reconstruction lands. */
function drawValidation() {
  const v = DATA.evidence.validation;
  const t = $('#validation');
  t.innerHTML = '';
  const head = el('tr');
  ['quantity', 'our reconstruction', 'published', 'difference'].forEach((h, i) =>
    head.appendChild(el('th', { class: i ? 'num' : '', scope: 'col', text: h })));
  t.appendChild(el('thead', {}, head));
  const body = el('tbody');
  v.checks.filter(c => c.published !== null).forEach(c => {
    const row = el('tr');
    const mark = c.status === 'exact' ? ' (exact)' : c.status === 'warn' ? ' ⚠' : '';
    row.append(
      el('td', { text: c.name + mark }),
      el('td', { class: 'num', text: c.reconstructed == null ? '—' : String(c.reconstructed) }),
      el('td', { class: 'num', text: String(c.published) }),
      el('td', { class: 'num', text: c.difference == null ? '—' : (c.difference >= 0 ? '+' : '') + c.difference })
    );
    body.appendChild(row);
  });
  t.appendChild(body);

  const r = DATA.evidence.reconstruction.placement_sensitivity;
  $('#sensitivity-note').innerHTML =
    `The published table fixes how many recurrences happened in each six-month window — that is `
    + `arithmetic, not estimation. The only thing left to assume is <em>where inside a window</em> `
    + `each one fell. Across every reasonable choice, the hazard ratio moves by just `
    + `<strong>${fmt(r.spread, 4)}</strong>, so the conclusion does not rest on the assumption.`;
}

/* ---------- plumbing ---------- */
function mount(sel, node) { const host = $(sel); host.innerHTML = ''; host.appendChild(node); }

function redraw() {
  drawConcept(); drawWindow(); drawPanels(); drawFunnel();
  drawWeights(); drawRanking(); drawConstruct(); drawKM();
  drawIconArrays(); drawExplainers(); drawValidation();
}

function provenance() {
  const m = DATA.manifest;
  const real = m.sample.is_real_tumour_data && m.predictor.is_real_prediction;
  $('#badge-source').textContent = real ? 'Real tumor data' : 'Demonstration run';
  if (!real) $('#badge-source').classList.add('warn');
  $('#footer-provenance').textContent =
    `Built from sample ${m.sample.id} (${m.sample.study}, ${m.sample.genome_build}) using `
    + `${m.predictor.name}. ${m.counts.mutations_validated} mutations verified against real protein `
    + `sequences, ${m.counts.candidates.toLocaleString()} fragments scored, ${m.counts.selected} selected. `
    + `Generated ${m.generated_date}.`;
}

async function boot() {
  try {
    const loaded = await Promise.all(FILES.map(f => fetch(`data/${f}.json`).then(r => {
      if (!r.ok) throw new Error(`${f}.json: ${r.status}`);
      return r.json();
    })));
    FILES.forEach((f, i) => { DATA[f] = loaded[i]; });
  } catch (err) {
    $('#main').prepend(el('div', { class: 'wrap' }, el('div', { class: 'note',
      html: `<strong>Could not load the data.</strong> This page reads JSON from <code>data/</code>. ` +
            `If you opened the file directly, serve the folder instead: <code>python -m http.server</code>. (${err.message})` })));
    return;
  }
  initTooltips(); initTheme(); provenance(); redraw();
}

document.addEventListener('DOMContentLoaded', boot);
