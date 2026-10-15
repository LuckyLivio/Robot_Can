"""Extract existing config, dataclass constants and citation metadata only."""
from pathlib import Path
import ast,csv,hashlib,json,shutil
PACK=Path(__file__).resolve().parents[1];SRC=PACK/'04_snapshot'
def main():
    out=PACK/'05_methods';out.mkdir(exist_ok=True)
    paths=['policy/bc_chunk_dev_v4/config.json',
           'reproduction/multiseed_20261012_01/protocol.json',
           'reproduction/confirmation_20261012_01/design.json',
           'reproduction/recovery_v5_20261012_01/study_plan.json',
           'reproduction/review_20261012_01/environment.json',
           'data/can_ph_lowdim_v15.manifest.json']
    paths += [f'models/multiseed_20261012_01_{m}_s{s}/config.json' for m in ['full','plain','direct','prediction_only'] for s in [17,23,41]]
    configs={p:json.loads((SRC/p).read_text(encoding='utf-8-sig')) for p in paths}
    code='reproduction/recovery_v5_20261012_01/recovery_controller.py'
    tree=ast.parse((SRC/code).read_text(encoding='utf-8-sig'))
    cfg=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Config')
    defaults={x.target.id:ast.literal_eval(x.value) for x in cfg.body if isinstance(x,ast.AnnAssign) and x.value is not None}
    result={'configs':configs,'recovery_v5_defaults':defaults,
            'sources_sha256':{p:hashlib.sha256((SRC/p).read_bytes()).hexdigest() for p in paths+[code]},
            'note':'Copied configuration and literal defaults, not a new runtime or experiment validation.'}
    (out/'EXTRACTED_SETTINGS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    refs=PACK/'06_references';refs.mkdir(exist_ok=True)
    for p in ['references_verified.bib','references_metadata.json']:
        shutil.copy2(SRC/'reproduction/consolidation_20261012_01'/p,refs/p)
    shutil.copy2(SRC/'RELATED_WORK.md',refs/'RELATED_WORK_ARCHIVED.md')
    metadata=json.loads((refs/'references_metadata.json').read_text(encoding='utf8'))
    rows=[{'key':r['key'],'title':r['title'],'official_url':r['url'],'metadata_checked_utc':r['checked_utc'],
           'verification_scope':r.get('scope','Official metadata, not full text'),'full_text_included':False} for r in metadata]
    with (refs/'REFERENCE_INVENTORY.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({'config_files':len(paths),'recovery_constants':len(defaults),'reference_entries':len(rows),'new_experiments':0}))
if __name__=='__main__':main()
