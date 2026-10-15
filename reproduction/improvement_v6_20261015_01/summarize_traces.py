"""Small descriptive audit of saved traces, including latency and changed episodes."""
from pathlib import Path
import json
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def main():
    changes=[];latency=[];blocks=[];controls=0
    for j in json.loads((RUN/'dev_a/jobs.json').read_text()):
        old=ROOT/'reproduction/recovery_v5_20261012_01/dev_a'/('v5'+j['id'][2:])/'trace.jsonl'
        base={(r['demo'],r['step']):r for l in old.open() if (r:=json.loads(l))}
        changed={}
        for line in (RUN/'dev_a'/j['id']/'trace.jsonl').open():
            r=json.loads(line);controls+=1;latency.append(r['decision_ms']);b=base.get((r['demo'],r['step']))
            if b is None or r['submitted_action']!=b['submitted_action']:changed.setdefault(r['demo'],r['step'])
            if r['recovery']['mode']=='BLOCKED':blocks.append((j['id'],r['demo'],r['step']))
        changes += [{'job':j['id'],'demo':name,'first_changed_command_step':step} for name,step in changed.items()]
    result={'development_control_steps':controls,'changed_command_episodes':changes,'blocked_steps':len(blocks),
            'decision_ms':{'median':float(np.median(latency)),'p95':float(np.quantile(latency,.95)),
                           'p99':float(np.quantile(latency,.99)),'max':float(max(latency)),'over_50ms_steps':int(sum(t>50 for t in latency))},
            'timing_note':'Wall time for Full scoring plus supervisor, excludes BC inference and simulator. Four parallel workers; not a real-time hardware benchmark.'}
    with (RUN/'analysis/trace_metrics.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
