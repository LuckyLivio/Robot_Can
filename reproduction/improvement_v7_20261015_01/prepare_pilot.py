"""Retain exactly the 37 previously known v6 diagnostic conditions."""
from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
old=ROOT/'reproduction/improvement_v6_20261015_01/protocols/pilot_jobs_a.json'
jobs=[]
for b in json.loads(old.read_text()):
    if b['version']!='v6':continue
    for v in ['v6','pose','unknown','v7']:
        j=copy.deepcopy(b);j['version']=v;j['id']=v+b['id'][2:]
        if v!='v6':j['config'].update(replan_on_change=v in ['pose','v7'],unknown_guard=v in ['unknown','v7'])
        jobs.append(j)
assert sum(len(j['demos']) for j in jobs)==148
with (RUN/'protocols/pilot_jobs.json').open('x',encoding='utf8') as f:json.dump(jobs,f,indent=2)
print(json.dumps({'episodes':148,'variants':4,'known_diagnostics_per_variant':37}))
