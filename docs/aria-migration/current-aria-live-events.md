# Current aria-live Event Schema

The Vencord aria-live plugin depends on websocket events from Aria bridge on `127.0.0.1:18790`.

## Connection/bootstrap events

- `connected`
- `cron_list`
- `cron_history`
- `session_snapshot`
- `queue_updated`

## Message/agent lifecycle events

- `message_received`
- `message_sending`
- `message_sent`
- `llm_input`
- `llm_output`
- `agent_end`
- `interrupted`

## Tool/subagent events

- `before_tool_call`
- `after_tool_call`
- `subagent_spawned`
- `subagent_ended`

## Compaction events

- `before_compaction`
- `after_compaction`

## Control commands accepted from plugin

- `interrupt`
- `queue_cancel`
- `queue_clear`
- `queue_promote`
- `queue_steer`

Hermes compatibility layer should translate Hermes events into these names and return structured errors for unsupported control commands instead of crashing.
