# Stops ReelForge's editor server (whatever is listening on port 5190) and any render it started.
$conn = Get-NetTCPConnection -LocalPort 5190 -State Listen -ErrorAction SilentlyContinue
if (-not $conn) { Write-Host "ReelForge isn't running."; exit 0 }
foreach ($procId in ($conn.OwningProcess | Sort-Object -Unique)) {
  & taskkill.exe /PID $procId /T /F | Out-Null   # /T also ends the renders it started
}
Write-Host "ReelForge stopped."
