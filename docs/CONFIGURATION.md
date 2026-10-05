# Configuration

← [Back to README](../README.md)

The backend reads `app/src/.env` (start from [`app/src/.env.example`](../app/src/.env.example)). The frontend reads `frontend/.env` (start from [`frontend/.env.example`](../frontend/.env.example)).

## Backend

### LLM

| Variable | Default | Description |
|---|---|---|
| `PROVIDER` | `google` | Orchestrator provider: `google`, `openai`, `azure_openai`, `anthropic`, `groq`, `mistral`, `ollama`, `huggingface` |
| `GOOGLE_API_KEY` | — | Gemini API key ([get one](https://aistudio.google.com/app/apikey)). Ignored when Vault is configured |
| `ORCHESTRATOR_MODEL` | `gemini-2.5-flash` | Model for chat and tool routing |
| `CODEGEN_MODEL` | `gemini-2.5-flash` | Model for text-to-SQL (always Google) |
| `TEMPERATURE` | `0.1` | Sampling temperature |
| `HTTP_PROXY` | — | Optional outbound proxy |

### Data warehouse

| Variable | Default | Description |
|---|---|---|
| `DATA_DB_ENGINE` | `starrocks` | `sqlite` (local `finance.db`, SQLite dialect) or `starrocks` (MySQL dialect) |
| `SQLITE_DATA_DB_PATH` | `app/src/finance.db` | Local data DB, opened read-only |
| `STARROCKS_IP` / `STARROCKS_PORT` | — / `3306` | StarRocks host and port (usually `9030`) |
| `STARROCKS_USER` / `STARROCKS_PASSWORD` | — | Credentials. Use a read-only user |
| `STARROCKS_DB` | — | Database name |
| `STARROCKS_POOL_SIZE` / `STARROCKS_POOL_MAX_OVERFLOW` / `STARROCKS_POOL_RECYCLE` | `5` / `10` / `1800` | Connection pool tuning |

### Session store

| Variable | Default | Description |
|---|---|---|
| `DB_TYPE` | `mongo` | `sqlite` or `mongo` |
| `SQLITE_SESSION_DB_PATH` | `app/src/sessions.db` | Created automatically |
| `MONGO_URI` | — | e.g. `mongodb://localhost:27017` |
| `DB_NAME` | — | MongoDB database name, e.g. `opsinsight` |
| `SESSION_TIMEOUT_SECONDS` | `30` | Session timeout |

### Elasticsearch archival

| Variable | Default | Description |
|---|---|---|
| `ES_ENABLED` | `true` | Set `false` to skip Elasticsearch entirely |
| `ES_HOST` / `ES_PORT` / `ES_SCHEME` | `localhost` / `9200` / `http` | Connection |
| `ES_USERNAME` / `ES_PASSWORD` | — | Optional basic auth |
| `ES_VERIFY_CERTS` | `true` | TLS verification for `https` |

### Vault

| Variable | Default | Description |
|---|---|---|
| `VAULT_ADDR` | — | When set, `GOOGLE_API_KEY` is read from Vault |
| `VAULT_USERNAME` / `VAULT_PASSWORD` | — | userpass auth |
| `VAULT_SECRET_PATH` | `dev_env` | KV v2 path under the `secret` mount |

## Frontend

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE` | `/interact-backend/api` | API base path used by the browser |
| `BACKEND_URL` | `http://127.0.0.1:5000` | Where the Vite dev server proxies `/interact-backend/*` |
