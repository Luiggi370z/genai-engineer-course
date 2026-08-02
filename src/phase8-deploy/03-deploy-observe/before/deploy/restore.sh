#!/usr/bin/env bash
# Put a backup back, with the writer stopped and the file checked first.
#
#   DEPLOY_LANE=fly FLY_APP=my-assistant ./deploy/restore.sh ./backups/20260801T221500-9f2c1ab34de5.db
#
# NOT LIVE-PROVISIONED. Gated off by default.
#
# A restore procedure nobody has run is a backup nobody has. Run this against a
# throwaway app once — the ten minutes it takes is the difference between having
# backups and believing you do.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ "${DEPLOY_LANE:-off}" == "fly" ]] || { echo "deploy lane off (DEPLOY_LANE=fly)."; exit 0; }
: "${FLY_APP:?set FLY_APP}"
BACKUP="${1:?path to a .db backup}"

# Checked BEFORE anything is stopped. Discovering the file is corrupt after you
# have taken the service down converts a recoverable incident into a longer one.
python -c "
import sys; sys.path.insert(0, 'src')
from release import verify_backup
print('source is readable:', verify_backup('$BACKUP', ['audit_log', 'approvals', 'outbox']))
"

# Stopped, not rolling. Two writers on one SQLite file — the restore and a live
# request — is how you get a database that is neither the backup nor the
# original. The brief downtime is the price of a deterministic outcome.
flyctl scale count 0 --app "$FLY_APP" --yes

# The displaced database is kept, not overwritten. If the restore turns out to
# be the wrong call, the state you were unhappy with is at least still there.
flyctl machine start --app "$FLY_APP" >/dev/null 2>&1 || true
flyctl ssh console --app "$FLY_APP" -C "mv /data/assistant.db /data/assistant.db.displaced" || true
flyctl ssh sftp shell --app "$FLY_APP" <<EOF
put $BACKUP /data/assistant.db
EOF

flyctl scale count 1 --app "$FLY_APP" --yes

# Proven the same way e2e proves persistence: the service is up, and the state
# that survives a restart is there. "The command succeeded" is not evidence.
sleep 5
curl -fsS "https://${FLY_APP}.fly.dev/health" && echo
echo "restored $BACKUP — now check a memory recalls and the audit count matches the backup"
