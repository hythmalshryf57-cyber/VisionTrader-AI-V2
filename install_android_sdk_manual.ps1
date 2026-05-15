$ErrorActionPreference = 'Stop'
$installRoot = 'C:\Android'
$toolsLatest = Join-Path $installRoot 'cmdline-tools\latest'
$sdkmanager = Join-Path $toolsLatest 'bin\sdkmanager.bat'
$licenseFile = 'C:\Windows\Temp\sdk_licenses.txt'

Write-Host "Preparing license file at $licenseFile..."
1..50 | ForEach-Object { 'y' } | Set-Content -Encoding ASCII -Path $licenseFile

if (-not (Test-Path $sdkmanager)) {
    Write-Host "ERROR: sdkmanager not found at $sdkmanager"
    exit 1
}

Write-Host "Accepting SDK licenses..."
Get-Content $licenseFile | & $sdkmanager --licenses

Write-Host "Installing platform-tools, Android 36, and build-tools 28.0.3..."
Get-Content $licenseFile | & $sdkmanager 'platform-tools' 'platforms;android-36' 'build-tools;28.0.3'

Write-Host "Installation complete."