"""Read-only project inspection; new reports only, no training or simulation."""
from pathlib import Path
import importlib.util, json, subprocess, sys
RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
OLD = ROOT / 'reproduction/project_audit_20261015_01'
sys.path.insert(0, str(ROOT))

def module(name):
    spec = importlib.util.spec_from_file_location('paper_audit_' + name, OLD / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.RUN = RUN
    return mod

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'inventory'
    if mode == 'inventory':
        module('inventory').main()
        module('audit_results').main()
    elif mode == 'assets':
        module('audit_assets').main()
    elif mode in ('statistics', 'contracts'):
        name = 'verify_statistics' if mode == 'statistics' else 'audit_contracts'
        source = (OLD / (name + '.py')).read_text(encoding='utf8')
        # Keep the old verified algorithms, redirect only their report directory.
        source = source.replace('RUN=Path(__file__).resolve().parent;', 'RUN=Path(' + repr(str(RUN)) + ');')
        exec(compile(source, str(OLD / (name + '.py')), 'exec'), {'__name__': '__main__', '__file__': str(OLD / (name + '.py'))})
    else:
        raise SystemExit('Use inventory, assets, statistics, or contracts')
