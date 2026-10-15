"""Verify the isolated evaluator against actual original simulator rollouts."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(RUN))
import evaluate_suite
import evaluate_delay
from train_suite import write_json

def args(output,noise,names):
    return argparse.Namespace(method='wm',model='headcal_20261012_01_calibrated_s17',policy='bc_chunk_dev_v4',
        policy_checkpoint='policy_15000.pt',split='dev',episodes=30,steps=400,delay=2,shift_index=None,fallback_index=2,
        candidates=4,horizon=8,noise=noise,risk_weight=.5,readout_weight=.02,gate_margin=.02,fallback='shift',
        score_only=True,candidate_mode='shift',demos=names,output_dir=str(output),trace=True)

names=['demo_105','demo_124','demo_97','demo_179']
new_clean=evaluate_suite.run(args(RUN/'validation/clean',0.,names))
old_clean=ROOT/'reproduction/tailprobe_20261012_01/original_reference/delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json'
new_noise=evaluate_suite.run(args(RUN/'validation/noise_new',.05,['demo_105']))
old_noise=evaluate_delay.run(args(RUN/'validation/noise_original',.05,['demo_105']))
checks=[]
for label,new,old in [('clean',new_clean,old_clean),('noise005',new_noise,old_noise)]:
    a=json.loads(new.read_text());b=json.loads(old.read_text())
    for ra,rb in zip(a['records'],b['records']):
        for key in ('demo','success','steps','peak_stage_reward','ever_grasped','selection_counts'):
            assert ra[key]==rb[key],(label,key)
    for name in a['resolved_demos']:
        rows_a=[json.loads(line) for line in (new.parent/a['trace_files'][name]).read_text().splitlines()]
        rows_b=[json.loads(line) for line in (old.parent/b['trace_files'][name]).read_text().splitlines()]
        assert len(rows_a)==len(rows_b)
        for ra,rb in zip(rows_a,rows_b):
            for field in ra:
                if field=='decision_ms':continue
                assert ra[field]==rb[field],(name,ra['step'],field)
        checks.append({'condition':label,'demo':name,'steps':len(rows_a),'all_trace_fields_except_timing_identical':True})
assert json.loads((RUN/'structural_validation.json').read_text())['passed']
write_json(RUN/'validation.json',{'passed':True,'checks':checks,'total_trace_steps':sum(c['steps'] for c in checks),
          'new_evaluator_preserves_original_full_and_noise_execution':True,
          'scope':'Score-based evaluator regression and dataset/initialization structure. Prediction-only head exclusion is additionally verified after training.'})
print(json.dumps({'validation':'passed','steps':sum(c['steps'] for c in checks)}),flush=True)
