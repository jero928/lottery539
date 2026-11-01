"use strict";
(()=>{
let current=null,page=1;
const el=id=>document.getElementById(id),pct=n=>Number.isFinite(n)?(n*100).toFixed(1)+'%':'—';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stamp=s=>s?new Date(s).toLocaleString('zh-TW',{timeZone:'Asia/Taipei'}):'尚未確認發布';
function records(){
 if(!current)return;
 const mode=el('record-type').value;
 const rows=mode==='backtest'?current.backtest.map(r=>({...r,modelVersion:r.modelVersion,phase:'歷史模擬',eligible:true})):
 current.records.map(v=>({date:v.result?.date||v.prediction.targetDate,period:v.prediction.period,tails:v.prediction.tails,numbers:v.result?.numbers||[],hit:v.result?.hit,eligible:v.result?.eligible,generatedAt:v.prediction.generatedAt,publishedAt:v.publication?.publishedAt,modelVersion:v.prediction.modelVersion,phase:v.publication?'實際發布':'待部署確認'}));
 rows.reverse();const pages=Math.max(1,Math.ceil(rows.length/10));page=Math.max(1,Math.min(page,pages));
 el('record-note').textContent=mode==='backtest'?'歷史模擬：每一期只使用較早開獎資料訓練，不是當時真正發布的成績。':'預測內容先保存且不可覆寫；網站成功部署並核對內容後才確認發布時間。逾時發布不列入實績。';
 el('ai-records').innerHTML=rows.slice((page-1)*10,page*10).map(r=>`<tr><td>${esc(r.date)}<small class="period-sub">第${esc(r.period)}期 · ${esc(r.phase)}</small></td><td>${r.tails.join('、')}尾</td><td><div class="result-balls">${r.numbers.length?r.numbers.map(n=>`<span class="result-ball ${r.tails.includes(n%10)?'matched':''}">${String(n).padStart(2,'0')}</span>`).join(''):'待官方公布'}</div></td><td>${r.eligible===false?'逾時／不計入':r.hit===undefined?'待開獎':r.hit?'雙尾成功':'未同時命中'}</td><td>${r.generatedAt?esc(stamp(r.generatedAt)):'歷史模擬'}<small class="period-sub">${r.generatedAt?'發布：'+esc(stamp(r.publishedAt))+' · ':''}${esc(r.modelVersion)}</small></td></tr>`).join('')||'<tr><td colspan="5">尚無紀錄</td></tr>';
 el('ai-page').textContent=`第${page}/${pages}頁 · 共${rows.length}期`;el('ai-prev').disabled=page<=1;el('ai-next').disabled=page>=pages;
}
window.renderTailAI=()=>{
 current=window.LOTTERY_DATA.ai;
 if(!current){el('ai-tails').textContent='等待有效模型資料';return;}
 const p=current.prediction,s=current.liveSummary;
 if(p){el('ai-scope').textContent=`第${p.period}期 · 預定${p.targetDate} · ${p.windowDays?"近"+p.windowDays+"天 · ":""}使用${p.historyCount}期資料`;
 el('ai-tails').innerHTML=p.tails.map(t=>`<div class="focus-pick"><div class="focus-number"><strong>${t}</strong><span>尾</span></div><div><b>單尾模型估計 ${pct(p.probabilities[t])}</b><p>對應號碼 ${Array.from({length:39},(_,i)=>i+1).filter(n=>n%10===t).map(n=>String(n).padStart(2,'0')).join('、')}</p></div></div>`).join('');
 el('ai-note').textContent=`兩個不同尾數必須都出現才算成功。產生：${stamp(p.generatedAt)} · ${p.modelVersion}。單尾機率不是雙尾同時命中機率。`;}
 el('ai-validation').innerHTML=`<div class="accuracy-grid"><div><span>雙尾同時命中率</span><b>${pct(s.rate)}</b><p>成功${s.hits}期／已結算${s.settled}期</p></div><div><span>實際發布總期數</span><b>${s.totalPredictions}</b><p>待開獎${s.pending}期 · 逾時排除${s.excluded}期</p></div><div><span>本組雙尾同時出現理論值</span><b>${pct(p?.baseline)}</b><p>按0尾3個、其他尾4個號碼計算</p></div></div>`;
 const bt=current.backtest,h=bt.filter(r=>r.hit).length,base=bt.reduce((n,r)=>n+r.baseline,0)/Math.max(1,bt.length);
 el('backtest-summary').textContent=`歷史模擬（獨立列示）：最近${bt.length}期雙尾同時命中 ${h}期（${bt.length?pct(h/bt.length):'—'}），同條件理論基準 ${pct(base)}。此數據不是實際發布成績。`;
 records();window.updatePredictionStatus();
};
window.updatePredictionStatus=()=>{const p=current?.prediction;if(p&&Date.now()>=Date.parse(p.targetDate+'T20:30:00+08:00'))el('ai-scope').textContent=`第${p.period}期 · 已到預定開獎時間，等待官方最新結果 · ${p.windowDays?"近"+p.windowDays+"天 · ":""}使用${p.historyCount}期資料`;};
el('record-type').onchange=()=>{page=1;records();};el('ai-prev').onclick=()=>{page--;records();};el('ai-next').onclick=()=>{page++;records();};
})();
