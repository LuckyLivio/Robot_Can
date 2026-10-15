"""Verify the Git upload's ignore/README edits against archived originals."""
import contextlib,hashlib,importlib.util,io,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; RUN=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    change=json.loads((RUN/'change.json').read_text(encoding='utf8'))
    assert digest(RUN/'gitignore_before.txt')==change['before_sha256']
    assert digest(ROOT/'.gitignore')==change['after_sha256']
    assert digest(RUN/'README_before.md')==change['readme_before_sha256']
    assert digest(ROOT/'README.md')==change['readme_after_sha256']
    spec=importlib.util.spec_from_file_location('previous_audit',ROOT/'reproduction/figures_audit_20261014_01/verify.py')
    previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
    original_digest=previous.digest
    def mapped_digest(path):
        if path==ROOT/'.gitignore':return digest(RUN/'gitignore_before.txt')
        if path==ROOT/'README.md':return digest(RUN/'README_before.md')
        return original_digest(path)
    previous.digest=mapped_digest
    output=io.StringIO()
    with contextlib.redirect_stdout(output):previous.main()
    prior=json.loads(output.getvalue());assert prior['passed']
    deep=ROOT/'reproduction/figures_deepcheck_20261014_01'
    for rel,sha in json.loads((deep/'manifest.json').read_text()).items():assert digest(deep/rel)==sha,rel
    for rel,sha in json.loads((deep/'diagnostics.json').read_text(encoding='utf8'))['sources_sha256'].items():assert digest(ROOT/rel)==sha,rel
    print(json.dumps({'passed':True,'repository':change['repository'],'historical_entries_checked':prior['historical_entries_checked'],
        'only_existing_files_changed_for_upload':['.gitignore','README.md'],
        'archives_byte_identical':True,'previous_figures_code_weights_results_unchanged':True,
        'deep_figure_audit_preserved':True,'preexisting_historical_differences':prior['preexisting_historical_differences'],
        'new_training_steps':0,'new_simulation_episodes':0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
