const $ = s => document.querySelector(s);
const state = { tab:'today', symbol:'NVDA', status:null, market:null, scanner:null, detail:null, journal:null, watchlist:[], events:null, watchOnly:false, sort:'change_prev_pct', error:'' };
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (v, digits=2) => v == null || !Number.isFinite(v) ? '—' : Number(v).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const signed = (v, suffix='%') => v == null ? '—' : `${v > 0 ? '+' : ''}${number(v)}${suffix}`;
const cls = v => v == null ? 'muted' : v >= 0 ? 'positive' : 'negative';
const date = v => v ? new Date(v).toLocaleString('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}) + ' ET' : '—';
const api = async (url, options={}) => { const r=await fetch(url, options); const d=await r.json(); if(!r.ok) throw new Error(d.error || `HTTP ${r.status}`); return d; };

function heading(label,title,subtitle){ return `<div class="eyebrow">${label}</div><h1>${title}</h1><p class="lede">${subtitle}</p>`; }
function badge(s){
 const onlyVolume=s.status==='partial'&&s.issues?.every(x=>['volume','zero_volume'].includes(x));
 return s.status==='valid'?'<span class="tag">PRICE + VOLUME COMPLETE</span>':onlyVolume?'<span class="tag">PRICE COMPLETE · NO VOLUME</span>':`<span class="tag warn">${esc(s.status.toUpperCase())}${s.issues?.length?' · '+esc(s.issues.join(', ')):''}</span>`;
}
function phaseLabel(phase){return ({premarket:'PREMARKET',regular:'REGULAR SESSION',after_hours:'AFTER HOURS',market_closed:'MARKET CLOSED'})[phase]||'SESSION UNKNOWN';}
function metricCard(label,s){return `<div class="card"><div class="between"><div class="card-label">${label}</div><span class="tag">${esc(s.symbol)}</span></div><div class="big ${cls(s.change_prev_pct)}">${signed(s.change_prev_pct)}</div><div class="small">$${number(s.last)} · ${signed(s.change_open_pct)} from open · gap ${signed(s.opening_gap_pct)} · range position ${number(s.session_range_position_pct,0)}%</div></div>`;}
function infoRow(label,value){return `<div class="row"><span>${label}</span><strong class="mono">${value}</strong></div>`;}
function nearest(s){const a=s.nearest_levels?.above,b=s.nearest_levels?.below;if(!a&&!b)return 'No tracked level';const item=a&&b?(Math.abs(a.distance_pct)<=Math.abs(b.distance_pct)?a:b):(a||b);return `${esc(item.name.replaceAll('_',' '))} ${signed(item.distance_pct)}`;}

function today(){
 const m=state.market;if(!m) return loading(); const b=m.breadth;
 return heading('01 / SESSION OVERVIEW','Latest market picture.',`${phaseLabel(m.session?.phase)} · Last completed data ${date(m.cutoff)} · ${b.eligible} of ${b.configured} stocks eligible`)+
 `<div class="grid three">${Object.entries(m.benchmarks).map(([k,s])=>metricCard(k==='SPY'?'S&P 500 ETF':k==='QQQ'?'Nasdaq-100 ETF':'Small-cap ETF',s)).join('')}</div>`+
 `<div class="section"><div class="section-head"><h2>Participation & breadth</h2><span class="section-note">TRACKED STOCKS ONLY</span></div><div class="grid two"><div class="card"><div class="card-label">ADVANCING / DECLINING</div><div class="big">${b.advancing} <span class="muted" style="font-size:18px">/</span> ${b.declining}</div><div class="small">${b.eligible} of ${b.configured} tracked stocks have eligible inputs. This sample is not exchange-wide breadth.</div></div><div class="card"><div class="card-label">INPUT COVERAGE</div><div class="big ${b.coverage_pct>=90?'positive':'neutral'}">${number(b.coverage_pct,1)}%</div><div class="small">${b.coverage_pct<90?'Low coverage: avoid broad directional interpretation.':'Counts use the same information cutoff.'}</div></div></div></div>`+
 `<div class="section"><div class="section-head"><h2>Sectors & themes</h2><span class="section-note">CHANGE · GAP · RANGE LOCATION</span></div><div class="grid four">${m.sectors.map(({symbol,name,snapshot:s})=>`<div class="card"><div class="card-label">${esc(name)}</div><div class="big ${cls(s.change_prev_pct)}">${signed(s.change_prev_pct)}</div><div class="small">${symbol} · gap ${signed(s.opening_gap_pct)} · range ${number(s.session_range_position_pct,0)}%</div></div>`).join('')}</div></div>`+
 `<div class="section"><div class="section-head"><h2>Scheduled context</h2><span class="section-note">IMPORTED SOURCES</span></div>${state.events?.items?.length?`<div class="grid two">${state.events.items.map(i=>`<div class="card"><strong>${esc(i.title)}</strong><p class="small">${date(i.scheduled_at)} · ${esc(i.type)} · ${esc(i.symbols.join(', '))}</p><a href="${esc(i.source_url)}" target="_blank" rel="noopener noreferrer">Source ↗</a></div>`).join('')}</div>`:'<div class="card small">Calendar unavailable. No displayed events does not imply none are scheduled.</div>'}</div>`+
 `<div class="section"><div class="section-head"><h2>How to read this</h2></div><div class="card"><div class="callout">The percentage above compares each symbol with its previous completed session close. “Since open” isolates today’s regular session. Sector ETFs are benchmarks; their moves alone do not explain why an individual stock moved.</div></div></div>`;
}

function scanner(){
 const d=state.scanner;if(!d)return loading();const sorted=[...d.items].filter(s=>!state.watchOnly||state.watchlist.includes(s.symbol)).sort((a,b)=>(b[state.sort]??-Infinity)-(a[state.sort]??-Infinity));
 return heading('02 / STOCK DISCOVERY','Find what changed.','Rank observable metrics; a high rank is a reason to look closer, not a trading signal.')+
 `<div class="section-head"><h2>${sorted.length} of ${d.items.length} tracked stocks</h2><div class="actions"><button class="outline" data-action="watch-filter">${state.watchOnly?'Show all':'Watchlist only'}</button><button class="outline" data-sort="change_prev_pct">Day move</button><button class="outline" data-sort="opening_gap_pct">Gap</button><button class="outline" data-sort="relative_pp">Relative</button><button class="outline" data-sort="session_range_position_pct">Range position</button></div></div>`+
 `<div class="table-wrap"><table><thead><tr><th>SYMBOL</th><th>VS PRIOR CLOSE</th><th>SINCE OPEN</th><th>OPENING GAP</th><th>VS SECTOR · PP</th><th>RANGE POSITION</th><th>NEAREST LEVEL</th><th>DATA</th></tr></thead><tbody>${sorted.map(s=>`<tr data-symbol="${esc(s.symbol)}"><td class="symbol">${esc(s.symbol)}</td><td class="${cls(s.change_prev_pct)}">${signed(s.change_prev_pct)}</td><td class="${cls(s.change_open_pct)}">${signed(s.change_open_pct)}</td><td class="${cls(s.opening_gap_pct)}">${signed(s.opening_gap_pct)}</td><td class="${cls(s.relative_pp)}">${signed(s.relative_pp,' pp')}</td><td>${number(s.session_range_position_pct,0)}%</td><td>${nearest(s)}</td><td>${badge(s)}</td></tr>`).join('')}</tbody></table></div>`+
 `<p class="small">Range position is 0% at the session low and 100% at the session high. Relative values compare the stock with its mapped sector or theme ETF over the same cutoff.</p>`;
}

function chart(bars,s){
 if(!bars?.length)return '<div class="empty">No completed minute bars available.</div>';
 const values=bars.map(b=>b.c), minimum=Math.min(...bars.map(b=>b.l)), maximum=Math.max(...bars.map(b=>b.h));const range=Math.max(maximum-minimum,.001);
 const x=i=>44+i*(706/Math.max(values.length-1,1));const y=v=>226-((v-minimum)/range)*188;
 const points=values.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
 const fill=`44,245 ${points} ${x(values.length-1).toFixed(1)},245`;
 const referenceLines=[['PDH',s.levels?.previous_high,'#f7c977'],['PDL',s.levels?.previous_low,'#ed8b87'],['OPEN',s.open,'#8097aa']].filter(([,v])=>v!=null&&v>=minimum&&v<=maximum).map(([name,v,color],i)=>`<line x1="44" y1="${y(v)}" x2="750" y2="${y(v)}" stroke="${color}" stroke-dasharray="5 6" stroke-width="1"/><text x="${700-i*48}" y="${Math.max(14,y(v)-5)}" fill="${color}" font-size="10">${name}</text>`).join('');
 const label=`<text x="46" y="23" fill="#8097aa" font-size="11">${number(maximum)}</text><text x="46" y="246" fill="#8097aa" font-size="11">${number(minimum)}</text>`;
 return `<div class="chart-box"><svg viewBox="0 0 790 264" role="img" aria-label="Completed one-minute closing prices for ${esc(s.symbol)}"><line class="chart-grid" x1="44" x2="750" y1="75" y2="75"/><line class="chart-grid" x1="44" x2="750" y1="150" y2="150"/><line class="chart-grid" x1="44" x2="750" y1="225" y2="225"/><polygon class="chart-fill" points="${fill}"/>${referenceLines}<polyline class="chart-line" points="${points}"/>${label}</svg></div>`;
}

function explorer(){
 const d=state.detail;if(!d)return loading();const s=d.snapshot;
 return heading('03 / INSTRUMENT LENS',`${esc(s.symbol)} <span class="${cls(s.change_prev_pct)}">${signed(s.change_prev_pct)}</span>`,`${esc(d.mode.replaceAll('_',' '))} · ${date(s.cutoff)} · ${d.bars.length} completed minute bars shown`)+
 `<div class="actions"><button class="outline" data-action="watch-toggle">${state.watchlist.includes(s.symbol)?'Remove from watchlist':'Add to watchlist'}</button></div>`+
 `<div class="split"><div class="card"><div class="between"><h2>Price path</h2><span class="tag">1-MINUTE · COMPLETED</span></div>${chart(d.bars,s)}<div class="small" style="margin-top:12px">PDH, PDL and the session open are drawn when they fall inside the visible range.</div></div><div class="card"><h2>Price context</h2><div class="divider"></div><div class="list">${infoRow('Last completed close',s.last==null?'—':'$'+number(s.last))}${infoRow('Since prior close',`<span class="${cls(s.change_prev_pct)}">${signed(s.change_prev_pct)}</span>`)}${infoRow('Since session open',`<span class="${cls(s.change_open_pct)}">${signed(s.change_open_pct)}</span>`)}${infoRow('Opening gap',`<span class="${cls(s.opening_gap_pct)}">${signed(s.opening_gap_pct)}</span>`)}${infoRow('Session high / low',`$${number(s.session_high)} / $${number(s.session_low)}`)}${infoRow('Session range position',number(s.session_range_position_pct,0)+'%')}${infoRow('5-session return',signed(s.return_5d_pct))}${infoRow('20-session return',signed(s.return_20d_pct))}${infoRow('ATR(14)',s.atr14==null?'Insufficient history':`$${number(s.atr14)} · ${number(s.atr_pct)}%`)}${infoRow('Vs '+esc(d.benchmark??'benchmark'),signed(s.relative_pp,' pp'))}</div><div class="divider"></div>${badge(s)}</div></div>`+
 `<div class="section grid two"><div class="card"><h2>Reference levels</h2>${Object.entries(s.levels||{}).map(([key,value])=>infoRow(esc(key.replaceAll('_',' ')),value==null?'Unavailable':'$'+number(value))).join('')}${infoRow('Feed opening gap',signed(s.opening_gap_pct))}</div><div class="card"><h2>Save an observation</h2><p class="small">Record what you notice now. The server captures the current snapshot; text is optional.</p><textarea id="observation-note" class="input" placeholder="What do you expect to observe next? What might contradict it?"></textarea><div class="actions" style="margin-top:12px"><button class="pill-button" data-action="save">Save current evidence</button></div><div id="save-result" class="small" style="margin-top:10px"></div></div></div>`;
}

const concepts=[
 ['Gap','Difference between the regular-session opening reference and previous completed close. A feed opening trade is not automatically the official opening auction.'],
 ['VWAP','Volume-weighted average price across eligible regular-session bars. It depends on the feed’s volume coverage and resets at session open.'],
 ['Relative strength','Stock return minus benchmark return measured over the same interval. The result is in percentage points, not percent.'],
 ['Breadth','Count of advancing versus declining stocks in a fixed tracked universe. This is not the full US market.'],
 ['RVOL','Volume so far divided by comparable historical same-time volume. It needs enough compatible past sessions; unavailable here until validated.'],
 ['Premarket high','Highest eligible premarket trade in the observed feed window. It is a reference level, not proof of sellers’ intent.'],
 ['Previous-day high','Highest eligible regular-session price from the prior completed trading session.'],
 ['Spread','Ask minus bid from a particular quote source. A narrow quoted spread does not guarantee executable depth.'],
 ['ATR','Average true range measures historical price movement across complete daily sessions. It is not a ceiling on future movement.'],
 ['Data cutoff','Latest completed common interval used to calculate a snapshot. A bar under construction is excluded.'],
];
function learn(){return heading('04 / REFERENCE DESK','Learn as you look.','Definitions are tied to the measurements on the dashboard. Expand a concept for the practical limitation.')+`<div class="learn-grid">${concepts.map(([term,meaning])=>`<div class="card learn-card"><details><summary>${term}</summary><p>${meaning}</p></details></div>`).join('')}</div>`;}
function journal(){const items=state.journal?.items;if(!items)return loading();return heading('05 / OBSERVATION LOG','Evidence you saved.','Returns describe subsequent recorded price bars; they are not simulated trade results.')+(items.length?`<div class="grid two">${items.map(i=>`<div class="card"><div class="between"><strong>${esc(i.snapshot.symbol)}</strong><span class="tag">${esc(i.snapshot.feed)}</span></div><div class="big ${cls(i.snapshot.change_prev_pct)}">${signed(i.snapshot.change_prev_pct)}</div><div class="small">Observed ${date(i.snapshot.cutoff)} · Saved ${date(i.created_at)}</div><div class="divider"></div><p>${esc(i.note)||'<span class="muted">No note</span>'}</p>${Object.entries(i.outcomes||{}).map(([name,o])=>infoRow(name+' outcome',`${signed(o.return_pct)} · ${esc(o.status)} · ${o.bars??0} bars`)).join('')}</div>`).join('')}</div>`:'<div class="card empty">No observations yet. Open a stock and save what you notice.</div>');}
function loading(){return '<div class="card empty">Loading data…</div>';}
function render(){
 const labels={today:'TODAY',scanner:'SCANNER',explorer:'STOCK EXPLORER',learn:'LEARN',journal:'OBSERVATIONS'};
 $('#crumb').textContent=labels[state.tab];
 $('.nav.active')?.classList.remove('active');document.querySelector(`.nav[data-tab="${state.tab}"]`)?.classList.add('active');
 $('#view').innerHTML=(state.error?`<div class="error">${esc(state.error)}</div>`:'')+({today,scanner,explorer,learn,journal}[state.tab]());
}
async function refresh(){
 try{
  const [status,market,scanner]=await Promise.all([api('/api/status'),api('/api/market'),api('/api/scanner')]);
  state.status=status;state.market=market;state.scanner=scanner;
  if(!status.symbols.includes(state.symbol))state.symbol=status.symbols.find(x=>!['SPY','QQQ','XLK'].includes(x))||status.symbols[0];
  state.detail=await api(`/api/stocks/${state.symbol}`);
  [state.journal,state.events]=await Promise.all([api('/api/observations'),api('/api/events')]);
  state.watchlist=(await api('/api/watchlist')).symbols;state.error='';
  const demo=status.mode==='synthetic_example';
  $('#banner').className='banner'+(demo?'':' iex');
  const selection=`<label for="provider-select">Source</label> <select id="provider-select" class="input" aria-label="Data provider"><option value="sample" ${status.selected==='sample'?'selected':''}>Example</option><option value="alpaca" ${status.selected==='alpaca'?'selected':''} ${!status.providers.alpaca?'disabled':''}>Alpaca IEX</option><option value="etoro" ${status.selected==='etoro'?'selected':''} ${!status.providers.etoro?'disabled':''}>eToro</option></select> <button class="pill-button" data-action="probe">Load recorded data</button>`;
  $('#banner').innerHTML=`<strong>${demo?'EXAMPLE DATA · NOT A LIVE MARKET':status.mode==='recorded_etoro'?'RECORDED ETORO PRICE CANDLES':'RECORDED IEX DATA · DELAYED'}</strong> &nbsp; ${esc(status.message)} · ${esc(date(market.cutoff))}. ${status.refresh_error?`<span class="negative">Refresh failed: ${esc(status.refresh_error)}</span>`:''} ${selection}`;
  $('#side-status').textContent=demo?'● Synthetic example':status.mode==='recorded_etoro'?'● Recorded eToro':'● Recorded Alpaca IEX';
  $('#mode-short').textContent=demo?'EXAMPLE':status.mode==='recorded_etoro'?'ETORO RECORDING':'RECORDED IEX';
  $('#footer-cutoff').textContent='AS OF '+date(market.cutoff);
  if(document.activeElement?.id!=='observation-note')render();
 }catch(error){state.error=error.message;render();}
}
document.addEventListener('click',async e=>{
 if(e.target.closest('[data-action="watch-filter"]')){state.watchOnly=!state.watchOnly;render();return;}
 if(e.target.closest('[data-action="watch-toggle"]')){
  const symbols=state.watchlist.includes(state.symbol)?state.watchlist.filter(s=>s!==state.symbol):[...state.watchlist,state.symbol];
  try{state.watchlist=(await api('/api/watchlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbols})})).symbols;render();}catch(err){state.error=err.message;render();}return;
 }
 if(e.target.closest('[data-action="probe"]')){
  const banner=$('#banner');banner.textContent='Loading recorded market data…';
  try{await api('/api/provider',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:state.status.selected})});await api('/api/probe',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});await refresh();}
  catch(err){banner.textContent='Data probe failed: '+err.message+' · The example dataset remains active.';}
  return;
 }
 const tab=e.target.closest('[data-tab]');if(tab){state.tab=tab.dataset.tab;render();return;}
 const sort=e.target.closest('[data-sort]');if(sort){state.sort=sort.dataset.sort;render();return;}
 const symbol=e.target.closest('[data-symbol]');if(symbol){state.symbol=symbol.dataset.symbol;state.tab='explorer';try{state.detail=await api(`/api/stocks/${state.symbol}`);state.error='';}catch(err){state.error=err.message;}render();return;}
 if(e.target.closest('[data-action="save"]')){
  const note=$('#observation-note').value;
  try{await api('/api/observations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:state.symbol,note})});state.journal=await api('/api/observations');$('#save-result').textContent='Saved with its current data cutoff.';$('#observation-note').value='';}catch(err){$('#save-result').textContent=err.message;}
 }
});
document.addEventListener('change',async e=>{if(e.target.id==='provider-select'){
 try{await api('/api/provider',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:e.target.value})});await refresh();}catch(err){state.error=err.message;render();}
}});
$('#clock').textContent=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date())+' ET';
refresh();
setInterval(refresh,45000);
