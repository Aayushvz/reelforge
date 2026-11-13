# Aayush's Editor launcher: start the editor's server in the background (if it isn't running) and open the editor in its
# own app window (Chrome or Edge app mode: no tabs, no address bar). Run hidden by Aayushs-Editor.vbs from the desktop
# shortcut. The server keeps running after the window closes, so renders carry on; Stop-Aayushs-Editor.ps1 stops it.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # tools\launcher -> the repo
$port = 5190
$url = "http://localhost:$port/"
$log = Join-Path $env:TEMP "reelforge-editor.log"

function Test-Up {
  try { return (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://localhost:$port/api/system").StatusCode -eq 200 }
  catch { return $false }
}

if (-not (Test-Up)) {
  # cmd keeps npm's output in a log; the window stays hidden
  Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -WorkingDirectory (Join-Path $repo "editor") `
    -ArgumentList "/c", "npm run dev > `"$log`" 2>&1"
  for ($i = 0; $i -lt 90 -and -not (Test-Up); $i++) { Start-Sleep -Milliseconds 700 }
  if (-not (Test-Up)) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("Aayush's Editor didn't start within a minute.`nDetails: $log", "Aayush's Editor") | Out-Null
    exit 1
  }
}

$browsers = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)
$browser = $browsers | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($browser) {
  Start-Process -FilePath $browser -ArgumentList "--app=$url", "--window-size=1600,1000"
} else {
  Start-Process $url   # no Chrome or Edge: the default browser
}
