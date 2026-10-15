param([string]$Tag = ('tailprobe_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')))
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Tag must be a simple new directory name.' }
$runRoot = Join-Path $taskRoot ('reproduction\' + $Tag)
if (Test-Path -LiteralPath $runRoot) { throw 'Output directory already exists; use a fresh Tag.' }
New-Item -ItemType Directory -Path $runRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'validate_and_register.py') -Destination $runRoot
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'analyze_probe.py') -Destination $runRoot
Push-Location $taskRoot
try {
    $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
    & $taskPython -X utf8 -B -u (Join-Path $runRoot 'validate_and_register.py')
    if ($LASTEXITCODE -ne 0) { throw 'Planning validation failed.' }
    & $taskPython -X utf8 -B -u evaluate_candidate_rollout.py --mode repeat --trace-demos demo_105 demo_124 demo_97 demo_179 --output-dir (Join-Path $runRoot 'repeat')
    if ($LASTEXITCODE -ne 0) { throw 'Repeat evaluation failed.' }
    & $taskPython -X utf8 -B -u evaluate_candidate_rollout.py --mode bc_tail --trace-demos demo_105 demo_124 demo_97 demo_179 --output-dir (Join-Path $runRoot 'bc_tail')
    if ($LASTEXITCODE -ne 0) { throw 'BC-tail evaluation failed.' }
    & $taskPython -X utf8 -B -u evaluate_delay.py --method wm --model headcal_20261012_01_calibrated_s17 --policy bc_chunk_dev_v4 --split dev --delay 2 --horizon 8 --candidates 4 --candidate-mode shift --fallback shift --fallback-index 2 --gate-margin 0.02 --risk-weight 0.5 --score-only --steps 400 --demos demo_105 demo_124 demo_97 demo_179 --trace --output-dir (Join-Path $runRoot 'original_reference')
    if ($LASTEXITCODE -ne 0) { throw 'Original evaluator reference failed.' }
    & $taskPython -X utf8 -B -u (Join-Path $runRoot 'analyze_probe.py')
    if ($LASTEXITCODE -ne 0) { throw 'Integration verification or analysis failed.' }
    Write-Output ('Complete: ' + (Join-Path $runRoot 'analysis\diagnosis.txt'))
} finally { Pop-Location }
