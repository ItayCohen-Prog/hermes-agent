# Current Aria Cron Jobs

System cron remains the source of truth until each job has a successful Hermes cron replacement run. Do not edit crontab as part of inventory.

Observed jobs:

| Job | Schedule | Notes |
|---|---:|---|
| `meet-recordings` | daily 04:30 | meeting recording processing/transcription |
| `security-audit` | daily 04:00 | writes security reports |
| `vector-reindex` | every 3h | reindexes Chroma/vector memory |
| `health-check` | daily 04:15 | system/workspace health check; recommended first migration |
| `weekly-audit` | Sunday 10:00 | weekly audit/reporting |
| `dashboard-update` | every 3h | updates `/home/aria/workspace/dashboard/status.json` |
| `ai-feed-digest` | daily 07:00 | AI feed digest |
| `youtube-feed` | daily 07:00 | YouTube feed workflow |
| `bridge-watchdog` | every minute | keeps/checks old Aria bridge; migrate/remove last |
| `email-check` | disabled | do not enable without explicit request |

Current wrapper:

```text
/home/aria/aria-bridge/cron_wrapper.py
```

Wrapper behavior:
- logs runs to `/home/aria/aria-bridge/cron-history.json`;
- sends `cron_started` / `cron_finished` to `http://127.0.0.1:18791/cron-event`;
- keeps max 50 history entries;
- applies a 1 hour timeout.

Migration rule: after each Hermes cron migration, observe at least one successful run before disabling the old cron entry.
