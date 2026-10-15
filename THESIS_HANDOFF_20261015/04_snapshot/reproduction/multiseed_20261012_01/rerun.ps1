param([string]$Tag = ('multiseed_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')))
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Tag must be a new simple directory name.' }
$taskRun = Join-Path $taskRoot ('reproduction\' + $Tag)
if (Test-Path -LiteralPath $taskRun) { throw 'Output already exists; choose a new Tag.' }
Push-Location $taskRoot
try {
    $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
    @'
from pathlib import Path
import hashlib,json,sys
root=Path.cwd();run=Path(sys.argv[1]);assert not run.exists()
before={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and not any(s in p.parts for s in ('.venv','__pycache__','.git','.idea'))}
run.mkdir()
(run/'before_manifest.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
'@ | & $taskPython -X utf8 -B -u - $taskRun
    if ($LASTEXITCODE -ne 0) { throw 'Snapshot failed.' }
    $taskScripts = @('register_suite.py','train_suite.py','evaluate_suite.py','run_suite.py','validate_suite.py','check_training.py','evaluate_offline.py','analyze_suite.py','finalize_suite.py')
    foreach ($taskScript in $taskScripts) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $taskScript) -Destination $taskRun }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'rerun.ps1') -Destination $taskRun
    foreach ($taskScript in @('register_suite.py','validate_suite.py')) {
        & $taskPython -X utf8 -B -u (Join-Path $taskRun $taskScript)
        if ($LASTEXITCODE -ne 0) { throw ($taskScript + ' failed.') }
    }
    & $taskPython -X utf8 -B -u (Join-Path $taskRun 'run_suite.py') --phase train
    if ($LASTEXITCODE -ne 0) { throw 'Training failed. Inspect the separate logs.' }
    & $taskPython -X utf8 -B -u (Join-Path $taskRun 'check_training.py')
    if ($LASTEXITCODE -ne 0) { throw 'Training verification failed.' }
    & $taskPython -X utf8 -B -u (Join-Path $taskRun 'evaluate_offline.py')
    if ($LASTEXITCODE -ne 0) { throw 'Offline diagnostics failed.' }
    & $taskPython -X utf8 -B -u (Join-Path $taskRun 'run_suite.py') --phase evaluate
    if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed. Inspect the separate logs.' }
    foreach ($taskScript in @('analyze_suite.py','finalize_suite.py')) {
        & $taskPython -X utf8 -B -u (Join-Path $taskRun $taskScript)
        if ($LASTEXITCODE -ne 0) { throw ($taskScript + ' failed.') }
    }
    Write-Output ('Complete: ' + (Join-Path $taskRun 'analysis\report.txt'))
} finally { Pop-Location }
