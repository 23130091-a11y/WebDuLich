# MVP Free-tier Checklist (AI-ready)

**Version:** 1.0  
**Dành cho:** Vibe-code với AI (Codex / OpenCode / Cursor…), chưa mua domain, chưa mua VPS, đang dùng free tier.  
**Mục tiêu:** Đưa checklist này vào AI → AI tự inspect code + chạy test + báo cáo rõ ràng.

> **Nguyên tắc:** Implemented ≠ Verified.  
> AI **không được** đánh PASS chỉ vì “code có”. Phải có Evidence thực tế.

---

## Cách dùng với AI (copy nguyên đoạn này)

```text
Bạn là Production Readiness Auditor.
Nhiệm vụ: Đánh giá dự án hiện tại theo checklist bên dưới.

Quy tắc bắt buộc:
1. Chỉ đánh PASS khi Acceptance Criteria đạt VÀ có Evidence cụ thể (file path, command output, test result).
2. Không giả định. Không tự tạo Evidence.
3. Nếu không thể verify (thiếu test, thiếu config, không chạy được) → đánh NOT VERIFIED.
4. Nếu mục không áp dụng với free-tier / local → đánh N/A và ghi lý do.
5. Ưu tiên kiểm tra thực tế: đọc code, chạy test, kiểm tra config, tìm secret, kiểm tra error handling.
6. Output theo đúng format ở cuối checklist.
7. Không sửa code trừ khi được yêu cầu rõ ràng.

Bắt đầu audit ngay.
```

---

## 1. Priority trong giai đoạn này

| Priority | Ý nghĩa với free-tier                        |
| -------- | -------------------------------------------- |
| **P0**   | Bắt buộc. FAIL → chưa nên cho user thật dùng |
| **P1**   | Nên có. Có thể tạm chấp nhận nếu ghi rõ risk |
| **P2**   | Để sau khi có user / có tiền                 |

Nhiều mục infra/DR/cost của bản Full sẽ là **N/A** ở giai đoạn này.

---

## 2. Checklist

### A. Product & Core Flow (P0)

| ID      | Priority | Requirement                         | Acceptance Criteria                                | AI cần làm gì                                                                          |
| ------- | -------- | ----------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------- |
| PRD-001 | P0       | Critical user journeys hoạt động    | Happy path + error path chính chạy được end-to-end | Tìm critical flow (auth, create, pay nếu có…). Chạy hoặc mô tả cách test thủ công/E2E. |
| PRD-002 | P0       | Business rule enforce ở backend     | Không thể bypass bằng sửa request/API              | Kiểm tra API handler: validation + authorization có ở server không.                    |
| PRD-003 | P1       | Có cách tắt nhanh feature nguy hiểm | Feature flag đơn giản hoặc env toggle              | Tìm xem có flag/env để tắt feature không.                                              |

---

### B. Frontend (P0–P1)

| ID     | Priority | Requirement                                         | Acceptance Criteria                                      | AI cần làm gì                                              |
| ------ | -------- | --------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------- |
| FE-001 | P0       | Không blank screen / fatal JS error ở critical page | Critical route load được, console không fatal error      | Đọc entry page + critical components. Tìm unhandled error. |
| FE-002 | P0       | Auth UX đúng                                        | Login / logout / expired session xử lý đúng phía UI      | Kiểm tra auth flow, redirect khi chưa login, xử lý 401.    |
| FE-003 | P0       | Form validation                                     | Client + server đều validate; invalid không tạo data xấu | Kiểm tra form + API validation tương ứng.                  |
| FE-004 | P1       | Loading / error / empty state                       | Critical async có trạng thái rõ                          | Tìm loading/error UI ở flow chính.                         |

---

### C. Backend & API (P0)

| ID     | Priority | Requirement                | Acceptance Criteria                                       | AI cần làm gì                                            |
| ------ | -------- | -------------------------- | --------------------------------------------------------- | -------------------------------------------------------- |
| BE-001 | P0       | Input validation           | Body/query/params được validate, reject rõ ràng           | Đọc validation schema / middleware.                      |
| BE-002 | P0       | Authentication enforcement | Protected route reject missing/invalid token              | Kiểm tra middleware auth trên protected routes.          |
| BE-003 | P0       | Authorization              | User không truy cập resource của người khác (IDOR)        | Tìm chỗ lấy resource theo ID → kiểm tra ownership check. |
| BE-004 | P0       | Error handling an toàn     | Không leak stack trace / secret / internal path ra client | Kiểm tra error handler / try-catch global.               |
| BE-005 | P0       | Transaction / consistency  | Multi-step quan trọng không để partial state              | Tìm mutation nhiều bước → có transaction không.          |
| BE-006 | P1       | Idempotency cơ bản         | Retry không tạo duplicate quan trọng (nếu có)             | Kiểm tra unique constraint hoặc idempotency key.         |

