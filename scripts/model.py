"""Port of existing regularized logistic model; both distinct tails must occur."""
import math
import numpy as np
from common import digest
VERSION='logistic-both-180d-v2'
RULE='both-distinct-tails-v1'
def theory(t):return 1-math.comb(39-(3 if t==0 else 4),5)/math.comb(39,5)
PRIOR=np.array([theory(t) for t in range(10)])
def both_theory(tails):
    if len(tails)!=2 or len(set(tails))!=2:raise ValueError('Exactly two distinct tails required')
    a,b=[3 if t==0 else 4 for t in tails]
    return 1-math.comb(39-a,5)/math.comb(39,5)-math.comb(39-b,5)/math.comb(39,5)+math.comb(39-a-b,5)/math.comb(39,5)
def hit(tails,numbers):
    if len(tails)!=2 or len(set(tails))!=2:raise ValueError('Exactly two distinct tails required')
    return set(tails).issubset({n%10 for n in numbers})
def features(rows):
    y=np.zeros((len(rows),10))
    for i,r in enumerate(rows):y[i,[n%10 for n in r['numbers']]]=1
    sums=np.vstack([np.zeros(10),y.cumsum(axis=0)]);gap=np.zeros(10);xx=[]
    for i in range(len(rows)+1):
        f=(sums[i]-sums[max(0,i-20)])/min(i,20) if i else PRIOR
        xx.append(np.column_stack([f-PRIOR,(np.minimum(gap,10)-(1-PRIOR)/PRIOR)/10]))
        if i<len(rows):gap=np.where(y[i],0,gap+1)
    return np.array(xx),y
def forecast(x,y,limit):
    if limit<45:raise ValueError('At least 45 draws required')
    train=x[20:limit].reshape(-1,2);labels=y[20:limit].reshape(-1)
    offset=np.tile(np.log(PRIOR/(1-PRIOR)),limit-20);w=np.zeros(2)
    for _ in range(250):
        p=1/(1+np.exp(-(offset+train@w)))
        w-=.8*(train.T@(p-labels)/len(labels)+.06*w)
    p=1/(1+np.exp(-(np.log(PRIOR/(1-PRIOR))+x[limit]@w)))
    tails=sorted(range(10),key=lambda t:(-p[t],t))[:2]
    return dict(tails=tails,probabilities=p.tolist(),baseline=both_theory(tails))
def analyze(rows):
    # The caller supplies only the fixed 180-calendar-day analysis window.
    seq=sorted(rows,key=lambda r:r['date']);x,y=features(seq)
    if len(seq)<45:raise ValueError('Insufficient history')
    records=[]
    for i in range(max(45,len(seq)-100),len(seq)):
        p=forecast(x,y,i)
        records.append(dict(period=seq[i]['period'],date=seq[i]['date'],numbers=seq[i]['numbers'],tails=p['tails'],hit=hit(p['tails'],seq[i]['numbers']),baseline=p['baseline'],trainedThrough=seq[i-1]['period'],modelVersion=VERSION,kind='historical_backtest',rule=RULE))
    result=forecast(x,y,len(seq))
    return dict(next=result,backtest=records,historyCount=len(seq),modelVersion=VERSION,rule=RULE,trainingHash=digest([dict(period=r['period'],date=r['date'],numbers=r['numbers']) for r in seq]))
