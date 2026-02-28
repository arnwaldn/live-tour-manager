#!/usr/bin/env sh
# =============================================================================
# GigRoute - PostgreSQL Backup Script
# Runs daily via Docker backup service. Retains 7 days of backups.
# =============================================================================

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/gigroute_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=7

echo "[backup] $(date) - Starting backup..."

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Run pg_dump and compress
pg_dump -h "${PGHOST}" -U "${PGUSER}" -d "${PGDATABASE}" \
    --no-owner --no-privileges --clean --if-exists \
    | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "[backup] $(date) - Backup successful: ${BACKUP_FILE} (${SIZE})"
else
    echo "[backup] $(date) - ERROR: Backup failed!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Remove backups older than retention period
echo "[backup] Cleaning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "gigroute_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
REMAINING=$(ls -1 "${BACKUP_DIR}"/gigroute_*.sql.gz 2>/dev/null | wc -l)
echo "[backup] ${REMAINING} backup(s) retained."
