"""Portable repository entry point. No command means help; reruns default to dry-run."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import subprocess
import sys
from portable import digest, serve, verify

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[1]
EXPERIMENTS = {
    'v11-development': ('improvement_v11_20261015_01', 'dev_a'),
    'v5-native': ('recovery_v5_20261012_01', 'confirmation'),
    'v5-geometry': ('recovery_v5_20261012_01', 'geometry_confirmation'),
}


def check_inputs():
    frozen = json.loads((RUN / 'REPRODUCTION_MANIFEST.json').read_text(encoding='utf8'))
    def check(item):
        if digest(ROOT / item['path']) != item['sha256']:
            raise ValueError('Frozen reproduction input changed: ' + item['path'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(check, frozen['files']))
    return len(frozen['files'])


def plan(experiment, output, job_id=None):
    folder, stage = EXPERIMENTS[experiment]
    study = ROOT / 'reproduction' / folder
    jobs_path = study / stage / 'jobs.json'
    jobs = json.loads(jobs_path.read_text(encoding='utf8'))
    if job_id:
        jobs = [job for job in jobs if job['id'] == job_id]
        if not jobs:
            raise ValueError('Unknown job-id for this frozen experiment')
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise FileExistsError('Output must be a NEW directory: ' + str(output))
    if output.is_relative_to(ROOT) and not output.is_relative_to(RUN / 'outputs'):
        raise ValueError('Inside this repository, output must be under this delivery/outputs directory')
    commands = []
    for job in jobs:
        name = job['id']
        if Path(name).name != name or name in {'.', '..'}:
            raise ValueError('Unsafe job ID')
        commands.append([sys.executable, '-X', 'utf8', '-B', '-u',
                         str(study / 'evaluate_recovery.py'), '--job-file', str(output / 'jobs.json'),
                         '--job-id', name, '--output-dir', str(output / name)])
    return {'experiment': experiment, 'output': str(output), 'jobs': jobs,
            'episodes': sum(len(job['demos']) for job in jobs), 'commands': commands,
            'scope': 'Repeat frozen known starts; NOT new independent confirmation.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command')
    sub.add_parser('verify', help='Verify preserved repository files and current delivery.')
    sub.add_parser('probe-models', help='7 saved-observation forwards and pip check; no environment/episode.')
    sub.add_parser('list-jobs', help='List frozen suites and job IDs.')
    demo = sub.add_parser('serve', help='Show built portable package.')
    demo.add_argument('--package', required=True, type=Path)
    demo.add_argument('--port', type=int, default=8767)
    demo.add_argument('--open', action='store_true')
    run = sub.add_parser('rerun', help='Plan a frozen run; --execute is required to simulate.')
    run.add_argument('--experiment', required=True, choices=EXPERIMENTS)
    run.add_argument('--output', required=True)
    run.add_argument('--job-id')
    run.add_argument('--execute', action='store_true')
    a = p.parse_args()
    if a.command is None:
        p.print_help()
        return
    if a.command == 'verify':
        subprocess.run([sys.executable, '-X', 'utf8', '-B', str(RUN / 'verify_delivery.py')], check=True)
    elif a.command == 'probe-models':
        check_inputs()
        subprocess.run([sys.executable, '-X', 'utf8', '-B', str(RUN / 'probe_models.py')], cwd=ROOT, check=True)
    elif a.command == 'serve':
        print(json.dumps(verify(a.package)))
        serve(a.package, a.port, a.open)
    elif a.command == 'list-jobs':
        for name, (folder, stage) in EXPERIMENTS.items():
            jobs = json.loads((ROOT / 'reproduction' / folder / stage / 'jobs.json').read_text())
            print(json.dumps({'experiment': name, 'episodes': sum(len(j['demos']) for j in jobs),
                              'jobs': [j['id'] for j in jobs]}))
    else:
        request = plan(a.experiment, a.output, a.job_id)
        count = check_inputs()
        if not a.execute:
            print(json.dumps({**request, 'execute': False, 'input_hashes_checked': count}, ensure_ascii=False, indent=2))
            return
        out = Path(request['output'])
        out.mkdir(parents=True, exist_ok=False)
        (out / 'jobs.json').write_text(json.dumps(request['jobs'], indent=2), encoding='utf8')
        (out / 'request.json').write_text(json.dumps(request, indent=2), encoding='utf8')
        # Sequential execution keeps resource use predictable on a new machine.
        for job, command in zip(request['jobs'], request['commands']):
            with (out / (job['id'] + '.log')).open('x', encoding='utf8') as log:
                subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            result = json.loads((out / job['id'] / 'result.json').read_text())
            if result['status'] != 'complete' or len(result['records']) != len(job['demos']):
                raise ValueError('Incomplete job: ' + job['id'])
        check_inputs()
        (out / 'completed.json').write_text(json.dumps({'complete': True, 'episodes': request['episodes'],
            'independent_confirmation': False, 'experiment': a.experiment}), encoding='utf8')


if __name__ == '__main__':
    main()
