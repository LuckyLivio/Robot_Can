"""Separate complete stages from the deliberately retained aborted smoke_b."""
from pathlib import Path
import json
RUN=Path(__file__).resolve().parent

def inventory():
    complete={};partial={}
    for start in sorted(RUN.glob('*/started.json')):
        folder=start.parent;name=folder.name
        jobs=json.loads((folder/'jobs.json').read_text());done=(folder/'completed.json').exists()
        counts={'requested_episodes':sum(len(j['demos']) for j in jobs),'completed_job_episodes':0,'completed_jobs':0,'incomplete_jobs':[],'not_started_jobs':[]}
        for j in jobs:
            p=folder/j['id']/'result.json'
            if not p.exists():counts['not_started_jobs'].append(j['id']);continue
            try:d=json.loads(p.read_text())
            except json.JSONDecodeError:counts['incomplete_jobs'].append({'job':j['id'],'reason':'invalid_partial_json'});continue
            if d['status']=='complete':counts['completed_jobs']+=1;counts['completed_job_episodes']+=len(d['records'])
            else:
                t=folder/j['id']/'trace.jsonl';n=0
                if t.exists():
                    for line in t.open():
                        try:json.loads(line);n+=1
                        except json.JSONDecodeError:break
                counts['incomplete_jobs'].append({'job':j['id'],'status':d['status'],'recorded_episodes':len(d['records']),'valid_trace_steps':n})
        if done:
            assert counts['completed_job_episodes']==counts['requested_episodes'] and not counts['incomplete_jobs'] and not counts['not_started_jobs'],name
            complete[name]=counts
        else:partial[name]=counts
    return {'completed_stages':complete,'incomplete_stages':partial,
            'completed_stage_executions':sum(c['completed_job_episodes'] for c in complete.values()),
            'complete_episodes_in_incomplete_stages':sum(c['completed_job_episodes'] for c in partial.values()),
            'note':'Repeated known conditions, action replays and physical replays are not independent samples. Incomplete stages are never treated as passed experiments.'}

if __name__=='__main__':
    d=inventory();(RUN/'analysis/execution_inventory.json').write_text(json.dumps(d,indent=2),encoding='utf8');print(json.dumps(d,indent=2))
