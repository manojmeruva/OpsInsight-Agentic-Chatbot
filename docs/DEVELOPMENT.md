# Development

← [Back to README](../README.md)

## Running tests

Tests live in `app/tests/`, outside the application source, so they are not copied into the Docker image. `app/tests/conftest.py` puts `app/src` on the import path.

```bash
pip install -r app/src/requirements-dev.txt
pytest app/tests          # from the repo root (or `pytest tests` from app/)
```

| File | Covers |
|---|---|
| `app/tests/test_api_efk_endpoints.py` | Archival and restore API endpoints |
| `app/tests/test_elasticsearch_repository.py` | `ElasticsearchRepository` |
| `app/tests/test_session_manager_efk.py` | `SessionManager` archival/restore flows |

## Manual checks

```bash
# Ask a question
curl -X POST http://127.0.0.1:5000/api/query -H "Content-Type: application/json" -d '{
  "user_input": "Show total debits for June 2026",
  "session_id": "test-1", "message_id": "m-1",
  "module_name": "FINANCE", "user_id": "analyst@local"
}'

# Iterate on prompts without creating a session
curl -X POST http://127.0.0.1:5000/api/auto-test -H "Content-Type: application/json" \
  -d '{"user_input": "Which accounts are overdrawn?", "module_name": "FINANCE"}'

# Inspect the local data
sqlite3 app/src/finance.db "SELECT bank_code, COUNT(*) FROM account GROUP BY 1;"
```

To test archival locally, start Elasticsearch and set `ES_ENABLED=true`:

```bash
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" -e "xpack.security.enabled=false" \
  elasticsearch:8.12.0
```

## Adding a domain

1. Write the domain prompt in `app/src/prompts/<tag>.md`. Include the schema, joins, business rules and few-shot SQL; use [`prompts/finance.md`](../app/src/prompts/finance.md) as the template.
2. Optionally, write a glossary for conceptual questions in `app/src/core/<tag>_operations.txt`.
3. In `Config.DOMAINS` (`app/src/config.py`), add the domain or update a placeholder: set `prompt_file`, `context_file` and `sample_questions`, and change `status` to `"active"`.
4. Restart the backend or call `GET /api/refresh-metadata` to rebuild `metadata.db`.

## Editing prompts

| Change | File |
|---|---|
| Persona, tool-routing and privacy rules | `app/src/prompts/sys_domain_prompt.py` |
| Text-to-SQL output format, Python safety rules | `app/src/prompts/base.md` |
| SQL dialect hints (SQLite / MySQL) | `app/src/core/prompts/prompt_builder.py` |
| Finance schema and business rules | `app/src/prompts/finance.md` |

After editing a domain prompt, refresh the metadata as in step 4 above.
