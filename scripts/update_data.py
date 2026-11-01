"""Reliable incremental official synchronization; transactional public snapshot."""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from common import ROOT,TZ,now,read,write,digest,audit
from model import analyze,hit,both_theory,VERSION,RULE
API='https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result'
WINDOW_DAYS=180

def analysis_window(rows,clock):
    end=clock.astimezone(TZ).date()
    start=end-dt.timedelta(days=WINDOW_DAYS-1)
    return [r for r in rows if start.isoformat()<=r['date']<=end.isoformat()]

def validate(rows,today=None):
    today=today or now().date();periods={};dates={}
    for raw in rows:
        r=dict(raw);date=dt.date.fromisoformat(r['date']);period=str(r['period']);ns=r['numbers']
        if date.isoformat()!=r['date'] or date>today:raise ValueError('Invalid/future date')
        if len(period)!=9 or not period.isdigit() or int(period[:3])+1911!=date.year or int(period[3:])<1:raise ValueError('Invalid period/date')
        if not isinstance(ns,list) or len(ns)!=5 or len(set(ns))!=5 or any(type(n)!=int or not 1<=n<=39 for n in ns):raise ValueError('Invalid five numbers')
        r.update(period=period,numbers=sorted(ns),tails=sorted({n%10 for n in ns}))
        if period in periods:
            old=periods[period]
            if old['date']!=r['date'] or old['numbers']!=r['numbers']:raise ValueError('Conflicting duplicate period '+period)
            for field in ('source','updatedAt','rawSha256'):
                if field not in old and field in r:old[field]=r[field]
            continue
        if r['date'] in dates:raise ValueError('Conflicting date')
        dates[r['date']]=period;periods[period]=r
    result=sorted(periods.values(),key=lambda r:r['date'])
    if not result:raise ValueError('Empty history')
    for a,b in zip(result,result[1:]):
        if a['date'][:4]==b['date'][:4] and int(b['period'])!=int(a['period'])+1:raise ValueError('Missing/nonsequential period')
        if a['date'][:4]!=b['date'][:4] and int(b['period'][3:])!=1:raise ValueError('Missing beginning of year')
    return result

def fetch_official(root,old,clock,fetch=None):
    cutoff=clock.astimezone(TZ).date()-dt.timedelta(days=WINDOW_DAYS-1)
    start=cutoff.isoformat()[:7]
    y,m=map(int,start.split('-'));first=y*12+m-1
    last=clock.year*12+clock.month-1
    added=[]
    for serial in range(first,last+1):
        yy,mm=divmod(serial,12);month=f'{yy}-{mm+1:02d}'
        url=f'{API}?month={month}&pageNum=1&pageSize=50'
        for attempt in range(3):
            try:
                body=fetch(url) if fetch else subprocess.check_output(['curl','--fail','--silent','--show-error','--location','--max-time','30',url])
                j=json.loads(body);rr=j['content']['daily539Res']
                if j['rtCode']!=0 or len(rr)!=j['content']['totalSize']:raise ValueError('Incomplete official response')
                if serial<last and not rr:raise ValueError('Missing historical month')
                break
            except Exception:
                if attempt==2:raise
                time.sleep(attempt+1)
        sha=hashlib.sha256(body).hexdigest();path=root/'archive'/'raw'/f'{month}-{sha[:16]}.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(body)
        audit(root,'official_response',month=month,sha256=sha,url=url,count=len(rr))
        for r in rr:
            date=r['lotteryDate'][:10]
            if not date.startswith(month):raise ValueError('Official month mismatch')
            if date<cutoff.isoformat():continue
            added.append(dict(date=date,period=str(r['period']),numbers=r['drawNumberSize'],source=url,updatedAt=clock.isoformat(),rawSha256=sha))
    # Preserve every old draw; exact duplicates deduplicate, contradictions abort.
    return validate(old+added,clock.date())

def next_target(latest):
    date=dt.date.fromisoformat(latest['date'])+dt.timedelta(days=1)
    while date.weekday()==6:date+=dt.timedelta(days=1)
    period=str(int(latest['period'])+1) if date.year==int(latest['date'][:4]) else f'{date.year-1911:03d}000001'
    return period,date.isoformat()

def verify_ledger(ledger):
    prev='genesis';seen=set()
    for p in ledger:
        if p['period'] in seen or len(set(p['tails']))!=2 or len(p['tails'])!=2:raise ValueError('Invalid prediction ledger')
        if p['previousHash']!=prev or digest({k:v for k,v in p.items() if k!='hash'})!=p['hash']:raise ValueError('Prediction ledger changed')
        seen.add(p['period']);prev=p['hash']

def settle(ledger,publications,rows,existing):
    verify_ledger(ledger);by_period={r['period']:r for r in rows};events={r['predictionHash']:r for r in publications}
    results={r['predictionHash']:r for r in existing}
    for p in ledger:
        actual=by_period.get(p['period']);published=events.get(p['hash'])
        if not actual or not published or p['hash'] in results:continue
        cutoff=dt.datetime.fromisoformat(actual['date']+'T20:30:00+08:00')
        timely=dt.datetime.fromisoformat(published['publishedAt'])<cutoff and dt.datetime.fromisoformat(p['generatedAt'])<cutoff
        results[p['hash']]=dict(predictionHash=p['hash'],period=actual['period'],date=actual['date'],numbers=actual['numbers'],tails=p['tails'],hit=hit(p['tails'],actual['numbers']),eligible=timely,reason='before_draw' if timely else 'late_publication',rule=RULE)
    return list(results.values())

