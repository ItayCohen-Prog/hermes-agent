from plugins.aria_compat.live_ws import LiveWSHub


def test_hub_defaults_and_connect_payload_tracks_clients():
    hub = LiveWSHub()

    assert hub.host == "127.0.0.1"
    assert hub.port == 18790
    assert hub.client_count == 0

    payload = hub.connect("client-1")

    assert hub.client_count == 1
    assert payload == {
        "type": "connected",
        "client_id": "client-1",
        "client_count": 1,
        "host": "127.0.0.1",
        "port": 18790,
    }

    hub.disconnect("client-1")
    assert hub.client_count == 0


def test_hub_host_and_port_are_configurable():
    hub = LiveWSHub(host="0.0.0.0", port=9999)

    assert hub.connect()["host"] == "0.0.0.0"
    assert hub.port == 9999


def test_supported_commands_return_ack_payloads():
    hub = LiveWSHub()

    for command in [
        "interrupt",
        "queue_cancel",
        "queue_clear",
        "queue_promote",
        "queue_steer",
    ]:
        result = hub.handle_command(command, item_id="abc", direction="up")
        assert result["ok"] is True
        assert result["type"] == "command_ack"
        assert result["command"] == command
        assert result["data"]["item_id"] == "abc"


def test_unsupported_command_returns_structured_error():
    result = LiveWSHub().handle_command("bogus")

    assert result["ok"] is False
    assert result["type"] == "error"
    assert result["error"] == "unsupported_command"
    assert result["command"] == "bogus"
