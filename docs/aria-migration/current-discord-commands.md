# Current Aria Discord Commands

These commands are currently owned by `/home/aria/aria-bridge/bridge.py`. Hermes-Aria should provide equivalents before cutover.

| Aria command | Current behavior | Target Hermes equivalent | Migration notes |
|---|---|---|---|
| `/new` | Clears/resets the current channel's Codex session. | Hermes `/new` for current Discord channel session. | Must only reset the invoking channel/thread session. |
| `/reset` | Alias for `/new`. | Alias to Hermes `/new`. | Add alias in centralized command registry/gateway. |
| `/compact` | Summarizes current session and starts a fresh seeded session. | Hermes `/compress` or compatibility `/compact`. | Preserve user-facing name for Discord. |
| `/context` | Shows session/context/token information. | Hermes `/status` plus Aria session/context extension. | Include channel session ID/recoverability. |
| `/status` | Shows bridge uptime, session count, websocket/plugin state. | Hermes `/status`/`/platforms` plus aria_compat status. | Preserve concise Discord output. |
| `/categories` | Shows configured workspace/Discord categories. | Aria compatibility plugin command. | Source is workspace category config. |
| `/sync_categories` | Creates/syncs configured Discord categories/channels. | Aria compatibility plugin command. | High-side-effect command; require explicit confirmation/dry-run first. |
| `/help` | Lists Aria commands. | Hermes `/help`/`/commands`. | Include Aria aliases in help. |

Discord formatting rules for compatibility:
- no markdown tables in live Discord replies;
- wrap multiple links in angle brackets to suppress embeds;
- one reaction max;
- if the request belongs in another channel, answer there and leave a short redirect in the original channel.
