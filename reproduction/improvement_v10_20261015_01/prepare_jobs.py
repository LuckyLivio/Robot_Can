from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];jobs=[]
for base in json.loads((ROOT/'reproduction/improvement_v9_20261015_01/protocols/pilot_jobs.json').read_text()):
    if base['version']!='v9':continue
    for v in ['v9','height','path','v10']:
        j=copy.deepcopy(base);j['id']=v+base['id'][2:];j['version']=v
        if v!='v9':j['config'].update(adaptive_height=v in ['height','v10'],edge_path=v in ['path','v10'])
        jobs.append(j)
assert sum(len(j['demos']) for j in jobs)==148
smoke=[j for j in jobs if j['version']!='v9' and any(t in j['id'] for t in ['regression_6000005','regression_6000049','known_side_s17'])]
for name,data in [('pilot_jobs.json',jobs),('smoke_jobs.json',smoke)]:
    with (RUN/'protocols'/name).open('x') as f:json.dump(data,f,indent=2)
print('pilot',sum(len(j['demos']) for j in jobs),'smoke',sum(len(j['demos']) for j in smoke))
