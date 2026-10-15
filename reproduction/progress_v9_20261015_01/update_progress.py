from pathlib import Path
import datetime,hashlib,json,re
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1];STUDY=ROOT/'reproduction/improvement_v9_20261015_01'
def main():
    current={'status':'机制测试通过 · 小测试进行中','adopted':False,'stage':None,'variants':None,'completed_episodes':0}
    for name in ['smoke_a','pilot_a','pilot_b','dev_a']:
        p=STUDY/name
        if not (p/'started.json').exists():continue
        current['stage']=name;current['status']=name+' · 运行中';rows={};n=0
        for f in p.glob('*/result.json'):
            try:d=json.loads(f.read_text());rs=d['records']
            except (json.JSONDecodeError,KeyError):continue
            v=d['job']['version'];r=rows.setdefault(v,{'success':0,'episodes':0});r['success']+=sum(x['success'] for x in rs);r['episodes']+=len(rs);n+=len(rs)
        current.update(variants=rows,completed_episodes=n)
        if (p/'completed.json').exists():current['status']=name+' · 已完成，核验中'
    if (STUDY/'analysis/final_receipt.json').exists():current.update(json.loads((STUDY/'analysis/final_receipt.json').read_text()))
    payload={'updated':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M +08:00'),'v9':current,
             'source':'Recorded result files. Pilot uses known conditions; these are not new independent starts.'}
    (RUN/'demo/progress.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    page=RUN/'demo/index.html';html=page.read_text(encoding='utf8')
    def version(m):
        attr,url=m.groups();p=url.split('?')[0];f=RUN/'demo'/p
        return attr+'="'+p+'?v='+hashlib.sha256(f.read_bytes()).hexdigest()[:12]+'"' if f.is_file() and f.suffix in ['.js','.css'] else m.group(0)
    html=re.sub(r'(src|href)="([^"]+)"',version,html);page.write_text(html,encoding='utf8');print(current['status'],current['completed_episodes'])
if __name__=='__main__':main()
