param([string]$Tag = ('candidate_truth_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')))
$ErrorActionPreference = 'Stop'
$Project = 'C:\Users\Livio\Desktop\robot_can'
Set-Location -LiteralPath $Project
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Tag must be a single safe directory name.' }
$Python = Join-Path $Project '.venv\Scripts\python.exe'
$Run = Join-Path $Project ('reproduction\' + $Tag)
if (Test-Path -LiteralPath $Run) { throw "Output already exists: $Run" }
$TraceDirectory = Join-Path $Run 'traces_real'
& $Python -B -u evaluate_delay.py --method wm --model queuepair_20261012_01_real_s17 --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --split dev --demos demo_97 demo_179 demo_105 --steps 400 --delay 2 --horizon 8 --candidates 4 --candidate-mode shift --fallback shift --fallback-index 2 --gate-margin 0.02 --score-only --trace --output-dir $TraceDirectory
if ($LASTEXITCODE -ne 0) { throw 'Trace evaluation failed.' }
$TraceResult = Join-Path $TraceDirectory 'delay_wm_dev_d2_shift_fbshift_fbi2_gm0.02_score.json'
& $Python -B -u diagnose_candidate_truth.py --trace-result $TraceResult --output-dir (Join-Path $Run 'audit')
if ($LASTEXITCODE -ne 0) { throw 'Candidate audit failed.' }
& $Python -B (Join-Path $PSScriptRoot 'summarize_results.py') --run-dir $Run
if ($LASTEXITCODE -ne 0) { throw 'Report rendering failed.' }
Write-Host "Completed: $Run"
