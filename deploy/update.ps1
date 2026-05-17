# =============================================================
# RichAITrading — Update Script
# Chạy từ thư mục project:
#   cd C:\sites\AI_Trading
#   .\deploy\update.ps1
# =============================================================

$PROJECT_DIR = "C:\sites\AI_Trading"
$PYTHON      = "C:\sites\AI_Trading\venv\Scripts\python.exe"

Set-Location $PROJECT_DIR

Write-Host "=== RichAITrading Update ===" -ForegroundColor Cyan

# 1. Pull code mới
Write-Host "`n[1/5] Git pull..." -ForegroundColor Yellow
git pull origin main
if (-not $?) {
    Write-Host "    Git pull thất bại. Kiểm tra lại remote hoặc conflict." -ForegroundColor Red
    exit 1
}
Write-Host "    Git pull OK" -ForegroundColor Green

# 2. Cài dependencies mới (nếu requirements.txt thay đổi)
Write-Host "`n[2/5] Cài dependencies..." -ForegroundColor Yellow
& $PYTHON -m pip install -r requirements.txt --quiet
Write-Host "    Dependencies OK" -ForegroundColor Green

# 3. Migrate database
Write-Host "`n[3/5] Migrate database..." -ForegroundColor Yellow
& $PYTHON manage.py migrate --noinput
Write-Host "    Migrate OK" -ForegroundColor Green

# 4. Collect static files
Write-Host "`n[4/5] Collect static files..." -ForegroundColor Yellow
& $PYTHON manage.py collectstatic --noinput --clear
Write-Host "    Static files OK" -ForegroundColor Green

# 5. Restart app (dừng process cũ, khởi động lại)
Write-Host "`n[5/5] Restart ứng dụng..." -ForegroundColor Yellow
taskkill /F /IM python.exe 2>$null
Start-Sleep -Seconds 2
Start-Process $PYTHON -ArgumentList "serve.py" -WorkingDirectory $PROJECT_DIR -WindowStyle Minimized
Start-Sleep -Seconds 3

# Kiểm tra process đã chạy chưa
$proc = Get-Process python -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "    App đã khởi động (PID: $($proc[0].Id))" -ForegroundColor Green
} else {
    Write-Host "    CẢNH BÁO: Không tìm thấy process python. Kiểm tra lại." -ForegroundColor Red
}

Write-Host "`n=== Cập nhật hoàn tất! ===" -ForegroundColor Cyan
