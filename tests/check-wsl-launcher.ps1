# Test argument boundaries without starting WSL or accessing network adapters.
$ErrorActionPreference = 'Stop'
$global:RecordedWslArguments = @()
function global:wsl.exe {
    $global:RecordedWslArguments = @($args)
    $global:LASTEXITCODE = 0
}
$launcher = Join-Path $PSScriptRoot '../windows/microduck-v7rc.ps1'
& $launcher -Action Serve -Distribution Ubuntu-24.04 -LinuxRepo '/home/test/repo with spaces' -AdvertiseIP 192.168.1.20
$expected = @('--distribution','Ubuntu-24.04','--cd','/home/test/repo with spaces','--','env','MICRODUCK_ADVERTISE_IP=192.168.1.20','bash','./scripts/microduck-sim','serve')
if (($global:RecordedWslArguments | ConvertTo-Json -Compress) -ne ($expected | ConvertTo-Json -Compress)) {
    throw 'WSL argument boundaries changed'
}
'PASS: WSL arguments preserve repository spaces and explicit IPv4'
