# Gỡ tất cả services — chạy với quyền Administrator
$NSSM = "C:\tools\nssm\win64\nssm.exe"

Write-Host "Gỡ services..." -ForegroundColor Yellow
& $NSSM stop   AiTrading 2>$null
& $NSSM remove AiTrading confirm 2>$null
& $NSSM stop   Nginx 2>$null
& $NSSM remove Nginx confirm 2>$null
redis-server --service-stop 2>$null
redis-server --service-uninstall 2>$null
Write-Host "Xong." -ForegroundColor Green
