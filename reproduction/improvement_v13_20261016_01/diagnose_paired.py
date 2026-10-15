"""Post-confirmation trace comparison; never changes controller or primary analysis."""
from pathlib import Path
import json,numpy as np
RUN=Path(__file__).resolve().parent

def traces(path):
    out={}
    for r in map(json.loads,path.open()):out.setdefault(r['demo'],[]).append(r)
    return out

if __name__=='__main__':
    data=json.loads((RUN/'analysis/confirmation.json').read_text());cache={};cases=[]
    def get(v,c,demo):
        key=(v,c)
        if key not in cache:cache[key]=traces(RUN/'confirmation'/f'{v}_{c}'/'trace.jsonl')
        return cache[key][demo]
    for ref in ['v6','v12']:
        for kind in ['rescues','regressions']:
            for condition,demo in data[kind][ref]:
                a=get(ref,condition,demo);b=get('v13',condition,demo)
                differing=next(((x,y) for x,y in zip(a,b) if not np.array_equal(x['submitted_action'],y['submitted_action'])),None)
                final={v:{'steps':len(t),'success':t[-1]['success_after'],'mode':t[-1]['recovery']['mode'],
                          'can_position':t[-1]['state_after'][16:19]} for v,t in [(ref,a),('v13',b)]}
                record={'reference':ref,'kind':kind,'condition':condition,'demo':demo,'final':final}
                if differing:
                    x,y=differing;record['first_command_difference']={'step':x['step'],
                        'same_observation':bool(np.array_equal(x['state_before'],y['state_before'])),
                        'reference_recovery':x['recovery'],'v13_recovery':y['recovery'],
                        'reference_command':x['submitted_action'],'v13_command':y['submitted_action'],
                        'state_before':y['state_before']}
                cases.append(record)
    out={'posthoc_only':True,'cases':cases,'note':'Saved trace comparison explains first divergence, not a new causal experiment or independent sample. No post-confirmation controller tuning.'}
    with (RUN/'analysis/confirmation_paired_diagnosis.json').open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps({'cases':len(cases),'rescues_vs_v6':len(data['rescues']['v6']),'regressions_vs_v6':len(data['regressions']['v6']),'rescues_vs_v12':len(data['rescues']['v12']),'regressions_vs_v12':len(data['regressions']['v12'])}))
