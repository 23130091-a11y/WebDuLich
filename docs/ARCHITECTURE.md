# Architecture — WebDuLich

Tài liệu điều hướng cho dev mới. Django 6.0 monolith, 2 app: `travel` (domain chính), `users` (auth + preference). DRF + JWT cho `/auth/*` và vài API JSON; phần lớn site là Django template truyền thống.

## 1. Request flows chính

### Booking (flow tiền — quan trọng nhất)

```
GET  /book-tour/<tour_id>/    book_tour      → booking_form.html (BookingForm)
POST /book-tour/<tour_id>/    book_tour      → tính giá server-side:
                                              total = adults*price + children*price*0.7 + VAT 10%
                                              → Booking(status='pending', payment_status='unpaid')
                                              → redirect booking_payment
GET  /payment/<booking_id>/   booking_payment → booking_payment.html (QR JS, manual transfer)
GET  /success/<booking_id>/   booking_success → payment_status unpaid→'processing' (user báo đã ck)
                                              → render booking_success.html
Admin đổi payment_status='paid'               → signals.py send_ticket_email → e_ticket.html → SMTP
GET  /booking-history/        booking_history → list đơn của user
```

Không có payment gateway — thanh toán là **manual transfer + admin xác nhận**. `payment_status='paid'` chỉ admin set (xem M4 trong SECURITY_AUDIT: `booking_success` tự lật unpaid→processing khi user mở link).

### Search

```
GET /search/?q=..&location=..&type=..   search        → ORM icontains + variants, lưu SearchHistory
GET /api/search/?q=..                   api_search    → score bằng utils_helpers.calculate_search_score
                                                      trên TOÀN BỘ Destination + TourPackage (loop Python!)
                                                      cache key lỗi — xem SECURITY_AUDIT H2
                                                      (meili_service.py tồn tại nhưng api_search KHÔNG gọi)
GET /api/provinces/?q=..                api_search_provinces → autocomplete tỉnh
```

`api_search` duyệt `for dest in Destination.objects.all()` rồi tính score trong Python — O(N) mỗi request, chỉ sống nhờ cache 10 phút (mà key đang sai, xem audit H2). `meili_service.py` đã viết sẵn nhưng view không dùng.

### Review + sentiment

```
POST /api/review/            api_submit_review        → bleach + spam regex + dedup IP/user 5ph
                                                      → ai_engine.analyze_sentiment(comment)
                                                      → update_destination_scores() → RecommendationScore
POST /api/tour_review/       api_submit_tour_review   → check Booking completed+paid → verified badge
POST /api/review/vote/       api_vote_review          → helpful/not_helpful, dedup theo user|IP
POST /api/review/report/     api_report_review        → ReviewReport (GenericFK), ≥3 report → pending
POST /api/analyze-sentiment/ api_analyze_sentiment    → realtime preview PhoBERT, 10/m
```

### Auth (API JSON, không dùng template)

```
POST /auth/register   users.RegisterView    → validate_password → user + JWT + session login
POST /auth/login      users.LoginView       → throttle 10/m, lookup email → authenticate(email)
POST /auth/preferences save_preferences     → bulk_create TravelPreference (t×loc matrix)
POST /auth/api/logout/ logout_view          → session logout + blacklist refresh token
```

### Home

`home()` (~L300-490) — view nặng nhất: static image scan + top destinations + personalized (TravelPreference ∪ viewed_history ∪ favorites) + featured + trending (SearchHistory 7 ngày có trọng số) + booking-based. Phần lớn qua `get_or_set_cache` 10–30 phút; phần personalized tính mỗi request.

## 2. Data model (travel/models.py ~775 dòng)

