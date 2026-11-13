# Stops Aayush's Editor's server (whatever is listening on port 5190) and any render it started.
$conn = Get-NetTCPConnection -LocalPort 5190 -State Listen -ErrorAction SilentlyContinue
if (-not $conn) { Write-Host "Aayush's Editor isn't running."; exit 0 }
foreach ($procId in ($conn.OwningProcess | Sort-Object -Unique)) {
  & taskkill.exe /PID $procId /T /F | Out-Null   # /T also ends the renders it started
}
Write-Host "Aayush's Editor stopped."
