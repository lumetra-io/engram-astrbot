# Privacy

This plugin sends data you explicitly route through it — the text of `/remember`, the question of `/recall`, and (if you enable `auto_archive`) every non-command chat message AstrBot delivers to the plugin — to the Engram REST API at `https://api.lumetra.io` (or the self-hosted `base_url` you configured). Memories are stored under your Engram tenant, scoped by the API key you provided in the plugin config (or `ENGRAM_API_KEY`).

The plugin does not collect, log, or transmit data to any third party other than the Engram service you've explicitly authorized. The plugin does not read other AstrBot resources (other plugins' data, model providers, conversation history outside the event it is handling) — only the message text and sender id of the event the AstrBot core passes to it.

Bucket names are derived from `bucket_strategy`:

- `per_user` (default): `{bucket_prefix}-{sender_id}` — one bucket per chat user.
- `per_chat`: `{bucket_prefix}-{session_id}` — one bucket per group/session.
- `fixed`: always `default_bucket`.

Sender ids and session ids come from the AstrBot platform adapter (QQ, Telegram, Discord, etc.) and are sent to Engram as part of the bucket name. If you do not want platform identifiers in Engram, use `bucket_strategy: fixed`.

For Engram's own data-handling and retention policy, see <https://lumetra.io/privacy>.
