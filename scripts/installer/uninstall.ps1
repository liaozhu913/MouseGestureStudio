$ErrorActionPreference = "Stop"

$appName = "MouseGestureStudio"
$installDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$appName"

Get-Process -Name $appName -ErrorAction SilentlyContinue | Stop-Process -Force

Remove-Item -Recurse -Force $startMenuDir -ErrorAction SilentlyContinue
Remove-Item -Force $desktopShortcut -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $uninstallKey -ErrorAction SilentlyContinue

$trashDir = Join-Path ([IO.Path]::GetTempPath()) "$appName-uninstall-$([Guid]::NewGuid().ToString('N'))"
try {
    Move-Item -Force -Path $installDir -Destination $trashDir
}
catch {
    $trashDir = $installDir
}

$cleanupScript = Join-Path ([IO.Path]::GetTempPath()) "$appName-cleanup-$([Guid]::NewGuid().ToString('N')).ps1"
@"
Start-Sleep -Seconds 2
Remove-Item -Recurse -Force '$trashDir' -ErrorAction SilentlyContinue
Remove-Item -Force '$cleanupScript' -ErrorAction SilentlyContinue
"@ | Set-Content -Encoding UTF8 -Path $cleanupScript

Start-Process -WindowStyle Hidden -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$cleanupScript`""
