# Hướng dẫn Deploy RichAITrading lên Windows VPS

Hướng dẫn từ A → Z: mua VPS, cài đặt, cấu hình, go-live.

---

## Mục lục

1. [Mua VPS Windows](#1-mua-vps-windows)
2. [Kết nối vào VPS](#2-kết-nối-vào-vps)
3. [Cài phần mềm cơ bản](#3-cài-phần-mềm-cơ-bản)
4. [Cài PostgreSQL](#4-cài-postgresql)
5. [Cài Redis](#5-cài-redis)
6. [Cài Nginx](#6-cài-nginx)
7. [Cài NSSM (Service Manager)](#7-cài-nssm)
8. [Clone và cấu hình project](#8-clone-và-cấu-hình-project)
9. [Cài services tự động](#9-cài-services-tự-động)
10. [Cấu hình tên miền và SSL](#10-cấu-hình-tên-miền-và-ssl)
11. [Kiểm tra cuối](#11-kiểm-tra-cuối)
12. [Cập nhật code](#12-cập-nhật-code)
13. [Xử lý sự cố](#13-xử-lý-sự-cố)

---

## 1. Mua VPS Windows

### Yêu cầu tối thiểu

| Thông số | Tối thiểu | Khuyến nghị |
|----------|-----------|-------------|
| RAM | 2 GB | 4 GB |
| vCPU | 1 | 2 |
| Ổ cứng | 40 GB SSD | 80 GB SSD |
| OS | Windows Server 2019 | Windows Server 2022 |
| Region | Singapore | Singapore |

### Nhà cung cấp đề xuất

#### Vultr (khuyến nghị cho người mới)
- **Website**: vultr.com
- **Giá**: ~$24/tháng (4GB RAM, 2 vCPU, 80GB SSD, Windows Server 2022)
- **Ưu điểm**: Dễ dùng, có region Singapore, billing theo giờ
- **Cách mua**:
  1. Đăng ký tài khoản tại vultr.com (cần credit card hoặc PayPal)
  2. Add funds → chọn số tiền (tối thiểu $10)
  3. **Deploy New Server** → chọn:
     - Type: **Cloud Compute - Optimized**
     - Location: **Singapore**
     - Image: **Windows Server 2022**
     - Plan: **4 GB RAM, 2 vCPU** ($24/tháng)
  4. Server Label: `richaitrading-prod`
  5. Click **Deploy Now** → chờ ~5 phút

#### Contabo (rẻ nhất)
- **Website**: contabo.com
- **Giá**: ~$15/tháng (8GB RAM, 4 vCPU, 100GB NVMe)
- **Lưu ý**: Windows Server tính thêm phí ~$5/tháng; thời gian khởi tạo lâu hơn (vài giờ)

#### Vietnix / AZDIGI (nhà cung cấp Việt Nam)
- Phù hợp nếu muốn thanh toán bằng VNĐ, hỗ trợ tiếng Việt
- Vietnix: vietnix.vn → VPS Windows
- AZDIGI: azdigi.com → VPS Windows

### Lấy thông tin truy cập

Sau khi VPS được tạo, lưu lại:
- **IP**: ví dụ `123.45.67.89`
- **Username**: `Administrator`
- **Password**: được hiển thị trên dashboard nhà cung cấp

---

## 2. Kết nối vào VPS

### Trên Windows (máy local)

1. Nhấn `Windows + R` → gõ `mstsc` → Enter
2. **Computer**: nhập IP của VPS
3. **Username**: `Administrator`
4. Click **Connect** → nhập password → OK

### Trên macOS / Linux

Dùng app **Microsoft Remote Desktop** (tải từ App Store / Microsoft Store) hoặc:
```
rdesktop 123.45.67.89
```

### Sau khi vào VPS lần đầu

Mở **PowerShell as Administrator** (chuột phải vào Start → Windows PowerShell (Admin)):

```powershell
# Đặt tên máy (tùy chọn)
Rename-Computer -NewName "richaitrading" -Restart

# Sau khi restart, mở PowerShell Admin lại
# Cho phép chạy scripts
Set-ExecutionPolicy RemoteSigned -Force

# Tắt Windows Firewall tạm để test (sẽ bật lại sau)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
```

---

## 3. Cài phần mềm cơ bản

Chạy tất cả trong **PowerShell Administrator**.

### 3.1 Cài Python 3.11

```powershell
# Tải Python 3.11 (x64)
$pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
Invoke-WebRequest -Uri $pythonUrl -OutFile "C:\Temp\python-3.11.9.exe"

# Cài silent với PATH
Start-Process "C:\Temp\python-3.11.9.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait

# Kiểm tra
python --version   # phải hiện Python 3.11.x
```

### 3.2 Cài Git

```powershell
$gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe"
Invoke-WebRequest -Uri $gitUrl -OutFile "C:\Temp\git-setup.exe"
Start-Process "C:\Temp\git-setup.exe" -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL" -Wait

# Refresh PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
git --version
```

### 3.3 Tạo thư mục làm việc

```powershell
New-Item -ItemType Directory -Force "C:\Temp" | Out-Null
New-Item -ItemType Directory -Force "C:\sites" | Out-Null
```

---

## 4. Cài PostgreSQL

PostgreSQL EDB installer hoạt động bình thường trên VPS Windows mới. **Không bị lỗi** như máy dev đã từng gặp.

### 4.1 Tải và cài

```powershell
# Tải PostgreSQL 16 installer
$pgUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64.exe"
Invoke-WebRequest -Uri $pgUrl -OutFile "C:\Temp\postgresql-setup.exe"

# Cài silent (thay YourPassword bằng mật khẩu thực)
Start-Process "C:\Temp\postgresql-setup.exe" -ArgumentList `
    "--mode unattended",
    "--unattendedmodeui none",
    "--superpassword YourStrongPassword123!",
    "--servicename postgresql-x64-16",
    "--serviceaccount NT AUTHORITY\NetworkService",
    "--datadir C:\PostgreSQL\16\data",
    "--serverport 5432" `
    -Wait

# Thêm psql vào PATH
$pgBin = "C:\Program Files\PostgreSQL\16\bin"
$currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
[System.Environment]::SetEnvironmentVariable("PATH", "$currentPath;$pgBin", "Machine")
$env:PATH = "$env:PATH;$pgBin"
```

### 4.2 Tạo database

```powershell
# Tạo database aitrading
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE aitrading ENCODING 'UTF8';"

# Kiểm tra
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "\l"
```

Khi được hỏi password, nhập mật khẩu đã đặt lúc cài (YourStrongPassword123!).

### 4.3 Lưu thông tin database

```
DB_ENGINE=postgresql
DB_NAME=aitrading
DB_USER=postgres
DB_PASSWORD=YourStrongPassword123!
DB_HOST=127.0.0.1
DB_PORT=5432
```

---

## 5. Cài Redis

### 5.1 Tải Redis cho Windows

```powershell
# Tải Redis 3.0.504 (bản stable cho Windows)
$redisUrl = "https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.msi"
Invoke-WebRequest -Uri $redisUrl -OutFile "C:\Temp\redis-setup.msi"

# Cài
Start-Process msiexec -ArgumentList "/i C:\Temp\redis-setup.msi /quiet ADDLOCAL=ALL" -Wait

# Kiểm tra service
Get-Service redis

# Test
redis-cli ping   # phải trả về PONG
```

> **Lưu ý**: Redis 3.0 cho Windows là bản cũ nhưng đủ dùng. Nếu cần Redis 7.x, dùng WSL2.

### 5.2 Đảm bảo Redis tự khởi động

```powershell
Set-Service -Name Redis -StartupType Automatic
Start-Service Redis
```

---

## 6. Cài Nginx

### 6.1 Tải Nginx

```powershell
# Tải Nginx stable cho Windows
$nginxUrl = "https://nginx.org/download/nginx-1.26.1.zip"
Invoke-WebRequest -Uri $nginxUrl -OutFile "C:\Temp\nginx.zip"

# Giải nén vào C:\nginx
Expand-Archive -Path "C:\Temp\nginx.zip" -DestinationPath "C:\Temp\nginx-extract" -Force
Move-Item "C:\Temp\nginx-extract\nginx-1.26.1" "C:\nginx" -Force
```

### 6.2 Cấu hình Nginx

Copy file config từ project (sau bước clone project ở phần 8):

```powershell
# Chạy SAU KHI đã clone project vào C:\sites\AI_Trading
Copy-Item "C:\sites\AI_Trading\deploy\nginx.conf" "C:\nginx\conf\nginx.conf" -Force
```

Sau đó edit file `C:\nginx\conf\nginx.conf` — thay 2 chỗ:
- `yourdomain.com www.yourdomain.com` → tên miền thực của bạn
- `C:/path/to/AI_Trading/` → `C:/sites/AI_Trading/`

---

## 7. Cài NSSM

NSSM (Non-Sucking Service Manager) giúp chạy bất kỳ chương trình nào như Windows Service.

```powershell
# Tải NSSM
$nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
Invoke-WebRequest -Uri $nssmUrl -OutFile "C:\Temp\nssm.zip"

# Giải nén
Expand-Archive -Path "C:\Temp\nssm.zip" -DestinationPath "C:\Temp\nssm-extract" -Force
New-Item -ItemType Directory -Force "C:\tools\nssm" | Out-Null
Copy-Item "C:\Temp\nssm-extract\nssm-2.24\win64\nssm.exe" "C:\tools\nssm\" -Force

# Thêm vào PATH
$currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
[System.Environment]::SetEnvironmentVariable("PATH", "$currentPath;C:\tools\nssm", "Machine")
$env:PATH = "$env:PATH;C:\tools\nssm"

# Kiểm tra
nssm version
```

---

## 8. Clone và cấu hình project

### 8.1 Clone code

```powershell
cd C:\sites

# Clone từ GitHub (thay bằng URL repo của bạn)
git clone https://github.com/yourusername/AI_Trading.git
cd AI_Trading
```

> Nếu repo private, cần cài SSH key hoặc dùng Personal Access Token:
> ```
> git clone https://your-token@github.com/yourusername/AI_Trading.git
> ```

### 8.2 Tạo virtual environment

```powershell
python -m venv venv
venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 8.3 Tạo file .env

```powershell
# Tạo file .env trong thư mục project
$envContent = @"
SECRET_KEY=your-very-long-random-secret-key-change-this-now
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,123.45.67.89

DB_ENGINE=postgresql
DB_NAME=aitrading
DB_USER=postgres
DB_PASSWORD=YourStrongPassword123!
DB_HOST=127.0.0.1
DB_PORT=5432

EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=richaitrading.support@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password

ADMIN_WALLET_ADDRESS=0xf3d2fFb82ce9bF6701F692a85320A9f87C2F68d6
USDT_CONTRACT_BSC=0x55d398326f99059fF775485246999027B3197955
BSCSCAN_API_KEY=your_bscscan_api_key
USDT_TO_COINS_RATE=1
WALLET_SCAN_INTERVAL_SECONDS=60
DJANGO_RUN_SCHEDULER=1

MT5_ACCOUNT=
MT5_PASSWORD=
MT5_SERVER=

GEMINI_API_KEY=your_gemini_api_key

REDIS_URL=redis://127.0.0.1:6379/0

AI_PLAN_WEEK_COST=20
AI_PLAN_MONTH_COST=50
AI_PLAN_YEAR_COST=400

TV_PLAN_WEEK_COST=10
TV_PLAN_MONTH_COST=30
TV_PLAN_YEAR_COST=200
"@
$envContent | Out-File -FilePath ".env" -Encoding utf8 -NoNewline
```

**Quan trọng — thay các giá trị sau:**

| Biến | Giá trị cần thay |
|------|-----------------|
| `SECRET_KEY` | Tạo ngẫu nhiên tại [djecrety.ir](https://djecrety.ir) |
| `ALLOWED_HOSTS` | Domain thực + IP VPS |
| `DB_PASSWORD` | Password PostgreSQL đã đặt ở bước 4 |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (không phải password Gmail thường) |
| `BSCSCAN_API_KEY` | Lấy tại bscscan.com/myapikey |
| `GEMINI_API_KEY` | Lấy tại aistudio.google.com |

### 8.4 Khởi tạo database và static files

```powershell
# Vẫn trong C:\sites\AI_Trading với venv đã activate

# Migrate database
venv\Scripts\python.exe manage.py migrate --noinput

# Tạo superuser
venv\Scripts\python.exe manage.py createsuperuser

# Thu thập static files
venv\Scripts\python.exe manage.py collectstatic --noinput

# Kiểm tra không có lỗi
venv\Scripts\python.exe manage.py check --deploy
```

### 8.5 Cập nhật Nginx config

```powershell
# Copy nginx config
Copy-Item "deploy\nginx.conf" "C:\nginx\conf\nginx.conf" -Force
```

Mở `C:\nginx\conf\nginx.conf` và sửa:
```nginx
server_name yourdomain.com www.yourdomain.com;   # ← tên miền của bạn

location /static/ {
    alias C:/sites/AI_Trading/staticfiles/;       # ← đường dẫn thực
}
location /media/ {
    alias C:/sites/AI_Trading/media/;             # ← đường dẫn thực
}
```

### 8.6 Cập nhật deploy scripts

Mở `deploy\install_services.ps1` và sửa 3 dòng đầu:

```powershell
$PROJECT_DIR = "C:\sites\AI_Trading"
$PYTHON      = "C:\sites\AI_Trading\venv\Scripts\python.exe"
$NSSM        = "C:\tools\nssm\nssm.exe"
```

---

## 9. Cài services tự động

Chạy script cài đặt (PowerShell Admin):

```powershell
cd C:\sites\AI_Trading
Set-ExecutionPolicy Bypass -Scope Process -Force
.\deploy\install_services.ps1
```

Script sẽ tự động:
1. Cài Redis service (nếu chưa có)
2. Collect static files
3. Migrate database
4. Cài **AiTrading** service (Waitress WSGI)
5. Cài **Nginx** service

### Kiểm tra services

```powershell
nssm status AiTrading   # phải là RUNNING
nssm status Nginx       # phải là RUNNING
Get-Service Redis        # phải là Running

# Test app
Invoke-WebRequest http://127.0.0.1:8000 -UseBasicParsing | Select-Object StatusCode
# phải trả về 200
```

---

## 10. Cấu hình tên miền và SSL

### 10.1 Trỏ tên miền

Đăng nhập vào nhà cung cấp domain (Namecheap, GoDaddy, PA Vietnam...) → DNS Management:

```
Type  Name    Value             TTL
A     @       123.45.67.89      300
A     www     123.45.67.89      300
```

Chờ DNS propagate (~5-30 phút).

### 10.2 Mở port Firewall

```powershell
# Mở port 80 (HTTP) và 443 (HTTPS)
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

### 10.3 Cài SSL miễn phí (Let's Encrypt) với win-acme

```powershell
# Tải win-acme
$wacmeUrl = "https://github.com/win-acme/win-acme/releases/download/v2.2.9.1701/win-acme.v2.2.9.1701.x64.trimmed.zip"
Invoke-WebRequest -Uri $wacmeUrl -OutFile "C:\Temp\wacme.zip"
Expand-Archive -Path "C:\Temp\wacme.zip" -DestinationPath "C:\tools\wacme" -Force

# Chạy win-acme (interactive)
C:\tools\wacme\wacs.exe
```

win-acme sẽ hỏi:
1. **N** (new certificate)
2. Nhập domain: `yourdomain.com` và `www.yourdomain.com`
3. Chọn HTTP validation (cần Nginx đang chạy)
4. Nó tự cài cert vào Windows Certificate Store

### 10.4 Cập nhật Nginx để dùng HTTPS

Sau khi có SSL cert, sửa `C:\nginx\conf\nginx.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;    # Redirect HTTP → HTTPS
}

server {
    listen 443 ssl;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate     C:/path/to/cert.pem;
    ssl_certificate_key C:/path/to/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 10M;

    location /static/ {
        alias C:/sites/AI_Trading/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias C:/sites/AI_Trading/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 60s;
    }
}
```

```powershell
# Test config Nginx
C:\nginx\nginx.exe -t

# Reload Nginx
nssm restart Nginx
```

---

## 11. Kiểm tra cuối

```powershell
# 1. Tất cả services đang chạy
nssm status AiTrading
nssm status Nginx
Get-Service Redis | Select-Object Status

# 2. Redis hoạt động
redis-cli ping   # → PONG

# 3. Database kết nối được
cd C:\sites\AI_Trading
venv\Scripts\python.exe manage.py dbshell   # vào psql shell, thoát bằng \q

# 4. Website phản hồi
Invoke-WebRequest https://yourdomain.com -UseBasicParsing | Select-Object StatusCode
# → StatusCode 200

# 5. Admin panel
# Mở trình duyệt: https://yourdomain.com/admin
# Đăng nhập bằng superuser đã tạo

# 6. Kiểm tra logs
Get-Content "C:\sites\AI_Trading\logs\waitress.log" -Tail 20
Get-Content "C:\sites\AI_Trading\logs\waitress_error.log" -Tail 20
```

---

## 12. Cập nhật code

Mỗi lần push code mới lên GitHub:

```powershell
# Chạy với quyền Administrator
cd C:\sites\AI_Trading
.\deploy\update.ps1
```

Script tự động:
1. `git pull origin main`
2. `pip install -r requirements.txt` (cài package mới nếu có)
3. `manage.py migrate`
4. `manage.py collectstatic`
5. `nssm restart AiTrading`

---

## 13. Xử lý sự cố

### App không khởi động

```powershell
# Xem log lỗi
Get-Content "C:\sites\AI_Trading\logs\waitress_error.log" -Tail 50

# Thử chạy tay để xem lỗi trực tiếp
cd C:\sites\AI_Trading
venv\Scripts\python.exe serve.py
```

### Lỗi 502 Bad Gateway (Nginx)

```powershell
# Kiểm tra Waitress có chạy không
nssm status AiTrading

# Kiểm tra port 8000 có mở không
netstat -ano | findstr :8000
```

### Redis không kết nối

```powershell
Get-Service Redis
Start-Service Redis
redis-cli ping
```

### Database connection refused

```powershell
# Kiểm tra PostgreSQL service
Get-Service postgresql-x64-16
Start-Service postgresql-x64-16

# Test kết nối
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d aitrading -c "SELECT 1"
```

### SSL cert hết hạn

win-acme tự gia hạn qua Windows Task Scheduler. Kiểm tra:
```powershell
Get-ScheduledTask -TaskName "*win-acme*"
```

### Restart tất cả khi VPS reboot

Tất cả services đã set `Start=SERVICE_AUTO_START` — khởi động tự động theo thứ tự:
Redis → AiTrading → Nginx

---

## Checklist trước khi go-live

- [ ] `SECRET_KEY` đã thay (không dùng giá trị mặc định)
- [ ] `DEBUG=False` trong `.env`
- [ ] `ALLOWED_HOSTS` chứa domain thực
- [ ] `DJANGO_RUN_SCHEDULER=1` để wallet scanner hoạt động
- [ ] SSL cert đã cài, HTTPS hoạt động
- [ ] Admin panel truy cập được tại `/admin`
- [ ] Gửi thử email OTP (đăng ký tài khoản mới)
- [ ] Nạp tiền test (TxHash thủ công)
- [ ] Kiểm tra trang AI Trading
- [ ] Backup `.env` (lưu nơi an toàn, không commit lên Git)
