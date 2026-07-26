# BANGUS BUHAI — Backend

FastAPI + SQLModel backend for tracking bangus (milkfish) grow-out tanks: water
quality, feeding, and per-tank summaries.

## Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The API serves at `http://127.0.0.1:8000`, interactive docs at `/docs`.

Optional `.env` file (see `config.py`) to override:

```
CORS_ORIGINS=http://localhost:5174,http://localhost:5173
DATABASE_URL=sqlite:///./database/bangusbuhai.db
```

## Endpoints

| Resource | Routes |
|---|---|
| Users | `POST/GET /users/`, `GET/PUT/DELETE /users/{id}` |
| Tanks | `POST/GET /tanks/`, `GET/PUT/DELETE /tanks/{id}`, `GET /tanks/{id}/summary` |
| Water logs | `POST/GET /tanks/{id}/logs`, `GET/PUT/DELETE /tanks/{id}/logs/{log_id}`, `GET /tanks/logs/all` |
| Feeding logs | `POST/GET /tanks/{id}/feedings`, `GET/DELETE /tanks/{id}/feedings/{feeding_id}` |
| Health | `GET /health` |

## Water quality status

Every water log response includes a computed `status` (`optimal` / `warning` /
`critical`) and human-readable `warnings`, based on general milkfish culture
thresholds (temperature, pH, turbidity) — see `services/water_quality.py`.
These are sane defaults, not a substitute for site-specific guidance.

