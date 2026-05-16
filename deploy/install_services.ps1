# =============================================================
# RichAITrading — Windows Service Installer
# Chạy với quyền Administrator:
#   Right-click PowerShell → "Run as Administrator"
#   cd C:\path\to\AI_Trading\deploy
#   .\install_services.ps1
# =============================================================

# ── Cấu hình — chỉnh 3 dòng này ──────────────────────────────
$PROJECT_DIR = "C:\path\to\AI_Trading"           # Thư mục project
$PYTHON      = "C:\path\to\AI_Trading\venv\Scripts\python.exe"  # Python trong venv
$NSSM        = "C:\tools\nssm\win64\nssm.exe"    # Đường dẫn nssm.exe
# ─────────────────────────────────────────────────────────────

Write-Host "=== RichAITrading Service Installer ===" -ForegroundColor Cyan

# 1. Redis service
Write-Host "`n[1/3] Cài Redis service..." -ForegroundColor Yellow
redis-server --service-uninstall 2>$null
redis-server --service-install
redis-server --service-start
Write-Host "    Redis service OK" -ForegroundColor Green

# 2. Collect static files
Write-Host "`n[2/3] Collect static files..." -ForegroundColor Yellow
Set-Location $PROJECT_DIR
& $PYTHON manage.py collectstatic --noinput
Write-Host "    Static files OK" -ForegroundColor Green

# 3. Migrate database
Write-Host "`n[3/3] Migrate database..." -ForegroundColor Yellow
& $PYTHON manage.py migrate --noinput
Write-Host "    Database OK" -ForegroundColor Green

# 4. Cài Waitress service
Write-Host "`nCài AiTrading (Waitress) service..." -ForegroundColor Yellow
& $NSSM stop   AiTrading 2>$null
& $NSSM remove AiTrading confirm 2>$null

& $NSSM install AiTrading $PYTHON
& $NSSM set     AiTrading AppParameters       "serve.py"
& $NSSM set     AiTrading AppDirectory        $PROJECT_DIR
& $NSSM set     AiTrading DisplayName         "RichAITrading Web"
& $NSSM set     AiTrading Description         "RichAITrading Waitress WSGI Server"
& $NSSM set     AiTrading Start               SERVICE_AUTO_START
& $NSSM set     AiTrading AppStdout           "$PROJECT_DIR\logs\waitress.log"
& $NSSM set     AiTrading AppStderr           "$PROJECT_DIR\logs\waitress_error.log"
& $NSSM set     AiTrading AppRotateFiles      1
& $NSSM set     AiTrading AppRotateBytes      10485760
& $NSSM set     AiTrading AppEnvironmentExtra "DJANGO_SETTINGS_MODULE=aitrading.settings"

# Tạo thư mục logs
New-Item -ItemType Directory -Force -Path "$PROJECT_DIR\logs" | Out-Null

& $NSSM start AiTrading
Write-Host "    AiTrading service OK" -ForegroundColor Green

# 5. Cài Nginx service
Write-Host "`nCài Nginx service..." -ForegroundColor Yellow
& $NSSM stop   Nginx 2>$null
& $NSSM remove Nginx confirm 2>$null

& $NSSM install Nginx "C:\nginx\nginx.exe"
& $NSSM set     Nginx AppDirectory  "C:\nginx"
& $NSSM set     Nginx DisplayName   "Nginx Web Server"
& $NSSM set     Nginx Start         SERVICE_AUTO_START

& $NSSM start Nginx
Write-Host "    Nginx service OK" -ForegroundColor Green

Write-Host "`n=== Hoàn tất! ===" -ForegroundColor Cyan
Write-Host "Web đang chạy tại http://yourdomain.com" -ForegroundColor Green
Write-Host ""
Write-Host "Quản lý services:"
Write-Host "  nssm restart AiTrading   # restart app"
Write-Host "  nssm restart Nginx       # restart nginx"
Write-Host "  nssm stop    AiTrading   # dừng app"
