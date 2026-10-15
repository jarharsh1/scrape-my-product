/* Keys stay in tab memory only. Provider output is always rendered as text. */
const $ = id => document.getElementById(id);
let credentials = {tavily: '', openai: ''};
let configured = {tavily_configured: false, openai_configured: false};
let controller = null;
let currentResult = null;

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function safeUrl(value) {
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !u.username && !u.password ? u.href : null; }
  catch { return null; }
}
function sourceLink(source, label) {
  const a = el('a', label || source.title);
  a.href = safeUrl(source.url) || '#'; a.target = '_blank'; a.rel = 'noopener noreferrer';
  return a;
}
function citations(ids, sources) {
  const span = el('span');
  for (const id of ids || []) {
    const source = sources.get(id); if (!source) continue;
    const a = sourceLink(source, `[${id}]`); a.className = 'source-cite'; a.title = source.title;
    span.append(a);
  }
  return span;
}
function cited(claim, sources, tag = 'p') {
  const node = el(tag, claim.text); node.append(citations(claim.source_ids, sources)); return node;
}
function readiness() {
  const ready = (credentials.tavily || configured.tavily_configured) && (credentials.openai || configured.openai_configured);
  $('connectionDot').classList.toggle('ready', Boolean(ready));
  $('connectionLabel').textContent = ready ? 'Tools connected' : 'Connections';
  $('tavilyStatus').textContent = configured.tavily_configured ? 'Available on server' : '';
  $('openaiStatus').textContent = configured.openai_configured ? 'Available on server' : '';
}
$('openSettings').onclick = () => { $('savedMessage').textContent = ''; $('settingsDialog').showModal(); };
$('closeSettings').onclick = () => $('settingsDialog').close();
$('errorSettings').onclick = () => $('settingsDialog').showModal();
$('settingsForm').onsubmit = event => {
  event.preventDefault(); credentials = {tavily: $('tavilyKey').value.trim(), openai: $('openaiKey').value.trim()};
  readiness(); $('settingsDialog').close();
};
$('clearKeys').onclick = () => {
  credentials = {tavily: '', openai: ''}; $('tavilyKey').value = ''; $('openaiKey').value = '';
  $('savedMessage').textContent = 'Tab keys cleared.'; readiness();
};
document.querySelectorAll('[data-query]').forEach(button => button.onclick = () => {
  $('query').value = button.dataset.query; $('query').focus();
});
$('query').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('compareForm').requestSubmit(); }
});
$('cancelResearch').onclick = () => controller?.abort();

$('compareForm').onsubmit = async event => {
  event.preventDefault(); if (controller) return;
  $('errorPanel').hidden = true; $('results').hidden = true; $('loadingPanel').hidden = false;
  $('compareButton').disabled = true; $('compareButton').textContent = 'Researching…';
  $('loadingNote').textContent = 'Researching the products you named…';
  controller = new AbortController();
  try {
    const headers = {'Content-Type': 'application/json'};
    if (credentials.tavily) headers['X-Tavily-Api-Key'] = credentials.tavily;
    if (credentials.openai) headers['X-OpenAI-Api-Key'] = credentials.openai;
    const response = await fetch('/api/compare', {method: 'POST', headers,
      body: JSON.stringify({query: $('query').value.trim(), country: $('country').value}), signal: controller.signal});
    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail;
      const message = typeof detail === 'string' ? detail : detail?.message || 'Please enter 2–4 product names and try again.';
      const error = new Error(message); error.setup = detail?.code === 'setup_required' || response.status === 401; throw error;
    }
    currentResult = data; render(data); $('results').hidden = false; $('results').focus();
  } catch (error) {
    if (error.name === 'AbortError') {
      $('errorTitle').textContent = 'Comparison cancelled.';
      $('errorMessage').textContent = 'You can edit the products and start again. Requests already sent may still incur provider charges.';
      $('errorSettings').hidden = true;
    } else {
      $('errorTitle').textContent = error.setup ? 'Connect your tools to start.' : 'We couldn’t finish that comparison.';
      $('errorMessage').textContent = error.message === 'Failed to fetch' ? 'Connection interrupted. Check the server and try again.' : error.message;
      $('errorSettings').hidden = !error.setup;
    }
    $('errorPanel').hidden = false;
  } finally {
    controller = null; $('loadingPanel').hidden = true; $('compareButton').disabled = false;
    $('compareButton').replaceChildren(document.createTextNode('Compare products '), el('span', '↗'));
  }
};

