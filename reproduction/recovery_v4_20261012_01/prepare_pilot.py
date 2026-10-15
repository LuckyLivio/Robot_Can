import json
from dataclasses import asdict
from setup_study import ROOT,RUN,write
from recovery_controller import Config

def config(version):
    return {} if version=='v2' else asdict(Config(alignment_switch=version in ['align_only','v4'],region_guard=version in ['region_only','v4']))

def main():
    old=json.loads((ROOT/'reproduction/recovery_v3_20261012_01/pilot_jobs_e.json').read_text())
    jobs=[]
    for version in ['v2','align_only','region_only','v4']:
        for j in old[:6]:
            jobs.append({**j,'id':version+j['id'][2:],'version':version,'config':config(version)})
        for method,seed,noise,demo in [('full',17,0.,6000049),('full',23,0.,6000000),('bc_k2',None,.05,6000005)]:
            jobs.append({'id':f'{version}_regression_{demo}','version':version,'method':method,'seed':seed,'noise':noise,'enabled':True,
                         'dataset':'reproduction/recovery_v3_20261012_01/confirmation_starts.hdf5','demos':[f'demo_{demo}'],'config':config(version)})
        jobs.append({'id':f'{version}_known_alignment','version':version,'method':'bc_k2','seed':None,'noise':.05,'enabled':True,
                     'demos':['demo_73'],'config':config(version)})
    write(RUN/'pilot_jobs_a.json',jobs)
    print(json.dumps({'jobs':len(jobs),'episodes':sum(len(j['demos']) for j in jobs)}))
if __name__=='__main__':main()
