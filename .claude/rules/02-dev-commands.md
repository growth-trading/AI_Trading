---
description: Các lệnh phát triển thường dùng — build, migrate, test, collectstatic
alwaysApply: true
---

## Cài đặt

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Database

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## Chạy server

```bash
python manage.py runserver
```

## Kiểm thử

```bash
python manage.py test                              # toàn bộ
python manage.py test accounts                     # một app
python manage.py test accounts.tests.TestClass     # một class cụ thể
```

## File tĩnh (production)

```bash
python manage.py collectstatic
```
