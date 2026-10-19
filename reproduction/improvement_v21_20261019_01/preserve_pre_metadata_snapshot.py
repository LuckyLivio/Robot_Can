"""Recover the two exact pre-metadata sources referenced by static receipt a.

Only removes the later receipt metadata fields and their test assertions from
copies. Current runtime and tests are never edited. Every recovered byte stream
must match the already saved receipt hash before a snapshot is written.
"""
from pathlib import Path
import hashlib
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    old_receipt = RUN / 'analysis/place_scope_static_a.json'
    evidence = json.loads(old_receipt.read_text(encoding='utf8'))
    changes = {
        'recovery/recovery_controller.py': [(
            "        receipt['place21']={'actual_mode_at_proposal':self.mode,'controller_mode':self.mode,\n"
            "                            'phase':phase,'held':bool(held),\n",
            "        receipt['place21']={'actual_mode_at_proposal':self.mode,'phase':phase,\n")],
        'inspect_place_scope_static.py': [(
            "            assert new[1]['place21']['controller_mode'] == 'PLACE'\n"
            "            assert new[1]['place21']['held'] is True\n", ''), (
            "        if expected_scope:\n"
            "            assert actual[1]['place21']['controller_mode'] == mode\n"
            "            assert actual[1]['place21']['actual_mode_at_proposal'] == mode\n"
            "            assert actual[1]['place21']['held'] is True\n", '')],
    }
    restored = []
    # Prepare and verify every reconstructed source before writing any file.
    for relative, replacements in changes.items():
        source = RUN / relative
        original = source.read_bytes()
        text = original.decode('utf8')
        for before, after in replacements:
            assert text.count(before) == 1, (relative, 'Exact reconstruction context')
            text = text.replace(before, after)
        content = text.encode('utf8')
        key = source.relative_to(ROOT).as_posix()
        assert sha(content) == evidence['source_sha256'][key], (relative, 'Historical SHA mismatch')
        restored.append((source, content, sha(original), key))
    destination = RUN / 'validation/pre_metadata_snapshot'
    assert not destination.exists(), 'Preserve existing snapshot; never overwrite'
    destination.mkdir()
    records = []
    for source, content, current_sha, key in restored:
        target = destination / source.relative_to(RUN)
        target.parent.mkdir(exist_ok=True, parents=True)
        with target.open('xb') as handle:
            handle.write(content)
        assert sha(source.read_bytes()) == current_sha
        records.append({'original_path': key, 'snapshot_path': target.relative_to(ROOT).as_posix(),
                        'sha256': sha(content), 'matches_original_receipt': True,
                        'current_source_unchanged': True, 'current_source_sha256': current_sha})
    record = {'passed': True, 'historical_receipt': old_receipt.relative_to(ROOT).as_posix(),
              'historical_receipt_sha256': sha(old_receipt.read_bytes()), 'reconstructed_sources': records,
              'scope': 'Exact historical source reconstruction verified by existing SHA256; not a rerun of the old tests.',
              'new_physics': 0, 'new_controller_replays': 0,
              'source_sha256': {Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__).read_bytes()),
                                old_receipt.relative_to(ROOT).as_posix(): sha(old_receipt.read_bytes())}}
    with (destination / 'receipt.json').open('x', encoding='utf8') as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == '__main__':
    main()