---

### D. Database (P0–P1)

| ID     | Priority | Requirement           | Acceptance Criteria                                    | AI cần làm gì                               |
| ------ | -------- | --------------------- | ------------------------------------------------------ | ------------------------------------------- |
| DB-001 | P0       | Schema có migration   | Có thể dựng DB từ migration (hoặc schema file rõ ràng) | Kiểm tra thư mục migration / schema.        |
| DB-002 | P0       | Constraint quan trọng | FK / UNIQUE / NOT NULL cho data critical               | Đọc schema, tìm thiếu constraint nguy hiểm. |
| DB-003 | P1       | Query nguy hiểm       | Không N+1 rõ ràng, không unbounded list                | Tìm query list không pagination.            |

> **Ghi chú free-tier:** Backup/restore production chưa bắt buộc. Nhưng nếu dùng Supabase/Neon free → ghi N/A với lý do “free tier managed backup”.

---

### E. Security (P0 – quan trọng nhất)

| ID      | Priority | Requirement                            | Acceptance Criteria                                          | AI cần làm gì                                                       |
| ------- | -------- | -------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------- |
| SEC-001 | P0       | Không có secret trong code             | Không hardcode API key, password, token                      | Scan toàn bộ repo tìm pattern secret (API_KEY, SECRET, password=…). |
| SEC-002 | P0       | Password hash đúng                     | Không lưu plaintext password                                 | Kiểm tra auth register/login.                                       |
| SEC-003 | P0       | Injection protection                   | SQL/ORM parameterized, không nối string                      | Kiểm tra raw query.                                                 |
| SEC-004 | P0       | XSS cơ bản                             | User content được escape/sanitize khi render                 | Kiểm tra chỗ render user input.                                     |
| SEC-005 | P0       | Auth + Authorization không bypass được | Đã test IDOR / missing auth                                  | Kết hợp BE-002 + BE-003.                                            |
| SEC-006 | P0       | CORS / cookie hợp lý                   | Không `Access-Control-Allow-Origin: *` + credentials         | Kiểm tra CORS config.                                               |
| SEC-007 | P1       | Rate limit cơ bản                      | Auth / expensive endpoint có giới hạn (nếu framework hỗ trợ) | Tìm middleware rate-limit.                                          |
| SEC-008 | P1       | Env tách biệt                          | `.env.example` có, `.env` nằm trong `.gitignore`             | Kiểm tra `.gitignore` + `.env.example`.                             |

---

### F. Reliability cơ bản (P0–P1)

| ID      | Priority | Requirement                    | Acceptance Criteria                   | AI cần làm gì                                       |
| ------- | -------- | ------------------------------ | ------------------------------------- | --------------------------------------------------- |
| REL-001 | P0       | Timeout outbound               | Gọi API ngoài có timeout              | Tìm fetch/axios/http client → có timeout không.     |
| REL-002 | P0       | Error không làm crash toàn app | Unhandled error được bắt              | Kiểm tra global error handler (frontend + backend). |
| REL-003 | P1       | Health check đơn giản          | Có `/health` hoặc tương đương trả 200 | Tìm route health.                                   |

---

### G. Testing (P0)

| ID       | Priority | Requirement                    | Acceptance Criteria                                        | AI cần làm gì                                               |
| -------- | -------- | ------------------------------ | ---------------------------------------------------------- | ----------------------------------------------------------- |
| TEST-001 | P0       | Critical logic có test         | Business logic quan trọng có unit/integration test và pass | Chạy `npm test` / `pytest` / tương đương. Báo kết quả thật. |
| TEST-002 | P0       | Critical flow có thể test được | Ít nhất có cách chạy thủ công hoặc E2E cho flow chính      | Liệt kê cách test critical journey.                         |
| TEST-003 | P1       | CI cơ bản (nếu có)             | Push → lint/test chạy được (GitHub Actions free cũng được) | Kiểm tra `.github/workflows` hoặc tương đương.              |

---

### H. Config & Deploy free-tier (P0–P1)

| ID      | Priority | Requirement                    | Acceptance Criteria                                                  | AI cần làm gì                   |
| ------- | -------- | ------------------------------ | -------------------------------------------------------------------- | ------------------------------- |
| CFG-001 | P0       | Production mode đúng           | DEBUG=false / NODE_ENV=production khi deploy                         | Kiểm tra env handling.          |
| CFG-002 | P0       | Secret không commit            | `.env` trong `.gitignore`, không có secret trong git history gần đây | Kiểm tra `.gitignore` + scan.   |
| CFG-003 | P1       | Deploy được trên free platform | Có hướng dẫn deploy Vercel / Railway / Render / Cloudflare free      | Đọc README deploy section.      |
| CFG-004 | P1       | README đủ để người khác chạy   | Clone → install → env → run được                                     | Đọc README, đánh giá freshness. |

