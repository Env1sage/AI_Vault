# 10 — Disaster Recovery Guide

Status: **Living document**, introduced in Phase 10 (ADR-022). Covers what's backed up, how to restore it, and the recovery targets this platform is designed against. The backup/restore procedure below was run for real during Phase 10's development — see §5 for the drill's actual results, not a hypothetical.

---

## 1. What's backed up

| Data | Backup method | Frequency | Retention |
|---|---|---|---|
| PostgreSQL (all 53 tables — every business record this platform has) | `pg_dump -Fc` (`infrastructure/scripts/backup.sh`) → S3 (`infrastructure/terraform/modules/storage`) | Daily (cron the backup script in production — not yet automated as its own scheduled job, see Known Issues) | 14 local, 90-365 days in S3 depending on environment |
| Terraform state | S3 versioning + DynamoDB lock (`environments/*/backend.tf`) | Every `apply` | Indefinite (S3 versioning) |
| Secrets | AWS Secrets Manager (`infrastructure/terraform/modules/secrets`) | N/A — Secrets Manager itself is the durable store, not a backup target | N/A |
| Redis | **Not backed up, by design** — see §2 |
| Uploaded/scanned file *content* | Never stored by this platform — files stay in the customer's own Google Drive; this platform stores metadata and vectors only | N/A |

## 2. What's NOT backed up (and why that's fine)

Redis holds: the Celery broker/result backend (in-flight job state — a lost job can be re-triggered from its own DB row, which *is* backed up), the rate-limiter's counters (a fresh window is a correct empty state after any restart), and the dashboard cache (regenerates on the next read). Nothing in Redis is the durable copy of anything — losing it entirely causes a brief availability blip (in-flight jobs need re-triggering, the dashboard recomputes once), never data loss.

## 3. Recovery targets

| Scenario | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
|---|---|---|
| Single ECS task crash | Seconds (ECS restarts it automatically) | Zero (no data was ever only on that task) |
| Database instance failure (Multi-AZ, production) | ~1-2 minutes (RDS automatic failover) | Zero (synchronous replication to the standby) |
| Full region/account data loss | Time to provision new infrastructure (`terraform apply`, ~15-30 min) + restore time (§4, minutes for this dataset's current size) | Up to 24 hours (daily backup cadence) — or since the last manual `backup.sh` run |
| Redis loss | Seconds (ECS/ElastiCache restarts; app reconnects automatically) | N/A — nothing durable lives there (§2) |

**Staging** has none of production's Multi-AZ guarantees — a database failure there means restoring from the most recent backup, not automatic failover; acceptable since staging exists to catch bugs, not to stay up.

## 4. Restore procedure

```bash
# 1. Identify the backup to restore (local or downloaded from S3)
ls infrastructure/backups/

# 2. Create or identify the target database (never restore over a live
#    database you might still need — see restore.sh's own confirmation prompt)
createdb -h <host> -U <user> vault_restore_target

# 3. Restore
DATABASE_URL="postgresql://<user>:<pass>@<host>:5432/vault_restore_target" \
  infrastructure/scripts/restore.sh infrastructure/backups/vault-<timestamp>.dump

# 4. If the backup predates the currently-deployed migrations, bring it current
DATABASE_URL="postgresql://<user>:<pass>@<host>:5432/vault_restore_target" \
  infrastructure/scripts/migrate.sh

# 5. Verify (see §5's own verification query) before cutting traffic over
```

To actually cut over: point `DATABASE_URL` (a Secrets Manager entry in production) at the restored database and redeploy — there is no in-place "promote a restored database" step beyond that, since the restored database *is* just a normal Postgres instance once restored.

## 5. Recovery drill (Phase 10 — real, not simulated)

Run against the founder's actual local development Postgres (49-53 tables, tens of thousands of rows accumulated across nine phases of real development and testing):

1. `infrastructure/scripts/backup.sh` against the real `vault` database → produced a 6.3 MB `pg_dump -Fc` file.
2. Created a disposable `vault_restore_drill` database.
3. `infrastructure/scripts/restore.sh` into it.
4. Compared every table's row count between source and restored database via a single `information_schema`-driven query.

**Result: all 53 tables matched exactly, row-for-row** — `alembic_version`, `approval_decisions` (87), `approval_requests` (158), `audit_logs` (6,476), `files` (3,082), `users` (2,070), `workflows` (124), and every other table, with zero discrepancies. The disposable database was dropped immediately after; nothing about the real local data was altered by the drill.

**A real bug was found and fixed during this drill**, not just a successful run: `backup.sh`'s original retention-pruning logic used `mapfile`, unavailable in macOS's default `/bin/bash` (3.2 — GPLv3 licensing keeps Apple from shipping a newer one). Rewritten without it and re-verified. This is exactly the kind of gap a drill is supposed to catch before a real incident does.

## 6. Secret recovery

Secrets live in AWS Secrets Manager, which has its own versioning and recovery window (30 days by default for a deleted secret, configurable) — no separate backup mechanism needed for secrets themselves. The one secret that, if truly lost with no recovery, causes real data loss (not just an outage) is `CONNECTOR_ENCRYPTION_KEY` — every stored Drive OAuth token becomes permanently undecryptable, requiring every connected organization to reconnect Google Workspace from scratch. Treat that key with the same care as the database itself: never rotate it without a migration plan, never let it exist in exactly one place.

## 7. Configuration backup

Infrastructure configuration is itself version-controlled (`infrastructure/terraform/`, `.github/workflows/`) — recovering "what the infrastructure should look like" is `git checkout` plus `terraform apply`, not a separate backup artifact. Terraform *state* (what actually exists, as opposed to what the code says should exist) is backed up via S3 versioning on the state bucket (§1).

## 8. Known limitations

- Automated (cron/scheduled) production backups are not yet wired up — `backup.sh` exists and is drilled, but nothing currently invokes it on a schedule in production; a natural Phase 11 item (an ECS scheduled task or a dedicated cron container).
- No cross-region backup replication yet — an S3 bucket in one region, no explicit disaster-recovery-region strategy for a full-region outage.
- The drill above was run against a local single instance, not the Multi-AZ production topology — a full production failover drill (killing the primary and confirming standby promotion) has not been performed, since no production environment exists yet to drill against.
