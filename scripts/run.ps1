$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$entry = Join-Path $root "src\mouse_gesture_studio\main.py"

& $python $entry

