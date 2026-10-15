"""Recompute existing table/CI checks without training or simulation."""
from pathlib import Path
import sys,json,hashlib,csv
import numpy as np
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];sys.path.insert(0,str(ROOT))
import make_figures as plots
def read(p):return json.loads(p.read_text(encoding='utf8'))
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
    sources={}
    for p in [ROOT/'figures/figure_data.json',ROOT/'reproduction/figures_deepcheck_20261014_01/diagnostics.json']:
        for rel,h in read(p)['sources_sha256'].items():assert sha(ROOT/rel)==h,rel;sources[rel]=h
    deep=ROOT/'reproduction/figures_deepcheck_20261014_01'
    for rel,h in read(deep/'manifest.json').items():assert sha(deep/rel)==h,rel
    checked=0
    for run,n,seed,isdev in [(plots.CONF,60,2026101203,False),(plots.DEV,30,20261012,True)]:
        groups=plots.records(run,n);plots.check_summary(groups,run)
        names=read(ROOT/run/('protocol.json' if isdev else 'design.json'))['demos' if isdev else 'state_names']
        rng=np.random.default_rng(seed);si=rng.integers(0,3,(20000,3));ii=rng.integers(0,n,(20000,n))
        def matrix(method,condition):
            if condition=='joint_equal_weight':return (matrix(method,'clean')+matrix(method,'noise005'))/2
            seeds=[None]*3 if method.startswith('bc_') else [17,23,41]
            return np.array([[groups[method,s,condition][name]['success'] for name in names] for s in seeds],float)
        def ci(v):return np.quantile(v[si[:,:,None],ii[:,None,:]].mean((1,2)),[.025,.975])*100
        for row in rows(ROOT/run/'analysis/summary.csv'):
            cond=('clean' if float(row['noise'])==0 else 'noise005') if isdev else row['condition']
            prefix='crossed_bootstrap_ci_' if isdev else 'paired_crossed_bootstrap_'
            assert np.allclose(ci(matrix(row['method'],cond)),[float(row[prefix+'low_percent']),float(row[prefix+'high_percent'])],atol=1e-7);checked+=1
        if not isdev:
            for row in rows(ROOT/run/'analysis/paired_comparisons.csv'):
                assert np.allclose(ci(matrix(row['left'],row['condition'])-matrix(row['right'],row['condition'])),[float(row['paired_crossed_bootstrap_low_pp']),float(row['paired_crossed_bootstrap_high_pp'])],atol=1e-7);checked+=1
    old=read(ROOT/'reproduction/environment_check_20261011_01/verification.json')['replacements']
    for x in old:assert sha(Path(x['target']))==x['after_sha256']
    result={'passed':True,'source_hashes':len(sources),'bootstrap_rows_recomputed':checked,'records_recounted':2640,'archived_user_weight_replacements_still_match':True,'scope':'Existing raw results and original bootstrap seed/unit/20000-draw rules; no experiments or model selection.'}
    with (RUN/'statistics_validation.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
