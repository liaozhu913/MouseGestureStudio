param(
    [string]$Version = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$appName = "MouseGestureStudio"
$buildScript = Join-Path $PSScriptRoot "build.ps1"
$installerScripts = Join-Path $PSScriptRoot "installer"
$installScript = Join-Path $installerScripts "install.ps1"
$uninstallScript = Join-Path $installerScripts "uninstall.ps1"
$buildInstallerDir = Join-Path $root "build\installer"
$packageDistRoot = Join-Path $root "build\package-dist"
$packageBuildRoot = Join-Path $root "build\package-build"
$distApp = Join-Path $packageDistRoot $appName
$payloadDir = Join-Path $buildInstallerDir "payload"
$payloadAppDir = Join-Path $payloadDir $appName
$payloadZip = Join-Path $buildInstallerDir "$appName.zip"

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $root "artifacts"
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $initFile = Join-Path $root "src\mouse_gesture_studio\__init__.py"
    $initText = Get-Content -Raw -Encoding UTF8 $initFile
    $match = [regex]::Match($initText, '__version__\s*=\s*"([^"]+)"')
    if ($match.Success) {
        $Version = $match.Groups[1].Value
    }
    else {
        $Version = "0.0.0"
    }
}

$iexpress = Join-Path $env:WINDIR "System32\iexpress.exe"
if (-not (Test-Path $iexpress)) {
    $iexpress = Join-Path $env:WINDIR "SysWOW64\iexpress.exe"
}
if (-not (Test-Path $iexpress)) {
    throw "IExpress was not found on this Windows installation."
}

& $buildScript -DistRoot $packageDistRoot -BuildRoot $packageBuildRoot -SkipStop

if (-not (Test-Path (Join-Path $distApp "$appName.exe"))) {
    throw "Application build output not found: $distApp"
}

Remove-Item -Recurse -Force $buildInstallerDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $buildInstallerDir, $payloadDir, $OutputDir | Out-Null

Copy-Item -Recurse -Force -Path $distApp -Destination $payloadAppDir
Copy-Item -Force -Path $uninstallScript -Destination (Join-Path $payloadAppDir "uninstall.ps1")

Compress-Archive -Path (Join-Path $payloadDir $appName) -DestinationPath $payloadZip -Force

$stagedInstallScript = Join-Path $buildInstallerDir "install.ps1"
$installText = Get-Content -Raw -Encoding UTF8 $installScript
$installText = $installText -replace '\$displayVersion = "[^"]*"', "`$displayVersion = `"$Version`""
Set-Content -Encoding UTF8 -Path $stagedInstallScript -Value $installText

$targetName = Join-Path $OutputDir "$appName-Setup-$Version.exe"
$sedPath = Join-Path $buildInstallerDir "$appName.sed"
$finishMessage = "$appName $Version has been installed."

Remove-Item -Force $targetName -ErrorAction SilentlyContinue

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[SourceFiles]
SourceFiles0=%SourcePath%
[SourceFiles0]
%FILE0%=
%FILE1%=
[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=$finishMessage
TargetName=$targetName
FriendlyName=$appName Installer
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1
SourcePath=$buildInstallerDir
FILE0=install.ps1
FILE1=$appName.zip
"@

Set-Content -Encoding ASCII -Path $sedPath -Value $sed

& $iexpress /N /Q $sedPath

$deadline = (Get-Date).AddSeconds(120)
$lastSize = -1
$stableCount = 0
while ((Get-Date) -lt $deadline) {
    if (Test-Path $targetName) {
        $currentSize = (Get-Item $targetName).Length
        if ($currentSize -gt 0 -and $currentSize -eq $lastSize) {
            $stableCount += 1
            if ($stableCount -ge 2) {
                break
            }
        }
        else {
            $stableCount = 0
            $lastSize = $currentSize
        }
    }
    Start-Sleep -Seconds 1
}

if (-not (Test-Path $targetName)) {
    throw "Installer was not created: $targetName"
}

Write-Host "Installer complete: $targetName"
