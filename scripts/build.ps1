$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$dist = Join-Path $root "dist"
$build = Join-Path $root "build"
$spec = Join-Path $root "MouseGestureStudio.spec"

Get-Process -Name "MouseGestureStudio" -ErrorAction SilentlyContinue | Stop-Process -Force

if (Test-Path $dist) {
    Remove-Item -Recurse -Force $dist
}

if (Test-Path $build) {
    Remove-Item -Recurse -Force $build
}

if (-not (Test-Path $python)) {
    throw "Python virtual environment not found: $python"
}

if (-not (Test-Path $spec)) {
    throw "PyInstaller spec not found: $spec"
}

& $python -m PyInstaller --noconfirm $spec

Write-Host "Build complete: $dist\MouseGestureStudio"
