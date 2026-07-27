# Registers the arcyinternalerter daily digest at 08:00.
# Run this script in PowerShell (no elevation needed for interactive logon tasks).

$ErrorActionPreference = 'Continue'

$projectDir = 'C:\Users\Ijtihed\Documents\GitHub\arcyinternalerter'
$pythonExe  = 'C:\Users\Ijtihed\AppData\Local\Programs\Python\Python313\python.exe'
$taskName   = 'arcyinternalerter daily digest'
$logDir     = Join-Path $projectDir 'logs'

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Write-Host "  created log dir: $logDir" -ForegroundColor DarkGray
}

# Daily log file — one file per calendar day (date formatted as YYYYMMDD).
$cmd = "/c `"`"$pythonExe`" tracker.py --digest >> `"$projectDir\logs\digest-`%date:~-4`%`%date:~-10,2`%`%date:~-7,2`%.log`" 2>&1`""
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $cmd -WorkingDirectory $projectDir

# 08:00 daily. StartWhenAvailable = catches missed runs if the laptop was off.
$trigger = New-ScheduledTaskTrigger -Daily -At '08:00'

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 15)

# Interactive logon — runs as you, no stored password needed.
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "  removed previous '$taskName'" -ForegroundColor DarkGray
}

Register-ScheduledTask `
    -TaskName  $taskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -Principal $principal `
    -Description "Daily 08:00 Telegram digest of India tech/SWE internships. 531 companies wired. Logs -> $logDir."

Write-Host "`n--- Registered task ---" -ForegroundColor Green
Get-ScheduledTask -TaskName $taskName |
    Select-Object TaskName, State,
        @{N='NextRun'; E={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}} |
    Format-List

Write-Host "Logs will be written to: $logDir\digest-YYYYMMDD.log" -ForegroundColor DarkGray
Write-Host "Done." -ForegroundColor Green
Start-Sleep -Seconds 3
