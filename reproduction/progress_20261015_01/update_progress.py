"""Publish local, evidence-derived status without editing historical pages."""
from pathlib import Path
import json,datetime
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def main():
    v6=json.loads((ROOT/'reproduction/improvement_v6_20261015_01/analysis/dev_comparison.json').read_text())
    v7=json.loads((ROOT/'reproduction/improvement_v7_20261015_01/analysis/pilot_b.json').read_text())
    v8=ROOT/'reproduction/improvement_v8_20261015_01'
    current={'status':'几何核查与实现中','pilot':None,'development':None,'adopted':False}
    for name in ['pilot_a','pilot_b']:
        p=v8/'analysis'/f'{name}.json'
        if p.exists():current.update(status='小测试已完成，正在核验',pilot=json.loads(p.read_text()),stage=name)
    if (v8/'analysis/final_receipt.json').exists():current.update(json.loads((v8/'analysis/final_receipt.json').read_text()))
    payload={'updated':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M +08:00'),
             'v6':{'development_success':236,'development_episodes':240,'improvement_vs_v5':0,'adopted':False},
             'v7':{v:{k:d[k] for k in ['success','episodes','rescues','regressions']} for v,d in v7['variants'].items()},'v8':current,
             'source':'Frozen JSON result summaries; stage-specific denominators. Known diagnostics are not independent confirmation.'}
    (RUN/'demo/progress.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    print(payload['updated'],current['status'])
if __name__=='__main__':main()
