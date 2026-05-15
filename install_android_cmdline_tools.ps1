$ErrorActionPreference = 'Stop'
$url = 'https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip'
$installRoot = 'C:\Android'
$toolsParent = Join-Path $installRoot 'cmdline-tools'
$toolsLatest = Join-Path $toolsParent 'latest'
$destZip = Join-Path $installRoot 'cmdline-tools.zip'

Write-Host "Creating install directories..."
if (-not (Test-Path $toolsParent)) { New-Item -ItemType Directory -Path $toolsParent | Out-Null }

Write-Host "Downloading Android command line tools..."
Invoke-WebRequest -Uri $url -OutFile $destZip -UseBasicParsing

Write-Host "Cleaning existing extracted tools..."
if (Test-Path $toolsLatest) { Remove-Item -Recurse -Force $toolsLatest }

Write-Host "Extracting archive..."
Expand-Archive -Path $destZip -DestinationPath $toolsParent -Force

$extracted = Join-Path $toolsParent 'cmdline-tools'
if (Test-Path $extracted) {
    if (Test-Path $toolsLatest) { Remove-Item -Recurse -Force $toolsLatest }
    Move-Item -Path $extracted -Destination $toolsLatest
}

if (Test-Path $destZip) { Remove-Item -Force $destZip }

Write-Host "Setting environment variables..."
[Environment]::SetEnvironmentVariable('ANDROID_HOME', $installRoot, 'User')
$existingPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$pathsToAdd = @(
    Join-Path $toolsLatest 'bin',
    Join-Path $installRoot 'platform-tools'
)
foreach ($p in $pathsToAdd) {
    if (-not ($existingPath -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ -eq $p })) {
        if ($existingPath.Trim().Length -gt 0) { $existingPath = "$existingPath;$p" } else { $existingPath = $p }
    }
}
[Environment]::SetEnvironmentVariable('Path', $existingPath, 'User')

$env:ANDROID_HOME = $installRoot
$env:PATH = "$($toolsLatest)\bin;$($installRoot)\platform-tools;$env:PATH"

Write-Host "Accepting sdkmanager licenses..."
$licenseFile = Join-Path $env:TEMP 'sdk_licenses.txt'
1..20 | ForEach-Object { 'y' } | Set-Content -Encoding ASCII -Path $licenseFile
Get-Content $licenseFile | & "$toolsLatest\bin\sdkmanager.bat" --licenses

Write-Host "Installing required SDK packages..."
& "$toolsLatest\bin\sdkmanager.bat" 'platform-tools' 'platforms;android-34' 'build-tools;34.0.0'

Write-Host "Running flutter doctor..."
if (Get-Command flutter -ErrorAction SilentlyContinue) {
    flutter doctor
} else {
    Write-Host 'flutter command not found. Please run flutter doctor after installing Flutter.'
}
