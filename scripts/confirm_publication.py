"""Append a deployment confirmation; never rewrite a prediction's content."""
import os
from common import ROOT,now,read,write,audit
from update_data import verify_ledger,settle,build_bundle,save_public

def confirm(root=ROOT,clock=None,run_url='',commit=''):
    clock=clock or now();data=read(root/'data.json');p=data['ai']['prediction']
    ledger=read(root/'archive/predictions.json',[]);verify_ledger(ledger)
    if not p or not any(x['hash']==p['hash'] for x in ledger):raise ValueError('Candidate is not in immutable ledger')
    pubs=read(root/'archive/publications.json',[])
    if any(r['predictionHash']==p['hash'] for r in pubs):return False
    pubs.append(dict(predictionHash=p['hash'],period=p['period'],publishedAt=clock.isoformat(),runUrl=run_url,sourceCommit=commit))
    rows=read(root/'archive/history.json');model=read(root/'archive/model.json');health=read(root/'status.json')
    results=settle(ledger,pubs,rows,read(root/'archive/settlements.json',[]))
    write(root/'archive/publications.json',pubs);write(root/'archive/settlements.json',results)
    save_public(root,build_bundle(rows,model,ledger,pubs,results,health),health)
    audit(root,'publication_confirmed',period=p['period'],predictionHash=p['hash'],commit=commit)
    return True

if __name__=='__main__':
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('PAGES_VERIFIED')!='true':raise SystemExit('Requires a successfully verified Pages deployment')
    changed=confirm(run_url=os.environ['RUN_URL'],commit=os.environ['SOURCE_COMMIT'])
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('changed='+str(changed).lower()+'\n')
