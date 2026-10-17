/* Provider output is always rendered as text. Credentials stay on the server. */
const $ = id => document.getElementById(id);
let controller = null;
let currentResult = null;

function el(tag, text, className) {
  const node = document.createElement(tag === 'details' ? 'section' : tag === 'summary' ? 'h4' : tag);
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
const catalog = [
 ['Samsung Galaxy S24 Plus','Phone · Samsung Galaxy S series'],['Samsung Galaxy S24 Ultra','Phone · Samsung Galaxy S series'],['Samsung Galaxy S25 Ultra','Phone · Samsung Galaxy S series'],
 ['Apple iPhone 16 Pro','Phone · Apple iPhone Pro series'],['Apple iPhone 16','Phone · Apple iPhone series'],['Google Pixel 9 Pro','Phone · Google Pixel Pro series'],['Google Pixel 9','Phone · Google Pixel series'],['Sony Xperia 1 VI','Phone · Sony Xperia series'],
 ['Sony WH-1000XM5','Over-ear headphones · Sony'],['Sennheiser Momentum 4 Wireless','Over-ear headphones · Sennheiser'],['Bose QuietComfort Ultra Headphones','Over-ear headphones · Bose'],['Apple AirPods Max (USB-C)','Over-ear headphones · Apple'],
 ['Kindle Paperwhite (12th generation)','E-reader · Amazon Kindle'],['Kobo Clara BW','E-reader · Kobo · black-and-white model'],['Kobo Libra Colour','E-reader · Kobo · colour model'],['Dyson V12 Detect Slim','Cordless vacuum · Dyson'],['Samsung Jet 75','Cordless vacuum · Samsung']
].map(([name,snippet])=>({name,snippet}));
const selected = new Set();
let picks = ['', ''];
function syncSelection() {
  selected.clear(); picks.filter(Boolean).forEach(p=>selected.add(p));
  $('query').value = [...selected].join(' vs ');
  $('pickerStatus').textContent = `${selected.size} selected`;
}
function drawDropdowns() {
  $('productDropdowns').replaceChildren();
  picks.forEach((picked,index)=>{
    const wrap=el('div',null,'product-dropdown'), label=el('label',`Product ${index+1}`), input=el('input'), menu=el('div',null,'suggestion-menu');
    input.id=`product-pick-${index}`;label.htmlFor=input.id;input.value=picked;input.placeholder='Type a product name…';input.autocomplete='off';
    input.setAttribute('role','combobox'); input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');
    menu.id=`product-options-${index}`;menu.setAttribute('role','listbox');menu.hidden=true;input.setAttribute('aria-controls',menu.id);
    let active=-1, options=[];
    const close=()=>{menu.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');};
    const choose=name=>{picks[index]=name;input.value=name;syncSelection();close();};
    const show=()=>{
      const q=input.value.trim().toLowerCase(); active=-1;menu.replaceChildren();input.removeAttribute('aria-activedescendant');
      options=catalog.filter(p=>p.name.toLowerCase().includes(q)&&!picks.some((n,i)=>i!==index&&n===p.name)).slice(0,7);
      if(q&&!catalog.some(p=>p.name.toLowerCase()===q)&&!picks.some((n,i)=>i!==index&&n.toLowerCase()===q)) options.push({name:input.value.trim(),snippet:'Search this model'});
      options.forEach((product,i)=>{const option=el('button');option.type='button';option.id=`option-${index}-${i}`;option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.append(el('strong',product.name),el('span',product.snippet));option.onmousedown=e=>e.preventDefault();option.onclick=()=>choose(product.name);menu.append(option);});
      if(!options.length)menu.append(el('p','No other matching products. Try a different name.','small muted'));
      menu.hidden=false; input.setAttribute('aria-expanded','true');
    };
    input.onfocus=show;
    input.oninput=()=>{picks[index]='';syncSelection();show();};
    input.onblur=()=>setTimeout(close,150);
    input.onkeydown=e=>{
      if(e.key==='Escape'){close();return;}
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();if(menu.hidden)show();if(!options.length)return;active=(active+(e.key==='ArrowDown'?1:-1)+options.length)%options.length;Array.from(menu.children).forEach((n,i)=>n.setAttribute('aria-selected',String(i===active)));input.setAttribute('aria-activedescendant',`option-${index}-${active}`);}
      if(e.key==='Enter'&&!menu.hidden){e.preventDefault();if(options.length)choose(options[active<0?0:active].name);}
    };
    wrap.append(label,input,menu);
    if(picks.length>2){const remove=el('button','Remove','text-button');remove.type='button';remove.setAttribute('aria-label',`Remove product ${index+1}`);remove.onclick=()=>{picks.splice(index,1);syncSelection();drawDropdowns();};wrap.append(remove);}
    $('productDropdowns').append(wrap);
  });
  $('addProduct').hidden=picks.length>=4;
}
$('addProduct').onclick=()=>{if(picks.length<4){picks.push('');drawDropdowns();$(`product-pick-${picks.length-1}`).focus();}};
drawDropdowns();
$('query').addEventListener('input',()=>{selected.clear();picks=picks.map(()=> '');drawDropdowns();$('pickerStatus').textContent='Using custom text search.';});
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
  picks=button.dataset.query.split(' vs ');syncSelection();drawDropdowns();$('compareButton').focus();
});
$('query').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); $('compareForm').requestSubmit(); }
});
$('cancelResearch').onclick = () => controller?.abort();

