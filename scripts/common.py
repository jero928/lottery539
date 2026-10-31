import datetime as dt
import hashlib
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TZ=dt.timezone(dt.timedelta(hours=8))
def now(): return dt.datetime.now(TZ)
def read(path,default=None):return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf8')
    os.replace(temp,path)
def audit(root,event,**kwargs):
    p=root/'archive'/'updates.jsonl';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf8') as f:f.write(json.dumps(dict(at=now().isoformat(),event=event,**kwargs),ensure_ascii=False)+'\n')
