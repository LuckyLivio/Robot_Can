"""Index every original v17 option chain without executing a controller."""
from collections import Counter
from pathlib import Path
import hashlib
import json

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
STAGE = ROOT/'reproduction/improvement_v17_20261019_01/smoke_a'


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    diagnosis = RUN/'analysis/short_route_diagnosis_a.json'
    prior = read(diagnosis)
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), diagnosis]}
    chains = []
    for case in prior['cases']:
        result_path = STAGE/case['job']/'result.json'
        sources[result_path.relative_to(ROOT).as_posix()] = sha(result_path)
        result = read(result_path)['records'][0]
        event = next(e for e in result['carry15_events']
                     if e['event'] == 'held_transport_search_complete' and e['step'] == case['original_finish_step'])
        chains.append({'job': case['job'], 'search_start_step': case['snapshot']['clock'],
                       'complete_original_search_event': event})
    options = [o for c in chains for o in c['complete_original_search_event']['options']]
    out = {'source_sha256': sources, 'search_count': len(chains), 'option_count': len(options),
           'new_controller_steps': 0, 'new_physical_episodes': 0,
           'option_reasons': dict(Counter(o['reason'] for o in options)),
           'accepted_candidates': dict(Counter(o['candidate'] for o in options if o['accepted'])),
           'chains': chains,
           'interpretation': 'Verbatim original finite option chains. Local IK failures stay unknown; accepted static routes do not establish closed-loop success.'}
    assert len(chains) == 23
    assert all(sha(ROOT/p) == h for p, h in sources.items())
    with (RUN/'analysis/short_route_rejection_chains_a.json').open('x', encoding='utf8') as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: out[k] for k in ['search_count', 'option_count', 'option_reasons', 'accepted_candidates']}))


if __name__ == '__main__':
    main()
