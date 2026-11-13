# Puts an "Aayush's Editor" shortcut on the desktop (and in the Start menu with -StartMenu). Safe to run again: it rewrites it.
param([switch]$StartMenu)
$here = $PSScriptRoot
$shell = New-Object -ComObject WScript.Shell
$targets = @([Environment]::GetFolderPath("Desktop"))
if ($StartMenu) { $targets += Join-Path ([Environment]::GetFolderPath("Programs")) "" }
foreach ($dir in $targets) {
  $lnk = $shell.CreateShortcut((Join-Path $dir "Aayush's Editor.lnk"))
  $lnk.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
  $lnk.Arguments = "`"$(Join-Path $here 'Aayushs-Editor.vbs')`""
  $lnk.WorkingDirectory = $here
  $lnk.IconLocation = (Join-Path $here "aayushs-editor.ico") + ",0"
  $lnk.Description = "Aayush's Editor: script to animated reel"
  $lnk.Save()
  Write-Host "Shortcut: $(Join-Path $dir "Aayush's Editor.lnk")"
}
