#!/usr/bin/env python3
"""Compatibility websocket for the Aria Vencord live panel.

The legacy Aria bridge used to own both Discord handling and the
``aria-live`` websocket on 127.0.0.1:18790.  During the Hermes gateway
cutover, Discord handling moves to Hermes, but the existing Vencord plugin
still connects to that websocket.  This small relay keeps the plugin online
without running a second Discord bot.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Set

import websockets

HOST = "127.0.0.1"
PORT = int(os.environ.get("ARIA_LIVE_PORT", "18790"))
LOGS = [
    Path("/home/aria/.hermes/profiles/aria/logs/gateway.log"),
    Path("/home/aria/.hermes/profiles/aria/logs/agent.log"),
]
CLIENTS: Set[websockets.WebSocketServerProtocol] = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s aria-live-compat: %(message)s",
)

INBOUND_RE = re.compile(r"inbound message: platform=discord user=(?P<user>.+?) chat=(?P<chat>\d+) msg=(?P<msg>.+)$")
RESPONSE_READY_RE = re.compile(
    r"response ready: platform=discord chat=(?P<chat>\d+) time=(?P<seconds>[\d.]+)s .* response=(?P<chars>\d+) chars"
)
SENDING_RE = re.compile(r"\[Discord\] Sending response \((?P<chars>\d+) chars\) to (?P<chat>\d+)")
SLASH_RE = re.compile(r"\[Discord\] slash '(?P<command>/.+?)' invoked by user=(?P<user>.+?) .* channel=(?P<chat>\d+)")


def now_ms() -> int:
    return int(time.time() * 1000)


def event(kind: str, message: str, **data):
    channel_id = data.get("channelId")
    return {
        "type": kind,
        "sessionKey": f"discord:hermes:{channel_id}" if channel_id else "hermes-gateway",
        "timestamp": now_ms(),
        "data": {"message": message, **data},
    }


def _unquote_log_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def parse_crontab():
    try:
        out = subprocess.check_output(["crontab", "-l"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []

    jobs = []
    for idx, raw in enumerate(out.splitlines()):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(None, 5)
        if len(parts) < 6:
            continue

        name = parts[5]
        if "#" in name:
            cmd, comment = name.split("#", 1)
            name = comment.strip() or cmd.strip()

        jobs.append({
            "id": f"cron-{idx}",
            "name": name[:80],
            "cronExpr": " ".join(parts[:5]),
            "command": parts[5],
            "status": "active",
        })
    return jobs


async def send(ws, obj):
    await ws.send(json.dumps(obj, ensure_ascii=False))


async def broadcast(obj):
    if not CLIENTS:
        return

    text = json.dumps(obj, ensure_ascii=False)
    stale = []
    for ws in list(CLIENTS):
        try:
            await ws.send(text)
        except Exception:
            stale.append(ws)

    for ws in stale:
        CLIENTS.discard(ws)


async def handler(ws):
    CLIENTS.add(ws)
    logging.info("client connected (%d total)", len(CLIENTS))
    await send(ws, event("connected", "Hermes live compatibility stream active"))
    await send(ws, {
        "type": "cron_list",
        "sessionKey": "system",
        "timestamp": now_ms(),
        "data": {"jobs": parse_crontab()},
    })
    await send(ws, {
        "type": "session_snapshot",
        "sessionKey": "system",
        "timestamp": now_ms(),
        "data": {"sessions": []},
    })
    await send(ws, {
        "type": "queue_updated",
        "sessionKey": "system",
        "timestamp": now_ms(),
        "data": {"items": []},
    })

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if msg.get("type") == "ping":
                await send(ws, {"type": "pong", "timestamp": now_ms()})
            elif msg.get("type") == "interrupt":
                await send(ws, event(
                    "system",
                    "Interrupt requested from plugin; Hermes gateway does not expose interrupt on this compatibility socket yet",
                ))
    finally:
        CLIENTS.discard(ws)
        logging.info("client disconnected (%d total)", len(CLIENTS))


def classify(line: str):
    msg = line.strip()
    if not msg:
        return None

    slash = SLASH_RE.search(msg)
    if slash:
        channel_id = slash.group("chat")
        command = slash.group("command")
        return event(
            "message_received",
            f"{slash.group('user')} ran {command}",
            channelId=channel_id,
            channel="Discord",
            **{"from": slash.group("user")},
            contentPreview=command,
            contentLength=len(command),
        )

    inbound = INBOUND_RE.search(msg)
    if inbound:
        channel_id = inbound.group("chat")
        content = _unquote_log_value(inbound.group("msg"))
        return event(
            "message_received",
            "Discord message received",
            channelId=channel_id,
            channel="Discord",
            **{"from": inbound.group("user")},
            contentPreview=content[:500],
            contentLength=len(content),
        )

    ready = RESPONSE_READY_RE.search(msg)
    if ready:
        channel_id = ready.group("chat")
        seconds = float(ready.group("seconds"))
        return event(
            "agent_end",
            "Hermes response ready",
            channelId=channel_id,
            success=True,
            durationMs=int(seconds * 1000),
            contentLength=int(ready.group("chars")),
        )

    sending = SENDING_RE.search(msg)
    if sending:
        channel_id = sending.group("chat")
        return event(
            "message_sent",
            "Discord response sent",
            channelId=channel_id,
            channel="Discord",
            to=channel_id,
            contentLength=int(sending.group("chars")),
            success=True,
        )

    if "Unauthorized user" in msg or "Ignoring message" in msg:
        return event("error", msg, source="gateway")
    if any(token in msg for token in ("ERROR", "Traceback", "Exception", "failed", "Failed")):
        return event("error", msg, source="gateway")

    return None


async def tail_logs():
    positions = {}
    for path in LOGS:
        try:
            positions[path] = path.stat().st_size
        except FileNotFoundError:
            positions[path] = 0

    while True:
        for path in LOGS:
            try:
                size = path.stat().st_size
                pos = positions.get(path, 0)
                if size < pos:
                    pos = 0
                if size <= pos:
                    continue

                with path.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    for line in f:
                        obj = classify(line)
                        if obj:
                            await broadcast(obj)
                    positions[path] = f.tell()
            except FileNotFoundError:
                positions[path] = 0
            except Exception as exc:
                logging.warning("tail failed for %s: %s", path, exc)

        await asyncio.sleep(1)


async def cron_loop():
    while True:
        await asyncio.sleep(60)
        await broadcast({
            "type": "cron_list",
            "sessionKey": "system",
            "timestamp": now_ms(),
            "data": {"jobs": parse_crontab()},
        })


async def main():
    async with websockets.serve(handler, HOST, PORT, ping_interval=30, ping_timeout=30):
        logging.info("listening on ws://%s:%s", HOST, PORT)
        await asyncio.gather(tail_logs(), cron_loop())


if __name__ == "__main__":
    asyncio.run(main())
