/* Provider output is always rendered as text. Credentials stay on the server. */
const $ = id => document.getElementById(id);
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
    const a = sourceLink(source, `↗`); a.className = 'source-cite'; a.title = `${new URL(source.url).hostname}: ${source.title}`; a.setAttribute("aria-label", a.title);
    span.append(a);
  }
  return span;
}
function cited(claim, sources, tag = 'p') {
  const node = el(tag, claim.text); node.append(citations(claim.source_ids, sources)); return node;
}
const catalog = ['Samsung Galaxy S24 Plus','Samsung Galaxy S24 Ultra','Samsung Galaxy S25 Ultra','Apple iPhone 16 Pro','Apple iPhone 16','Google Pixel 9 Pro','Google Pixel 9','Sony Xperia 1 VI','Sony WH-1000XM5','Sennheiser Momentum 4 Wireless','Bose QuietComfort Ultra Headphones','Apple AirPods Max (USB-C)','Kindle Paperwhite (12th generation)','Kobo Clara BW','Kobo Libra Colour','Dyson V12 Detect Slim','Samsung Jet 75'];
const selected = new Set();
function syncSelection() {
  $('query').value = [...selected].join(' vs ');
  $('selectedProducts').replaceChildren();
  selected.forEach(name => { const b=el('button', `${name} ×`); b.type='button'; b.setAttribute('aria-label', `Remove ${name}`); b.onclick=()=>{selected.delete(name);syncSelection();}; $('selectedProducts').append(b); });
  $('pickerStatus').textContent = `${selected.size}/4 selected. You can also edit the text search below.`;
  drawCatalog();
}
function drawCatalog() {
  const q=$('catalogSearch').value.toLowerCase(); const matches=catalog.filter(n=>n.toLowerCase().includes(q));
  $('catalogList').replaceChildren();
  matches.forEach(name=>{const b=el('button',name);b.type='button';b.setAttribute('aria-pressed',String(selected.has(name)));b.disabled=!selected.has(name)&&selected.size>=4;b.onclick=()=>{selected.has(name)?selected.delete(name):selected.add(name);syncSelection();};$('catalogList').append(b);});
  if(!matches.length) $('catalogList').append(el('p','Not in this catalog? Enter the exact model in the text search below.','small muted'));
}
$('catalogSearch').addEventListener('input',drawCatalog); drawCatalog();
$('query').addEventListener('input',()=>{selected.clear();$('selectedProducts').replaceChildren();$('pickerStatus').textContent='Using custom text search.';drawCatalog();});
function numericCharts(data, sources) {
  const grid=el('section',null,'metric-grid'); grid.setAttribute('aria-label','Comparable specifications');
  for(const row of data.rows) {
    if(!/battery|weight|display size|screen size|storage|charging/i.test(row.attribute)) continue;
    const values=row.values.map(v=>{const m=v.value.trim().match(/^(?:up to\s+)?(\d+(?:\.\d+)?)\s*(hours?|hrs?|mah|g|grams?|inches|inch|gb|w)(?:\s*\([^)]*\))?$/i);return m&&v.source_ids.length?{value:Number(m[1]),unit:m[2].toLowerCase().replace(/^(hours?|hrs?)$/,'h').replace(/^grams?$/,'g').replace(/^inch(?:es)?$/,'in'),cell:v}:null;});
    if(values.some(v=>!v)||new Set(values.map(v=>v.unit)).size!==1)continue;
    const max=Math.max(...values.map(v=>v.value));if(!max)continue;
    const box=el('article',null,'metric-card');box.append(el('h3',row.attribute));
    values.forEach((v,i)=>{const line=el('div',null,'metric-line');line.append(el('span',data.products[i].name),el('strong',`${v.value} ${v.unit}`));const track=el('div',null,'metric-track'),bar=el('div',null,'metric-bar');bar.style.width=`${v.value/max*100}%`;bar.style.background=['#375b47','#d55a36','#566ea2','#987142'][i];track.append(bar);box.append(line,track,citations(v.cell.source_ids,sources));});
    box.append(el('p',/weight/i.test(row.attribute)?'Lower weight is lighter; other tradeoffs still matter.':'Reported specification, not an overall quality score.','small muted'));grid.append(box);if(grid.children.length===4)break;
  }
  return grid;
}
document.querySelectorAll('[data-query]').forEach(button => button.onclick = () => {
  selected.clear(); $('selectedProducts').replaceChildren(); drawCatalog(); $('query').value = button.dataset.query; $('query').focus();
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
      $('errorMessage').textContent = 'You can edit the products and start again.';
    } else {
      $('errorTitle').textContent = error.setup ? 'Comparison is temporarily unavailable.' : 'We couldn’t finish that comparison.';
      $('errorMessage').textContent = error.message === 'Failed to fetch' ? 'Connection interrupted. Check the server and try again.' : error.message;
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

  const verdict = el('div', null, 'verdict'), verdictBody = el('div');
  verdictBody.append(el('h3', data.recommendation.verdict));
  const reason=el('details'); reason.append(el('summary','Why this recommendation?'),el('p',data.recommendation.reason)); verdictBody.append(reason);
  verdictBody.append(citations(data.recommendation.source_ids, sources));
  verdict.append(el('div', data.recommendation.product_id ? 'OUR TAKE ↗' : 'THE EVIDENCE SO FAR', 'verdict-label'), verdictBody); root.append(verdict);
  const cards = el('div', null, 'product-grid'); cards.style.setProperty('--count', data.products.length);
  for (const [i, product] of data.products.entries()) {
    const card = el('article', null, 'product-card');
    card.append(el('span', `0${i+1} / THE OPTION`, 'product-number'), el('h3', product.name));
    const productSources = data.sources.filter(source => source.product_id === product.id);
    const photoCandidates = productSources.flatMap(source => (source.image_urls || []).filter(url => safeUrl(url)).map(url => ({source,url})));
    const photoSource = photoCandidates[0]?.source;
    const figure = el('figure', null, 'product-photo');
    if (photoSource) {
      const img = el('img'); img.src = photoSource.image_urls.find(url => safeUrl(url));
      img.alt = `${product.name} - image from source website`; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer';
      let photoIndex = 0;
      img.onerror = () => {
        const next = photoCandidates[++photoIndex];
        if (next) { img.src = next.url; caption.replaceChildren(sourceLink(next.source, `Image: ${new URL(next.source.url).hostname}`)); }
        else figure.replaceChildren(el('span', 'Image unavailable', 'muted'));
      };
      const caption = el('figcaption'); caption.append(sourceLink(photoSource, `Image: ${new URL(photoSource.url).hostname}`));
      figure.append(img, caption);
    } else { figure.append(el('span', 'No matching product image found', 'muted')); }
    card.append(figure);
    const sourceNav = el('details', null, 'product-websites'); sourceNav.append(el('summary', `Sources (${productSources.length})`));
    productSources.forEach(source => sourceNav.append(sourceLink(source, `${new URL(source.url).hostname.replace(/^www\./, '')}`)));
    card.append(sourceNav);
    if (product.variant_note) card.append(el('p', product.variant_note, 'variant-note'));
    const best = cited(product.best_for, sources); best.className = 'best-for'; card.append(best);
    card.append(el('h4', 'COMPARE SELLER PRICES'));
    card.append(el('p', 'Listed prices found during research. Search listings can lag behind seller updates; confirm final price and delivery at checkout.', 'small muted'));
    const offers = [...product.offers].sort((a,b) => a.currency.localeCompare(b.currency) || a.amount-b.amount);
    if (!offers.length) card.append(el('p', 'No direct seller price verified. Open the source websites above to check availability.', 'small muted'));
    const sellerDetails=el("details"); sellerDetails.append(el("summary", `All seller offers (${offers.length})`));
    for (const [offerIndex, offer] of offers.entries()) {
      const source = sources.get(offer.source_id); if (!source) continue;
      const box = el('div', null, 'seller-offer');
      box.append(el('p', source.kind === 'page' ? 'Listed on seller page' : 'Listed in search result · seller page not verified', 'small muted'));
      box.append(el('strong', offer.price_text), el('p', new URL(source.url).hostname.replace(/^www\./, ''), 'seller-name'));
      box.append(el('p', `${offer.variant} · ${offer.condition} · ${offer.availability.replaceAll('_',' ')}`, 'small'));
      box.append(el('p', `Shipping: ${offer.shipping || 'Not verified'}`, 'small muted'));
      const peers = offers.filter(o => o.currency === offer.currency && o.variant === offer.variant && o.condition === 'new' && o.availability === 'in_stock');
      if (offer.availability === 'in_stock' && peers.length > 1 && offer.amount === Math.min(...peers.map(o => o.amount))) box.append(el('span', 'Lowest observed for this variant', 'price-badge'));
      const buy = sourceLink(source, offer.availability === 'out_of_stock' ? 'Check seller availability ↗' : 'View offer / Buy ↗'); buy.className = 'buy-link'; box.append(buy);
      box.append(el('p', `Checked ${new Date(source.retrieved_at).toLocaleString()}`, 'small muted'));
      const proof = el('details'); proof.append(el('summary', 'Price evidence'), el('p', offer.evidence_quote)); box.append(proof);
      if(offerIndex===0) card.append(box); else sellerDetails.append(box);
    }
    if(offers.length>1)card.append(sellerDetails);
    for (const [label, claims] of [['Why buy this', product.strengths], ['Why not buy this', product.limitations]]) {
      const section=el('section',null,'buy-reasons');section.append(el('h4',label));const ul=el('ul');
      if(!claims.length)ul.append(el('li','Not enough evidence yet.','unknown'));
      claims.slice(0,2).forEach(claim=>ul.append(cited(claim,sources,'li')));section.append(ul);
      if(claims.length>2){const more=el('details');more.append(el('summary','More reasons'));claims.slice(2).forEach(claim=>more.append(cited(claim,sources)));section.append(more);}card.append(section);
    }
    cards.append(card);
  }
  root.append(numericCharts(data,sources), cards);
  const fullSpecs=el('details',null,'full-specs');fullSpecs.append(el('summary','Compare all specifications'));root.append(fullSpecs);
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
  table.append(tbody); scroller.append(table); fullSpecs.append(scroller);
  const notes = [...data.assumptions, ...data.caveats, ...data.warnings];
  if (notes.length) { const box = el('details', null, 'notes'); box.append(el('summary', 'Uncertainties and research notes'));  const ul = el('ul'); notes.forEach(n => ul.append(el('li', n))); box.append(ul); root.append(box); }
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
