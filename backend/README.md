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

## What changed from the original

- Implemented `waterlog_routes.py`/`waterlog_services.py`, which were stubs
  (`return` with nothing).
- Fixed `user_routes.py` calling services with `id` (Python's builtin) instead
  of the actual path parameter — this raised a `TypeError` on every
  get/update/delete user call.
- Fixed `tank_services.update_tank`, which had a dangling `setattr(tank, key, val)`
  statement left over from commented-out code, using undefined `key`/`val`.
- Fixed `waterlog_services.create_water_log` calling `db.refresh()` before
  `db.commit()` and `db.commit(log_db)` with an invalid argument.
- Added `owner_id` on tanks, unique/indexed email on users, and indexed
  `tank_id` foreign keys.
- Added feeding-log tracking, water-quality evaluation, and a tank summary
  endpoint as new features.
- Added `requirements.txt`, `config.py`, `.gitignore` (the `.db` file and
  `__pycache__` were previously being committed), and this README.
