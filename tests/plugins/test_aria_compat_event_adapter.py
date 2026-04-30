from plugins.aria_compat.event_adapter import adapt_event, aria_event_name


def test_known_event_names_are_mapped_to_aria_live_names():
    assert aria_event_name("tool.start") == "before_tool_call"
    assert aria_event_name("tool.complete") == "after_tool_call"
    assert aria_event_name("message.received") == "message_received"
    assert aria_event_name("message.sending") == "message_sending"
    assert aria_event_name("message.sent") == "message_sent"
    assert aria_event_name("agent.complete") == "agent_end"
    assert aria_event_name("compression.start") == "before_compaction"
    assert aria_event_name("compression.complete") == "after_compaction"


def test_unknown_event_name_is_stable_and_does_not_crash():
    assert aria_event_name("custom.event") == "custom.event"
    assert aria_event_name("") == "unknown"
    assert aria_event_name(None) == "unknown"


def test_adapt_event_preserves_payload_and_adds_aria_name():
    source = {"type": "tool.start", "tool": "terminal", "args": {"command": "pwd"}}

    adapted = adapt_event(source)

    assert adapted["type"] == "before_tool_call"
    assert adapted["aria_event"] == "before_tool_call"
    assert adapted["source_type"] == "tool.start"
    assert adapted["payload"] == source


def test_adapt_event_accepts_event_name_key_and_non_dict_payloads():
    assert adapt_event({"event": "message.sent", "text": "ok"})["type"] == "message_sent"
    assert adapt_event("tool.complete")["type"] == "after_tool_call"