| Model | Core? | Quan hệ / ghi chú |
|---|---|---|
| `Category` | core | slug, icon; TourPackage + Destination đều FK |
| `TravelType` | core | M2M với Destination |
| `Destination` | core | M2M travel_type, JSONField tags, lat/lon, `get_nearby_*_data()` gọi service trực tiếp từ model (fat model) |
| `DestinationImage` | phụ | gallery cho destination |
| `TourPackage` | core | FK destination+category, price, JSONField tags, `update_rating()` aggregate từ TourReview |
| `TourImage` | phụ | |
| `TourReview` | core | FK tour+user, sentiment fields, GenericRelation reports. **BUG: `not_helpful_count` khai báo 2 lần** (dòng thứ 2 đè dòng 1 — vô hại vì cùng kiểu nhưng là dấu hiệu merge cẩu thả) |
| `Booking` | core | booking_code `HH`+6 số random loop-unique; status/payment_status choices |
| `SearchHistory` | phụ | query + user_ip — PII-lite, cần retention job |
| `Review` | core | destination review, sentiment, IP/UA cho anti-spam, reports GenericRelation |
| `ReviewVote` | phụ | FK tới cả Review lẫn TourReview + 2 UniqueConstraint — thiết kế lệch (nên 1 FK generic) |
| `ReviewReport` | phụ | GenericFK tới Review/TourReview |
| `RecommendationScore` | core | **OneToOne tới CẢ Destination lẫn TourPackage trên cùng 1 bảng** — 1 row chỉ dùng 1 trong 2 FK, mất khả năng enforce "đúng 1 FK" ở DB level |
| `AccountProfile` | phụ | 1-1 user: phone/birthday/profession/avatar — lặp `avatar` với `users.User.avatar` (2 nơi lưu avatar!) |
| `Favorite` (tour) | core | unique(user, tour) |
| `FavoriteDestination` | core | unique(user, destination) — 2 model favorite riêng (có thể gộp GenericFK hoặc giữ — đổi phải migrate) |
| `RecommendationConfig` | phụ | singleton trọng số scoring, enforce ở `save()` |

## 3. AI pipeline

```
ai_engine.py (1235 dòng — gộp mọi thứ):
  SentimentAnalyzer        PhoBERT fine-tuned (travel/phobert-travel-sentiment-final/)
                           lazy-load qua singleton get_sentiment_analyzer()
                           fallback rule-based: JSON keywords + negation/intensifier/
                           sarcasm/contrast + NEGATIVE_BEHAVIOR_PATTERNS override
                           _combine_scores(): 8-case gating PhoBERT↔rule weighted
  RecommendationEngine     wraps scoring_engine (Universal Scoring v2.1)
  Public funcs             analyze_sentiment, get_similar_destinations,
                           get_personalized_recommendations (LƯU Ý: dùng
                           destination.travel_type__icontains — M2M không có icontains,
                           code chết, chỉ chạy khi được gọi — hiện không view nào gọi)

scoring_engine.py (530 dòng): component ∈[0,10] → overall ∈[0,100] × confidence
spam_detector.py  (454 dòng): 7 loại spam — VIẾT XONG NHƯNG KHÔNG FILE NÀO IMPORT
                              (dead module, chỉ regex inline ở api_submit_review)
```

Vị trí model weights: `ai_engine.py` tìm ở `travel/models/phobert-travel-sentiment-final/` — **sai path**, model thật ở `travel/phobert-travel-sentiment-final/` (thiếu cấp `models/`) → luôn fallback về HF public `wonrax/phobert-...` hoặc rule-based. Model fine-tuned trong repo không bao giờ được load.

`update_all_scores.py` (repo root, chạy tay qua `django.setup()`) **duplicate** `update_destination_scores()` trong views.py và `management/commands/calculate_scores.py` — 3 bản cùng công thức.

## 4. Trùng lặp / code smell chính

