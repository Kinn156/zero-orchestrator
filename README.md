# Deploy Dashboard

Full-stack dashboard to verify Supabase credentials, trigger Netlify deployments, and generate database table SQL from a prompt. Works with **mock responses** when keys are empty or prefixed with `mock`.

## Project structure

- `backend/` — FastAPI (`main.py`)
- `frontend/` — React + Vite + Tailwind CSS

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python main.py
```

API: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/verify-supabase` | Verify Supabase URL + key |
| POST | `/api/deploy-netlify` | Trigger Netlify deploy |
| POST | `/api/create-table` | Prompt → table name + SQL preview |

Set `FORCE_MOCK=1` to always use mock responses.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (proxies `/api` and `/health` to the backend)

Use **Fill mock credentials** on the dashboard to demo without real API keys.

## Notes

- **Supabase**: Live verification hits the REST root with your anon key. Table creation returns SQL to run in the Supabase SQL editor (anon keys cannot run DDL via REST by default).
- **Netlify**: Live deploy uses your token; if `site_id` is omitted, the first site on your account is used.
