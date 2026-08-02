#!/usr/bin/env bash
# Back up the one thing that cannot be regenerated, and prove it is readable.
#
#   DEPLOY_LANE=fly FLY_APP=my-assistant ./deploy/backup.sh [keep]
#
# NOT LIVE-PROVISIONED. Gated off by default, like every external lane here.
#
# All durable state is one SQLite file (ADR-0005): memory, audit log, approvals,
# idempotency keys, the outbox. Qdrant re-ingests and Ollama re-pulls, so this
# file is the whole backup story — which is a design decision paying off, not an
# accident.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ "${DEPLOY_LANE:-off}" == "fly" ]] || { echo "deploy lane off (DEPLOY_LANE=fly)."; exit 0; }
: "${FLY_APP:?set FLY_APP}"
KEEP="${1:-7}"
DEST="${BACKUP_DIR:-./backups}"
mkdir -p "$DEST"

SHA="$(flyctl ssh console --app "$FLY_APP" -C 'printenv GIT_SHA' 2>/dev/null | tr -d '\r\n' || git rev-parse HEAD)"
NAME="$(python -c "
import datetime, sys
sys.path.insert(0, 'src')
from release import backup_name
print(backup_name(at=datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds'), sha='$SHA'))
")"

# Taken through SQLite's own online-backup API, never `cp`. A file copy of a
# database being written to is torn: the WAL and the main file disagree, and you
# find out at restore time, which is the worst moment on offer.
flyctl ssh console --app "$FLY_APP" -C \
  "python -c \"import sqlite3; sqlite3.connect('/data/assistant.db').backup(sqlite3.connect('/data/$NAME'))\""
flyctl ssh sftp get "/data/$NAME" "$DEST/$NAME" --app "$FLY_APP"
flyctl ssh console --app "$FLY_APP" -C "rm -f /data/$NAME"

# Verified here rather than "later". An unverified backup is a folder of files
# you HOPE are a database, and the only place this check ever actually runs is
# the script that took the copy.
python -c "
import sys; sys.path.insert(0, 'src')
from release import prune, verify_backup
from pathlib import Path
counts = verify_backup('$DEST/$NAME', ['audit_log', 'approvals', 'idempotency', 'outbox', 'memories'])
print('verified', '$NAME', counts)
for stale in prune([p.name for p in Path('$DEST').glob('*.db')], keep=int('$KEEP')):
    Path('$DEST', stale).unlink()
    print('pruned', stale)
"
