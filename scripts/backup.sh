#!/bin/bash
#
# Nightly backup of the Domovik database and uploaded documents.
# Z10 (2026-07-25): the privacy policy promised daily backups with 30-day retention
# and none existed - a server failure would have destroyed every submitted
# application. Runs as the mihailo user from cron:
#
#     0 1 * * * /var/www/domovik/scripts/backup.sh >> /var/www/domovik/logs/backup.log 2>&1
#
# Contents (per run, both gzipped):
#     db-YYYYmmdd-HHMMSS.sql.gz       full mysqldump of the application database
#     media-YYYYmmdd-HHMMSS.tar.gz    everything under media/ (applicant documents)
#
# RESTORE:
#     gunzip -c BACKUP_DIR/db-<stamp>.sql.gz | mysql -u USER -p DBNAME
#     tar xzf BACKUP_DIR/media-<stamp>.tar.gz -C /var/www/domovik
#
# The backups hold personal data, so BACKUP_DIR is 0700 and the files 0600.
# They live on the SAME disk as the server: this protects against a bad migration,
# an accidental delete or a corrupt table, NOT against losing the machine. An
# off-site copy is still a separate, unfinished task.
set -euo pipefail

PROJECT_DIR=/var/www/domovik
BACKUP_DIR=/home/mihailo/backups/domovik
RETENTION_DAYS=30
STAMP=$(date +%Y%m%d-%H%M%S)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# --- credentials ---------------------------------------------------------
# Read from .env. Passed to mysqldump through a temp defaults file rather than
# --password=, which would expose the password in `ps` to every user on the box.
get_env() { grep -E "^$1=" "$PROJECT_DIR/.env" | head -1 | cut -d= -f2-; }

DB_NAME=$(get_env DB_NAME)
DB_USER=$(get_env DB_USER)
DB_PASSWORD=$(get_env DB_PASSWORD)
DB_HOST=$(get_env DB_HOST)
DB_HOST=${DB_HOST:-localhost}

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    log "GREŠKA: DB_NAME/DB_USER nisu pročitani iz .env - prekidam."
    exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

DEFAULTS_FILE=$(mktemp)
chmod 600 "$DEFAULTS_FILE"
trap 'rm -f "$DEFAULTS_FILE"' EXIT
cat > "$DEFAULTS_FILE" <<EOF
[client]
user=$DB_USER
password=$DB_PASSWORD
host=$DB_HOST
EOF

# --- database ------------------------------------------------------------
DB_FILE="$BACKUP_DIR/db-$STAMP.sql.gz"
log "Backup baze $DB_NAME -> $(basename "$DB_FILE")"

# --single-transaction: consistent snapshot without locking the site out.
# Written to .part first so an interrupted run never leaves a truncated file
# that looks like a valid backup.
mysqldump --defaults-extra-file="$DEFAULTS_FILE" \
    --single-transaction \
    --routines \
    --triggers \
    --no-tablespaces \
    "$DB_NAME" | gzip > "$DB_FILE.part"
mv "$DB_FILE.part" "$DB_FILE"
chmod 600 "$DB_FILE"

# gzip of an empty dump is ~20 bytes; anything that small means the dump failed.
DB_SIZE=$(stat -c%s "$DB_FILE")
if [ "$DB_SIZE" -lt 1024 ]; then
    log "GREŠKA: dump baze je samo $DB_SIZE bajtova - verovatno neuspeo. Brišem."
    rm -f "$DB_FILE"
    exit 1
fi

# --- uploaded documents --------------------------------------------------
MEDIA_FILE="$BACKUP_DIR/media-$STAMP.tar.gz"
log "Backup dokumenata -> $(basename "$MEDIA_FILE")"
tar czf "$MEDIA_FILE.part" -C "$PROJECT_DIR" media
mv "$MEDIA_FILE.part" "$MEDIA_FILE"
chmod 600 "$MEDIA_FILE"

# --- retention -----------------------------------------------------------
# Deleted only after the new backup succeeded, so a failing run never leaves
# the server with nothing.
DELETED=$(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.gz' -mtime +$RETENTION_DAYS -print -delete | wc -l)
find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.part' -mtime +1 -delete

log "Gotovo. Baza: $(du -h "$DB_FILE" | cut -f1), dokumenta: $(du -h "$MEDIA_FILE" | cut -f1). Obrisano starih: $DELETED. Ukupno: $(du -sh "$BACKUP_DIR" | cut -f1)"
