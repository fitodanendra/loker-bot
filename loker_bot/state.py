"""Reads and saves bot state through the Cloudflare Worker (no git commits needed)."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from loker_bot import http

Transport = Callable[[str, str, dict, Optional[dict]], Any]


class StateError(RuntimeError):
    pass


@dataclass(frozen=True)
class State:
    prefs_raw: Any
    seen: dict[str, str]
    config: Any


class StateClient:
    def __init__(self, base_url: str, secret: str, transport: Transport = http.request_json):
        self._url = base_url.rstrip("/") + "/state"
        self._headers = {"Authorization": f"Bearer {secret}"}
        self._transport = transport

    def load(self) -> State:
        body = self._send("GET")
        if not isinstance(body, dict):
            raise StateError("Worker returned an unexpected response")
        seen = body.get("seen") or {}
        return State(prefs_raw=body.get("prefs"), seen=dict(seen), config=body.get("config"))

    def save(self, seen: Optional[dict[str, str]] = None, config: Optional[dict] = None) -> None:
        """Save only what changed; skipping unchanged keys keeps KV writes low."""
        payload = {key: value for key, value in (("seen", seen), ("config", config)) if value is not None}
        if payload:
            self._send("PUT", payload)

    def _send(self, method: str, payload: Optional[dict] = None) -> Any:
        try:
            return self._transport(method, self._url, self._headers, payload)
        except Exception as error:
            raise StateError(f"State {method} failed: {error}") from error
