$projectDir = 'C:\Users\Ijtihed\Documents\GitHub\arcyinternalerter'
$pythonExe  = 'C:\Users\Ijtihed\AppData\Local\Programs\Python\Python313\python.exe'
$taskName   = 'arcyinternalerter daily digest'

# Daily fast path: no --jobspy, no --browser. The 16 JobSpy companies
# (Google, Meta, Tesla, ASML, Atlassian, Cisco, ServiceNow, Oracle,
# Intel, Coinbase, Klarna, UiPath, Confluent, Arm, Broadcom, Qualcomm)
# are skipped by default. Run manually with --jobspy when you want them.
$cmd = "/c `"`"$pythonExe`" tracker.py --digest >> `"$projectDir\logs\digest-`%date:~-4`%`%date:~-10,2`%`%date:~-7,2`%.log`" 2>&1`""
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument $cmd -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger -Daily -At '09:00'

# Allow more time, JobSpy adds about 2 minutes
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 15)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "EU tech / SWE Telegram digest. Polls ~150 companies via direct ATS APIs. JobSpy companies (Google/Meta/Tesla/Atlassian/Cisco/Oracle/ServiceNow/ASML/Intel/Coinbase/Klarna/UiPath/Confluent/Arm/Broadcom/Qualcomm) are opt-in, run manually with --jobspy to include them."

Write-Host "`n--- Updated task ---" -ForegroundColor Cyan
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State, @{N='NextRun';E={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}}, @{N='Action';E={($_.Actions | ForEach-Object { "$($_.Execute) $($_.Arguments)" }) -join '; '}} | Format-List

Write-Host "Done. Task updated to leave out --jobspy." -ForegroundColor Green
Start-Sleep -Seconds 3  # brief pause so user can see the result before window closes
