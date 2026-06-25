$ErrorActionPreference = "Stop"

$appName = "MouseGestureStudio"
$publisher = "MouseGestureStudio"
$displayVersion = "0.2.0"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$payloadZip = Join-Path $scriptDir "$appName.zip"
$installRoot = Join-Path $env:LOCALAPPDATA "Programs"
$installDir = Join-Path $installRoot $appName
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$appName"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"
$startShortcut = Join-Path $startMenuDir "$appName.lnk"
$uninstallShortcut = Join-Path $startMenuDir "Uninstall $appName.lnk"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$appName"

function New-AppShortcut {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$IconLocation,
        [string]$Description
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $TargetPath
    if ($Arguments) {
        $shortcut.Arguments = $Arguments
    }
    if ($WorkingDirectory) {
        $shortcut.WorkingDirectory = $WorkingDirectory
    }
    if ($IconLocation) {
        $shortcut.IconLocation = $IconLocation
    }
    if ($Description) {
        $shortcut.Description = $Description
    }
    $shortcut.Save()
}

if (-not (Test-Path $payloadZip)) {
    throw "Installer payload not found: $payloadZip"
}

Get-Process -Name $appName -ErrorAction SilentlyContinue | Stop-Process -Force

$tempExtract = Join-Path ([IO.Path]::GetTempPath()) "$appName-install-$([Guid]::NewGuid().ToString('N'))"
$dataBackup = Join-Path ([IO.Path]::GetTempPath()) "$appName-data-$([Guid]::NewGuid().ToString('N'))"

try {
    New-Item -ItemType Directory -Force -Path $tempExtract, $installRoot | Out-Null

    $existingData = Join-Path $installDir "data"
    if (Test-Path $existingData) {
        Copy-Item -Recurse -Force -Path $existingData -Destination $dataBackup
    }

    Expand-Archive -Path $payloadZip -DestinationPath $tempExtract -Force

    if (Test-Path $installDir) {
        Remove-Item -Recurse -Force $installDir
    }

    $sourceDir = Join-Path $tempExtract $appName
    Copy-Item -Recurse -Force -Path $sourceDir -Destination $installDir

    if (Test-Path $dataBackup) {
        $installedData = Join-Path $installDir "data"
        if (Test-Path $installedData) {
            Remove-Item -Recurse -Force $installedData
        }
        Copy-Item -Recurse -Force -Path $dataBackup -Destination $installedData
    }

    $exePath = Join-Path $installDir "$appName.exe"
    $uninstallPath = Join-Path $installDir "uninstall.ps1"

    New-Item -ItemType Directory -Force -Path $startMenuDir | Out-Null
    New-AppShortcut -Path $startShortcut -TargetPath $exePath -WorkingDirectory $installDir -IconLocation "$exePath,0" -Description $appName
    New-AppShortcut -Path $desktopShortcut -TargetPath $exePath -WorkingDirectory $installDir -IconLocation "$exePath,0" -Description $appName
    New-AppShortcut -Path $uninstallShortcut -TargetPath "powershell.exe" -Arguments "-NoProfile -ExecutionPolicy Bypass -File `"$uninstallPath`"" -WorkingDirectory $installDir -IconLocation "$exePath,0" -Description "Uninstall $appName"

    $uninstallCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$uninstallPath`""
    $estimatedSize = [int]((Get-ChildItem -Recurse -Force $installDir | Measure-Object -Property Length -Sum).Sum / 1KB)

    New-Item -Force -Path $uninstallKey | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "DisplayName" -Value $appName -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "DisplayVersion" -Value $displayVersion -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "Publisher" -Value $publisher -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "InstallLocation" -Value $installDir -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "DisplayIcon" -Value "$exePath,0" -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "UninstallString" -Value $uninstallCommand -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "QuietUninstallString" -Value $uninstallCommand -PropertyType String | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "EstimatedSize" -Value $estimatedSize -PropertyType DWord | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "NoModify" -Value 1 -PropertyType DWord | Out-Null
    New-ItemProperty -Force -Path $uninstallKey -Name "NoRepair" -Value 1 -PropertyType DWord | Out-Null

    Start-Process -FilePath $exePath
}
finally {
    Remove-Item -Recurse -Force $tempExtract, $dataBackup -ErrorAction SilentlyContinue
}
