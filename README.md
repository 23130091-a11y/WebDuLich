# WebDuLich — Hệ thống gợi ý du lịch AI thông minh

Nhóm 24 · Python / Django 6 · DRF + JWT · PhoBERT sentiment

Web du lịch cho phép khám phá địa điểm & tour, đặt tour, và có hệ thống
gợi ý cá nhân hóa + phân tích cảm xúc review bằng AI (PhoBERT fine-tuned
cho tiếng Việt).

## Tính năng chính

- Tìm kiếm địa điểm/tour (autocomplete, lịch sử tìm kiếm theo IP, lọc theo thể loại)
- Gợi ý cá nhân hóa dựa trên sở thích (TravelPreference) + điểm sentiment review
- Review địa điểm/tour: vote hữu ích, báo cáo vi phạm, phân tích sentiment AI
- Đặt tour: form booking, trang thanh toán VietQR, lịch sử đặt tour, verified-purchase review
- Yêu thích (tour + địa điểm), hồ sơ cá nhân, đổi mật khẩu (JWT)
- Weather (OpenWeatherMap + Open-Meteo fallback), nearby places, chỉ đường (OSRM)

## Tech stack

| Thành phần | Công nghệ |
|---|---|
| Backend | Django 6, Django REST Framework, SimpleJWT |
| DB | SQLite (dev) / PostgreSQL (prod, `dj-database-url`) |
| Cache | LocMem (dev) / Redis khi multi-worker |
| AI | PhoBERT (transformers, torch) — chạy server-side, fallback rule-based |
| Static | WhiteNoise (prod), django-ratelimit, drf-spectacular |
| Deploy | Railway (Procfile + release migrate) |

## Chạy dự án (local)

```bash
# 1. Clone + tạo môi trường
git clone https://github.com/H-Thanh0603/WebDuLich.git
cd WebDuLich
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Cấu hình môi trường
cp .env.example .env             # rồi điền giá trị (xem phần dưới)
# Dev tối thiểu: USE_LOCAL_DB=true, DJANGO_DEBUG=true

# 4. Migrate + chạy
python manage.py migrate
python manage.py runserver
```

Truy cập http://127.0.0.1:8000 — tài khoản admin: `python manage.py createsuperuser`.

### Biến môi trường (`see .env.example`)

- `USE_LOCAL_DB=true` — dùng SQLite cho dev; production đặt `DATABASE_URL` (Railway tự inject)
- `SECRET_KEY`, `ALLOWED_HOSTS` — **bắt buộc** khi `DJANGO_DEBUG=false` (fail-fast lúc boot)
- `OPENWEATHERMAP_API_KEY`, `MEILI_HOST`/`MEILI_API_KEY`, `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` — tuỳ chọn, để trống là tính năng tương ứng tự degrade (Open-Meteo keyless, ORM search, no email)

### AI model (PhoBERT)

Thứ tự load khi chạy (`travel/ai_engine.py`):

1. Model fine-tuned tại `travel/phobert-travel-sentiment-final/` (weights **không nằm trong repo** — tải riêng hoặc train bằng `finetune_phobert/`)
2. Fallback model public `wonrax/phobert-base-vietnamese-sentiment` từ HF hub (lần inference đầu sẽ tự tải ~500MB)
3. Fallback cuối: rule-based (keyword), hệ thống vẫn chạy đầy đủ

## Kiểm thử

```bash
python manage.py test          # unit/integration tests
python manage.py check         # system checks
python manage.py makemigrations --check --dry-run   # model ≠ migration sẽ fail
```

CI (`.github/workflows/ci.yml`): gitleaks secret scan → pip-audit → migration check → system check → tests.

## Deploy (Railway)

1. Tạo project Railway từ repo — `Procfile` đã có `release: migrate` + `web: gunicorn`
2. Đặt Variables: `SECRET_KEY`, `ALLOWED_HOSTS`, `DJANGO_DEBUG=false`, `CSRF_TRUSTED_ORIGINS`, `ADMIN_URL_PATH`, `TRUST_X_FORWARDED_FOR=true`
3. Backup DB: `scripts/backup_db.sh` (pg_dump → gzip, giữ 7 bản)

Xem thêm: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md) · [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md) · [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md) · [docs/AI_EVAL.md](docs/AI_EVAL.md)
