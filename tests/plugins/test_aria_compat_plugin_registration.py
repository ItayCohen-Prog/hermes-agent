from hermes_cli.plugins import PluginManager, get_plugin_commands


def test_aria_compat_plugin_registers_commands_and_gateway_hook(monkeypatch):
    import hermes_cli.plugins as plugins_mod

    manager = PluginManager()
    monkeypatch.setattr(plugins_mod, "_plugin_manager", manager)
    monkeypatch.setattr(plugins_mod, "_get_enabled_plugins", lambda: {"aria_compat"})

    manager.discover_and_load(force=True)

    commands = get_plugin_commands()
    assert "categories" in commands
    assert "sync_categories" in commands
    assert "aria-live" in commands
    assert "aria-cron-import" in commands
    assert "pre_gateway_dispatch" in manager._hooks


def test_aria_compat_registered_commands_are_safe_text_outputs(monkeypatch):
    import hermes_cli.plugins as plugins_mod

    manager = PluginManager()
    monkeypatch.setattr(plugins_mod, "_plugin_manager", manager)
    monkeypatch.setattr(plugins_mod, "_get_enabled_plugins", lambda: {"aria_compat"})
    manager.discover_and_load(force=True)

    sync = get_plugin_commands()["sync_categories"]["handler"]("")
    cron = get_plugin_commands()["aria-cron-import"]["handler"]("")

    assert "dry_run" in sync
    assert "No Hermes cron jobs were created" in cron
