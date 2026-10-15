from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];OLD=ROOT/'reproduction/improvement_v12_20261015_01'
jobs=[]
bases=[j for j in json.loads((OLD/'protocols/pilot_jobs.json').read_text()) if j['version']=='v12']
confirm=json.loads((OLD/'confirmation/jobs.json').read_text());analysis=json.loads((OLD/'analysis/confirmation.json').read_text())
# Nine paired regressions and three shared failures. Explicitly known now.
extra=[tuple(r) for r in analysis['regressions']]
extra += [('full_s17_clean','demo_12000014'),('full_s23_noise005','demo_12000008'),('full_s41_noise005','demo_12000008')]
for condition,demo in extra:
    b=copy.deepcopy(next(j for j in confirm if j['id']=='v12_'+condition))
    b.update(id='v12_known_'+condition+'_'+demo,demos=[demo]);bases.append(b)
for b in bases:
    for version in ['v12','support','escape','v13']:
        j=copy.deepcopy(b);j.update(id=version+'_'+b['id'].split('_',1)[1],version=version)
        if version!='v12':j['config'].update(stable_support=version in ['support','v13'],wait_escape=version in ['escape','v13'])
        jobs.append(j)
smoke_names=['held_wait_demo87','regression_6000005','known_side_s17','known_bc_k2_clean_demo_12000011',
             'known_full_s23_clean_demo_12000036','known_full_s23_noise005_demo_12000021']
smoke=[j for j in jobs if j['id'].split('_',1)[1] in smoke_names]
assert sum(len(j['demos']) for j in jobs)==200 and len(smoke)==24
for n,js in [('pilot_jobs.json',jobs),('smoke_jobs.json',smoke)]:
    with (RUN/'protocols'/n).open('x') as f:json.dump(js,f,indent=2)
print('pilot200 smoke24')