$('compareForm').onsubmit = async event => {
  event.preventDefault(); if (controller) return;
  if($('query').value.trim().length<5){$('pickerStatus').textContent='Select at least two products, or type their names.';return;}
  $('errorPanel').hidden = true; $('results').hidden = true; $('loadingPanel').hidden = false;
  $('compareButton').disabled = true; $('compareButton').textContent = 'Researching…';
  $('loadingNote').textContent = 'Researching the products you named…';
  controller = new AbortController();
  try {
    const headers = {'Content-Type': 'application/json'};
    const response = await fetch('/api/compare', {method: 'POST', headers,
      body: JSON.stringify({query: $('query').value.trim() + ($('priority').value ? `. Buying priority: ${$('priority').value}.` : ''), country: $('country').value}), signal: controller.signal});
    if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("Research is temporarily unavailable. Please try again.");
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


function productPhoto(product, sources) {
  const figure=el('figure',null,'product-photo');
  const seen=new Set();
  const candidates=sources.flatMap(source=>(source.image_urls||[]).filter(url=>safeUrl(url)&&!seen.has(url)&&seen.add(url)).map(url=>({source,url})));
  candidates.sort((a,b)=>imagePenalty(a.url)-imagePenalty(b.url));
  const img=el('img'),caption=el('figcaption');img.alt=`${product.name} product photo`;img.referrerPolicy='no-referrer';img.decoding='async';
  let index=-1,timer;
  function next(){clearTimeout(timer);const candidate=candidates[++index];if(!candidate){figure.replaceChildren(el('div','Photo unavailable','photo-placeholder'));return;}caption.replaceChildren(sourceLink(candidate.source,`Photo: ${new URL(candidate.source.url).hostname.replace(/^www\./,'')}`));img.src=candidate.url;timer=setTimeout(next,6000);}
  img.onerror=next;img.onload=()=>{clearTimeout(timer);if(img.naturalWidth<120||img.naturalHeight<100)next();};figure.append(img,caption);next();return figure;
}
function imagePenalty(url){return /headband|microphone|controls|wearing|case|cable|test|graph/i.test(url)?10:0;}
function rowCategory(row){const name=row.attribute.toLowerCase();if(/camera|video|photo/.test(name))return 'Camera';if(/battery|charg/.test(name))return 'Battery';if(/display|screen|resolution|refresh/.test(name))return 'Display';if(/processor|chip|ram|storage|performance/.test(name))return 'Performance';if(/weight|dimension|build|water|design/.test(name))return 'Design';return 'Other';}
function render(data) {
  const root=$('results');root.replaceChildren();const sources=new Map(data.sources.map(s=>[s.id,s]));
  const head=el('div',null,'result-heading');const title=el('div');title.append(el('p',`${data.country} · Checked ${new Date(data.checked_at).toLocaleString()}`,'result-meta'));
  const share=el('button','Share shortlist ↗','text-button');share.onclick=async()=>{const url=new URL(location.href);url.search='';url.searchParams.set('compare',data.products.map(p=>p.name).join(' vs '));try{await navigator.clipboard.writeText(url.href);share.textContent='Link copied';}catch{share.textContent='Copy link';const field=el('input');field.value=url.href;field.readOnly=true;head.append(field);field.select();}};head.append(title,share);root.append(head);
  const missing=data.rows.reduce((n,r)=>n+r.values.filter(v=>v.value==='Not verified').length,0);
  const trust=el('div',null,'trust-strip');trust.append(el('span',`${sources.size} linked sources`),el('span',`${data.rows.length} compared attributes`),el('span',missing?`${missing} unverified cells`:'All cells have source links'));
  const tabs=el('div',null,'result-tabs');tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','Comparison views');root.append(tabs);
  const panels={};const buttons={};
  function activate(key){Object.entries(panels).forEach(([k,p])=>{p.hidden=k!==key;buttons[k].setAttribute('aria-selected',String(k===key));buttons[k].tabIndex=k===key?0:-1;});}
  for(const [key,label] of [['overview','Overview'],['differences','Key differences'],['specs','All specs'],['prices','Prices & stores'],['sources','Sources']]){
    const b=el('button',label);b.id=`tab-${key}`;b.setAttribute('role','tab');b.setAttribute('aria-controls',`panel-${key}`);b.onclick=()=>activate(key);tabs.append(b);buttons[key]=b;
    const panel=el('section',null,'result-panel');panel.id=`panel-${key}`;panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby',b.id);panels[key]=panel;root.append(panel);
    b.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const keys=Object.keys(buttons);let i=keys.indexOf(key);i=e.key==='Home'?0:e.key==='End'?keys.length-1:(i+(e.key==='ArrowRight'?1:-1)+keys.length)%keys.length;activate(keys[i]);buttons[keys[i]].focus();};
  }
  const verdict=el('details',null,'verdict');verdict.append(el('summary','Which should I choose?'));const verdictText=el('div');verdictText.append(el('h3',data.recommendation.verdict));const why=el('details');why.append(el('summary','See the reasoning'),el('p',data.recommendation.reason),citations(data.recommendation.source_ids,sources));verdictText.append(why);verdict.append(el('span','THE SHORT ANSWER','verdict-label'),verdictText);
  const cards=el('div',null,'product-grid');cards.style.setProperty('--count',data.products.length);
  for(const [i,p] of data.products.entries()){
    const refs=data.sources.filter(s=>s.product_id===p.id),card=el('article',null,'product-card');
    card.style.setProperty('--product-color',['#286b61','#b65e3a','#6261a0','#9b732f'][i]);
    card.append(productPhoto(p,refs),el('h3',p.name));
    
    const offers=p.offers.filter(o=>o.availability!=='out_of_stock');
    const priced=offers.filter(o=>sources.has(o.source_id));
    if(priced.length){const currency=priced[0].currency;const same=priced.filter(o=>o.currency===currency).sort((a,b)=>a.amount-b.amount);const offer=same[0];const source=sources.get(offer.source_id);
      const price=el('div',null,'quick-price');price.append(el('strong',new Intl.NumberFormat(undefined,{style:'currency',currency:offer.currency,maximumFractionDigits:2}).format(offer.amount)),el('span',offer.variant,'small muted'));
      const buy=sourceLink(source,'View at '+new URL(source.url).hostname.replace(/^www\./,'' )+' ↗');buy.className='quick-buy';price.append(buy);
      price.append(el('span',source.kind==='page'?'Listed price · check checkout total':'Search price · confirm at store','small muted'));card.append(price);
    }else card.append(el('p','Price unavailable','price-unavailable'));
    const store=el('button',offers.length?`${offers.length} offer${offers.length===1?'':'s'} →`:'Check stores →','store-action');store.onclick=()=>activate('prices');card.append(store);
    for(const [label,claims,type] of [['Why buy this',p.strengths,'positive'],['Why not buy this',p.limitations,'negative']]){const section=el('section',null,`buy-reasons ${type}`);section.append(el('h4',label));const ul=el('ul');claims.forEach(c=>ul.append(cited(c,sources,'li')));if(!claims.length)ul.append(el('li','Not enough evidence yet.','muted'));section.append(ul);card.append(section);}
    if(p.variant_note){const note=el('details',null,'variant-detail');note.append(el('summary','Model & variant notes'),el('p',p.variant_note));card.append(note);}cards.append(card);
    const sellerGroup=el('section',null,'seller-group');sellerGroup.append(el('h3',p.name));
    if(!p.offers.length)sellerGroup.append(el('p','No seller price confirmed in this search. No estimate has been substituted.','empty-state'));
    for(const offer of [...p.offers].sort((a,b)=>a.currency.localeCompare(b.currency)||a.amount-b.amount)){
      const source=sources.get(offer.source_id);if(!source)continue;const box=el('article',null,'seller-offer');
      const seller=el('div');seller.append(el('strong',new URL(source.url).hostname.replace(/^www\./,'')),el('p',`${offer.variant} · ${offer.availability.replaceAll('_',' ')}`,'small muted'));
      const amount=el('div');let price=offer.price_text;try{price=new Intl.NumberFormat(undefined,{style:'currency',currency:offer.currency,maximumFractionDigits:2}).format(offer.amount);}catch{}amount.append(el('strong',price),el('p',/bank|coupon|exchange|cashback|emi/i.test(offer.price_text)?'Conditional offer — check evidence':'Observed listing','small muted'));
      const link=sourceLink(source,'Visit store ↗');link.className='buy-link';box.append(seller,amount,link);
      const proof=el('details',null,'offer-proof');proof.append(el('summary','Price details & evidence'),el('p',`Shipping: ${offer.shipping}. Condition: ${offer.condition}. ${source.kind==='page'?'Seller page extract':'Search listing, page not verified'}. Checked ${new Date(source.retrieved_at).toLocaleString()}.`),el('blockquote',offer.evidence_quote));box.append(proof);sellerGroup.append(box);
    }
    panels.prices.append(sellerGroup);
  }
  const matrix=el('div',null,'table-scroll comparison-matrix');matrix.tabIndex=0;
  matrix.setAttribute('aria-label','Product comparison. Scroll horizontally for more products.');
  const grid=el('table');grid.style.setProperty('--count',data.products.length);
  const header=el('thead'),headerRow=el('tr');headerRow.append(el('th','Compare'));
  data.products.forEach(p=>{const cell=el('th',p.name);cell.scope='col';headerRow.append(cell);});header.append(headerRow);grid.append(header);
  const body=el('tbody'),productCards=Array.from(cards.children);
  for(const [label,match] of [
    ['Product',n=>n.className==='product-photo'],
    ['Price & stores',n=>['quick-price','price-unavailable','store-action'].includes(n.className)],
    ['Why buy',n=>n.className==='buy-reasons positive'],
    ['Why skip',n=>n.className==='buy-reasons negative'],
    ['Variant',n=>n.className==='variant-detail']
  ]){const row=el('tr'),labelCell=el('th',label);labelCell.scope='row';row.append(labelCell);
    productCards.forEach(card=>{const cell=el('td');Array.from(card.children).filter(match).forEach(n=>cell.append(n));if(!cell.children.length)cell.append(el('span','—'));row.append(cell);});body.append(row);
  }
  grid.append(body);matrix.append(grid);panels.overview.append(matrix);
  panels.prices.prepend(el('p','Compare the exact variant and final checkout total. Listed prices may exclude shipping or depend on an offer; this is not complete market coverage.','panel-intro'));
  const charts=numericCharts(data,sources);panels.differences.append(el('h3','The numbers that separate them'),charts);
  if(!charts.children.length)panels.differences.append(el('p','No directly comparable numeric measurements found. Compare the sourced differences below.','empty-state'));
  function tableFor(rows){const scroller=el('div',null,'table-scroll');scroller.tabIndex=0;const table=el('table'),thead=el('thead'),tr=el('tr');tr.append(el('th','Attribute'));data.products.forEach(p=>{const th=el('th',p.name);th.scope='col';tr.append(th);});thead.append(tr);table.append(thead);const body=el('tbody');rows.forEach(r=>{const tr=el('tr'),th=el('th',r.attribute);th.scope='row';tr.append(th);r.values.forEach(v=>{const td=el('td',v.value,v.value==='Not verified'?'unknown':'');td.append(citations(v.source_ids,sources));tr.append(td);});body.append(tr);});table.append(body);scroller.append(table);return scroller;}
  const differences=data.rows.filter(r=>new Set(r.values.map(v=>v.value.trim().toLowerCase())).size>1);panels.differences.append(el('p','Different reported values, not automatic quality rankings. Unknown values remain unverified.','panel-intro'),tableFor(differences));
  const filterbar=el('div',null,'spec-filters'),search=el('input'),category=el('select'),onlyLabel=el('label'),only=el('input');search.type='search';search.placeholder='Find a specification…';search.setAttribute('aria-label','Find a specification');category.setAttribute('aria-label','Specification category');['All sections',...new Set(data.rows.map(rowCategory))].forEach(c=>{const o=el('option',c);o.value=c;category.append(o);});only.type='checkbox';onlyLabel.append(only,document.createTextNode(' Differences only'));filterbar.append(search,category,onlyLabel);const specRows=el('div');panels.specs.append(filterbar,specRows);
  function filterSpecs(){const rows=data.rows.filter(r=>(!search.value||r.attribute.toLowerCase().includes(search.value.toLowerCase()))&&(category.value==='All sections'||rowCategory(r)===category.value)&&(!only.checked||differences.includes(r)));specRows.replaceChildren(rows.length?tableFor(rows):el('p','No matching specifications.','empty-state'));}
  search.oninput=category.onchange=only.onchange=filterSpecs;filterSpecs();
  const notes=el('details',null,'notes');notes.append(el('summary','Assumptions, gaps & conflicts'));[...data.assumptions,...data.caveats,...data.warnings].forEach(n=>notes.append(el('p',n)));panels.sources.append(notes);
  const list=el('div',null,'source-list');data.sources.forEach(s=>{const item=el('article');item.append(el('span',`${s.kind==='page'?'PAGE EXTRACT':'SEARCH EXCERPT'} · ${new URL(s.url).hostname}`,'source-kind'),sourceLink(s),el('p',s.excerpt,'small muted'));list.append(item);});panels.sources.append(list);
  const download=el('button','Download full research ↓','text-button');download.onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='comparison-research.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};panels.sources.append(download);
  root.append(el('p','Prices and availability may change.','result-footnote'));activate('overview');
}
const sharedQuery = new URL(location.href).searchParams.get('compare');
if(sharedQuery){$('query').value=sharedQuery.slice(0,600);picks=sharedQuery.split(/\s+vs\s+/i).slice(0,4);while(picks.length<2)picks.push('');drawDropdowns();$('pickerStatus').textContent='Shared shortlist loaded. Compare to fetch fresh research.';}
