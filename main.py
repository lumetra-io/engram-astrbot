"""AstrBot plugin: Engram long-term memory.

Adds two slash commands:
  /remember <text>         store a memory in Engram
  /recall <question>       semantic search over your memories

Optionally auto-archives every incoming message to Engram when
`auto_archive: true` is set in the plugin config.

API key resolution order:
  1. plugin config `api_key`
  2. env var ENGRAM_API_KEY
"""

from __future__ import annotations

import os
import re
from typing import Optional

import aiohttp

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


PLUGIN_NAME = "astrbot_plugin_engram"
PLUGIN_VERSION = "v0.1.0"
DEFAULT_BASE = "https://api.lumetra.io"
_SAFE_BUCKET = re.compile(r"[^a-zA-Z0-9._-]+")


def _slug(value: str, fallback: str = "anon") -> str:
    if not value:
        return fallback
    cleaned = _SAFE_BUCKET.sub("-", value).strip("-.").lower()
    return cleaned or fallback


@register(
    "astrbot_plugin_engram",
    "Lumetra",
    "Durable, explainable long-term memory for AstrBot via Lumetra Engram.",
    PLUGIN_VERSION,
    "https://github.com/lumetra-io/engram-astrbot",
)
class EngramPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        timeout = aiohttp.ClientTimeout(total=int(self.config.get("timeout_seconds", 30)))
        self._session = aiohttp.ClientSession(timeout=timeout)
        if not self._api_key():
            logger.warning(
                "[engram] No API key configured. Set `api_key` in the plugin config "
                "or export ENGRAM_API_KEY. /remember and /recall will fail until set."
            )
        else:
            logger.info("[engram] plugin %s ready; base=%s", PLUGIN_VERSION, self._base_url())

    async def terminate(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # -------- config helpers --------

    def _api_key(self) -> str:
        return (self.config.get("api_key") or os.environ.get("ENGRAM_API_KEY") or "").strip()

    def _base_url(self) -> str:
        return (self.config.get("base_url") or DEFAULT_BASE).rstrip("/")

    def _bucket_for(self, event: AstrMessageEvent) -> str:
        strategy = self.config.get("bucket_strategy", "per_user")
        prefix = self.config.get("bucket_prefix", "astrbot") or "astrbot"
        default_bucket = self.config.get("default_bucket", "astrbot") or "astrbot"

        if strategy == "fixed":
            return _slug(default_bucket, fallback="astrbot")

        if strategy == "per_chat":
            try:
                sid = event.unified_msg_origin  # session-level id (group or private)
            except Exception:
                sid = None
            sid = sid or getattr(event, "session_id", None) or event.get_sender_id() or "default"
            return _slug(f"{prefix}-{sid}", fallback=default_bucket)

        # default: per_user
        uid = event.get_sender_id() or "anon"
        return _slug(f"{prefix}-{uid}", fallback=default_bucket)

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "User-Agent": f"engram-astrbot/{PLUGIN_VERSION}",
        }

    # -------- low-level REST --------

    async def _post(self, path: str, payload: dict) -> tuple[int, dict | str]:
        assert self._session is not None
        url = f"{self._base_url()}{path}"
        async with self._session.post(url, json=payload, headers=self._auth_headers()) as resp:
            try:
                body = await resp.json()
            except Exception:
                body = await resp.text()
            return resp.status, body

    async def _store(self, bucket: str, content: str) -> tuple[int, dict | str]:
        return await self._post(f"/v1/buckets/{bucket}/memories", {"content": content})

    async def _query(self, bucket: str, query: str) -> tuple[int, dict | str]:
        # NB: Engram expects `query`, not `question`.
        return await self._post("/v1/query", {"query": query, "bucket": bucket})

    # -------- commands --------

    @filter.command("remember")
    async def cmd_remember(self, event: AstrMessageEvent):
        """Store a memory: /remember <text>"""
        if not self._api_key():
            yield event.plain_result(
                "[engram] No API key configured. Set `api_key` in the plugin config "
                "or export ENGRAM_API_KEY."
            )
            return

        # event.message_str strips the leading "/remember " for us, but be defensive.
        raw = (event.message_str or "").strip()
        text = re.sub(r"^/?remember\s+", "", raw, count=1).strip()
        if not text:
            yield event.plain_result("Usage: /remember <thing to remember>")
            return

        bucket = self._bucket_for(event)
        try:
            status, body = await self._store(bucket, text)
        except Exception as exc:
            logger.exception("[engram] store failed")
            yield event.plain_result(f"[engram] store failed: {exc}")
            return

        if 200 <= status < 300:
            mid = ""
            if isinstance(body, dict):
                mid = body.get("memory_id") or body.get("id") or ""
            tail = f" (id={mid[:8]})" if mid else ""
            yield event.plain_result(f"[engram] stored in bucket `{bucket}`{tail}")
        else:
            yield event.plain_result(f"[engram] HTTP {status}: {body}")

    @filter.command("recall")
    async def cmd_recall(self, event: AstrMessageEvent):
        """Recall memories: /recall <question>"""
        if not self._api_key():
            yield event.plain_result(
                "[engram] No API key configured. Set `api_key` in the plugin config "
                "or export ENGRAM_API_KEY."
            )
            return

        raw = (event.message_str or "").strip()
        question = re.sub(r"^/?recall\s+", "", raw, count=1).strip()
        if not question:
            yield event.plain_result("Usage: /recall <question>")
            return

        bucket = self._bucket_for(event)
        try:
            status, body = await self._query(bucket, question)
        except Exception as exc:
            logger.exception("[engram] query failed")
            yield event.plain_result(f"[engram] query failed: {exc}")
            return

        if 200 <= status < 300 and isinstance(body, dict):
            answer = body.get("answer") or body.get("response") or ""
            if not answer:
                yield event.plain_result(f"[engram] (no answer) bucket=`{bucket}`")
                return
            yield event.plain_result(answer)
        else:
            yield event.plain_result(f"[engram] HTTP {status}: {body}")

    # -------- optional auto-archive --------

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_any_message(self, event: AstrMessageEvent):
        """Auto-archive every chat message to Engram when enabled in config."""
        if not self.config.get("auto_archive", False):
            return
        if not self._api_key():
            return

        text = (event.message_str or "").strip()
        if not text:
            return
        # Skip slash commands so we don't double-store /remember <thing>.
        if text.startswith("/"):
            return
        min_len = int(self.config.get("auto_archive_min_length", 8))
        if len(text) < min_len:
            return

        bucket = self._bucket_for(event)
        sender = event.get_sender_name() or event.get_sender_id() or "user"
        content = f"{sender}: {text}"
        try:
            status, body = await self._store(bucket, content)
            if status >= 300:
                logger.warning("[engram] auto-archive HTTP %s: %s", status, body)
        except Exception:
            logger.exception("[engram] auto-archive failed")
        # NB: do NOT yield anything — this handler is silent.