---

### I. Observability tối thiểu (P1)

| ID      | Priority | Requirement          | Acceptance Criteria                                             | AI cần làm gì           |
| ------- | -------- | -------------------- | --------------------------------------------------------------- | ----------------------- |
| OBS-001 | P1       | Log lỗi quan trọng   | Error được log (console hoặc service free như Sentry free tier) | Kiểm tra error logging. |
| OBS-002 | P1       | Không log secret/PII | Log không chứa password, token, full card…                      | Scan log statement.     |

---

### J. AI Features (chỉ khi project có AI)

| ID     | Priority | Requirement                       | Acceptance Criteria                          | AI cần làm gì                                          |
| ------ | -------- | --------------------------------- | -------------------------------------------- | ------------------------------------------------------ |
| AI-001 | P0       | API key không lộ client           | Key chỉ ở server / edge function             | Kiểm tra frontend có gọi thẳng OpenAI/Anthropic không. |
| AI-002 | P0       | Có limit input                    | Không cho user gửi prompt vô hạn             | Kiểm tra validation length/token.                      |
| AI-003 | P0       | Fail không crash                  | Provider down → trả lỗi đẹp, không 500 trắng | Kiểm tra try/catch quanh AI call.                      |
| AI-004 | P1       | Không gửi data nhạy cảm lung tung | Prompt không chứa secret/PII ngoài ý muốn    | Kiểm tra chỗ build prompt.                             |

---

### K. Những mục **N/A** ở giai đoạn free-tier (ghi rõ)

| Mục                              | Lý do N/A                                                     |
| -------------------------------- | ------------------------------------------------------------- |
| Domain + HTTPS custom            | Chưa mua domain                                               |
| VPS / resource limit production  | Đang dùng free platform                                       |
| Automated backup + restore drill | Free managed DB (Supabase/Neon…) hoặc chưa có data quan trọng |
| Full Disaster Recovery / RPO-RTO | Chưa có user thật                                             |
| Load testing quy mô lớn          | Chưa có traffic                                               |
| Cost monitoring / budget alert   | Chưa chi tiền                                                 |
| WAF / Bot protection trả phí     | Chưa cần                                                      |
| Multi-region / advanced scaling  | Chưa cần                                                      |

AI **phải** đánh `N/A` các mục trên và ghi lý do, **không** cố gắng PASS/FAIL chúng.

---

## 3. Evidence Record (bắt buộc)

Với mỗi mục P0, AI phải ghi theo format:

```markdown
### [ID] — Status: PASS | FAIL | PARTIAL | NOT VERIFIED | N/A

- **Evidence:** (file path, đoạn code, command output, test result)
- **Risk:** Low / Medium / High / Critical
- **Ghi chú:** ...
```

---

## 4. Output format bắt buộc của AI

```markdown
# MVP Free-tier Audit Report

## Overall

- Status: READY / CONDITIONAL / NOT READY
- Có thể cho user thật dùng chưa: Có / Chưa / Có điều kiện

## Summary

| Priority | PASS | FAIL | PARTIAL | NOT VERIFIED | N/A |
| -------- | ---- | ---- | ------- | ------------ | --- |
| P0       |      |      |         |              |     |
| P1       |      |      |         |              |     |

## P0 Blockers (bắt buộc sửa trước khi cho user dùng)

1. [ID] — mô tả ngắn + cách sửa gợi ý
2. ...

## Security Findings (quan trọng)

- ...

## Những gì đã làm tốt

- ...

## Missing Evidence / Không thể verify

- ...

## Recommended Next Actions (ưu tiên)

### Phải làm ngay (P0)

1. ...

### Nên làm sớm (P1)

1. ...

### Để sau khi có user / có tiền

1. ...

## Final Decision

GO / CONDITIONAL GO / NO-GO

Lý do ngắn:
```

---

## 5. Golden Rules cho giai đoạn này

1. **Security + Core flow + Không leak secret** quan trọng hơn performance và scale.
2. Có thể chạy local + deploy free (Vercel/Railway/Render/Supabase…) là đủ để bắt đầu có user.
3. Khi có user thật và bắt đầu thu tiền → chuyển sang checklist Full (v1.1) và mua domain + VPS/managed service.
4. AI chỉ PASS khi có Evidence. Không có Evidence = NOT VERIFIED.

---

**Cách đưa vào AI:**

1. Copy toàn bộ file này.
2. Paste vào Codex / OpenCode / Cursor.
3. Thêm dòng: `Hãy audit toàn bộ repository hiện tại theo checklist trên.`
4. (Tuỳ chọn) Chỉ định thư mục hoặc file quan trọng nếu project lớn.
