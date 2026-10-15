from pathlib import Path
import copy, json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
old=ROOT/'reproduction/improvement_v11_20261015_01'
bases=[j for j in json.loads((old/'protocols/pilot_jobs.json').read_text()) if j['version']=='v11']
j=next(j for j in json.loads((old/'protocols/dev_jobs.json').read_text()) if j['id']=='v11_full_s41_noise005')
j=copy.deepcopy(j);j.update(id='v11_held_wait_demo87',demos=['demo_87']);bases.append(j)
jobs=[]
for b in bases:
    for v in ['v11','history','v12']:
        j=copy.deepcopy(b);j.update(id=v+'_'+b['id'].split('_',1)[1],version=v)
        if v!='v11':j['config'].update(wait_hold_history=True,passive_wait_hold=v=='v12')
        jobs.append(j)
smoke=[j for j in jobs if j['id'].split('_',1)[1] in ['held_wait_demo87','regression_6000005','known_side_s17']]
for n,js in [('pilot_jobs.json',jobs),('smoke_jobs.json',smoke)]:
    with (RUN/'protocols'/n).open('x') as f:json.dump(js,f,indent=2)
print('pilot',sum(len(j['demos']) for j in jobs),'smoke',sum(len(j['demos']) for j in smoke))
