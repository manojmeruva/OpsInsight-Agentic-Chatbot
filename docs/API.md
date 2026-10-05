# API Reference

← [Back to README](../README.md)

**Base URL**

| Environment | URL |
|---|---|
| Direct (local) | `http://127.0.0.1:5000/api` |
| Through the frontend dev proxy / reverse proxy | `http://<host>/interact-backend/api` |

FastAPI runs with `root_path="/interact-backend"`, and the proxy strips this prefix. Interactive docs are at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| POST | [`/query/stream`](#post-querystream) | Ask a question, streamed (SSE) — used by the UI |
| POST | [`/query`](#post-query) | Ask a question, single JSON response |
| GET | [`/modules`](#get-modules) | Domains and sample questions |
| GET | [`/getsessions`](#get-getsessions) | Sessions grouped by date |
| GET | [`/getsession/data`](#get-getsessiondata) | Messages of one session |
| DELETE | [`/deletesession`](#delete-deletesession) | Delete a session |
| POST | [`/like-feedback`](#post-like-feedback) | Thumbs up/down |
| POST | [`/message-feedback`](#post-message-feedback) | Text feedback |
| POST | [`/translate`](#post-translate) | English ↔ Arabic |
| POST | [`/speech-to-text`](#post-speech-to-text) | WAV transcription |
| POST | [`/load-session-history`](#post-load-session-history) | Restore sessions from Elasticsearch |
| POST | [`/archive-session-data`](#post-archive-session-data) | Archive sessions to Elasticsearch |
| POST | [`/sync-to-elk`](#post-sync-to-elk) | Incremental or full sync to Elasticsearch |
| GET | [`/refresh-metadata`](#get-refresh-metadata) | Rebuild `metadata.db` |
| POST | [`/auto-test`](#post-auto-test) | Prompt testing without the UI |

---

### POST /query

Main chat endpoint.

```json
{
  "user_input": "What is the total available balance by bank?",
  "session_id": "3f1c…",
  "message_id": "a91b…",
  "module_name": "FINANCE",
  "request_timestamp": "2026-10-04T10:30:00Z",
  "user_id": "analyst@local"
}
```

Response:

```json
{
  "response": [
    { "type": "text",  "content": "Here is the available balance by bank:" },
    { "type": "table", "content": [{ "Bank": "AXIS BANK LIMITED", "Total Available Balance (INR)": 231680596.77 }] },
    { "type": "image", "mime_type": "image/png", "content": "<base64>" }
  ],
  "response_id": "6ac289081c60a235b7005b84",
  "response_timestamp": "2026-10-04T10:30:05Z",
  "sql": "SELECT b.bank_name AS \"Bank\", …"
}
```

| Part type | Content |
|---|---|
| `text` | Markdown |
| `table` | Array of row objects |
| `image` | Base64 PNG chart |

`sql` is the generated query, or `null` for text-only answers.

### POST /query/stream

Same request body as [`/query`](#post-query). The response is `text/event-stream`. Each event has the form `event: <name>` + `data: <json>`.

| Event | Data | When |
|---|---|---|
| `start` | `{response_id, response_timestamp}` | Immediately |
| `status` | `{stage, message}` | Progress: `thinking`, `retrieving`, `writing`, `generating_sql`, `running_query`, `retrying` |
| `delta` | `{index, text}` | Text tokens for response part `index` (English questions only; Arabic answers arrive as whole parts) |
| `part` | `{index, part}` | Final content of part `index`. Replaces any deltas for that index. `replace_all: true` means discard earlier parts |
| `sql` | `{sql}` | Generated SQL (data questions only) |
| `done` | `{response_id, response_timestamp, response, sql}` | Final payload, identical to `/query` |

```text
event: status
data: {"stage": "generating_sql", "message": "Generating SQL…"}

event: delta
data: {"index": 0, "text": "Axis Bank holds "}
```

```bash
curl -N -X POST http://127.0.0.1:5000/api/query/stream -H "Content-Type: application/json"   -d '{"user_input":"What is a UTR?","session_id":"s1","message_id":"m1","module_name":"FINANCE","user_id":"analyst@local"}'
```

If the client disconnects, the server stops generating. Reverse proxies must not buffer this route; the response sets `X-Accel-Buffering: no` for Nginx.

### GET /modules

```json
{
  "data_engine": "sqlite",
  "modules": [
    {
      "module": "FINANCE", "tag": "finance", "status": "active",
      "display_name": "Finance — Accounts & Transactions", "short_name": "Finance",
      "description": "…", "icon": "landmark",
      "sample_questions": ["What is the total available balance across all accounts, by bank?"]
    },
    { "module": "RETAIL", "status": "placeholder", "…": "…" }
  ]
}
```

### GET /getsessions

Header: `user-id: analyst@local`

```json
{
  "Today": [
    { "sessionId": "3f1c…", "sessionName": "Total balance by bank", "createdAt": "2026-10-04T10:30:05", "module_name": "FINANCE" }
  ],
  "Yesterday": [],
  "Last 7 Days": []
}
```

### GET /getsession/data

Header: `session-id: 3f1c…`

```json
{
  "messages": [
    {
      "request":  { "id": "a91b…", "message": "Total balance by bank", "timestamp": "…" },
      "response": { "id": "6ac2…", "message": [ … ], "sql": "SELECT …", "feedback": null, "is_like": null, "timestamp": "…" }
    }
  ]
}
```

### DELETE /deletesession

Header: `session-id: 3f1c…`. Deletes the session and all its messages.

### POST /like-feedback

```json
{ "session_id": "3f1c…", "response_id": "6ac2…", "is_like": true }
```

### POST /message-feedback

```json
{ "session_id": "3f1c…", "response_id": "6ac2…", "feedback": "Chart labels overlap." }
```

Both feedback endpoints return `404` if the message is not found.

### POST /translate

```json
{ "text": "What is the total balance?", "direction": "en-to-ar" }
```

`direction` can be `en-to-ar`, `english-to-arabic`, `ar-to-en` or `arabic-to-english`.

### POST /speech-to-text

`multipart/form-data` with these fields:
- `file`: WAV audio
- `translate`: `"true"` (default) or `"false"`

```json
{ "success": true, "transcription": "…", "translation": "…" }
```

### POST /load-session-history

```json
{ "user_email": "analyst@local", "days": 7 }
```

Returns `{ "status", "sessions_loaded", "messages_loaded", "time_taken" }`, or `"status": "skipped"` when Elasticsearch is unavailable.

### POST /archive-session-data

```json
{ "user_email": "analyst@local" }
```

Returns `{ "status", "sessions_archived", "messages_archived", "messages_cleaned_from_mongo", "time_taken" }`.

### POST /sync-to-elk

```json
{ "full_sync": false }
```

With `full_sync: false`, only data updated in the last 24 hours is synced.

### GET /refresh-metadata

Rebuilds `metadata.db` from `metadata_vol/` if present, otherwise from `Config.DOMAINS`.

```json
{ "status": "success", "message": "Refreshed metadata from git repo.", "counts": { "prompts": 3 } }
```

### POST /auto-test

Runs a question through the pipeline without creating a session. Use it to iterate on prompts.

```json
{ "user_input": "Show total debits for June 2026", "module_name": "FINANCE", "history": [] }
```
