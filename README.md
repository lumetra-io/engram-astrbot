# astrbot_plugin_lumetra_engram

Long-term memory for [AstrBot](https://github.com/AstrBotDevs/AstrBot), powered by [Lumetra Engram](https://lumetra.io). Adds two slash commands and optional silent auto-archive of every chat message.

| Command | What it does |
| --- | --- |
| `/remember <text>` | Stores `<text>` as a memory in your Engram bucket. |
| `/recall <question>` | Semantic + graph search over your memories; returns Engram's synthesized answer. |

When `auto_archive: true` is set in the plugin config, every non-command message AstrBot delivers to the plugin is also stored to Engram in the background. Slash commands are skipped to avoid double-storing.

## Install

### Option A — Install from the AstrBot dashboard

1. Open the AstrBot WebUI -> **Plugins** -> **Install from URL**.
2. Paste:
   ```
   https://github.com/lumetra-io/engram-astrbot
   ```
3. Click **Install**, then enable the plugin.

### Option B — Clone into AstrBot's plugin directory

```bash
cd /path/to/AstrBot/data/plugins
git clone https://github.com/lumetra-io/engram-astrbot.git astrbot_plugin_lumetra_engram
pip install -r astrbot_plugin_lumetra_engram/requirements.txt
```

Restart AstrBot (or hit **Reload Plugins** in the WebUI).

## Configure

In the AstrBot WebUI, open **Plugins -> Engram Memory -> Config**, or edit `data/config/astrbot_plugin_lumetra_engram_config.json` directly.

| Key | Default | Notes |
| --- | --- | --- |
| `api_key` | `""` | Your Engram key (`eng_live_...`). If blank, the plugin falls back to the `ENGRAM_API_KEY` env var. |
| `base_url` | `https://api.lumetra.io` | Change only if self-hosting Engram. |
| `bucket_strategy` | `per_user` | One of `per_user`, `per_chat`, `fixed`. |
| `bucket_prefix` | `astrbot` | Prepended to derived bucket names. |
| `default_bucket` | `astrbot` | Used when `bucket_strategy: fixed`. |
| `auto_archive` | `false` | Silently store every non-command message. |
| `auto_archive_min_length` | `8` | Skip messages shorter than this many chars. |
| `timeout_seconds` | `30` | HTTP timeout per Engram call. |

Get an API key at <https://lumetra.io/app/api-keys>.

## How bucket names work

| Strategy | Bucket = |
| --- | --- |
| `per_user` (default) | `{bucket_prefix}-{sender_id}` |
| `per_chat` | `{bucket_prefix}-{session_id}` |
| `fixed` | `default_bucket` |

Bucket names are slugified to `[a-z0-9._-]`. Buckets are created lazily on first write — no provisioning step.

## Usage

```
User: /remember Jacob prefers dark roast and is allergic to hazelnut.
Bot:  [engram] stored in bucket `astrbot-12345` (id=48616bc8)

User: /recall what coffee should I order for Jacob?
Bot:  Jacob prefers dark roast. Avoid anything with hazelnut.
```

## Privacy

See [PRIVACY.md](PRIVACY.md). The plugin only talks to Engram (and only with parameters you route through it).

## License

MIT — see [LICENSE](LICENSE).
