# Backup & Restore — WebDuLich

## Backup (PostgreSQL)

### Chạy thủ công

```bash
DATABASE_URL="postgresql://user:pass@host:5432/db" ./scripts/backup_db.sh
```

Kết quả: file `backups/webdulich_YYYYMMDD_HHMMSS.sql.gz`, tự dọn chỉ giữ 7 bản gần nhất.

### Chạy định kỳ (cron, mỗi ngày 3h sáng)

```cron
0 3 * * * cd /path/to/WebDuLich && DATABASE_URL="postgresql://..." ./scripts/backup_db.sh >> backups/backup.log 2>&1
```

Lưu ý với Railway: Railway đã có backup tự động theo plan, script này là lớp
bảo hiểm off-site — chạy `pg_dump` từ máy local với `DATABASE_URL` lấy từ
Railway Dashboard (chỉ possible khi DB public).

## Restore (PHẢI TEST ÍT NHẤT 1 LẦN/TRƯỚC KHI NHẬN BOOKING THẬT)

### 1. Restore vào DB scratch để test

```bash
# Tạo DB rỗng để test
createdb webdulich_restore_test

# Giải nén và restore
gunzip -c backups/webdulich_<timestamp>.sql.gz | psql "$RESTORE_TEST_URL"

# Kiểm tra dữ liệu
psql "$RESTORE_TEST_URL" -c "SELECT COUNT(*) FROM travel_tourpackage;"
psql "$RESTORE_TEST_URL" -c "SELECT COUNT(*) FROM users_user;"
```

### 2. Restore lên production (chỉ khi thảm họa)

```bash
# CẢNH BÁO: ghi đè toàn bộ dữ liệu hiện tại
gunzip -c backups/webdulich_<timestamp>.sql.gz | psql "$PROD_DATABASE_URL"
```

## RPO / RTO hiện tại

- **RPO** (mất dữ liệu tối đa): 24h (nếu cron chạy hằng ngày) — booking nhận
  trong khoảng này có thể mất nếu DB chết. Muốn RPO thấp hơn: tăng tần suất cron.
- **RTO** (thời gian khôi phục): ~30 phút (restore thủ công qua các bước trên,
  giả sử có DB mới sẵn).

## Đã test restore chưa?

| Ngày | File backup | Kết quả |
|------|-------------|---------|
| (điền sau lần test đầu) | | |
