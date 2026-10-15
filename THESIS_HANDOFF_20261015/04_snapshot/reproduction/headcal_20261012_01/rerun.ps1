param([string]$Tag = ('headcal_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')))
$ErrorActionPreference = 'Stop'
$Project = 'C:\Users\Livio\Desktop\robot_can'
Set-Location -LiteralPath $Project
if ($Tag -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Tag must be a safe directory name.' }
$Python = Join-Path $Project '.venv\Scripts\python.exe'
$Run = Join-Path $Project ('reproduction\' + $Tag)
if (Test-Path -LiteralPath $Run) { throw "Output exists: $Run" }
& $Python -B -u calibrate_score_head.py --tag $Tag
if ($LASTEXITCODE -ne 0) { throw 'Calibration training failed.' }
foreach ($Arm in @('control', 'calibrated')) {
    $Model = "${Tag}_${Arm}_s17"
    & $Python -B -u evaluate_delay.py --method wm --model $Model --policy bc_chunk_dev_v4 --policy-checkpoint policy_15000.pt --split dev --episodes 30 --steps 400 --delay 2 --horizon 8 --candidates 4 --candidate-mode shift --fallback shift --fallback-index 2 --gate-margin 0.02 --score-only --output-dir (Join-Path $Run $Arm)
    if ($LASTEXITCODE -ne 0) { throw "Development evaluation failed: $Arm" }
}
& $Python -B -u analyze_head_calibration.py --tag $Tag
if ($LASTEXITCODE -ne 0) { throw 'Analysis failed.' }
Write-Host "Completed: $Run"
