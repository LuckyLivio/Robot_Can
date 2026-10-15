"""Snapshot small plotting inputs and extract already recorded trajectories."""
from pathlib import Path
import csv, hashlib, json, shutil
RUN=Path(__file__).resolve().parent; ROOT=RUN.parents[1]
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def dump(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    target=RUN/'inputs';target.mkdir(exist_ok=False)
    groups=json.loads((ROOT/'THESIS_HANDOFF_20261015/03_figures/FIGURE_GROUPS.json').read_text(encoding='utf8'))
    paths={p for g in groups for p in g['data_sources']}
    paths.update(['THESIS_HANDOFF_20261015/03_figures/FIGURE_GROUPS.json',
        'reproduction/recovery_v5_20261012_01/analysis_dev_a/summary.json',
        'reproduction/improvement_v6_20261015_01/analysis/pilot_b.json',
        'reproduction/improvement_v6_20261015_01/analysis/dev_comparison.json',
        'reproduction/improvement_v11_20261015_01/analysis/development.json',
        'reproduction/improvement_v11_20261015_01/analysis/wall_edge_trajectories.csv',
        'reproduction/improvement_v10_20261015_01/analysis/wall_edge_trajectories.csv'])
    sources={}
    for rel in sorted(paths):
        p=ROOT/rel;q=target/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        sources[rel]={'sha256':sha(p),'bytes':p.stat().st_size,'copy':q.relative_to(RUN).as_posix()}
    traces={
        'v6_aperture_v5':('reproduction/improvement_v6_20261015_01/pilot_b/v5_known_pressure/trace.jsonl','demo_11000013'),
        'v6_aperture_v6':('reproduction/improvement_v6_20261015_01/pilot_b/v6_known_pressure/trace.jsonl','demo_11000013'),
        'v6_infeasible_v5':('reproduction/recovery_v5_20261012_01/dev_a/v5_full_s23_clean/trace.jsonl','demo_188'),
        'v6_infeasible_v6':('reproduction/improvement_v6_20261015_01/dev_a/v6_full_s23_clean/trace.jsonl','demo_188'),
        'v11_regression_v6':('reproduction/improvement_v6_20261015_01/dev_a/v6_full_s41_noise005/trace.jsonl','demo_87'),
        'v11_regression_v11':('reproduction/improvement_v11_20261015_01/dev_a/v11_full_s41_noise005/trace.jsonl','demo_87')}
    for v in ['v10','axis','guard','v11']:
        traces['v11_edge_'+v]=(f'reproduction/improvement_v11_20261015_01/pilot_a/{v}_regression_6000005/trace.jsonl','demo_6000005')
    for name,(rel,demo) in traces.items():
        p=ROOT/rel;rows=[]
        with p.open(encoding='utf8') as f:
            for line in f:
                r=json.loads(line)
                if r['demo']==demo:
                    rows.append({k:r[k] for k in ['demo','step','state_before','state_after','success_after']}|{'mode':r['recovery']['mode']})
        assert rows and all(b['step']==a['step']+1 for a,b in zip(rows,rows[1:]))
        q=target/'traces'/(name+'.json');dump(q,rows)
        sources[rel]={'sha256':sha(p),'bytes':p.stat().st_size,'extract':q.relative_to(RUN).as_posix(),'demo':demo,'records':len(rows),'extraction':'Saved state arrays, step, success and recovery mode; no simulator.'}
    dump(RUN/'PLOT_SOURCES.json',sources)
    print(json.dumps({'sources':len(sources),'trace_extracts':len(traces),'new_experiments':0}))
if __name__=='__main__':main()
