'use strict';
// Pure browser JavaScript. Local machine learning; no framework or build step.
const $=id=>document.getElementById(id);let days=180,draws=window.LOTTERY_DATA.draws,rows=[],historyPage=1;
const dateTW=d=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(d);
const percent=v=>(100*v).toFixed(1)+'%';
function theory(t){let miss=1;for(let i=0;i<5;i++)miss*=(39-(t===0?3:4)-i)/(39-i);return 1-miss;}
function render(){const today=dateTW(new Date()),end=Date.parse(today+'T00:00:00+08:00');rows=draws.filter(d=>{const t=Date.parse(d.date+'T00:00:00+08:00');return t>=end-(days-1)*86400000&&t<=end}).sort((a,b)=>b.date.localeCompare(a.date));const stats=Array.from({length:10},(_,tail)=>{const hits=rows.filter(d=>d.numbers.some(n=>n%10===tail)).length;const gap=rows.findIndex(d=>d.numbers.some(n=>n%10===tail));return {tail,hits,rate:rows.length?hits/rows.length:0,gap:gap<0?rows.length:gap};});
$('sample').textContent=`近${days}天，共${rows.length}期：${rows.at(-1)?.date||'—'} ～ ${rows[0]?.date||'—'}`;
$('stats').innerHTML=stats.map(s=>`<tr><td>${s.tail}尾</td><td>${s.hits}</td><td>${percent(s.rate)}</td><td>${percent(theory(s.tail))}</td><td>${s.gap}${s.gap===rows.length?'以上':''}期</td></tr>`).join('');
$('tails').innerHTML=rows.length?[...stats].sort((a,b)=>b.rate-a.rate||a.tail-b.tail).slice(0,2).map(s=>`<div class="focus-pick"><div class="focus-number"><strong>${s.tail}</strong><span>尾</span></div><div>歷史頻率 ${percent(s.rate)}<br>出現 ${s.hits} / ${rows.length} 期</div></div>`).join(''):'目前區間無資料';
renderHistory();
window.renderTailAI(rows,days);
const latest=[...draws].sort((a,b)=>b.date.localeCompare(a.date))[0];$('latest').textContent=latest?`${latest.date} · 第${latest.period}期`:'無資料';$('balls').innerHTML=latest?latest.numbers.map(n=>`<span>${String(n).padStart(2,'0')}</span>`).join(''):'';}
function renderHistory(){
const totalPages=Math.max(1,Math.ceil(rows.length/10));historyPage=Math.max(1,Math.min(historyPage,totalPages));
const offset=(historyPage-1)*10,visible=rows.slice(offset,offset+10);
$('history').innerHTML=visible.map(d=>`<tr><td>${d.date}</td><td>${d.period}</td><td>${d.numbers.map(n=>String(n).padStart(2,'0')).join('　')}</td></tr>`).join('');
$('page-info').textContent=rows.length?`第 ${historyPage} / ${totalPages} 頁 · 第 ${offset+1}–${offset+visible.length} 期，共 ${rows.length} 期`:'目前區間無開獎資料';
$('prev-page').disabled=historyPage<=1;$('next-page').disabled=historyPage>=totalPages;
}
$('prev-page').onclick=()=>{historyPage--;renderHistory();};
$('next-page').onclick=()=>{historyPage++;renderHistory();};
function tick(){window.updatePredictionStatus?.();const now=new Date(),day=dateTW(now);let target=new Date(day+'T20:30:00+08:00');const dow=new Date(day+'T12:00:00+08:00').getUTCDay();if(dow!==0&&now>=target&&now<new Date(day+'T21:30:00+08:00')&&!draws.some(d=>d.date===day)){$('schedule').textContent=day;$('countdown').textContent='開獎時段中，等待公告';return;}if(now>=target)target=new Date(+target+86400000);while(new Date(+target+28800000).getUTCDay()===0)target=new Date(+target+86400000);let sec=Math.max(0,Math.floor((target-now)/1000));$('schedule').textContent=dateTW(target)+' 20:30 起';$('countdown').textContent=[Math.floor(sec/3600),Math.floor(sec/60)%60,sec%60].map(n=>String(n).padStart(2,'0')).join(' : ');}
document.querySelectorAll('[data-days]').forEach(b=>b.onclick=()=>{days=Number(b.dataset.days);historyPage=1;document.querySelectorAll('[data-days]').forEach(x=>x.classList.toggle('selected',x===b));render();});

let fetchedAt=window.LOTTERY_DATA.fetchedAt;
function status(message='') {const age=(Date.now()-Date.parse(fetchedAt))/3600000; $('status').textContent=(location.protocol==='file:'?'':'已發布資料 · ')+'官方資料取得時間：'+new Date(fetchedAt).toLocaleString('zh-TW',{timeZone:'Asia/Taipei'})+(age>2?' · 超過2小時未更新，請檢查 GitHub Actions':'')+(message?' · '+message:'');}

function health(s){$('sync-health').textContent=`${s.state==='ok'?'同步正常':'同步異常'} · ${s.message} · 最後成功更新：${s.lastSuccessAt?new Date(s.lastSuccessAt).toLocaleString('zh-TW',{timeZone:'Asia/Taipei'}):'尚未成功'} · 最近檢查：${s.checkedAt?new Date(s.checkedAt).toLocaleString('zh-TW',{timeZone:'Asia/Taipei'}):'—'}`;$('sync-health').classList.toggle('warn',s.state!=='ok');}
function valid(d){
 if(d?.schemaVersion!==3||!Array.isArray(d.draws)||!d.draws.length||!d.ai||d.ai.rule!=='both-distinct-tails-v1'||!Number.isFinite(Date.parse(d.fetchedAt)))return false;
 const ids=new Set();
 for(const r of d.draws){if(!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!/^\d{9}$/.test(r.period)||!Array.isArray(r.numbers)||r.numbers.length!==5||new Set(r.numbers).size!==5||r.numbers.some(n=>!Number.isInteger(n)||n<1||n>39)||ids.has(r.period))return false;ids.add(r.period);}
 const p=d.ai.prediction;return p&&p.tails.length===2&&new Set(p.tails).size===2&&p.tails.every(t=>Number.isInteger(t)&&t>=0&&t<=9)&&p.afterPeriod===[...d.draws].sort((a,b)=>b.date.localeCompare(a.date))[0].period;
}
let syncing=false;
async function sync(){
 if(location.protocol==='file:'){status();return;}if(syncing)return;syncing=true;
 try{
  const sr=await fetch('./status.json?t='+Date.now(),{cache:'no-store'});if(!sr.ok)throw Error();const s=await sr.json();if(!['ok','error'].includes(s.state))throw Error();health(s);
  if(s.state==='error'){status('同步失敗，保留目前開獎資料與預測');return;}
  if(s.snapshotId===window.LOTTERY_DATA.snapshotId){tick();return;}
  const r=await fetch('./data.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error();const d=await r.json();if(!valid(d)||d.snapshotId!==s.snapshotId||Date.parse(d.fetchedAt)<Date.parse(fetchedAt))throw Error();
  window.LOTTERY_DATA=d;draws=d.draws;fetchedAt=d.fetchedAt;render();tick();status('資料版本已自動更新');
 }catch{$('sync-health').textContent='目前無法確認線上同步狀態，保留目前資料。';$('sync-health').classList.add('warn');status('讀取更新失敗，保留目前資料');}finally{syncing=false;}
}
status();render();tick();sync();setInterval(tick,1000);setInterval(sync,60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
