"""Read-only preservation and numerical checks; no training or simulation."""
from pathlib import Path
import sys,json,hashlib,subprocess,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import make_figures as plots
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
    old=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'reproduction/figures_audit_20261014_01/verify.py')],check=True,capture_output=True,text=True,encoding='utf8')
    prior=json.loads(old.stdout);assert prior['passed']
    d=load(RUN/'diagnostics.json')
    for rel,value in d['sources_sha256'].items():assert sha(ROOT/rel)==value,rel
    for rel,value in load(RUN/'manifest.json').items():assert sha(RUN/rel)==value,rel
    checked=0
    for run,n,seed,isdev in [(plots.CONF,60,2026101203,False),(plots.DEV,30,20261012,True)]:
        groups=plots.records(run,n);plots.check_summary(groups,run)
        names=load(ROOT/run/('protocol.json' if isdev else 'design.json'))['demos' if isdev else 'state_names']
        rng=np.random.default_rng(seed);si=rng.integers(0,3,(20000,3));ii=rng.integers(0,n,(20000,n))
        def matrix(method,condition):
            if condition=='joint_equal_weight':return (matrix(method,'clean')+matrix(method,'noise005'))/2
            seeds=[None]*3 if method.startswith('bc_') else [17,23,41]
            return np.array([[groups[method,s,condition][name]['success'] for name in names] for s in seeds],dtype=float)
        def ci(values):return np.quantile(values[si[:,:,None],ii[:,None,:]].mean((1,2)),[.025,.975])*100
        for row in csvrows(ROOT/run/'analysis/summary.csv'):
            cond=('clean' if float(row['noise'])==0 else 'noise005') if isdev else row['condition']
            lo,hi=ci(matrix(row['method'],cond))
            prefix='crossed_bootstrap_ci_' if isdev else 'paired_crossed_bootstrap_'
            assert np.allclose([lo,hi],[float(row[prefix+'low_percent']),float(row[prefix+'high_percent'])],atol=1e-7)
            checked+=1
        if not isdev:
            for row in csvrows(ROOT/run/'analysis/paired_comparisons.csv'):
                v=matrix(row['left'],row['condition'])-matrix(row['right'],row['condition'])
                assert np.allclose(ci(v),[float(row['paired_crossed_bootstrap_low_pp']),float(row['paired_crossed_bootstrap_high_pp'])],atol=1e-7)
                checked+=1
    assert len(d['checkpoint_metrics'])==72 and len(d['dev_group_details'])==36
    assert max(r['mse_abs_error'] for r in d['log_recomputation_errors'])<1e-5
    assert max(r['regret_abs_error'] for r in d['log_recomputation_errors'])<1e-5
    print(json.dumps({'passed':True,'checkpoint_count':36,'fixed_set_evaluations':72,
        'bootstrap_rows_independently_recomputed':checked,'source_files_unchanged':len(d['sources_sha256']),
        'previous_figures_and_code_weights_results_unchanged':True,'prior_historical_entries_checked':prior['historical_entries_checked'],
        'preexisting_historical_differences':prior['preexisting_historical_differences'],
        'new_training_steps':0,'new_simulation_episodes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
