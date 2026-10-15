$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $projectRoot
$PY = Join-Path $projectRoot '.venv\Scripts\python.exe'
$DIAG = Join-Path $projectRoot ('reproduction\decision_diagnostic_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
if (Test-Path -LiteralPath $DIAG) { throw "Output already exists: $DIAG" }
function Run-Python {
    & $PY -B @args
    if ($LASTEXITCODE -ne 0) { throw "Python failed with exit code $LASTEXITCODE" }
}
$shared = @('evaluate_delay.py', '--model', 'fixed_20261011_234708_859_full',
    '--policy', 'bc_chunk_dev_v4', '--policy-checkpoint', 'policy_15000.pt',
    '--split', 'dev', '--demos', 'demo_105', 'demo_179', '--steps', '400',
    '--delay', '2', '--trace', '--output-dir', $DIAG)
Run-Python @shared --method wm --horizon 8 --candidates 4 --candidate-mode shift --score-only --fallback shift --fallback-index 2 --gate-margin .02 --risk-weight .5
Run-Python @shared --method bc_shift --shift-index 2
Run-Python analyze_delay_traces.py --input-dir $DIAG --output-dir (Join-Path $DIAG 'analysis')
Write-Host "Diagnostic report: $(Join-Path $DIAG 'analysis\diagnosis.txt')"
