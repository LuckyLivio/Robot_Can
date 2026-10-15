"""Publish local, evidence-derived status without editing historical pages."""
from pathlib import Path
import json,datetime,hashlib,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
def main():
    v6=json.loads((ROOT/'reproduction/improvement_v6_20261015_01/analysis/dev_comparison.json').read_text())
    v7=json.loads((ROOT/'reproduction/improvement_v7_20261015_01/analysis/pilot_b.json').read_text())
    v8=ROOT/'reproduction/improvement_v8_20261015_01'
    current={'status':'几何核查与实现中','pilot':None,'development':None,'adopted':False}
    for name in ['pilot_a','pilot_b']:
        p=v8/'analysis'/f'{name}.json'
        if p.exists():current.update(status='小测试已完成，正在核验',pilot=json.loads(p.read_text()),stage=name)
    if (v8/'pilot_b/started.json').exists() and not (v8/'pilot_b/completed.json').exists():current['status']='第 2 轮五路消融运行中'
    if (v8/'analysis/final_receipt.json').exists():current.update(json.loads((v8/'analysis/final_receipt.json').read_text()))
    payload={'updated':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M +08:00'),
             'v6':{'development_success':v6['v6_successes'],'development_episodes':v6['episodes'],'improvement_vs_v5':v6['net_success_change'],'adopted':False},
             'v7':{v:{k:d[k] for k in ['success','episodes','rescues','regressions']} for v,d in v7['variants'].items()},'v8':current,
             'source':'Frozen JSON result summaries; stage-specific denominators. Known diagnostics are not independent confirmation.'}
    (RUN/'demo/progress.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    page=RUN/'demo/index.html';html=page.read_text(encoding='utf8')
    def version(match):
        attr,url=match.groups();path=url.split('?')[0];file=RUN/'demo'/path
        if file.is_file() and file.suffix in ['.js','.css']:
            return attr+'="'+path+'?v='+hashlib.sha256(file.read_bytes()).hexdigest()[:12]+'"'
        return match.group(0)
    html=re.sub(r'(src|href)="([^"]+)"',version,html);page.write_text(html,encoding='utf8')
    print(payload['updated'],current['status'])
if __name__=='__main__':main()
