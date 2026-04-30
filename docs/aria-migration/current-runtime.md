# Current Aria Runtime Inventory

Captured for the Hermes-absorbs-Aria migration. No secrets are included.

## Host/runtime

- User: `aria`
- Main Hermes repo: `/home/aria/hermes-agent`
- Aria bridge repo: `/home/aria/aria-bridge`
- Operational workspace: `/home/aria/workspace`

## Services

### `aria-bridge.service`

Runs the live Discord-to-Codex Aria bridge:

```text
/home/aria/bridge-venv/bin/python3 /home/aria/aria-bridge/bridge.py
```

Responsibilities:
- Discord bot/event loop
- per-channel sessions and queues
- slash commands
- attachment handling and transcript writing
- aria-live websocket
- HTTP health/dashboard/cron/hooks/PC endpoints
- Codex provider orchestration

### `hermes-dashboard.service`

Runs Hermes dashboard/TUI:

```text
/home/aria/hermes-agent/venv/bin/python /home/aria/.local/bin/hermes dashboard --tui --host 127.0.0.1 --port 9119 --no-open
```

Responsibilities:
- dashboard web UI on localhost
- embedded Hermes TUI/PTY chat
- supporting Hermes status/config UI

## Ports

- `22`: SSH
- `80`, `443`: Traefik/Docker public proxy
- `127.0.0.1:5678`: n8n
- `127.0.0.1:9119`: Hermes dashboard/TUI
- `127.0.0.1:18790`: aria-live websocket for Vencord plugin
- `0.0.0.0:18791`: Aria bridge HTTP API
- `41641/udp`: Tailscale

## Health endpoint

Current Aria bridge exposes:

```text
GET http://127.0.0.1:18791/health
```

Observed response shape:

```json
{"status":"ok","sessions":17,"ws_clients":1,"uptime_s":56771}
```

Target Hermes compatibility should preserve the old keys and may add:

```json
{"runtime":"hermes","profile":"aria"}
```

## Docker limitation

Docker is active, but user `aria` cannot access `/var/run/docker.sock` directly. Do not assume `docker ps` works without elevated access.
