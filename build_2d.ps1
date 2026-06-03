$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPy = 'd:\Work\.venv\Scripts\python.exe'
$py = if (Test-Path $venvPy) { $venvPy } else { 'python' }
Set-Location $project

& $py -m PyInstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name TienLoDoKiep2D `
  --add-data "assets\audio_2d;assets\audio_2d" `
  --add-data "assets\external_oga;assets\external_oga" `
  --add-data "assets\kenney_particle_pack;assets\kenney_particle_pack" `
  --add-data "assets\kenney_tiny_dungeon;assets\kenney_tiny_dungeon" `
  --add-data "assets\ninja_adventure_pack;assets\ninja_adventure_pack" `
  --add-data "assets\valley_maps;assets\valley_maps" `
  --add-data "assets\valley_ruin_pack;assets\valley_ruin_pack" `
  game_2d.py

if ($LASTEXITCODE -eq 0) {
  Write-Host "Build complete: $project\dist\TienLoDoKiep2D\TienLoDoKiep2D.exe"
}
