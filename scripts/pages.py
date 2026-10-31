"""Inspect existing Pages mode; trigger legacy build without changing settings.

Uses the job-scoped GITHUB_TOKEN from the environment; never prints it.
"""
import argparse
import json
import os
import subprocess
import time
import urllib.request
from common import ROOT,read

def api(path,method='GET'):
    req=urllib.request.Request('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/'+path,method=method,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def inspect():
    info=api('pages');mode=info.get('build_type','legacy');source=info.get('source',{})
    if mode=='legacy' and (source.get('branch')!=os.environ['GITHUB_REF_NAME'] or source.get('path')!='/'):
        raise RuntimeError('Pages source is not this branch/root; review Settings > Pages before deployment')
    print(json.dumps(dict(buildType=mode,source=source,url=info['html_url'])))
    with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'mode={mode}\nurl={info["html_url"]}\n')

def verify(url):
    expected=read(ROOT/'data.json')['snapshotId'];health=read(ROOT/'status.json')
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        try:
            def fetch(name):
                request=urllib.request.Request(url.rstrip('/')+'/'+name+'?verify='+str(time.time_ns()),headers={'Cache-Control':'no-cache'})
                with urllib.request.urlopen(request,timeout=25) as r:return json.load(r)
            data=fetch('data.json');status=fetch('status.json')
            if data.get('snapshotId')==expected and status.get('checkedAt')==health.get('checkedAt') and status.get('snapshotId')==expected:
                print('Verified public Pages snapshot:',expected);return
        except Exception as exc:print('Waiting for Pages propagation:',type(exc).__name__)
        time.sleep(10)
    raise TimeoutError('Public Pages snapshot did not match; do not confirm a prediction')

def legacy(url):
    expected=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    api('pages/builds','POST')
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        build=api('pages/builds/latest')
        if build.get('commit')==expected:
            if build['status']=='built':verify(url);return
            if build['status']=='errored':raise RuntimeError('Pages build failed: '+str(build.get('error')))
        time.sleep(10)
    raise TimeoutError('Pages build was not confirmed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['inspect','legacy','verify']);p.add_argument('--url');args=p.parse_args()
    if args.command=='inspect':inspect()
    elif args.command=='legacy':legacy(args.url)
    else:verify(args.url)
