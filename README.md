# Analyst Chatbot (Uber Finch like assistant) - Technical Documentation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Backend Deep Dive](#5-backend-deep-dive)
6. [API Reference](#7-api-reference)
7. [Database Schemas](#8-database-schemas)
8. [Session Lifecycle](#9-session-lifecycle)
9. [Deployment](#10-deployment)
10. [Environment Variables](#11-environment-variables)
11. [Security](#12-security)
12. [Testing](#13-testing)
13. [Airflow Integration](#14-airflow-integration)

---

## 1. Overview

**SQL-Chatbot** is an AI-powered conversational analytics platform that enables users to query enterprise business data using natural language. It integrates Google Gemini Flash for LLM capabilities and supports:

- **Natural language to SQL** — Users ask questions in plain English or Arabic; the system generates SQL, executes it against StarRocks, and returns formatted tables or charts.
- **Multi-turn conversations** — Full context-aware chat sessions with Gemini function calling.
- **Data visualization** — Automatic chart/plot generation using matplotlib.
- **RAG (Retrieval-Augmented Generation)** — Fetches domain-specific business logic documents to answer contextual questions.
- **Multi-language support** — Bidirectional English-Arabic translation.
- **Voice input** — Speech-to-text transcription via Gemini.
- **Session archival** — Hot storage in MongoDB with long-term archival to Elasticsearch.
- **Multi-module support** — SMOP, ELOSS, GSP, TLMS, SAATD, FTEMS, RBA, SPLM, LD, LP domains.
- **Feedback collection** — Like/dislike reactions and text feedback on every response.

---

## 2. Architecture

### High-Level System Diagram

```
                          +---------------------+
                          |   React Frontend    |
                          |  (TypeScript + MUI) |
                          +----------+----------+
                                     |
                        HTTP (Axios) | Port 5001
                                     |
                          +----------v----------+
                          |   FastAPI Backend    |
                          |   (Python 3.12)     |
                          |   Port 5000          |
                          +----------+----------+
                                     |
              +----------+-----------+-----------+----------+
              |          |                       |          |
     +--------v---+  +---v--------+     +--------v---+ +---v---------+
     |  MongoDB   |  | StarRocks  |     |Elasticsearch| |  SQLite    |
     | (Sessions) |  | ( Data) |     | (Archival)  | | (Metadata) |
     +------------+  +------------+     +-------------+ +------------+
                                                |
                                        +-------v-------+
                                        |   Grafana     |
                                        | (Dashboards)  |
                                        +---------------+
```

### Data Flow — Query Processing

```
User Query (English or Arabic)
    |
    v
Frontend sends POST /api/query
    |
    v
Backend: Translate Arabic to English (if needed)
    |
    v
SessionManager loads/creates MultiTurnConversation
    |
    v
Gemini LLM (gemini-2.0-flash-001) with Function Calling
    |
    +---> Tool: get_data_from_sql
    |         |
    |         +---> PromptBuilder reads schema from SQLite (metadata.db)
    |         +---> Text-to-SQL (Gemini 2.5 Flash, structured JSON output)
    |         +---> Execute SQL + Python on StarRocks via PyMySQL
    |         +---> Return table (markdown) or chart (base64 image)
    |
    +---> Tool: get_context_from_rag
    |         |
    |         +---> Read business logic docs (Smart_meter_operations.txt)
    |         +---> Return context to Gemini for synthesis
    |
    +---> Text-only response (general questions)
    |
    v
Translate response back to Arabic (if input was Arabic)
    |
    v
Save message + timing data to MongoDB
    |
    v
Return JSON response to frontend
```

---

## 3. Tech Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | FastAPI | 0.115.5 |
| ASGI Server | Uvicorn | 0.24.0 |
| Language | Python | 3.12.8 |
| LLM SDK | google-genai/Langchain | 1.22.0 |
| LLM Model (Chat) | Gemini 2.0 Flash | gemini-2.0-flash-001 |
| LLM Model (Text-to-SQL) | Gemini 2.5 Flash | gemini-2.5-flash |
| Session Store | pymongo | 4.10.1 |
| Data Warehouse Driver | pymysql | 1.1.1 |
| Archival Store | elasticsearch-py | 8.x (<9.0) |
| Data Processing | pandas | 2.2.3 |
| Visualization | matplotlib | 3.9.2 |
| Data Validation | pydantic | 2.9.2 |


### Infrastructure

| Component | Technology |
|-----------|-----------|
| Data Warehouse | StarRocks (MySQL-compatible, port 9030) |
| Session Database | MongoDB |
| Archival Database | Elasticsearch 8.12.0 |
| Metadata Cache | SQLite (metadata.db) |
| Orchestration | Docker Compose |
| Scheduling | Apache Airflow |
| Dashboards | Grafana |

---

## 4. Project Structure

```
SQL-Chatbot-Gemini-2.5/
|app/src/
│
├── controllers/ # API layer (request/response handling)
├── core/ # Core logic (LLM orchestration, pipelines)
├── repositories/ # Data access layer (SQL, DB interactions)
├── session_management/ # Chat/session handling (state, memory)
├── utils/ # Utility functions (helpers, common logic)
├── prompts/ # Prompt templates for LLM
├── metadata_vol/ # Metadata storage / configs
├── logs/ # Application logs
├── tests/ # Unit & integration tests
│
├── config.py # Configuration management
├── main.py # Entry point (API routes binding)
├── startup.py # App initialization logic
├── metadata.db # Local metadata DB (SQLite)
├── requirements.txt # Production dependencies
├── requirements-dev.txt # Dev dependencies
├── .env # Environment variables
│
├── Dockerfile # Containerization setup
└── README.md # Project documentation
|
+-- airflow/
|   +-- dags/
|       +-- mongo_to_elk_sync_dag.py      # Nightly MongoDB -> ES sync
|
+-- docs/
|   +-- EFK_Chat_History_Archival.md      # EFK archival architecture doc
|   +-- Technical_Documentation.md        # This document
|
+-- SQL-Chatbot-metadata/                     # Metadata management (separate)
```

---

## 5. Backend Deep Dive

### 5.1 FastAPI Application (`main.py`)

The application entry point initializes:

- **FastAPI** with `root_path="/SQL-Chatbot-backend"` for reverse-proxy deployment
- **CORS middleware** — allows all origins (development)
- **GlobalErrorExecution middleware** — catches unhandled exceptions, returns consistent JSON
- **Gemini client** — initialized with API key (supports optional HTTP proxy)
- **SessionManager** — singleton managing all session operations

**Startup flow:**
1. Load `.env` via python-dotenv
2. Configure logging to `logs/app_errors_and_activity.log`
3. Initialize SessionManager with API key + StarRocks DB config
4. Initialize Gemini client (with proxy if `HTTP_PROXY` is set)

### 5.2 Core Conversation Engine (`core/conversation.py`)

**Class: `MultiTurnConversation`**

This is the heart of the application. Each active session holds one instance.

**Constructor Parameters:**
- `chat_history` — Previous Gemini conversation history (restored from MongoDB)
- `module_name` — The business module (e.g., "SMOP")
- `current_timestamp` — For time-aware query generation
- `test` / `sys_test_prompt` / `tag_list` — Testing overrides

**Initialization:**
1. Creates Gemini client with API key
2. Loads StarRocks DB config from environment
3. Generates system instruction via `generate_smart_meter_prompt()` which reads domains from `metadata.db`
4. Declares two function tools for Gemini:
   - `get_data_from_sql` — Data extraction and visualization
   - `get_context_from_rag` — Business logic document retrieval
5. Creates Gemini chat session with `gemini-2.0-flash-001`, temperature=0.1

**Key Methods:**

| Method | Description |
|--------|-------------|
| `chat(user_input)` | Main entry point. Sends to Gemini, handles tool calls, retries on failure (max 2 attempts) |
| `text_to_sql(user_input, sys_prompt, history)` | Calls `gemini-2.5-flash` with structured JSON output to generate SQL + Python code |
| `execute_dynamic_code(my_output)` | Executes generated SQL/Python against StarRocks, returns tables or charts |
| `get_data_from_sql(user_input, history, tag)` | Orchestrates: PromptBuilder -> text_to_sql -> execute_dynamic_code |
| `get_context_from_rag(user_input, history, tag)` | Reads `Smart_meter_operations.txt` for domain context |
| `translate_arabic_to_english(text)` | Detects Arabic via Unicode regex, translates if needed |
| `translate_english_to_arabic(text, is_arabic)` | Translates response back if original input was Arabic |
| `history()` | Returns cleaned conversation history (filters out text/function_response parts) |
| `text_to_sql_history(tag)` | Extracts domain-filtered conversation history for text-to-SQL context |

**Retry Mechanism:**
```
Attempt 1: Generate SQL -> Execute
    |
    +-- Success -> Return result
    |
    +-- Failure -> Send error + traceback to Gemini for correction
                      |
                      v
                  Attempt 2: Corrected SQL -> Execute
                      |
                      +-- Success -> Return result
                      +-- Failure -> Return fallback error message
```

**Timing Instrumentation:**
Every operation is timed and stored in a nested tree structure (`self.timing_data`) for performance monitoring:
```json
[
  {
    "function": "gemini_call_1",
    "time": 1.23,
    "children": [
      {
        "function": "get_data_from_sql",
        "time": 3.45,
        "children": [
          { "function": "text_to_sql", "sql": "SELECT ...", "time": 2.0 },
          { "function": "sql_query_execution", "time": 0.5 }
        ]
      }
    ]
  }
]
```

### 5.3 Prompt System

**System Instruction Generation (`prompts/sys_domain_prompt.py`):**
- Reads domains from `metadata.db` SQLite
- Builds system prompt: "You are a helpful assistant" + domain classifications + tool usage rules
- Each domain is classified with its tag for Gemini function calling

**Schema-Aware Prompt Builder (`core/prompts/prompt_builder.py`):**

**Class: `PromptBuilder`**

Called for every `get_data_from_sql` invocation. Reads from `metadata.db` to build:

1. **Schema information** — Tables, columns, data types, comments per domain
2. **Relationships** — Foreign key and join relationships between tables
3. **FAQs** — Example questions with their corresponding SQL (few-shot prompting)
4. **Business logic** — Domain descriptions

The prompt format:
```
[Base text-to-SQL instructions]
[Schema: tables, columns, types]
[Relationships: table joins]
[FAQ examples: question -> SQL]
```

### 5.4 Session Management (`session_management/session_manager_mongo.py`)

**Class: `SessionManager`**

Manages the lifecycle of chat sessions:

| Method | Description |
|--------|-------------|
| `get_session(timestamp, session_id, module, email, user_input)` | Creates or retrieves a MultiTurnConversation. Sets session name from first user query. |
| `add_message_to_session(message)` | Inserts placeholder message doc into MongoDB before processing |
| `update_message_after_response(response_id, update_data)` | Updates message with AI response, timing, response_time |
| `save_history(session_id, chat_history)` | Saves Gemini conversation history to session document |
| `get_active_sessions(user_email)` | Returns sessions grouped by: Today / Yesterday / Last 7 Days |
| `get_session_messages(session_id)` | Formats messages for frontend consumption |
| `update_like_feedback(session_id, response_id, like)` | Saves thumbs up/down |
| `update_message_feedback(session_id, response_id, feedback)` | Saves text feedback |
| `load_session_history_from_es(user_email, days)` | Restores last N days from Elasticsearch to MongoDB (login) |
| `archive_session_data_to_es(user_email)` | Archives all sessions to Elasticsearch (logout) |
| `delete_session(session_id)` | Removes session and all its messages |

### 5.5 Repositories

**SessionRepository (`repositories/SessionRepository.py`):**
- MongoDB collections: `sessions`, `session_messages`
- CRUD operations with ObjectId-based lookups
- Aggregation queries for session grouping by date

**ElasticsearchRepository (`repositories/ElasticsearchRepository.py`):**
- Indices: `SQL-Chatbot_sessions`, `SQL-Chatbot_session_messages`
- Bulk indexing with upsert semantics (document `_id` = session_id / response_id)
- Availability check with graceful degradation
- Handles binary data serialization (base64 encoding for bytes like `thought_signature`)

### 5.6 Metadata Sync (`utils/MetadataSyncService.py`)

Synchronizes metadata from StarRocks data warehouse to local SQLite (`metadata.db`):

```
StarRocks (AIS_DWH)           SQLite (metadata.db)
+------------------+          +------------------+
| modules          |  -----> | modules          |
| domains          |  -----> | domains          |
| entities         |  -----> | entities         |
| attributes       |  -----> | attributes       |
| relationships    |  -----> | relationships    |
| faqs             |  -----> | faqs             |
+------------------+          +------------------+
```

Triggered via `POST /api/refresh-metadata` or `GET /api/refresh-local-metadata`.

---

## 6. API Reference

### Base URL

- Development: `http://127.0.0.1:5000/SQL-Chatbot-backend`
- Production: `https://<domain>/SQL-Chatbot-backend`

### Endpoints

#### POST /api/query

Main chat query endpoint. Processes user input through Gemini LLM.

**Request:**
```json
{
  "user_input": "What is the total billing amount for January?",
  "session_id": "abc123",
  "message_id": "msg456",
  "module_name": "SMOP",
  "request_timestamp": "2026-03-02T10:30:00Z",
  "user_id": "user@email.com",
  "user_tab": "billing_efficiency"
}
```

**Response:**
```json
{
  "response": [
    { "type": "text", "content": "## Billing Summary\n\n| Month | Amount |\n|---|---|\n| Jan | 1,234,567 |" },
    { "type": "image", "mime_type": "image/jpeg", "content": "<base64>" }
  ],
  "response_id": "507f1f77bcf86cd799439011",
  "response_timestamp": "2026-03-02T10:30:05Z"
}
```

**Response types:**
- `text` — Markdown-formatted text or table
- `image` — Base64-encoded chart image (JPEG)

---

#### POST /api/translate

Translates text between English and Arabic.

**Request:**
```json
{
  "text": "What is the total revenue?",
  "direction": "en-to-ar"
}
```

**Directions:** `en-to-ar`, `english-to-arabic`, `ar-to-en`, `arabic-to-english`

**Response:**
```json
{
  "success": true,
  "original": "What is the total revenue?",
  "translation": "ما هو إجمالي الإيرادات؟",
  "direction": "en-to-ar"
}
```

---

#### POST /api/speech-to-text

Transcribes WAV audio and optionally translates to English.

**Request:** `multipart/form-data`
- `file` (required) — WAV audio file
- `translate` (optional, default: `"true"`) — Whether to translate to English

**Response:**
```json
{
  "success": true,
  "transcription": "ما هو إجمالي الفواتير",
  "translation": "What is the total billing"
}
```

---

#### POST /api/like-feedback

Saves thumbs up/down reaction on a message.

**Request:**
```json
{
  "session_id": "abc123",
  "response_id": "507f1f77bcf86cd799439011",
  "is_like": true
}
```

---

#### POST /api/message-feedback

Saves text feedback on a message.

**Request:**
```json
{
  "session_id": "abc123",
  "response_id": "507f1f77bcf86cd799439011",
  "feedback": "The SQL query was correct but the chart labels need improvement."
}
```

---

#### GET /api/getsessions

Returns user's sessions grouped by date.

**Headers:** `user_id: user@email.com`

**Response:**
```json
{
  "Today": [
    {
      "session_id": "abc123",
      "session_name": "Total billing amount for January",
      "module_name": "SMOP",
      "created_at": "2026-03-02T09:00:00Z",
      "last_updated": "2026-03-02T10:30:00Z"
    }
  ],
  "Yesterday": [],
  "Last 7 Days": []
}
```

---

#### GET /api/getsession/data

Returns all messages for a session.

**Headers:** `session_id: abc123`

---

#### DELETE /api/deletesession

Deletes a session and all its messages.

**Headers:** `session_id: abc123`

---

#### POST /api/load-session-history

Loads last N days of sessions from Elasticsearch to MongoDB. Called on user login.

**Request:**
```json
{
  "user_email": "user@email.com",
  "days": 7
}
```

**Response:**
```json
{
  "status": "success",
  "sessions_loaded": 5,
  "messages_loaded": 42,
  "time_taken": 1.23
}
```

---

#### POST /api/archive-session-data

Archives all user sessions from MongoDB to Elasticsearch. Called on user logout.

**Request:**
```json
{
  "user_email": "user@email.com"
}
```

**Response:**
```json
{
  "status": "success",
  "sessions_archived": 5,
  "messages_archived": 42,
  "messages_cleaned_from_mongo": 42,
  "time_taken": 2.15
}
```

---

#### GET /api/refresh-metadata

Syncs metadata from StarRocks to local SQLite. Returns counts of synced records.

---

#### GET /api/refresh-local-metadata

Refreshes local SQLite metadata schema without StarRocks sync.

---

#### POST /api/auto-test

Testing endpoint for iterating on prompts. Accepts user input, module, and optional history.

**Request:**
```json
{
  "user_input": "Show total billing",
  "module_name": "SMOP",
  "history": []
}
```

**Response:**
```json
{
  "sql": ["SELECT SUM(billing_amount) FROM ..."],
  "response": [{ "type": "text", "content": "..." }],
  "history": [...]
}
```

---

#### POST /api/auto-test-tag

Testing endpoint for domain classification. Returns the tag assigned by Gemini.

**Request:**
```json
{
  "user_input": "What is energy loss in sector 5?",
  "module_name": "SMOP",
  "history": [],
  "test": true,
  "tag_list": ["billing_efficiency", "RCRDC", "read_reliability"],
  "system_domain_prompt": "..."
}
```

**Response:**
```json
{
  "tag": "billing_efficiency",
  "history": [...],
  "timing": 0.85
}
```

---

## 7. Database Schemas

### 7.1 MongoDB

**Collection: `sessions`**

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Unique session identifier |
| user_email | string | User's email address |
| session_name | string | First user query (auto-set) |
| module_name | string | Module code (SMOP, TLMS, etc.) |
| avg_response_time | float | Average LLM response time |
| query_exec_time | float | Average query execution time |
| created_at | datetime | Session creation timestamp |
| last_updated | datetime | Last activity timestamp |
| chat_history | array | Gemini native conversation history (for restoring sessions) |

**Collection: `session_messages`**

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Parent session ID |
| message_id | string | Client-generated message ID |
| response_id | string | Server-generated response ID (ObjectId) |
| user_input | string | Original user question |
| translated_input | string | English translation (if Arabic input) |
| response | array | LLM response array [{type, content, mime_type}] |
| execution_times | array | Nested timing tree |
| input_timestamp | string | Client-side timestamp |
| timestamp | datetime | Server-side timestamp |
| response_time | float | Total response time (seconds) |
| error_message | string | Error traceback (if failed) |
| like | boolean | true = thumbs up, false = thumbs down, null = no reaction |
| feedback | string | Free-text user feedback |

### 7.2 Elasticsearch

**Index: `SQL-Chatbot_sessions`**

| Field | ES Type | Description |
|-------|---------|-------------|
| session_id | keyword | Unique ID (also document `_id`) |
| user_email | keyword | User email |
| session_name | text | Session name |
| module_name | keyword | Module code |
| session_type | keyword | Session type |
| avg_response_time | float | Average response time |
| query_exec_time | float | Query execution time |
| created_at | date | Creation timestamp |
| last_updated | date | Last update timestamp |
| chat_history | object (disabled) | Gemini history (not indexed) |

**Index: `SQL-Chatbot_session_messages`**

| Field | ES Type | Description |
|-------|---------|-------------|
| session_id | keyword | Parent session ID |
| message_id | keyword | Client message ID |
| response_id | keyword | Server response ID (also document `_id`) |
| user_input | text | Original question |
| translated_input | text | Translated input |
| response | object (disabled) | Response array (not indexed) |
| execution_times | object (disabled) | Timing tree (not indexed) |
| input_timestamp | keyword | Client timestamp |
| timestamp | date | Server timestamp |
| response_time | float | Total response time |
| error_message | text | Error details |
| like | boolean | User reaction |
| feedback | text | User feedback text |

### 7.3 SQLite (metadata.db)

Local cache of metadata from StarRocks. Tables:

- **modules** — `id`, `name`, `description`
- **domains** — `id`, `module_id`, `name`, `description`, `schema`
- **entities** — `id`, `domain_id`, `name`, `description`
- **attributes** — `id`, `entity_id`, `name`, `data_type`, `is_primary_key`, `is_nullable`, `is_unique`, `default_value`, `comment`
- **relationships** — `id`, `domain_id`, `name`, `from_entity_id`, `to_entity_id`, `relationship_type`, `description`
- **faqs** — `id`, `FAQ`, `SQL`, `Tag`

### 7.4 StarRocks (AIS_DWH)

The source-of-truth data warehouse containing:

- **Business data tables** — Queried by generated SQL (per-domain schemas)
- **Metadata tables** — `modules`, `domains`, `entities`, `attributes`, `relationships`, `faqs` — synced to SQLite

---

## 8. Session Lifecycle

### Login Flow

```
1. User enters credentials on Login page
2. Client-side validation against user list
3. POST /api/load-session-history { user_email, days: 7 }
4. Backend checks ES availability
   - ES DOWN -> Return "skipped", continue with MongoDB-only
   - ES UP -> Query SQL-Chatbot_sessions + SQL-Chatbot_session_messages for last 7 days
5. Upsert sessions/messages into MongoDB (skip duplicates)
6. Frontend fetches GET /api/getsessions to populate sidebar
7. User sees last 7 days of chat history
```

### Active Session

```
1. User selects module -> creates new session OR clicks existing session
2. User types query -> POST /api/query
3. Backend: insert placeholder message -> process with Gemini -> update message
4. Response returned to frontend (text/image/table)
5. User can provide like/dislike + text feedback
6. Gemini conversation history saved to MongoDB session.chat_history
```

### Logout Flow

```
1. User clicks Logout
2. POST /api/archive-session-data { user_email }
3. Backend checks ES availability
   - ES DOWN -> Return "skipped", data stays in MongoDB
   - ES UP -> Bulk index all sessions + messages to ES
4. On success: cleanup MongoDB (delete messages, clear chat_history)
5. Session metadata kept in MongoDB (for quick reference)
6. Frontend clears state -> redirect to /login
```

### Nightly Sync (Airflow)

```
Schedule: 0 2 * * * (2:00 AM daily)
DAG: mongo_to_elk_nightly_sync
Action: POST /SQL-Chatbot-backend/api/sync-to-elk { "full_sync": false }
Purpose: Catch any sessions that weren't archived during normal logout
Retries: 2, with exponential backoff (3min -> 15min max)
```

### Duplicate Prevention

| Operation | Key Field | Strategy |
|-----------|-----------|----------|
| Login (ES -> MongoDB) | session_id / response_id | Skip if already exists |
| Logout (MongoDB -> ES) | _id = session_id / response_id | Upsert (overwrite) |

---

## 9. Deployment

### Docker Images

**Backend:**
```dockerfile
FROM python:3.12.8-slim
WORKDIR /SQL-Chatbot-backend
COPY app/src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/src/ .
EXPOSE 5000
CMD ["python", "main.py"]
```

### Port Mapping

| Service | Container Port | Host Port |
|---------|---------------|-----------|
| Backend (FastAPI) | 5000 | 5000 |
| Frontend (React) | 5001 | 5001 (or 3000) |
| MongoDB | 27017 | 27017 |
| Elasticsearch | 9200 | 9200 |
| StarRocks | 9030 | 9030 |

### Sub-Path Deployment

- Backend API: `/SQL-Chatbot-backend/api/*`
- Frontend UI: `/SQL-Chatbot-frontend/*`

---

## 10. Environment Variables

### Backend (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | `AIzaSy...` |
| `GCP_PROJECT_ID` | GCP project (for Vertex AI) | `sec-prod-insights` |
| `GCP_LOCATION` | GCP region | `us-central1` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON path | `utils/Secrets/gemini-sa.json` |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/` |
| `DB_NAME` | MongoDB database name | `chat_session_db` |
| `STARROCKS_IP` | StarRocks host | `144.24.132.143` |
| `STARROCKS_PORT` | StarRocks port | `9030` |
| `STARROCKS_USER` | StarRocks user | `aissys` |
| `STARROCKS_PASSWORD` | StarRocks password | *(empty or set)* |
| `STARROCKS_DB` | StarRocks database | `AIS_DWH` |
| `ES_HOST` | Elasticsearch host | `localhost` |
| `ES_PORT` | Elasticsearch port | `9200` |
| `ES_USERNAME` | ES basic auth user | *(optional)* |
| `ES_PASSWORD` | ES basic auth password | *(optional)* |
| `ES_SCHEME` | ES protocol | `http` |
| `ES_VERIFY_CERTS` | Verify SSL certs | `false` |
| `HTTP_PROXY` | HTTP proxy for Gemini API | *(optional)* |

### Frontend (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API base URL | `http://127.0.0.1:5000` |

---

## 11. Security

### SQL Guardrails (`utils/sql_keywords_guardrails.py`)
- Blocks dangerous SQL keywords: `DROP`, `DELETE`, `ALTER`, `TRUNCATE`, etc.
- Validates generated SQL before execution against StarRocks

### CORS
- Currently allows all origins (`*`) — restrict in production

### Authentication
- Client-side credential validation (development)
- JWT token support in API request headers
- API client interceptors redirect to login on 401/403

### Error Handling
- **GlobalErrorExecution middleware** catches all unhandled exceptions
- Error tracebacks stored in `error_message` field (not exposed to users)
- User-facing error: *"We acknowledge your question. Energon is in the training phase, and the response will be available soon."*
- All errors logged to `logs/app_errors_and_activity.log`

### Content Sanitization
- Frontend uses DOMPurify to sanitize all markdown/HTML content before rendering

### Gemini API Security
- API key stored in `.env` (not in code)
- Optional Vertex AI service account authentication (commented out, available for production)
- System prompts not exposed to frontend

---

## 12. Testing

### Test Files

| File | Coverage |
|------|----------|
| `tests/test_api_efk_endpoints.py` | API endpoints for ES/Kibana integration |
| `tests/test_elasticsearch_repository.py` | ElasticsearchRepository operations |
| `tests/test_session_manager_efk.py` | SessionManager archival/restore flows |

### Manual Testing

**Start Elasticsearch locally:**
```bash
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.12.0
```

**Test archive (logout):**
```bash
curl -X POST http://localhost:5000/SQL-Chatbot-backend/api/archive-session-data \
  -H "Content-Type: application/json" \
  -d '{"user_email": "user@email.com"}'
```

**Test load (login):**
```bash
curl -X POST http://localhost:5000/SQL-Chatbot-backend/api/load-session-history \
  -H "Content-Type: application/json" \
  -d '{"user_email": "user@email.com", "days": 7}'
```

**Test query:**
```bash
curl -X POST http://localhost:5000/SQL-Chatbot-backend/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Show total billing for January 2026",
    "session_id": "test-session-1",
    "message_id": "msg-1",
    "module_name": "SMOP",
    "user_id": "user@email.com"
  }'
```

**Verify Elasticsearch indices:**
```bash
curl http://localhost:9200/SQL-Chatbot_sessions/_count
curl http://localhost:9200/SQL-Chatbot_session_messages/_count
```

### Auto-Test Endpoints

Use `/api/auto-test` and `/api/auto-test-tag` to iterate on prompts without the full UI:

```bash
# Test SQL generation
curl -X POST http://localhost:5000/SQL-Chatbot-backend/api/auto-test \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Show total billing", "module_name": "SMOP"}'

# Test domain classification
curl -X POST http://localhost:5000/SQL-Chatbot-backend/api/auto-test-tag \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "What is energy loss?",
    "module_name": "SMOP",
    "test": true,
    "tag_list": ["billing_efficiency", "RCRDC"]
  }'
```

---

## 13. Airflow Integration

### DAG: `mongo_to_elk_nightly_sync`

**File:** `airflow/dags/mongo_to_elk_sync_dag.py`

| Property | Value |
|----------|-------|
| Schedule | `0 2 * * *` (2:00 AM UTC daily) |
| Task | `sync_mongo_to_elk` |
| Method | POST to `/SQL-Chatbot-backend/api/sync-to-elk` |
| Retries | 2 (exponential backoff: 3min -> 15min) |
| Timeout | 10 minutes per execution |
| Max Active Runs | 1 (prevents overlapping) |

**Airflow Connection:**
- Connection ID: `SQL-Chatbot_backend_api`
- Must be configured in Airflow to point to the backend host

**Purpose:** Catches any sessions that weren't archived during normal logout (e.g., browser closed without logging out).

---

## Appendix: Version Compatibility Notes

| Component | Version | Notes |
|-----------|---------|-------|
| Elasticsearch Server | 8.12.0 | |
| elasticsearch-py | >=8.0, <9.0 | v9.x sends `compatible-with=9` headers rejected by ES 8.x |
| Python | 3.12.8 | |
| Node.js | 18 (Alpine) | For frontend build and serve |
| Gemini Chat Model | gemini-2.0-flash-001 | Used for main conversation + translation |
| Gemini SQL Model | gemini-2.5-flash | Used for structured JSON text-to-SQL generation |
