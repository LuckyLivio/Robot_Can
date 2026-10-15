from pathlib import Path
import json,copy
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
jobs=[]
for base in json.loads((ROOT/'reproduction/improvement_v8_20261015_01/protocols/pilot_jobs.json').read_text()):
    if base['version'] not in ['v6','v8']:continue
    versions=['v6'] if base['version']=='v6' else ['v8','joint','bounded','v9']
    for v in versions:
        j=copy.deepcopy(base);j['id']=v+base['id'][2:];j['version']=v
        if v not in ['v6','v8']:j['config'].update(joint_selection=v in ['joint','v9'],bounded_planning=v in ['bounded','v9'])
        jobs.append(j)
assert sum(len(j['demos']) for j in jobs)==185
with (RUN/'protocols/pilot_jobs.json').open('x') as f:json.dump(jobs,f,indent=2)
smoke=[j for j in jobs if j['version'] in ['joint','bounded','v9'] and any(t in j['id'] for t in ['regression_6000005','known_side_s17'])]
with (RUN/'protocols/smoke_jobs.json').open('x') as f:json.dump(smoke,f,indent=2)
print('pilot',sum(len(j['demos']) for j in jobs),'smoke',sum(len(j['demos']) for j in smoke))
