# Deployment

← [Back to README](../README.md)

## Backend image

The root [`Dockerfile`](../Dockerfile) builds the API (Python 3.12 slim, port 5000):

```bash
docker build -t opsinsight-backend .
docker run -p 5000:5000 --env-file app/src/.env opsinsight-backend
```

## Frontend build

```bash
cd frontend
npm ci
npm run build        # static files in frontend/dist
```

Serve `dist/` from any static host or Nginx. Route `/interact-backend/` to the backend and strip the prefix:

```nginx
location /interact-backend/ {
    proxy_pass http://backend:5000/;
    proxy_http_version 1.1;
    proxy_buffering off;          # required for /api/query/stream (SSE)
    proxy_read_timeout 300s;
}
location / {
    root /usr/share/nginx/html;
    try_files $uri /index.html;
}
```

## Production services

| Service | Port | Purpose |
|---|---|---|
| Backend (FastAPI) | 5000 | API |
| Frontend | 5001 (dev) / 80 | UI |
| StarRocks | 9030 | Data warehouse (`DATA_DB_ENGINE=starrocks`) |
| MongoDB | 27017 | Sessions (`DB_TYPE=mongo`) |
| Elasticsearch | 9200 | Archival (`ES_ENABLED=true`) |
| Vault | 8200 | Gemini API key (`VAULT_ADDR`) |

### Loading finance data into StarRocks / MySQL

Create the three tables with the DDL in [DATA_MODEL.md](DATA_MODEL.md#finance-domain), load the data, and point `STARROCKS_*` at that database. The prompts automatically switch to the MySQL dialect when `DATA_DB_ENGINE=starrocks`.

### Domain metadata

Mount the git metadata repo at `app/src/metadata_vol/` using the layout `<MODULE>/<tag>/prompt.md` (+ `description.txt`). It is loaded on startup and by `GET /api/refresh-metadata`. Without the mount, `Config.DOMAINS` is used.

## Airflow nightly sync

The DAG `mongo_to_elk_nightly_sync` (kept in the Airflow repo, not in this one) archives sessions that were never archived at logout.

| Property | Value |
|---|---|
| Schedule | `0 2 * * *` (02:00 UTC) |
| Action | `POST /interact-backend/api/sync-to-elk` with `{"full_sync": false}` |
| Retries | 2, exponential backoff 3 → 15 min |
| Timeout | 10 min |
| Max active runs | 1 |
| Connection ID | `SQL-Chatbot_backend_api` (points to the backend host) |
