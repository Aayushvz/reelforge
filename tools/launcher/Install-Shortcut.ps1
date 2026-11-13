# Puts a "ReelForge" shortcut on the desktop (and in the Start menu with -StartMenu). Safe to run again: it rewrites it.
param([switch]$StartMenu)
$here = $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell
$targets = @([Environment]::GetFolderPath("Desktop"))
if ($StartMenu) { $targets += Join-Path ([Environment]::GetFolderPath("Programs")) "" }
foreach ($dir in $targets) {
  $lnk = $shell.CreateShortcut((Join-Path $dir "ReelForge.lnk"))
  $lnk.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
  $lnk.Arguments = "`"$(Join-Path $here 'ReelForge.vbs')`""
  $lnk.WorkingDirectory = $here
  $lnk.IconLocation = (Join-Path $here "reelforge.ico") + ",0"
  $lnk.Description = "ReelForge: script to animated reel"
  $lnk.Save()
  Write-Host "Shortcut: $(Join-Path $dir 'ReelForge.lnk')"
}
