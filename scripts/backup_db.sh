#!/usr/bin/env bash
# ============================================================
# Backup PostgreSQL cho WebDuLich (chạy trên server/Railway shell
# hoặc cron). Giữ lại 7 bản gần nhất.
#
# Cách dùng:
#   DATABASE_URL="postgresql://..." ./scripts/backup_db.sh [thư_muục_lưu]
#
# Restore: xem docs/BACKUP_RESTORE.md
# ============================================================
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
KEEP_COUNT=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: Biến DATABASE_URL chưa được đặt." >&2
  echo "Ví dụ: DATABASE_URL=\"postgresql://user:pass@host:5432/db\" $0" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/webdulich_${TIMESTAMP}.sql.gz"

echo "→ Đang backup..."
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"
echo "✅ Đã tạo: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Giữ lại $KEEP_COUNT bản gần nhất
ls -1t "$BACKUP_DIR"/webdulich_*.sql.gz 2>/dev/null | tail -n +$((KEEP_COUNT + 1)) | while read -r old; do
  echo "→ Dọn bản cũ: $old"
  rm -f "$old"
done

echo "Số bản hiện có: $(ls -1 "$BACKUP_DIR"/webdulich_*.sql.gz | wc -l) (giữ tối đa $KEEP_COUNT)"
