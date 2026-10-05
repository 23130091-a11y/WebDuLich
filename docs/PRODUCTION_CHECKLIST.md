# Production Checklist — WebDuLich

Trạng thái: **OK** = đã xong · **FIX** = có nhưng sai/thiếu · **MISSING** = chưa có.

| # | Mục | Trạng thái | Chi tiết + việc cần làm |
|---|-----|-----------|--------------------------|
| 1 | Config tách dev/prod | ✅ OK | Không cần `production.py` — settings đã 12-factor: `DJANGO_DEBUG`, `DATABASE_URL`, fail-fast khi prod thiếu `SECRET_KEY`/`ALLOWED_HOSTS` (`settings.py:~55`). Giữ nguyên. |
| 2 | SECRET_KEY/DEBUG/HOSTS từ env | ✅ OK | `SECRET_KEY` fallback insecure chỉ khi dev; prod raise RuntimeError. `.env.example` đủ biến. |
| 3 | DB → Postgres | ✅ OK | `dj-database-url` + `psycopg[binary]` đã có trong requirements.txt. Settings hỗ trợ `DATABASE_URL` + `PG*` (sslmode=require, conn_max_age=600). Migration data SQLite→PG: `python manage.py dumpdata --natural-foreign --natural-primary > data.json` (SQLite) → đổi env → `migrate` → `loaddata data.json`. Backup: `scripts/backup_db.sh` + `docs/BACKUP_RESTORE.md`. |
| 4 | Static/media | ⚠️ FIX | WhiteNoise đã có trong requirements — static OK. Media: `FileSystemStorage` local, **`urls.py` chỉ serve media khi DEBUG** → prod cần nginx `location /media/` hoặc volume/S3. Cho tới khi có user thật, Railway volume + serve qua middleware là chấp nhận được. |
| 5 | WSGI server | ✅ OK | `gunicorn` trong requirements + `Procfile`: `release: python manage.py migrate` + `web: gunicorn myproject.wsgi --workers 2 --timeout 120`. 2 worker là trần vì torch — xem #7. |
| 6 | Security headers | ✅ OK | SSL redirect, HSTS+preload, secure cookies, nosniff, X-Frame-Options, Referrer-Policy, `SECURE_PROXY_SSL_HEADER` — đầy đủ khi prod. |
| 7 | AI model runtime | ⚠️ NOTE | (a) Path model đã đúng (`travel/phobert-travel-sentiment-final`) + **fallback chain mới**: fine-tuned hỏng → HF public (`wonrax/phobert-base-vietnamese-sentiment`, tự tải ~500MB lần đầu) → rule-based. (b) Weights fine-tuned **không nằm trong repo** (gitignore) — muốn chạy model fine-tuned trên prod thì phải tải/train riêng; không có thì fallback HF public vẫn hoạt động. (c) torch load trong web process, lazy singleton — giữ `workers=1-2` hoặc tách AI service sau. |
| 8 | Rate limit | ✅ OK | `django-ratelimit` 3.x resolve dotted callable qua `import_string` — `RATELIMIT_IP_META_KEY = 'travel.views.get_client_ip'` hoạt động đúng (chỉ tin XFF khi `TRUST_X_FORWARDED_FOR=true`, lấy rightmost entry). Thêm: submit review/tour-review 10/h/user, change-password 10/h/user. |
| 9 | Backup | ⚠️ FIX | `scripts/backup_db.sh` (pg_dump gzip, giữ 7 bản) + `docs/BACKUP_RESTORE.md`. **Chưa có cron/scheduled** — Railway: bật volume backup hoặc schedule pg_dump. |
| 10 | .env.example | ✅ OK | Đủ biến prod: `DATABASE_URL` (comment), `CSRF_TRUSTED_ORIGINS`, `ADMIN_URL_PATH`, `SECURE_SSL_REDIRECT`, `REDIS_URL`, `TRUST_X_FORWARDED_FOR`. |
| 11 | Logging | ⚠️ FIX | Console INFO root + `django.request` WARNING — đủ cho Railway log drain. Có log review/booking event cơ bản. **Còn thiếu**: `mail_admins` khi 500, logger riêng `travel.booking` chi tiết hơn (ai set paid). |
| 12 | Cache backend | ⚠️ NOTE | LocMemCache per-process — OK 1 worker. Comment trong settings đã nói rõ: >1 worker phải Redis. `invalidate_cache(pattern)` no-op trên LocMem — chấp nhận được ở quy mô này. |
| 13 | Migrations | ✅ OK | `makemigrations --check --dry-run` sạch (CI chạy step này). |
| 14 | CI/CD | ✅ OK | `.github/workflows/ci.yml`: gitleaks, pip-audit, makemigrations check, manage.py check, test. Thiếu: deploy step (OK nếu Railway auto-deploy). |
| 15 | Health check | ✅ OK | `/health/` (`travel/urls.py` → `views.health`): SELECT 1 lên DB, trả JSON 200/500. |
| 16 | Email | ⚠️ FIX | SMTP Gmail qua env — đúng. Nhưng signal `send_ticket_email` không try/except → SMTP chết là fail save booking (SECURITY_AUDIT H3). Prod Gmail app-password nằm trong `.env` local — rotate khi deploy sang env Railway. |

## File cần tạo/sửa để lên prod

```
nginx.conf (nếu tự host)  serve /media/ + proxy_pass gunicorn
```

## Deploy doc — clone → chạy (Railway)

```bash
# 1. Variables trên Railway:
DATABASE_URL          # auto-inject từ Postgres plugin
SECRET_KEY            # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
ALLOWED_HOSTS         yourapp.up.railway.app
CSRF_TRUSTED_ORIGINS  https://yourapp.up.railway.app
ADMIN_URL_PATH        quan-tri-<random>/
EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / OPENWEATHERMAP_API_KEY / MEILI_*

# 2. Build (Railway tự chạy):
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate

# 3. Start command (Procfile):
gunicorn myproject.wsgi --workers 2 --timeout 120 --bind 0.0.0.0:$PORT

# 4. Model PhoBERT: nếu muốn model fine-tuned (không có thì tự fallback
#    sang HF public, lần đầu tải ~500MB) — mount volume tại
#    travel/phobert-travel-sentiment-final/ hoặc để HF hub tự tải.

# 5. Data: loaddata từ dump SQLite nếu migrate dữ liệu có sẵn
```

## Thứ tự ưu tiên trước khi public

1. Serve `/media/` ở prod — ảnh địa điểm/tour là nội dung chính
2. H3 email signal (try/except quanh send_ticket_email) — trước khi có booking thật
3. `mail_admins` khi 500 + log booking chi tiết
4. Backup schedule (pg_dump cron) sau khi có data quan trọng
5. Cân nhắc JWT refresh token → httpOnly cookie (hiện đang ở localStorage)
