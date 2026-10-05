# Security Audit — WebDuLich

Ngày audit: theo working tree hiện tại. Phạm vi: `travel/`, `users/`, `myproject/settings.py`, `.env.example`, `.github/workflows/ci.yml`.

**Tổng quan tốt hơn kỳ vọng**: đã có fail-fast prod config, HSTS, secure cookies, JWT rotation + blacklist, throttle login, sanitize bằng bleach, fail-closed khi thiếu SECRET_KEY/ALLOWED_HOSTS, gitleaks + pip-audit trong CI, admin URL đổi qua env. Các finding dưới đây là lỗ hổng còn lại.

## Critical

| # | File:line | Lỗi | Khai thác | Fix |
|---|-----------|-----|-----------|-----|
| C1 | `.gitignore` (toàn file) | File lưu **UTF-16 LE + BOM + CRLF**. gitignore chỉ parse ASCII/UTF-8 → **toàn bộ rules không có tác dụng**. `git check-ignore .env db.sqlite3 media` → exit 1 (không ignore). `.env` đang chứa `EMAIL_HOST_PASSWORD` thật, `db.sqlite3` 796KB chứa user data — `git add -A` là lộ ngay. 276 file `media/` đã được track sẵn. | Commit lộ secret + user DB | Convert về UTF-8: `iconv -f UTF-16LE -t UTF-8 .gitignore > .gitignore.u8 && mv .gitignore.u8 .gitignore` rồi `git rm --cached` các file lẽ ra đã bị ignore. Rotate EMAIL app password nếu từng commit. |
| C2 | `travel/views.py:get_client_ip()` tin `X-Forwarded-For[0]` vô điều kiện | Attacker tự set header → spoof IP tùy ý → bypass dedup review (`user_ip` 5 phút), spoof `reporter_ip`, gian `ReviewVote` per-IP, ghi `SearchHistory.user_ip` sai — rate-limit `key='ip'` cũng bị bypass theo. (Đính chính: `RATELIMIT_IP_META_KEY` dạng dotted path lib **có** resolve qua `import_string` — đọc `core.py:_get_ip` — nên key resolution đúng, chỉ giá trị IP là giả được.) | ✅ FIXED: `get_client_ip` chỉ đọc XFF khi `TRUST_X_FORWARDED_FOR=True` (env, bật ở prod sau proxy) + lấy entry phải nhất; dev dùng `REMOTE_ADDR`. |

## High

| # | File:line | Lỗi | Khai thác | Fix |
|---|-----------|-----|-----------|-----|
| H1 | (gộp vào C2 ở trên — cùng root cause `get_client_ip`, đã fix chung) | — | — | — |
| H2 | `travel/views.py:~1365` `api_search` | `cache_key = get_cache_key('api_search_v3', query=query.lower()[:5])` — key chỉ 5 ký tự đầu của query. "da nang food" và "da nang hotel" → **cùng key, trả kết quả của nhau** trong 10 phút. Không phải lỗ bảo mật trực tiếp nhưng là data-integrity bug trên endpoint public. | Kết quả search sai | `query=query.lower()` (full string, `get_cache_key` đã tự hash khi >200 ký tự). |
| H3 | `travel/signals.py:8-21` `send_ticket_email` | `post_save` trên Booking: mọi lần `.save()` một booking `payment_status='paid'` đều gửi lại email vé (admin edit, status đổi completed...). Email gửi **không try/except** — SMTP chết → exception trong signal → transaction save booking **fail**, admin không thao tác được đơn paid. | Email spam + lock booking ops | Ghi nhận `email_sent_at` / check `update_fields`, wrap `msg.send()` trong try/except + log. |
| H4 | `requirements.txt` thiếu dep production | Settings dùng `whitenoise` middleware (luôn), `dj_database_url` (khi có `DATABASE_URL`), `meilisearch` SDK, PostgreSQL driver — **không cái nào trong requirements.txt**. Deploy prod theo file này → crash ngay `import whitenoise` hoặc `import dj_database_url`. | Deploy chết / lặng lẽ fallback | Thêm `whitenoise`, `dj-database-url`, `psycopg[binary]`, `meilisearch`, `gunicorn`. |

## Medium

