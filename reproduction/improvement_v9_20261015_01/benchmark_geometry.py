"""Same fixed diagnostic states: old mesh search versus cached sliced search."""
from pathlib import Path
import json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
from recovery.geometry import Search,projected_parts
from reproduction.improvement_v8_20261015_01.recovery.geometry import plan
from reproduction.improvement_v8_20261015_01.recovery.recovery_controller import RecoveryController
def main():
    results=[]
    for suffix,step in [('known_side_s41',120),('regression_6000005',140)]:
        path=ROOT/'reproduction/improvement_v8_20261015_01/pilot_b'/('v8_'+suffix)/'trace.jsonl'
        row=next(r for r in map(json.loads,path.open()) if r['step']==step);x=np.array(row['state_before'],np.float32)
        for trial in range(3):
            c=RecoveryController([.1975,.4025,.8],.8,x);tic=time.perf_counter();old,reason,n=plan(c,x);old_ms=1000*(time.perf_counter()-tic)
            projected_parts.cache_clear();tic=time.perf_counter();s=Search(c,x);init_ms=1000*(time.perf_counter()-tic);slices=[]
            while not s.done:
                tic=time.perf_counter();s.advance(8);slices.append(1000*(time.perf_counter()-tic))
            assert (old is None)==(s.chosen is None)
            if old is not None:assert old['key']==s.chosen['key']
            results.append({'case':suffix,'trial':trial,'old_monolithic_ms':old_ms,'new_init_ms':init_ms,
                            'new_slice_max_ms':max(slices,default=0),'new_total_ms':init_ms+sum(slices),'slices':len(slices),
                            'candidates':n,'chosen_same':True})
    receipt={'passed':True,'results':results,'scope':'Cold-cache serial microbenchmark on two fixed diagnostic inputs. Runtime outside these paths is excluded; not hardware-real-time certification.'}
    with (RUN/'analysis/geometry_benchmark.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt))
if __name__=='__main__':main()
