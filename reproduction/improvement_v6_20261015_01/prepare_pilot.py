"""Register the four-way recovery ablation on previously known diagnostics."""
from pathlib import Path
import copy,json
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
old=ROOT/'reproduction/recovery_v5_20261012_01'
base=[j for j in json.loads((old/'pilot_jobs_b.json').read_text()) if j['version']=='v5']
extra=copy.deepcopy(next(j for j in base if j['id']=='v5_side_wall'))
extra.update(id='v5_known_pressure',dataset='reproduction/recovery_v5_20261012_01/geometry_starts.hdf5',
             demos=[f'demo_{n}' for n in [11000006,11000012,11000013,11000014]])
base.append(extra)
jobs=[]
# Interleave variants so the same family finishes at about the same time.
for b in base:
    for variant in ['v5','r1','r2','v6']:
        j=copy.deepcopy(b);j['version']=variant;j['id']=variant+b['id'][2:];j['steps']=400
        if variant!='v5':j['config'].update(aperture_guard=variant in ['r1','v6'],prevent_repeat=variant in ['r2','v6'])
        jobs.append(j)
with (RUN/'protocols/pilot_jobs_a.json').open('x',encoding='utf8') as f:json.dump(jobs,f,indent=2)
print(json.dumps({'cases_per_variant':sum(len(j['demos']) for j in base),'episodes':sum(len(j['demos']) for j in jobs),
                  'scope':'Known diagnostic starts; no independent confirmation claim.'}))
