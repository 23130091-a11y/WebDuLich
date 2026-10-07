# Plan sửa WebDuLich theo audit — P0+P1+P2+CI (target Railway + PostgreSQL)

Thứ tự thực thi: A → B → C → D → E → F → G. Mỗi phase có bước verify riêng; không phase nào được coi là xong khi verify fail.

## Phase A — Môi trường & baseline (bắt buộc đầu tiên)
Repo chỉ có venv Windows → không chạy được trên Linux này; mọi fix cần môi trường chạy được để verify.

- **A1.** Tạo venv Linux `.venv/` (thêm vào `.gitignore`), cài `requirements.txt` + `gunicorn`, `whitenoise`, `psycopg[binary]`, `dj-database-url`, `pip-audit`.
- **A2.** Baseline: `python manage.py check` (kỳ vọng lộ lỗi `INSTALLED_APPS` chứa `'django.utils.text'`), `python manage.py test users` (kỳ vọng fail test `test_login_missing_fields` vì code trả 400, test kỳ vọng 401). Ghi lại output làm mốc.
- **A3.** So sánh `SELECT name FROM django_migrations WHERE app='travel'` (28 dòng applied) với 27 file trong `travel/migrations/` để tìm migration "ma" (đã applied nhưng file không tồn tại/đổi tên) — kết quả quyết định rename hay squash ở C4.

## Phase B — Secrets & Settings production (P0)

