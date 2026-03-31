"""
Webhook Ingestion: Receives and routes inbound webhooks.

Supports:
- Webhook registration with optional secret-based verification
- Payload transformation to IncomingMessage
- Routing webhooks through the engine as system messages
"""

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from realize_core.channels.base import BaseChannel, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


@dataclass
class WebhookEndpoint:
    """A registered webhook endpoint."""

    name: str
    system_key: str
    secret: str = ""  # HMAC secret for signature verification
    enabled: bool = True
    message_template: str = ""  # Template for converting payload to message
    last_received: float = 0.0
    receive_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    # Replay protection
    replay_protection: bool = False
    max_age_seconds: int = 300  # Reject payloads older than 5 minutes
    timestamp_field: str = "timestamp"  # Payload field containing Unix timestamp
    # Rate limiting (requests per minute, 0 = unlimited)
    rate_limit: int = 0

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 signature."""
        if not self.secret:
            return True  # No secret configured, skip verification

        expected = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()

        # Support both raw and prefixed signatures
        sig_clean = signature.replace("sha256=", "")
        return hmac.compare_digest(expected, sig_clean)

    def format_payload(self, payload: dict) -> str:
        """
        Convert a webhook payload to a human-readable message.

        If message_template is set, uses it for formatting.
        Otherwise, creates a structured summary.
        """
        if self.message_template:
            try:
                return self.message_template.format(**payload)
            except (KeyError, ValueError):
                pass

        # Default: summarize the payload
        lines = [f"Webhook received: {self.name}"]
        for key, value in payload.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"  {key}: {value}")
            elif isinstance(value, dict):
                lines.append(f"  {key}: {{{len(value)} fields}}")
            elif isinstance(value, list):
                lines.append(f"  {key}: [{len(value)} items]")
        return "\n".join(lines)


class WebhookChannel(BaseChannel):
    """
    Webhook ingestion channel.

    Receives incoming webhooks, verifies signatures, transforms payloads
    into messages, and routes them through the engine.
    """

    # Webhook responses are for system/automation consumption, not humans
    humanize_output = False

    def __init__(self, system_key: str = ""):
        super().__init__("webhook")
        self.system_key = system_key
        self._endpoints: dict[str, WebhookEndpoint] = {}
        self._rate_counters: dict[str, list[float]] = {}

    async def start(self):
        """Webhook channel is driven by HTTP server."""
        self.logger.info(f"Webhook channel ready ({len(self._endpoints)} endpoints)")

    async def stop(self):
        self.logger.info("Webhook channel stopped")

    async def send_message(self, message: OutgoingMessage):
        """Webhooks are inbound-only; no outbound mechanism."""
        self.logger.debug("Webhook channel does not support outbound messages")

    def format_instructions(self) -> str:
        return (
            "This message came from a webhook. Analyze the data and "
            "take appropriate action. Respond with a structured summary "
            "of what happened and any actions taken."
        )

    # -----------------------------------------------------------------------
    # Endpoint management
    # -----------------------------------------------------------------------

    def register_endpoint(self, endpoint: WebhookEndpoint):
        """Register a webhook endpoint."""
        self._endpoints[endpoint.name] = endpoint
        self.logger.info(f"Registered webhook endpoint: {endpoint.name}")

    def unregister_endpoint(self, name: str) -> bool:
        """Remove a webhook endpoint."""
        return self._endpoints.pop(name, None) is not None

    def get_endpoint(self, name: str) -> WebhookEndpoint | None:
        """Get a webhook endpoint by name."""
        return self._endpoints.get(name)

    def load_from_yaml(self, yaml_path: str | Path):
        """
        Load webhook endpoints from YAML config.

        Format:
        ```yaml
        webhooks:
          github_push:
            system_key: my-business
            secret: ${GITHUB_WEBHOOK_SECRET}
            message_template: "GitHub push to {repository[name]}: {head_commit[message]}"

          stripe_payment:
            system_key: my-business
            secret: ${STRIPE_WEBHOOK_SECRET}
            message_template: "Payment received: {data[object][amount]} {data[object][currency]}"
        ```
        """
        import os

        path = Path(yaml_path)
        if not path.exists():
            return

        try:
            import yaml
        except ImportError:
            logger.warning("pyyaml not installed, cannot load webhook config")
            return

        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        # Merge top-level webhooks: and voice.webhooks: sections
        webhook_configs = {
            **config.get("webhooks", {}),
            **config.get("voice", {}).get("webhooks", {}),
        }
        for name, cfg in webhook_configs.items():
            secret = cfg.get("secret", "")
            # Resolve env vars in secrets
            if isinstance(secret, str) and secret.startswith("${") and secret.endswith("}"):
                secret = os.getenv(secret[2:-1], "")

            self.register_endpoint(
                WebhookEndpoint(
                    name=name,
                    system_key=cfg.get("system_key", self.system_key),
                    secret=secret,
                    enabled=cfg.get("enabled", True),
                    message_template=cfg.get("message_template", ""),
                    metadata=cfg.get("metadata", {}),
                    replay_protection=cfg.get("replay_protection", False),
                    max_age_seconds=cfg.get("max_age_seconds", 300),
                    timestamp_field=cfg.get("timestamp_field", "timestamp"),
                    rate_limit=cfg.get("rate_limit", 0),
                )
            )

    # -----------------------------------------------------------------------
    # Webhook processing
    # -----------------------------------------------------------------------

    async def process_webhook(
        self,
        endpoint_name: str,
        payload: dict[str, Any],
        body_bytes: bytes = b"",
        signature: str = "",
    ) -> OutgoingMessage | None:
        """
        Process an incoming webhook.

        Args:
            endpoint_name: The registered endpoint name
            payload: Parsed JSON payload
            body_bytes: Raw body bytes (for signature verification)
            signature: The signature header value

        Returns:
            OutgoingMessage if processed, None if rejected
        """
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            self.logger.warning(f"Unknown webhook endpoint: {endpoint_name}")
            return None

        if not endpoint.enabled:
            self.logger.info(f"Webhook endpoint '{endpoint_name}' is disabled")
            return None

        # Verify signature
        if body_bytes and signature:
            if not endpoint.verify_signature(body_bytes, signature):
                self.logger.warning(f"Webhook signature verification failed: {endpoint_name}")
                return None

        # Replay protection — reject stale payloads
        if endpoint.replay_protection:
            ts = payload.get(endpoint.timestamp_field)
            if ts is not None:
                try:
                    ts_float = float(ts)
                    age = time.time() - ts_float
                    if age > endpoint.max_age_seconds:
                        self.logger.warning(
                            f"Webhook replay rejected: {endpoint_name} "
                            f"(payload age {age:.0f}s > {endpoint.max_age_seconds}s)"
                        )
                        return None
                except (TypeError, ValueError):
                    self.logger.warning(f"Webhook replay check: non-numeric timestamp in {endpoint_name}")

        # Rate limiting
        if endpoint.rate_limit > 0:
            if not self._check_rate_limit(endpoint_name, endpoint.rate_limit):
                self.logger.warning(f"Webhook rate limit exceeded: {endpoint_name}")
                return None

        # Update stats
        now = time.time()
        endpoint.last_received = now
        endpoint.receive_count += 1

        # Transform to message
        text = endpoint.format_payload(payload)
        message = IncomingMessage(
            user_id="webhook",
            text=text,
            system_key=endpoint.system_key,
            channel="webhook",
            metadata={
                "endpoint": endpoint_name,
                "payload": payload,
            },
        )

        response = await self.handle_incoming(message)
        return response

    def _check_rate_limit(self, endpoint_name: str, limit: int) -> bool:
        """Check if an endpoint is within its rate limit (requests per minute)."""
        now = time.time()
        window_start = now - 60

        # Get or create counter for this endpoint
        timestamps = self._rate_counters.get(endpoint_name, [])
        # Prune old entries outside the 1-minute window
        timestamps = [t for t in timestamps if t > window_start]

        if len(timestamps) >= limit:
            self._rate_counters[endpoint_name] = timestamps
            return False

        timestamps.append(now)
        self._rate_counters[endpoint_name] = timestamps
        return True

    @property
    def endpoint_count(self) -> int:
        return len(self._endpoints)

    def status_summary(self) -> dict:
        return {
            "total_endpoints": self.endpoint_count,
            "endpoints": {
                name: {
                    "enabled": ep.enabled,
                    "system_key": ep.system_key,
                    "has_secret": bool(ep.secret),
                    "receive_count": ep.receive_count,
                    "last_received": ep.last_received,
                }
                for name, ep in self._endpoints.items()
            },
        }