def build_bundle(rows,model,ledger,pubs,settlements,health):
    by_hash={r['predictionHash']:r for r in settlements};by_pub={r['predictionHash']:r for r in pubs}
    live=[r for r in settlements if r['eligible']];hits=sum(r['hit'] for r in live)
    current=next((p for p in reversed(ledger) if p['afterPeriod']==rows[-1]['period']),None)
    views=[dict(prediction=p,publication=by_pub.get(p['hash']),result=by_hash.get(p['hash'])) for p in ledger]
    ai=dict(rule=RULE,prediction=current,liveSummary=dict(totalPredictions=len(pubs),settled=len(live),hits=hits,rate=hits/len(live) if live else None,pending=sum(v['publication'] is not None and v['result'] is None for v in views),excluded=sum(not r['eligible'] for r in settlements)),backtest=model['backtest'],records=views,modelVersion=VERSION,historyCount=model['historyCount'],storedHistoryCount=len(rows),windowDays=WINDOW_DAYS)
    data=dict(schemaVersion=3,fetchedAt=health.get('lastSuccessAt'),draws=list(reversed(rows)),ai=ai)
    data['snapshotId']=digest(data)
    return data

def save_public(root,data,health):
    write(root/'data.json',data)
    temp=root/'data.js.tmp';temp.write_text('window.LOTTERY_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';',encoding='utf8');temp.replace(root/'data.js')
    write(root/'status.json',dict(health,snapshotId=data['snapshotId']))

def run(root=ROOT,fetch=None,clock=None):
    clock=clock or now()
    protected=['data.json','data.js','archive/history.json','archive/model.json','archive/predictions.json','archive/settlements.json']
    backup={n:(root/n).read_bytes() if (root/n).exists() else None for n in protected}
    previous=read(root/'status.json',{})
    try:
        old=validate(read(root/'archive/history.json',read(root/'data.json')['draws']),clock.date())
        rows=fetch_official(root,old,clock,fetch)
        training=analysis_window(rows,clock)
        signature=digest([dict(period=r['period'],date=r['date'],numbers=r['numbers']) for r in training])
        model=read(root/'archive/model.json')
        if not model or model.get('trainingHash')!=signature or model.get('modelVersion')!=VERSION:model=analyze(training)
        ledger=read(root/'archive/predictions.json',[]);verify_ledger(ledger)
        period,date=next_target(rows[-1])
        if not any(p['period']==period for p in ledger):
            p=dict(period=period,targetDate=date,afterPeriod=rows[-1]['period'],tails=model['next']['tails'],probabilities=model['next']['probabilities'],baseline=model['next']['baseline'],generatedAt=clock.isoformat(),modelVersion=VERSION+'-'+signature[:12],trainingHash=signature,historyCount=len(training),windowDays=WINDOW_DAYS,trainingStart=training[0]['date'],trainingEnd=training[-1]['date'],rule=RULE,previousHash=ledger[-1]['hash'] if ledger else 'genesis')
            p['hash']=digest(p);ledger.append(p)
        pubs=read(root/'archive/publications.json',[])
        results=settle(ledger,pubs,rows,read(root/'archive/settlements.json',[]))
        added=len(rows)-len(old)
        health=dict(state='ok',checkedAt=clock.isoformat(),lastSuccessAt=clock.isoformat(),lastNewDrawAt=clock.isoformat() if added else previous.get('lastNewDrawAt'),latestPeriod=rows[-1]['period'],latestDate=rows[-1]['date'],newDraws=added,message='新獎號及預測已更新' if added else '官方尚無新一期，保留既有資料與預測')
        data=build_bundle(rows,model,ledger,pubs,results,health)
        write(root/'archive/history.json',rows);write(root/'archive/model.json',model);write(root/'archive/predictions.json',ledger);write(root/'archive/settlements.json',results)
        save_public(root,data,health)
        audit(root,'sync_success',latest=rows[-1]['period'],added=added,prediction=period)
        print(json.dumps(dict(count=len(rows),latest=rows[-1]['period'],newDraws=added,nextPeriod=period,tails=data['ai']['prediction']['tails'],liveSettled=len([r for r in results if r['eligible']])),ensure_ascii=False))
        return True
    except Exception as exc:
        for name,content in backup.items():
            path=root/name
            if content is not None:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
            elif path.exists():path.unlink()
        write(root/'status.json',dict(previous,state='error',checkedAt=clock.isoformat(),message='同步失敗，保留上一版開獎資料與預測',detail=f'{type(exc).__name__}: {exc}'))
        audit(root,'sync_failed',detail=str(exc));print(str(exc),file=sys.stderr);return False

if __name__=='__main__':sys.exit(0 if run() else 1)
