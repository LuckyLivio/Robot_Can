"""Standard-library-only hash check of the portable copied figure bundle."""
from pathlib import Path
import csv,hashlib,json
OUT=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    with (OUT/'FIGURE_PROVENANCE.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    for row in rows:
        p=OUT/row['bundle_relative_path'];assert p.is_file(),p
        assert sha(p)==row['sha256'],p
        assert p.stat().st_size==int(row['bytes']),p
        if p.suffix=='.pdf':assert p.read_bytes().startswith(b'%PDF-'),p
        if p.suffix=='.png':assert p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),p
        if p.suffix=='.svg':assert '<svg' in p.read_text(encoding='utf8'),p
    source=json.loads((OUT/'SOURCE_MATERIAL_MANIFEST.json').read_text(encoding='utf8'))
    for row in source:
        assert sha(OUT/row['bundle_relative_path'])==row['sha256'],row
    groups=json.loads((OUT/'FIGURE_GROUPS.json').read_text(encoding='utf8'))
    assert {r['group_id'] for r in rows}=={g['group_id'] for g in groups}
    print(json.dumps({'passed':True,'figure_groups':len(groups),'figure_files':len(rows),'source_files':len(source),'new_training_steps':0,'new_model_inference':0,'new_simulation_episodes':0},ensure_ascii=False))
if __name__=='__main__':main()
