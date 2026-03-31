"""Runtime coverage for channel adapters using the canonical engine wrapper."""

import json
from unittest.mock import AsyncMock

import pytest
from realize_core.channels.api import APIChannel
from realize_core.channels.web import WebChannel
from realize_core.channels.webhooks import WebhookChannel, WebhookEndpoint


@pytest.mark.asyncio
async def test_api_channel_dispatches_through_engine(monkeypatch):
    process_message = AsyncMock(return_value="API channel response")
    monkeypatch.setattr("realize_core.engine.process_message", process_message)

    channel = APIChannel()
    result = await channel.process_chat(user_id="user-1", text="hello", system_key="alpha")

    assert result == "API channel response"
    kwargs = process_message.await_args.kwargs
    assert kwargs["channel"] == "api"
    assert kwargs["system_key"] == "alpha"


@pytest.mark.asyncio
async def test_web_channel_websocket_dispatches_through_engine(monkeypatch):
    process_message = AsyncMock(return_value="Web channel response")
    monkeypatch.setattr("realize_core.engine.process_message", process_message)

    channel = WebChannel(system_key="alpha")
    sent_messages = []

    async def send_callback(payload):
        sent_messages.append(payload)

    client_id = await channel.connect_client("user-2", send_callback)
    result = await channel.handle_ws_message(client_id, '{"type":"chat","text":"hello from web"}')

    assert result is None
    assert len(sent_messages) == 1
    payload = json.loads(sent_messages[0])
    assert payload["type"] == "message"
    assert payload["text"] == "Web channel response"
    kwargs = process_message.await_args.kwargs
    assert kwargs["channel"] == "web"
    assert kwargs["system_key"] == "alpha"


@pytest.mark.asyncio
async def test_webhook_channel_dispatches_through_engine(monkeypatch):
    process_message = AsyncMock(return_value="Webhook processed")
    monkeypatch.setattr("realize_core.engine.process_message", process_message)

    channel = WebhookChannel()
    channel.register_endpoint(WebhookEndpoint(name="github", system_key="alpha"))

    response = await channel.process_webhook("github", {"action": "push"})

    assert response is not None
    assert response.text == "Webhook processed"
    kwargs = process_message.await_args.kwargs
    assert kwargs["channel"] == "webhook"
    assert kwargs["system_key"] == "alpha"
