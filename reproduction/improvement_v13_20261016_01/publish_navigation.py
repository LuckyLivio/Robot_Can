"""Update active entry points while preserving their exact prior bytes."""
from pathlib import Path
import json,re,shutil
RUN=Path(__file__).resolve().parent;ROOT=RUN.parents[1]
docs=['README.md','index.html','STATUS.md','DEMO_GUIDE.md','RESULTS.md','EVIDENCE_INDEX.md','PROJECT_NAVIGATION.md','THESIS_HANDOFF_LATEST.md','PROGRAM_GUIDE.md']
summary='v13进行中：小测试v13为6/6，v12为3/6；正在按门槛推进消融、开发与独立确认。'
if (RUN/'SUMMARY.json').exists():summary=json.loads((RUN/'SUMMARY.json').read_text(encoding='utf8'))['headline']
banner=f'> **v13更新（2026-10-16）**：{summary} [本轮前端](reproduction/improvement_v13_20261016_01/index.html) · [本轮说明](reproduction/improvement_v13_20261016_01/README.md)。旧v12及其他代码、权重和结果保留。\n\n'
for name in docs:
    p=ROOT/name;backup=RUN/'before'/name
    if not backup.exists():shutil.copy2(p,backup)
    if name=='index.html':
        p.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=reproduction/improvement_v13_20261016_01/index.html"><title>CAN LAB</title><a href="reproduction/improvement_v13_20261016_01/index.html">打开v13成果页面</a></html>',encoding='utf8')
    else:
        s=p.read_text(encoding='utf8');s=re.sub(r'^> \*\*v13更新[^\n]*\n\n','',s)
        p.write_text(banner+s,encoding='utf8')
(RUN/'document_changes.json').write_text(json.dumps({'updated':docs},indent=2),encoding='utf8')
print(summary)