| # | File:line | Lỗi | Fix |
|---|-----------|-----|-----|
| M1 | `users/views.py:RegisterView` | Không throttle → tạo account hàng loạt (account-farming cho review spam). | Thêm `throttle_classes=[AnonRateThrottle]` với scope riêng (vd 5/h). |
| M2 | `travel/views.py:~156` `change_password_api` | `set_password(new_password)` không qua `validate_password` → user tự hạ mật khẩu về "123456" sau khi register ép strong. | `from django.contrib.auth.password_validation import validate_password; validate_password(new_password, user)` trước `set_password`. |
| M3 | `users/views.py:logout_view` | Không `@permission_classes` → ai cũng POST refresh token bất kỳ để blacklist (deny-of-logout, thiệt hại nhỏ). | `@permission_classes([IsAuthenticated])`. |
| M4 | `travel/views.py:booking_success` (~L870) | Chỉ cần user mở URL success là `payment_status` unpaid→**processing** — ghi nhận "đã báo thanh toán" mà không có bằng chứng chuyển khoản. Admin có thể nhầm đơn chưa trả tiền là đang xử lý. | Đổi trạng thái bằng hành động rõ ràng (nút "Tôi đã chuyển khoản" POST) hoặc chỉ admin set; hiện flow chỉ là manual-trust nên rủi ro chấp nhận được nếu admin verify lại trước khi `paid` — ghi chú vào runbook. |
| M5 | `travel/views.py:api_submit_tour_review` (~L900) | `comment` lưu DB **không `bleach.clean`** (khác `api_submit_review` có sanitize). Template hiện autoescape nên XSS chưa lộ, nhưng dữ liệu bẩn nằm sẵn trong DB chờ 1 template `|safe` bất cẩn. | `bleach.clean(comment)[:2000]` giống hàm bên cạnh. |
| M6 | `travel/views.py:api_profile` PUT | `profile.birthday = request.data.get("birthday")` — string rác → `ValidationError` khi save → 500 thay vì 400. `phone`/`profession` không giới hạn độ dài check. | Validate qua `ProfileUpdateForm`/serializer đã có sẵn trong `forms.py`. |
| M7 | Upload `ImageField` (avatar, destination images) | Không giới hạn kích thước/loại file ở app level — Pillow verify image nhưng ảnh 50MB vẫn nhận → disk full. | `DATA_UPLOAD_MAX_MEMORY_SIZE` + validator `FileExtensionValidator`/size check trong form. |
| M8 | `users/views.py:LoginView` | `User.objects.get(email=email)` rồi `authenticate(username=user_obj.email)` — response message giống nhau (tốt) nhưng 2 nhánh timing khác nhau đáng kể (1 query vs hash password) → email-enumeration qua timing. | Gọi `authenticate` luôn kể cả khi `DoesNotExist` (dummy hash) hoặc chấp nhận — mức thấp. |

## Low / note

- `api_submit_review` dùng `datetime.now()` naive so sánh với `created_at` aware (`USE_TZ` mặc định True ở Django 6) → RuntimeWarning + cửa sổ 5-phút lệch giờ. Dùng `timezone.now()`.
- `SearchHistory` lưu IP + query của guest vô hạn — có `cleanup_search_history` command nhưng phải chạy tay; cân nhắc retention job (PII tối thiểu).
- `ReviewReport.object_id` là `PositiveIntegerField` không giới hạn + `review_obj` GenericFK — đã có check tồn tại, OK.
- `booking_code` random `HH`+6 số trong loop — đoán được (10^6 không gian), nhưng chỉ dùng làm nội dung chuyển khoản, không phải auth token → chấp nhận được; không dùng làm lookup secret.
- `source.html` 406KB ở repo root — kiểm tra có embed credential/track không trước khi giữ.
- Template `destination_detail.html` dùng `|safe` cho `route_info.geometry` + `nearby_*_json` — data nguồn từ service nội bộ (tọa độ, URL maps) chứ không phải user input → rủi ro thấp, nhưng nên đổi sang `json_script` filter cho sạch.
- `api_analyze_sentiment` public POST chạy PhoBERT inference mỗi request — rate-limit 10/m đúng hướng, nhưng xem C2: bucket đang chung toàn site.

## Checklist đã OK (không cần làm)

- [x] `DEBUG` mặc định False, fail-fast khi thiếu `SECRET_KEY`/`ALLOWED_HOSTS` ở prod
- [x] Secret đọc từ env, không hardcode key trong code (check toàn repo)
- [x] HSTS 1 năm + preload, `SESSION_COOKIE_SECURE/HTTPONLY`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, X-Frame-Options middleware
- [x] Không raw SQL / `extra()` / `cursor.execute` ngoài `ANALYZE` trong management command
- [x] `bleach.clean` trên review/comment chính, `|safe` chỉ trên data nội bộ
- [x] Booking IDOR: `booking_payment`, `booking_success`, `booking_history` đều filter `user=request.user`; giá tính server-side từ `tour.price`, không tin client
- [x] Login throttle 10/min, JWT 15 phút + rotation + blacklist sau rotation
- [x] CSRF middleware đủ; không `@csrf_exempt` còn sót (bản cũ đã xóa — comment cuối views.py)
- [x] `password_validation` đầy đủ 4 validator khi register
- [x] CI: gitleaks + pip-audit + `makemigrations --check` + `manage.py check`

## Thứ tự nên xử lý

1. **C1** (gitignore UTF-16) — 1 lệnh, chặn lộ secret ngay.
2. **C2 + H1** (rate-limit key + XFF trust) — sửa 1 chỗ `get_client_ip` + settings.
3. **H4** (requirements) — unblock deploy.
4. **H2, H3** — data correctness + email.
5. M1–M6 theo thứ tự liệt kê.
