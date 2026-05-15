$ErrorActionPreference = 'Stop'
$licenseFile = 'C:\Windows\Temp\sdk_licenses.txt'
$cmd = 'C:\Android\cmdline-tools\latest\bin\sdkmanager.bat'

Write-Host "Preparing license file..."
1..50 | ForEach-Object { 'y' } | Set-Content -Encoding ASCII -Path $licenseFile

if (-not (Test-Path $cmd)) {
    Write-Error "sdkmanager not found at $cmd"
    exit 1
}

Write-Host "Installing Android platform-tools..."
Get-Content $licenseFile | & $cmd 'platform-tools'

Write-Host "Platform-tools installation script finished."