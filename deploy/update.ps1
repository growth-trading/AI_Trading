# =============================================================
# RichAITrading — Update Script
# Chạy với quyền Administrator:
#   cd C:\path\to\AI_Trading\deploy
#   .\update.ps1
# =============================================================

# ── Cấu hình — chỉnh 2 dòng này ──────────────────────────────
$PROJECT_DIR = "C:\path\to\AI_Trading"
$PYTHON      = "C:\path\to\AI_Trading\venv\Scripts\python.exe"
# ─────────────────────────────────────────────────────────────

Set-Location $PROJECT_DIR

Write-Host "=== RichAITrading Update ===" -ForegroundColor Cyan

# 1. Pull code mới
Write-Host "`n[1/4] Git pull..." -ForegroundColor Yellow
git pull origin main
if (-not $?) {
    Write-Host "    Git pull thất bại. Kiểm tra lại remote hoặc conflict." -ForegroundColor Red
    exit 1
}
Write-Host "    Git pull OK" -ForegroundColor Green

# 2. Cài dependencies mới (nếu requirements.txt thay đổi)
Write-Host "`n[2/4] Cài dependencies..." -ForegroundColor Yellow
& $PYTHON -m pip install -r requirements.txt --quiet
Write-Host "    Dependencies OK" -ForegroundColor Green

# 3. Migrate database
Write-Host "`n[3/4] Migrate database..." -ForegroundColor Yellow
& $PYTHON manage.py migrate --noinput
Write-Host "    Migrate OK" -ForegroundColor Green

# 4. Collect static files
Write-Host "`n[4/4] Collect static files..." -ForegroundColor Yellow
& $PYTHON manage.py collectstatic --noinput --clear
Write-Host "    Static files OK" -ForegroundColor Green

# 5. Restart app
Write-Host "`nRestart AiTrading service..." -ForegroundColor Yellow
nssm restart AiTrading
Start-Sleep -Seconds 2
$status = nssm status AiTrading
Write-Host "    AiTrading status: $status" -ForegroundColor Green

Write-Host "`n=== Cập nhật hoàn tất! ===" -ForegroundColor Cyan
