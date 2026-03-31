"""Regression tests for the shipped root cli.py entrypoint."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def load_root_cli_module():
    spec = importlib.util.spec_from_file_location("root_cli_runtime", ROOT / "cli.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_root_cli_status_parses_boolean_env(monkeypatch, capsys):
    module = load_root_cli_module()

    monkeypatch.setenv("BROWSER_ENABLED", "false")
    monkeypatch.setenv("MCP_ENABLED", "0")
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: {"systems": []})
    monkeypatch.setattr("realize_core.config.build_systems_dict", lambda config, kb_path=None: {})

    module.cmd_status(SimpleNamespace())
    captured = capsys.readouterr()

    assert "Browser: disabled" in captured.out
    assert "MCP: disabled" in captured.out


def test_root_cli_bot_uses_current_telegram_constructor(monkeypatch):
    module = load_root_cli_module()
    captured = {}

    class FakeTelegramChannel:
        def __init__(self, bot_token, system_key="", authorized_users=None, mode="single", name="", topic_routing=None):
            captured["bot_token"] = bot_token
            captured["system_key"] = system_key
            captured["authorized_users"] = authorized_users
            captured["mode"] = mode
            captured["name"] = name

        async def start(self):
            captured["started"] = True
            # Raise KeyboardInterrupt to exit the infinite stop_event.wait() loop,
            # mirroring how the real bot stops.
            raise KeyboardInterrupt

        async def stop(self):
            pass

    monkeypatch.setattr(
        "realize_core.config.load_config",
        lambda config_path=None: {
            "channels": [
                {
                    "type": "telegram",
                    "token": "token-123",
                    "system_key": "alpha",
                    "authorized_users": ["1", "2"],
                }
            ]
        },
    )
    monkeypatch.setattr("realize_core.channels.telegram.TelegramChannel", FakeTelegramChannel)

    module.cmd_bot(SimpleNamespace())

    assert captured["bot_token"] == "token-123"
    assert captured["system_key"] == "alpha"
    assert captured["authorized_users"] == {1, 2}
    assert captured["started"] is True


def test_root_cli_index_uses_force_flag(monkeypatch, capsys):
    module = load_root_cli_module()
    index_kb_files = Mock(return_value=7)

    monkeypatch.setattr("realize_core.config.load_config", lambda config_path=None: {"kb_path": "vault-root"})
    monkeypatch.setattr("realize_core.kb.indexer.index_kb_files", index_kb_files)

    module.cmd_index(SimpleNamespace())
    captured = capsys.readouterr()

    index_kb_files.assert_called_once_with("vault-root", force=True)
    assert "Indexed 7 files from vault-root" in captured.out
