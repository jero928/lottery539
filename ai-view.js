'use strict';
(()=>{
let cacheKey='',cached=null;
const pct=n=>(n*100).toFixed(1)+'%';
window.renderTailAI=(rows,days)=>{
 const key=JSON.stringify(rows);
 if(key!==cacheKey){cached=window.TailAI.modelAnalysis(rows);cacheKey=key;}
 const model=cached,scope=document.getElementById('ai-scope'),tails=document.getElementById('ai-tails'),note=document.getElementById('ai-note'),validation=document.getElementById('ai-validation'),records=document.getElementById('ai-records');
 scope.textContent=`近${days}天 · ${rows.length}期 · 資料截至${rows[0]?.date||'—'}`;
 if(!model){tails.textContent='樣本不足45期，暫不產生預測。';note.textContent='請擴大分析區間或等待資料更新。';validation.textContent='無可用回測結果';records.innerHTML='';return;}
 tails.innerHTML=model.pair.tails.map(t=>{const p=model.predictions.find(p=>p.tail===t);return `<div class="focus-pick"><div class="focus-number"><strong>${t}</strong><span>尾</span></div><div><b>模型單尾估計 ${pct(p.probability)}</b><p>理論單尾機率 ${pct(window.TailAI.theory(t))}</p><p>對應號碼 ${Array.from({length:39},(_,i)=>i+1).filter(n=>n%10===t).map(n=>String(n).padStart(2,'0')).join('、')}</p></div></div>`;}).join('');
 note.textContent='每期固定選2尾，任一尾出現算命中。對應號碼僅為尾數分類，並非全部會開出。';
 const p=model.pair;
 validation.innerHTML=`<div class="accuracy-grid"><div><span>最近${model.testDraws}期回測命中率</span><b>${pct(p.rate)}</b><p>命中${p.hits}期／共${model.testDraws}期</p></div><div><span>相同選尾條件的理論基準</span><b>${pct(p.baseline)}</b><p>兩個非0尾通常約70.5%</p></div><div><span>近似95%信賴區間</span><b class="interval-value">${pct(p.interval.low)}–${pct(p.interval.high)}</b></div></div>`;
 records.innerHTML=[...p.records].reverse().map(r=>`<tr><td>${r.date}</td><td>${r.tails.join('、')}尾</td><td><div class="result-balls">${r.numbers.map(n=>`<span class="result-ball ${r.tails.includes(n%10)?'matched':''}" title="${r.tails.includes(n%10)?'命中預測尾數':'未命中預測尾數'}">${String(n).padStart(2,'0')}</span>`).join('')}</div></td><td>${r.hit?'命中':'未中'}</td></tr>`).join('');
};
})();
