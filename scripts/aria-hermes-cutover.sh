#!/usr/bin/env bash
set -euo pipefail

# Cut over live Discord handling from the legacy Aria bridge to Hermes profile `aria`.
# Run as root, e.g.:
#   sudo /home/aria/hermes-agent/scripts/aria-hermes-cutover.sh

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run with sudo/root so systemd can stop aria-bridge.service and install the Hermes gateway service." >&2
  exit 1
fi

cd /home/aria/hermes-agent

# Ensure Hermes has the Discord adapter dependency in its venv.
/home/aria/hermes-agent/venv/bin/python - <<'PY'
import importlib.util, sys
if not importlib.util.find_spec('discord'):
    raise SystemExit('discord.py is not installed in /home/aria/hermes-agent/venv')
PY

# Stop legacy Aria first so the same Discord bot token is not connected twice.
systemctl stop aria-bridge.service

# Install/update a boot-time Hermes gateway system service scoped to the aria profile.
env HOME=/home/aria USER=aria LOGNAME=aria HERMES_HOME=/home/aria/.hermes/profiles/aria \
  /home/aria/hermes-agent/venv/bin/python -m hermes_cli.main --profile aria gateway install --system --run-as-user aria --force

# Start Hermes gateway for the aria profile.
env HOME=/home/aria USER=aria LOGNAME=aria HERMES_HOME=/home/aria/.hermes/profiles/aria \
  /home/aria/hermes-agent/venv/bin/python -m hermes_cli.main --profile aria gateway start --system

systemctl --no-pager --full status hermes-gateway-aria.service || true

echo
printf 'Legacy Aria bridge: '
systemctl is-active aria-bridge.service || true
printf 'Hermes Aria gateway: '
systemctl is-active hermes-gateway-aria.service || true

echo
printf 'Done. Send a Discord DM/mention to the bot to test Hermes-as-Aria.\n'
