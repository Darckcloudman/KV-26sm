$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\SMP12C VibroDiag.lnk")
$Shortcut.TargetPath = "D:\Coding\pyton_pro\run_app.bat"
$Shortcut.WorkingDirectory = "D:\Coding\pyton_pro"
$Shortcut.IconLocation = "python.exe,0"
$Shortcut.Save()
Write-Host "Ярлык создан на рабочем столе!" -ForegroundColor Green