| Vấn đề | Vị trí | Ghi chú |
|---|---|---|
| 3 file ai_engine | `ai_engine.py` (đang dùng), `ai_engine_backup.py`, `ai_engine_new.py` | backup/new là snapshot cũ — xoá được, git giữ history |
| 3 bản update scores | `views.py:update_destination_scores`, `update_all_scores.py`, `commands/calculate_scores.py` | gộp về 1 hàm trong services |
| `spam_detector.py` 454 dòng | không ai import | dead module — hoặc wire vào api_submit_review (thay regex inline) hoặc xoá |
| `favorite_list` URL khai báo 2 lần | `urls.py` dòng `favorites/` xuất hiện 2 lần | Django dùng bản đầu — xoá bản thừa |
| `forms.py` import `User` sai | `from django.contrib.auth.models import User` | sai model! `AUTH_USER_MODEL='users.User'` — `UserUpdateForm` bind vào model auth.User mặc định, không phải custom user → save() ghi sai bảng nếu form này được dùng (hiện không view nào dùng, may mắn) |
| Fat model | `Destination.get_weather_data` gọi `requests` HTTP trực tiếp trong model | vi phạm layering; move sang services |
| Session key lệch | home đọc `viewed_history`, destination_detail ghi `viewed_destinations` | **2 key khác nhau → personalized dựa trên viewed_history không bao giờ có data** |
| `meili_service` + `reindex_meili` | service hoàn chỉnh, view không gọi | feature flag chết — hoặc wire vào api_search hoặc đánh dấu unused |
| views.py 2115 dòng | logic business, AI, util, admin helper (`display_review`) lẫn nhau | tách theo domain — xem roadmap |
| `Rating...` — `TourPackage` dùng `tags` JSONField, `Destination` cũng JSONField | taggit (`TaggableManager`) import ở models.py nhưng **không model nào dùng** | dependency thừa |
| `from linecache import cache` | models.py dòng 2 | import rác, shadowing nguy hiểm |
| `destination_list` view | urls có mount, comment "chưa sd" | |

## 5. Dependencies lạ trong requirements.txt

- `networkx`, `sympy`, `mpmath`, `safetensors`, `filelock`, `fsspec` — transitive của torch/transformers, OK.
- **Thiếu** (dùng nhưng không khai): `whitenoise`, `dj-database-url`, `psycopg`, `meilisearch`, `gunicorn`, `python-dotenv` có rồi. Chi tiết: SECURITY_AUDIT H4.
- `bleach`, `django-ratelimit`, `taggit`, `drf-spectacular` — đã dùng đúng (taggit chỉ import, chưa dùng thật).

## 6. Module map nhanh

```
myproject/settings.py   12-factor, fail-fast prod, DB: DATABASE_URL > PG* > SQLite
myproject/urls.py       admin(env path) + travel + auth + drf-spectacular docs
travel/views.py         2115 dòng — mọi view (xem flows ở mục 1)
travel/models.py        775 dòng — 17 model
travel/forms.py         3 form (UserUpdateForm bind sai User — xem mục 4)
travel/services/        weather (OWM→Open-Meteo), routing, distance_helper,
                        nearby_service (chỉ build Google Maps URL — không API call),
                        meili_service (viết xong, không gọi)
travel/ai_engine.py     PhoBERT + rule-based hybrid (đọc mục 3)
travel/scoring_engine.py universal scoring v2.1
travel/spam_detector.py  DEAD — không ai import
travel/cache_utils.py   get_cache_key/get_or_set_cache — LocMemCache
travel/signals.py       email vé khi paid (xem audit H3)
travel/management/commands/  15 command: import csv/destinations, crawl reviews,
                        calculate_scores, reindex_meili, cleanup, diagnostics...
users/views.py          Register/Login/preferences/logout (JWT + session hybrid)
users/serializers.py    UserSerializer (validate_password OK)
finetune_phobert/       notebook + scripts train model, không phải runtime code
data/, scripts/, WebDuLich/(nested dir?)  — kiểm tra trước khi dọn
```

## 7. Fix nhanh đề xuất (≤1 ngày, impact cao)

1. Đổi path model trong `ai_engine.py`: `travel/models/phobert-...` → `travel/phobert-travel-sentiment-final` — model fine-tuned mới thật sự chạy.
2. Thống nhất session key `viewed_destinations` ở `home()`.
3. `api_search` cache key dùng full query.
4. `users/views.py` — xoá nhánh `User.objects.get` trước `authenticate` (authenticate nhận username=email trực tiếp, `USERNAME_FIELD='email'`).
5. `forms.py` — `from django.contrib.auth import get_user_model`.
