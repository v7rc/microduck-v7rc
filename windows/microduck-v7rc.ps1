# Windows frontend: run the unchanged Unix robot stack inside WSL2 Ubuntu.
[CmdletBinding()]
param(
    [ValidateSet('Setup','Serve','Bridge','Down','Health','Doctor','Test')]
    [string]$Action = 'Serve',
    [string]$Distribution = 'Ubuntu-24.04',
    [string]$LinuxRepo,
    [string]$AdvertiseIP,
    [switch]$Headless
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'WSL is missing. Install WSL2 + Ubuntu-24.04; see docs/INSTALL.en.md.'
}
if (-not $LinuxRepo) {
    $linuxUserHome = (& wsl.exe --distribution $Distribution -- sh -c 'printf %s "$HOME"').Trim()
    if ($LASTEXITCODE -ne 0 -or -not $linuxUserHome.StartsWith('/')) { throw 'Cannot locate the Linux home directory.' }
    $LinuxRepo = "$linuxUserHome/microduck-v7rc"
}
if (-not $LinuxRepo.StartsWith('/')) { throw 'LinuxRepo must be an absolute Linux path, e.g. /home/louis/microduck-v7rc.' }
if (-not $AdvertiseIP) {
    $candidates = @(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | ForEach-Object { $_.IPv4Address.IPAddress } | Select-Object -Unique)
    if ($candidates.Count -ne 1) { throw 'Multiple/no LAN addresses. Specify -AdvertiseIP with the IPv4 address reachable by your phone.' }
    $AdvertiseIP = $candidates[0]
}
$parsedAddress = $null
if (-not [System.Net.IPAddress]::TryParse($AdvertiseIP, [ref]$parsedAddress) -or $parsedAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw 'AdvertiseIP must be an IPv4 address.'
}
$wslArguments = @('--distribution', $Distribution, '--cd', $LinuxRepo, '--', 'env', "MICRODUCK_ADVERTISE_IP=$AdvertiseIP")
if ($Headless) { $wslArguments += 'DUCK_SIM_VIEWER=0' }
switch ($Action) {
    'Setup'  { $command = @('bash','./scripts/setup') }
    'Serve'  { $command = @('bash','./scripts/microduck-sim','serve') }
    'Bridge' { $command = @('bash','./scripts/v7rc-bridge') }
    'Down'   { $command = @('bash','./scripts/microduck-sim','down') }
    'Health' { $command = @('bash','./scripts/microduck-sim','ctl','health') }
    'Doctor' { $command = @('bash','./scripts/microduck-sim','doctor') }
    'Test'   { $command = @('./microduck_rl/.venv/bin/python','-m','unittest','discover','-s','tests','-v') }
}
# Argument arrays preserve spaces; no interpolated sh -c command or Invoke-Expression.
& wsl.exe @wslArguments @command
exit $LASTEXITCODE
