"""Read-only current delivery and preserved project hash check."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
from portable import digest

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]


def main():
    baseline = json.loads((RUN / 'baseline.json').read_text())
    current = json.loads((RUN / 'DELIVERY_MANIFEST.json').read_text())
    def old(item):
        rel, expected = item
        p = RUN / 'before' / rel if rel in baseline['authorized_documents'] else ROOT / rel
        if not p.is_file() or digest(p) != expected:
            raise ValueError('Preserved asset differs: ' + rel)
    def new(item):
        rel, expected = item
        p = ROOT / rel
        if not p.is_file() or digest(p) != expected:
            raise ValueError('Current delivery differs: ' + rel)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(old, baseline['files'].items()))
        list(pool.map(new, current['files'].items()))
    print(json.dumps({'passed': True, 'historical_files': len(baseline['files']),
                      'delivery_files': len(current['files']), 'old_code_weights_results_unchanged': True,
                      'new_simulation_episodes': 0, 'scope': 'Hashes only; physical reruns are not performed.'}))


if __name__ == '__main__':
    main()
