# Architecture

← [Back to README](../README.md)

- [System overview](#system-overview)
- [Query processing flow](#query-processing-flow)
- [Backend components](#backend-components)
- [Session lifecycle](#session-lifecycle)
- [Security](#security)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)

---

## System overview

```
                     +-----------------------------+
                     |  React Frontend (Vite, TS)  |
                     |         :5001               |
                     +--------------+--------------+
                                    | HTTP  /interact-backend/api/*
                     +--------------v--------------+
                     |   FastAPI Backend (3.12)    |
                     |         :5000               |
                     +--------------+--------------+
                                    |
      +-------------+---------------+---------------+---------------+
      |             |                               |               |
+-----v------+ +----v-----------+         +---------v-----+ +-------v------+
| Sessions   | | Data warehouse |         | Archival      | | Metadata     |
| MongoDB /  | | StarRocks /    |         | Elasticsearch | | SQLite       |
| SQLite     | | SQLite (local) |         | (optional)    | | metadata.db  |
+------------+ +----------------+         +---------------+ +--------------+
```

| Store | Production | Local run |
|---|---|---|
| Data the generated SQL runs against | StarRocks (MySQL dialect) | `app/src/finance.db`, opened read-only |
| Chat sessions and messages | MongoDB | `app/src/sessions.db` |
| Long-term archive | Elasticsearch | disabled |
| Domain prompts | `metadata.db`, built from the git metadata volume | `metadata.db`, built from `Config.DOMAINS` |
| Gemini API key | HashiCorp Vault | `GOOGLE_API_KEY` in `.env` |

## Query processing flow

```
User question (English or Arabic)
  │
  ▼
POST /api/query/stream  (SSE)   or   POST /api/query  (single JSON)
  │
  ├─ Translate Arabic → English (if needed)
  ├─ SessionManager loads / creates MultiTurnConversation
  │
  ▼
Orchestrator LLM (Gemini) with tool calling
  │
  ├─► get_data_from_sql
  │     ├─ PromptBuilder: base.md + SQL dialect rules + domain prompt (metadata.db)
  │     ├─ Code-gen LLM → structured JSON { intent, sql_query, python }
  │     ├─ Execute SQL + Python against the data warehouse
  │     └─ Return table rows or a PNG chart  (retried once on failure)
  │
  ├─► get_context_from_rag
  │     └─ Read the domain's context file (e.g. core/finance_operations.txt)
  │
  └─► Plain text answer
  │
  ├─ Translate back to Arabic (if input was Arabic)
  ├─ Persist message, generated SQL and timing tree
  ▼
SSE events: start → status… → delta… → part… → sql → done
(/api/query returns the collected parts as one JSON response)
```

### Streaming

`MultiTurnConversation.chat_stream()` is an async generator and the single source of truth; `chat()` just collects its `part` events.

- **LLM text** is streamed with `llm.astream()`. Chunks are re-assembled with `message_chunk_to_message`, so tool calls and history behave exactly as in non-streaming mode.
- **Tool progress.** The SQL tool reports stages through an `asyncio.Queue` callback. Its blocking work (text-to-SQL, query execution, plotting) runs in `asyncio.to_thread`, so events keep flowing while it runs.
- **Arabic.** Answers to Arabic questions are translated whole, so they arrive as complete `part` events instead of token deltas.

## Backend components

### Conversation engine — `core/conversation.py`

`MultiTurnConversation` holds one chat session.

- Built through the async factory `MultiTurnConversation.create(...)`. It generates the system instruction with `generate_domain_prompt(module_name)`.
- `chat_stream(user_input)` binds the two tools to the orchestrator LLM, streams the answer, dispatches the tool call and retries SQL generation once, sending the error and traceback back to the LLM. `chat()` is a non-streaming wrapper around it.
- Every step is timed into a nested `timing_data` tree that is stored with the message.

### Tools — `core/tools.py`

| Function | Purpose |
|---|---|
| `text_to_sql` | Calls the code-gen LLM with structured output (`Cgen`: `intent` + `sql_query` + `python`) |
| `execute_dynamic_code` | Runs the generated SQL and Python with a pooled or read-only connection and returns rows or a chart |
| `get_context_from_rag` | Returns the active domain's glossary/policy document |
| `build_tools` | Binds both tools to the current request's state |

### LLM providers — `core/llm_factory.py`

The provider is selected with `PROVIDER` (`google` by default). It also supports `openai`, `azure_openai`, `anthropic`, `groq`, `mistral`, `ollama` and `huggingface`.

- `get_llm()` returns the orchestrator model (`ORCHESTRATOR_MODEL`).
- `get_codegen_llm()` returns the text-to-SQL model (`CODEGEN_MODEL`). It always uses Google.

### Prompt system

| File | Role |
|---|---|
| `prompts/sys_domain_prompt.py` | Orchestrator system prompt: persona, active domains, tool rules, privacy rules |
| `prompts/base.md` | Text-to-SQL instructions shared by all domains. `{SQL_DIALECT_RULES}` is filled in per engine |
| `prompts/finance.md` | Finance domain prompt: schema, joins, masking rules, channel mapping, few-shot SQL |
| `core/prompts/prompt_builder.py` | Combines base prompt, dialect rules and domain prompt |
| `core/prompts/prompt_cache.py` | Reads domain prompts from `metadata.db` by tag or module |

### Domains and metadata — `config.py`, `utils/git_metadata_loader.py`

Domains are declared in `Config.DOMAINS`, with the active domain first and placeholders after it. On startup and on `GET /api/refresh-metadata`, `metadata.db` is rebuilt:

1. If `metadata_vol/<MODULE>/<tag>/prompt.md` exists (the mounted git metadata repo), it is used.
2. Otherwise prompts are loaded from the `prompt_file` entries in `Config.DOMAINS`.

The rebuild writes to a temp file and swaps it in atomically, so a failed load keeps the previous DB.

### Sessions — `session_management/`, `repositories/`

- `SessionManager` creates and restores conversations, stores messages and feedback, and handles archival.
- `RepositoryFactory` picks `SessionRepository` (MongoDB) or `SQLiteSessionRepository` based on `DB_TYPE`.
- `ElasticsearchRepository` does bulk upserts keyed by `session_id` / `response_id`. It is enabled when `ES_ENABLED=true`.

## Session lifecycle

**Login.** `POST /api/load-session-history` copies the last N days from Elasticsearch into the session store and skips records that already exist. If ES is down, the call returns `skipped`.

**Active session.**
1. The user picks a domain and asks a question with `POST /api/query`.
2. A placeholder message is inserted, the question is processed, and the message is updated with the answer.
3. Like/dislike and text feedback update the same message.
4. The LangChain message history is saved on the session document.

**Logout.** `POST /api/archive-session-data` bulk-indexes the user's sessions and messages into ES. Only after that succeeds does it delete the messages from MongoDB and clear `chat_history`. Session metadata is kept.

**Nightly sync.** An Airflow DAG calls `POST /api/sync-to-elk` to catch sessions that were never archived. See [DEPLOYMENT.md](DEPLOYMENT.md#airflow-nightly-sync).

| Operation | Key | Strategy |
|---|---|---|
| ES → session store (login) | `session_id` / `response_id` | Skip if it exists |
| Session store → ES (logout, sync) | `_id = session_id` / `response_id` | Upsert |

## Security

- **Generated code isolation.** In SQLite mode the data DB is opened read-only (`mode=ro`), so writes fail. The prompts forbid DDL/DML. In production, use a read-only StarRocks user.
- **Sensitive columns.** Account numbers are shown masked to the last 4 digits. UTR numbers are treated as encrypted: they are never displayed or matched with `WHERE =`.
- **Prompt protection.** The system prompt tells the model never to reveal prompts, schema or internal logic.
- **Errors.** `GlobalErrorExecution` middleware catches unhandled exceptions. Tracebacks are stored in `error_message` and written to `logs/app_errors_and_activity.log`. Users only see a generic fallback message.
- **Secrets.** The API key comes from Vault (when `VAULT_ADDR` is set) or `.env`. `.env` is git-ignored.
- **CORS.** All origins are allowed (`*`). Restrict this in production.

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115, Uvicorn, Pydantic 2 |
| LLM | LangChain 1.x, `langchain-google-genai`, Gemini 2.5 Flash |
| Data | pandas, matplotlib / seaborn, SQLAlchemy + PyMySQL, sqlite3 / aiosqlite |
| Sessions & archival | pymongo, elasticsearch-py (>=8, <9) |
| Secrets | hvac (HashiCorp Vault) |
| Frontend | React 18, TypeScript, Vite 5, react-markdown, lucide-react |
| Infrastructure | StarRocks, MongoDB, Elasticsearch 8.12, Apache Airflow, Docker |

> elasticsearch-py must stay below 9.0. Version 9.x sends `compatible-with=9` headers that ES 8.x rejects.

## Project structure

```
.
├── app/src/
│   ├── main.py                  # FastAPI app and routers
│   ├── startup.py               # Lifespan: DB pool, metadata rebuild, API key, SessionManager
│   ├── config.py                # Settings, domain registry (Config.DOMAINS)
│   ├── controllers/             # API routes
│   ├── core/
│   │   ├── conversation.py      # MultiTurnConversation
│   │   ├── tools.py             # text-to-SQL, code execution, RAG
│   │   ├── llm_factory.py       # LLM provider switch
│   │   ├── database.py          # StarRocks pool / SQLite read-only connection
│   │   ├── prompts/             # Prompt builder and metadata.db cache
│   │   └── finance_operations.txt   # Finance glossary (RAG context)
│   ├── prompts/                 # base.md, finance.md, system prompt
│   ├── repositories/            # MongoDB, SQLite and Elasticsearch repositories
│   ├── session_management/      # SessionManager
│   ├── utils/                   # Metadata loader
│   ├── finance.db               # Local finance data (SQLite)
│   └── metadata.db              # Domain prompt cache (SQLite)
├── app/tests/                   # pytest suite (kept outside src)
├── frontend/                    # React UI
├── docs/                        # Documentation
└── Dockerfile                   # Backend image
```