function render(data) {
  const root = $('results'); root.replaceChildren();
  const sources = new Map(data.sources.map(s => [s.id, s]));
  const head = el('div', null, 'result-heading'), heading = el('div');
  heading.append(el('span', 'THE RESEARCH, SIDE BY SIDE', 'eyebrow'), el('h2', data.title),
    el('div', `${data.country} · Researched ${new Date(data.checked_at).toLocaleString()} · ${data.sources.length} sources`, 'result-meta'));
  const actions = el('div', null, 'result-actions'), download = el('button', 'Export research ↓', 'text-button');
  download.onclick = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(currentResult, null, 2)], {type: 'application/json'}));
    const a = el('a'); a.href = url; a.download = 'sidebyside-comparison.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  actions.append(download); head.append(heading, actions); root.append(head);
  if (data.assumptions.length) root.append(el('p', `Working assumptions: ${data.assumptions.join(' ')}`, 'assumptions'));
  const verdict = el('div', null, 'verdict'), verdictBody = el('div');
  verdictBody.append(el('h3', data.recommendation.verdict), el('p', data.recommendation.reason));
  verdictBody.append(citations(data.recommendation.source_ids, sources));
  verdict.append(el('div', data.recommendation.product_id ? 'OUR TAKE ↗' : 'THE EVIDENCE SO FAR', 'verdict-label'), verdictBody); root.append(verdict);
  const cards = el('div', null, 'product-grid'); cards.style.setProperty('--count', data.products.length);
  for (const [i, product] of data.products.entries()) {
    const card = el('article', null, 'product-card');
    card.append(el('span', `0${i+1} / THE OPTION`, 'product-number'), el('h3', product.name));
    if (product.variant_note) card.append(el('p', product.variant_note, 'variant-note'));
    const best = cited(product.best_for, sources); best.className = 'best-for'; card.append(best);
    for (const [label, claims] of [['WHAT STANDS OUT', product.strengths], ['THE TRADEOFFS', product.limitations]]) {
      card.append(el('h4', label)); const ul = el('ul');
      if (!claims.length) ul.append(el('li', 'Not enough evidence to verify.', 'unknown'));
      claims.forEach(claim => ul.append(cited(claim, sources, 'li'))); card.append(ul);
    }
    card.append(el('h4', 'OBSERVED PRICES'));
    if (!product.offers.length) card.append(el('p', 'No price verified for this market.', 'small muted'));
    for (const offer of product.offers) {
      const source = sources.get(offer.source_id); if (!source) continue;
      const a = sourceLink(source, offer.price_text); a.className = 'offer';
      a.append(el('span', `${new URL(source.url).hostname.replace(/^www\./, '')} ↗`)); card.append(a);
    }
    cards.append(card);
  }
  root.append(cards, el('h3', 'The details that make a difference.', 'table-title'));
  const scroller = el('div', null, 'table-scroll'); scroller.tabIndex = 0; scroller.setAttribute('aria-label', 'Scrollable product comparison');
  const table = el('table'), thead = el('thead'), headerRow = el('tr');
  headerRow.append(el('th', 'A closer look'));
  data.products.forEach(p => { const th = el('th', p.name); th.scope = 'col'; headerRow.append(th); });
  thead.append(headerRow); table.append(thead); const tbody = el('tbody');
  for (const row of data.rows) {
    const tr = el('tr'), label = el('th', row.attribute); label.scope = 'row'; tr.append(label);
    row.values.forEach(v => { const td = el('td', v.value, v.value === 'Not verified' ? 'unknown' : ''); td.append(citations(v.source_ids, sources)); tr.append(td); });
    tbody.append(tr);
  }
  table.append(tbody); scroller.append(table); root.append(scroller);
  const notes = [...data.caveats, ...data.warnings];
  if (notes.length) { const box = el('div', null, 'notes'); box.append(el('strong', 'Worth keeping in mind')); const ul = el('ul'); notes.forEach(n => ul.append(el('li', n))); box.append(ul); root.append(box); }
  const details = el('details', null, 'sources'); details.append(el('summary', `Open the research trail · ${sources.size} sources`));
  const list = el('ol', null, 'source-list');
  data.sources.forEach(source => {
    const li = el('li'); li.id = source.id;
    li.append(el('div', `${source.id} / ${source.kind === 'page' ? 'PAGE EXTRACT' : 'SEARCH EXCERPT'}`, 'source-kind'), sourceLink(source),
      el('p', source.excerpt), el('span', `Retrieved ${new Date(source.retrieved_at).toLocaleString()}`, 'muted'));
    list.append(li);
  });
  details.append(list); root.append(details, el('p', 'AI-assisted synthesis of linked sources; details may be incomplete or incorrect. Prices are observed listings, not checkout quotes. Check the exact variant, delivery, and final price with the seller.', 'result-footnote'));
}

fetch('/api/compare/status').then(r => r.ok ? r.json() : Promise.reject()).then(data => {configured = data; readiness();}).catch(() => readiness());