- **B1. (User tự làm NGAY — tôi sẽ kèm hướng dẫn cụ thể)**: Rotate Gmail app password (Google Account → Security → App passwords) và tạo OpenWeatherMap key mới (revoke key `17bfbfe5...`). Việc này không chặn code phía dưới.
- **B2.** `git rm --cached .env db.sqlite3 db_backup.sqlite3` (file vẫn còn trên disk local). Tạo `.env.example` chỉ chứa placeholder. Verify `.gitignore` đã phủ các file này.
- **B3.** Overhaul `myproject/settings.py`:
  - `SECRET_KEY`, `DEBUG` (default **False**), `ALLOWED_HOSTS` đọc từ env; chỉ fallback secret-insecure khi DEBUG=True
  - Xóa `'django.utils.text'` khỏi INSTALLED_APPS (settings.py:27)
  - DB: ưu tiên `DATABASE_URL` (dj-database-url, chuẩn Railway), fallback `PG*` vars, `USE_LOCAL_DB=true` → sqlite cho dev (giữ tương thích với máy nhóm)
  - Thêm `STATIC_ROOT` + Whitenoise middleware + STATICFILES_STORAGE; các `SECURE_*` headers khi not DEBUG
  - `LOGGING` console; DRF thêm `DEFAULT_THROTTLE_RATES` (anon 30/min) + `DEFAULT_PAGINATION_CLASS`
  - `SIMPLE_JWT`: access **15 phút**, refresh 30 ngày, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` (token_blacklist app đã có sẵn)
  - Comment ghi rõ: Redis chỉ khi ≥2 worker (không thêm dependency bây giờ)
- **B4.** `requirements.txt` thêm gunicorn/whitenoise/psycopg/dj-database-url; tạo `requirements-inference.txt` tách torch/transformers (không bắt buộc cài cho web tier).
- **B5. Verify:** `manage.py check` sạch; boot `DEBUG=False` không crash; `git ls-files | grep -E '^\.env$|sqlite3'` trả trống.

## Phase C — Endpoint & performance critical (P0)

- **C1.** Xóa bản duplicate `api_submit_tour_review` thứ 2 (`travel/views.py:2105-2171`, bản `@csrf_exempt` — Python giữ bản này, vô hiệu hóa bản an toàn ở line 850). Giữ bản line 850; thêm `@ratelimit(key='ip', rate='10/h')` + `bleach.clean` cho comment.
- **C2.** `api_analyze_sentiment` (views.py:2029): thêm `@ratelimit(key='ip', rate='10/m')`, cap text 1000 ký tự (400 nếu vượt). Giữ public vì UI dùng preview cho guest.
- **C3.** `all_tours` (views.py:34-127) — fix PERF-001: bỏ vòng lặp `analyze_sentiment` trên mọi review mọi tour. Thay bằng:
  - `annotate(avg_sentiment=Avg('reviews__sentiment_score'), review_count=Count('reviews'))` — sentiment đã được lưu sẵn vào DB khi tạo review
  - Keywords tổng hợp từ 2 cột JSON `positive_keywords`/`negative_keywords` đã lưu
  - `Paginator` trên **queryset** (không còn paginate list Python đã tính AI)
- **C4.** Migration theo kết quả A3: chỉ lệch tên → rename file + sửa `dependencies`; DAG xấu → `squashmigrations`. Verify: migrate vào DB sqlite **mới hoàn toàn từ đầu** thành công (chứng minh deploy PG mới được).

## Phase D — Race condition & business logic (P1)

- **D1.** Vote count (views.py:1657-1681): read-modify-write → `F('helpful_count') + 1` / `F('not_helpful_count') - 1` qua `.update()`.
- **D2.** Report count (views.py:1754-1763): `F('report_count') + 1`, rồi `refresh_from_db()` + set status nếu ≥3.
- **D3.** `booking_code` (models.py:395-405): sinh code + `try/except IntegrityError` retry tối đa 3 lần (bỏ vòng `while exists()` — vẫn có race window).
- **D4.** `booking_payment` (views.py:793-819): hiển thị từ `booking.total_price` đã lưu — không recompute từ giá tour hiện tại (fix sai lệch khi admin đổi giá sau khi khách đặt).
- **D5.** Thêm `('processing', 'Đang xử lý')` vào `PAYMENT_STATUS` (models.py:365-369) + makemigrations (đang được ghi ở views.py:827 nhưng không nằm trong choices).
- **D6.** `update_destination_scores` (views.py:1826-1827): `destination.rating` → field `avg_rating` (Destination không có field `rating` — hiện tại mỗi submit review fail âm thầm trong except).
- **D7.** Thống nhất session key: views.py:303 đọc `viewed_history` nhưng views.py:1147 ghi `viewed_destinations` → dùng 1 key duy nhất (`viewed_history`). Chấp nhận session cũ reset.
- **D8.** `goi_y_theo_the_loai` (views.py:609-626): `rating` → `average_rating`; `tags` là JSONField không phải taggit — bỏ `.all()`/`values_list`, đọc như list.
- **D9.** Login/Register (`users/views.py`): throttle login 10/min per IP qua DRF throttle class riêng.

## Phase E — External service & cache (P1)

- **E1.** Weather cache (`services/weather_service.py`): wrap `get_current_weather`/`get_weather_forecast` bằng `get_or_set_cache` TTL 600s, key = (round(lat,2), round(lon,2), date) — hết trạng thái chặn request 5-10s khi OWM/Open-Meteo chậm.
- **E2.** `signals.py` email: `try/except` + `logger.error` + `fail_silently=True` — admin duyệt thanh toán không bao giờ crash vì SMTP.
- **E3.** Cache invalidation: signal `post_save`/`post_delete` cho `TourPackage`/`Review` → `invalidate_cache(keys=['homepage:featured_tours', ...])`.

## Phase F — Tests & CI (P2)

- **F1.** Fix `users/tests.py` các kỳ vọng sai (401 → 400 cho missing fields).
- **F2.** Viết `travel/tests.py` (hiện trống):
  - Booking: giá adult/child/VAT đúng, `booking_code` unique, `total_price` lưu đúng
  - Review destination: yêu cầu login, chặn spam 5 phút, sentiment lưu vào cột
  - Vote: đổi vote đảo count đúng (verify sau khi có F expressions)
  - `all_tours`: có pagination + **patch `analyze_sentiment` assert không được gọi** (chống regression C3)
  - `api_search`: trả 429 khi vượt rate limit
- **F3.** `.github/workflows/ci.yml` (Python 3.12): install → `pip-audit` → `makemigrations --check --dry-run` → `manage.py check` → `manage.py test` (env `USE_LOCAL_DB=true`).
- **F4.** Backup/DR: `scripts/backup_db.sh` (pg_dump `$DATABASE_URL`, giữ 7 bản gần nhất) + `docs/BACKUP_RESTORE.md` các bước restore; chạy 1 lần restore vào DB scratch để chứng minh procedure chạy được.

## Phase G — Cleanup, tối ưu & docs (P2)

- **G1.** Xóa dead code (đã grep xác minh không được import chỗ khác): `ai_engine_new.py`, `ai_engine_backup.py`, `spam_detector.py`, `source.html`, `fix_ai_engine.py`, `update_all_scores.py`, `test_sentiment_quick.py`; bỏ `print()` ở views.py:1581, 1693 → logger.
- **G2.** `urls.py:52` bỏ route `favorites/` trùng; `destination_detail.html:923,968-969` đổi `{{ ...|safe }}` sang `json_script` (chống JSON-in-JS-string injection).
- **G3.** `api_search` (views.py:1270-1377): pre-filter DB-side bằng `icontains` (name/location/slug) rồi fuzzy-score chỉ trên shortlist — hết full-scan Python toàn bảng.
- **G4.** README mới: bảng env vars, bước setup (venv, migrate, createsuperuser, .env), deploy Railway (DATABASE_URL, start command gunicorn, attach PG plugin).
- **G5. (Đề xuất — cần cả nhóm đồng ý, default KHÔNG làm)** `git rm -r --cached media/` (50MB binary trong git); nếu làm kèm docs seed ảnh.

## Verify tổng cuối cùng

1. `manage.py check` + `makemigrations --check` sạch
2. Migrate thành công trên DB sqlite mới hoàn toàn (bằng chứng chuỗi migration deploy được lên PG mới)
3. Toàn bộ test pass (users + travel)
4. `git ls-files` không còn `.env`/`db*.sqlite3`; `pip-audit` không CVE nghiêm trọng chưa vá
5. Smoke test `DEBUG=False` + gunicorn: GET 200 cho `/`, `/tours/`, `/search/`, `/api/search/`

**Effort ước tính:** ~4-5 buổi (P0 ≈ 1; P1 ≈ 1.5; P2+CI ≈ 1.5-2). B1 là hành động user tự làm (rotate 2 key), tôi sẽ đưa hướng dẫn cụ thể ngay đầu buổi thực thi; mọi việc còn lại tôi làm trực tiếp.