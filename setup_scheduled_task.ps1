# Registers TWO scheduled tasks, each calling a launcher .cmd:
#   1. "arcy daily digest"   -> run_digest.cmd  (board digest, daily 08:00)
#   2. "arcy weekly jobspy"  -> run_jobspy.cmd  (full sweep, Mondays 07:00)
# Both use StartWhenAvailable so a run missed while the laptop was off fires
# as soon as it's next turned on. No elevation needed.

$ErrorActionPreference = 'Continue'

$projectDir = 'C:\Users\subodh\Projects\arcyinternalerter'

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

function Register-Digest {
    param($Name, $Script, $Trigger, $Hours, $Desc)

    $action = New-ScheduledTaskAction -Execute (Join-Path $projectDir $Script) -WorkingDirectory $projectDir

    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours $Hours) `
        -RestartCount 2 `
        -RestartInterval (New-TimeSpan -Minutes 15)

    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $Name -Confirm:$false
        Write-Host "  removed previous '$Name'" -ForegroundColor DarkGray
    }

    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $Trigger `
        -Settings $settings -Principal $principal -Description $Desc | Out-Null
    Write-Host "  registered '$Name'" -ForegroundColor Green
}

Register-Digest `
    -Name 'arcy daily digest' `
    -Script 'run_digest.cmd' `
    -Trigger (New-ScheduledTaskTrigger -Daily -At '08:00') `
    -Hours 1 `
    -Desc "Daily 08:00 Telegram digest (boards). Catches up on turn-on. Logs -> logs\digest-*.log"

Register-Digest `
    -Name 'arcy weekly jobspy' `
    -Script 'run_jobspy.cmd' `
    -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '07:00') `
    -Hours 2 `
    -Desc "Weekly Monday 07:00 jobspy sweep (banks, MBB, Stockholm). Catches up on turn-on. Logs -> logs\jobspy-*.log"

Write-Host "`n--- Registered tasks ---" -ForegroundColor Green
Get-ScheduledTask -TaskName 'arcy daily digest','arcy weekly jobspy' |
    Select-Object TaskName, State,
        @{N='NextRun'; E={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}} |
    Format-List
Write-Host "Done." -ForegroundColor Green
