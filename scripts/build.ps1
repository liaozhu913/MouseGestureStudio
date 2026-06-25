param(
    [string]$DistRoot = "",
    [string]$BuildRoot = "",
    [switch]$SkipStop
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$dist = if ([string]::IsNullOrWhiteSpace($DistRoot)) { Join-Path $root "dist" } else { $DistRoot }
$build = if ([string]::IsNullOrWhiteSpace($BuildRoot)) { Join-Path $root "build" } else { $BuildRoot }
$spec = Join-Path $root "MouseGestureStudio.spec"

$dist = [IO.Path]::GetFullPath($dist)
$build = [IO.Path]::GetFullPath($build)

if (-not $SkipStop) {
    $running = Get-Process -Name "MouseGestureStudio" -ErrorAction SilentlyContinue
    if ($running) {
        try {
            $running | Stop-Process -Force -ErrorAction Stop
        }
        catch {
            throw "MouseGestureStudio is still running and cannot be stopped from this shell. Exit it from the tray icon or run this build from an elevated PowerShell, then retry."
        }
    }
}

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

& $python -m PyInstaller --noconfirm --distpath $dist --workpath $build $spec

Write-Host "Build complete: $dist\MouseGestureStudio"
