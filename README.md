# DineBot — FastAPI + React + SQLite Table Booking Chatbot

A lightweight restaurant discovery and table-booking chatbot web app:
1. User logs in (or registers / uses the demo account).
2. Chatbot displays nearby restaurants sorted by distance.
3. User selects a restaurant to inspect its menu and per-dish nutrient values (`calories_kcal`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`).
4. User can like dishes and proceed to book a table, go back to pick another restaurant, or exit without booking.

## Project Structure

- `backend/` — FastAPI async API (`aiosqlite`, SQLite WAL mode, JWT auth, OpenRouter LLM for chat + AI-fetched dish ingredients/nutrients with SQLite caching, bounding-box + Haversine nearby query, atomic `BEGIN IMMEDIATE` table booking).
- `frontend/` — Responsive Material UI (MUI) WhatsApp-style chat interface (`useState`, `useEffect`, plain `fetch()` in `src/api.js`) with embedded EazyDiner-style restaurant, ingredient/nutrient menu, and booking cards.

## OpenRouter AI Configuration

Copy `backend/.env.example` to `backend/.env` and set your `OPENROUTER_API_KEY` (already configured locally in `backend/.env` and git-ignored):

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.5-flash-lite
```

DineBot uses `google/gemini-2.5-flash-lite` with compact JSON prompts, `max_tokens` caps, and SQLite persistence so each restaurant's ingredients and nutrient values are fetched once and cached. If `OPENROUTER_API_KEY` is omitted, it falls back to local Ollama or deterministic matching.

## Running Locally

### 1. Backend (FastAPI)

From `C:\Users\sathw\Desktop\chatbot_paysmart`:

```bat
.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload --port 8000
```

API docs will be at `http://127.0.0.1:8000/docs`.

### 2. Frontend (React + Vite)

In a second terminal:

```bat
cd C:\Users\sathw\Desktop\chatbot_paysmart\frontend
npm install
npm run dev
```

*(If using PowerShell and `npm.ps1` is blocked, use `npm.cmd install` and `npm.cmd run dev`.)*

Open `http://localhost:5173`. Demo credentials: `demo@dinebot.com` / `demo1234`.

## Running Tests

```powershell
cd C:\Users\sathw\Desktop\chatbot_paysmart
.\.venv\Scripts\pytest.exe backend\tests -v
```
