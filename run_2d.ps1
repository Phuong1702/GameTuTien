$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPy = 'd:\Work\.venv\Scripts\python.exe'
$py = if (Test-Path $venvPy) { $venvPy } else { 'python' }
Set-Location $project
& $py game_2d.py
