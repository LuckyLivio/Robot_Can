from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
jobs=[]
for b in json.loads((ROOT/'reproduction/improvement_v7_20261015_01/protocols/pilot_jobs.json').read_text()):
    if b['version']!='v6':continue
    for v in ['v6','v7','geometry','retreat','v8']:
        j=copy.deepcopy(b);j['version']=v;j['id']=v+b['id'][2:]
        if v!='v6':j['config'].update(replan_on_change=True,unknown_guard=True)
        if v not in ['v6','v7']:
            j['config'].update(geometry_support=v in ['geometry','v8'],retreat_replan=v in ['retreat','v8'],pose_wait_steps=60 if v in ['retreat','v8'] else 40)
        jobs.append(j)
assert sum(len(j['demos']) for j in jobs)==185
with (RUN/'protocols/pilot_jobs.json').open('x') as f:json.dump(jobs,f,indent=2)
print('185 episodes, 5 variants, same 37 known diagnostic conditions')
