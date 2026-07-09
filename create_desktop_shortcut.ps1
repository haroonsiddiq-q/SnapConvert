# Run this once, from inside the SnapConvert folder, in PowerShell:
#   powershell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "SnapConvert.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = """$here\start_snapconvert_silent.vbs"""
$shortcut.WorkingDirectory = $here
$shortcut.IconLocation = "shell32.dll,43"   # a generic "app window" icon; swap for your own .ico if you have one
$shortcut.Description = "Launch SnapConvert"
$shortcut.Save()

Write-Host "Shortcut created on Desktop: $shortcutPath"
