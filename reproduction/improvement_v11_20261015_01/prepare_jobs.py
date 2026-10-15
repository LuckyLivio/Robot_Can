from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];jobs=[]
for base in json.loads((ROOT/'reproduction/improvement_v10_20261015_01/protocols/pilot_jobs.json').read_text()):
    if base['version']!='v10':continue
    for v in ['v10','axis','guard','v11']:
        j=copy.deepcopy(base);j['id']=v+base['id'][3:];j['version']=v
        if v!='v10':j['config'].update(axis_alignment=v in ['axis','v11'],can_guard=v in ['guard','v11'])
        jobs.append(j)
smoke=[j for j in jobs if j['version']!='v10' and any(t in j['id'] for t in ['regression_6000005','regression_6000049','known_side_s17'])]
for name,data in [('pilot_jobs.json',jobs),('smoke_jobs.json',smoke)]:
    with (RUN/'protocols'/name).open('x') as f:json.dump(data,f,indent=2)
print('pilot',sum(len(j['demos']) for j in jobs),'smoke',sum(len(j['demos']) for j in smoke))
