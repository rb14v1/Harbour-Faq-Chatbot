# FAQ Chatbot

A single-user-role FAQ chatbot: curate FAQ question/answer pairs, then ask
natural-language questions and get an answer grounded in the most similar
FAQ entries (retrieval-augmented generation / RAG), via a REST API consumed
by a React frontend.

Stack: React + Vite (frontend), Django REST Framework (backend),
PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) (vector
storage/search). No Celery/Redis — there is no background or async work in
this app.

## Stub-by-default AI layer

No OpenAI API key is required to run or test this app. `backend/apps/common/ai.py`
has two functions, each with a real path and a stub path:

- `get_embedding(text)` — with `OPENAI_API_KEY` set, calls OpenAI's embeddings
  API (`OPENAI_EMBEDDING_MODEL`, default `text-embedding-3-large`, truncated
  to `OPENAI_EMBEDDING_DIMENSIONS` via OpenAI's `dimensions` param, default
  1536). Without a key, returns a **deterministic pseudo-random vector**
  seeded from a SHA-256 hash of the text. This makes embedding generation
  reproducible and the whole pipeline (embed → store → similarity search →
  answer) fully testable with no network access or API cost — **but the stub
  vector has no relationship to the text's actual meaning**. Similarity
  search over stub embeddings will not return semantically relevant results;
  real search quality requires a real `OPENAI_API_KEY`.
- `generate_answer(question, context_snippets)` — with a key set, calls
  OpenAI's chat completions API (`OPENAI_CHAT_MODEL`, default `gpt-5.6-sol`,
  wired through exactly as configured — this model name is unverified in
  this environment). Without a key, returns a templated string, e.g.
  `[STUB AI RESPONSE — set OPENAI_API_KEY for real output] Found 3 related FAQ(s). Top match: ...`.

The frontend's Ask page shows a "running in stub mode" banner whenever the
returned answer carries the stub marker.

## Vector storage: Postgres (pgvector) vs. SQLite (dev-only)

`backend/apps/common/embedding_field.py` defines `EmbeddingField()`, a
factory returning:

- **Postgres**: `pgvector.django.VectorField(dimensions=EMBEDDING_DIMENSIONS)`.
  Requires the `vector` Postgres extension, created automatically by a
  `RunPython` guard in `apps/faqs/migrations/0001_initial.py` (`CREATE
  EXTENSION IF NOT EXISTS vector;`, skipped on non-Postgres backends).
- **SQLite** (dev-only, `USE_SQLITE=True`): a plain `JSONField` storing a
  list of floats, since pgvector has no SQLite backend.

`backend/apps/common/vector_search.py` provides `similarity_search(queryset,
query_vector, top_k, field_name='embedding')` with the same signature either
way: on Postgres it delegates ranking to `pgvector.django.CosineDistance` in
an `.order_by()` clause (DB-side, index-friendly); on SQLite it pulls
candidates into Python and computes cosine similarity directly. Both return
the top-k instances, nearest-first, each with a `.similarity_score`
attribute attached.

**This repository's local Postgres does not have pgvector installed yet**
(handled by a separate setup step, not part of this app's build). Everything
in this repo has been verified end-to-end against SQLite via `USE_SQLITE=True`;
the Postgres/pgvector code path is written to the same contract but has not
been run against a live Postgres here. See "Verification status" below.

## Data model

- `User` (`apps/accounts`) — email-based login, single role (no admin/staff
  distinction beyond Django's own `is_staff`/`is_superuser` for `/admin/`).
- `FAQEntry` (`apps/faqs`) — `user` FK (owner/curator), `question`, `answer`,
  `embedding` (of `question + "\n" + answer`, recomputed on every create or
  edit that touches `question`/`answer`), `created_at`, `updated_at`.
- `ChatLog` (`apps/faqs`) — `user` FK, `question_asked`, `generated_answer`,
  `matched_faq_ids` (JSON list of `FAQEntry` ids used as context),
  `created_at`. A read-only history of asked questions.

Every queryset in the app is scoped to `user=request.user` — FAQ entries,
chat logs, and `/api/ask/`'s candidate pool never cross user boundaries (see
cross-user isolation tests in `apps/faqs/tests/`).

### Seed data

`apps/faqs/migrations/0002_seed_demo_data.py` is an idempotent data
migration (`get_or_create` keyed on user email / `(user, question)`, safe to
re-run) that creates:

- A demo user: `demo@example.com` / `demo12345`
- 15 FAQ entries on a single coherent topic — a SaaS product's
  billing/account support FAQs (upgrades, downgrades, payment methods,
  invoices, cancellation, refunds, password/email changes, team seats,
  account deletion, failed payments, usage limits) — chosen so that a demo
  question (e.g. "How do I cancel my plan?") has plausible nearest matches.

Each seeded entry's embedding is computed via the same `get_embedding`
function used at request time (stub vectors, since no API key is configured
in this environment).

## REST API

All endpoints except registration/login/refresh require a JWT access token
(`Authorization: Bearer <token>`).

- `POST /api/auth/register/`
- `POST /api/auth/login/` — returns `{access, refresh}`
- `POST /api/auth/refresh/`
- `POST /api/auth/logout/` — blacklists the given refresh token
- `GET /api/auth/me/`
- `GET/POST /api/faqs/`, `GET/PUT/PATCH/DELETE /api/faqs/{id}/` — FAQ entry
  CRUD, scoped to the authenticated user
- `POST /api/ask/` — `{"question": "..."}` → embeds the question, finds the
  user's own top-`ASK_TOP_K` (default 3) most similar FAQ entries, generates
  an answer grounded in them, logs the exchange, and returns
  `{answer, matched_faqs: [{id, question, answer, score}]}`
- `GET /api/chat-logs/`, `GET /api/chat-logs/{id}/` — read-only history of
  the user's own `/api/ask/` requests

## Running with Docker (Postgres + pgvector)

```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://localhost:5173 — Backend: http://localhost:8000/api —
Django admin: http://localhost:8000/admin/.

## Running the backend without Docker (dev-only SQLite)

For environments without Postgres/pgvector available (e.g. this sandbox),
`USE_SQLITE=True` switches the whole app to SQLite with a JSONField-based
embedding column, per `apps/common/embedding_field.py`. Never set this in
production or docker-compose.

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv/bin/activate on macOS/Linux
pip install -r requirements.txt

export USE_SQLITE=True
export DJANGO_SETTINGS_MODULE=config.settings.dev

python manage.py migrate      # applies schema + seed data migration
python manage.py test         # full test suite
python manage.py runserver
```

## Running the frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
npm run build   # production build
```

## Verification status (this environment)

Verified locally (Python 3.12, Node 22, SQLite dev mode — no Docker/Postgres/
pgvector available here):

| Check | Result |
|---|---|
| `pip install -r requirements.txt` | pass |
| `manage.py check` | pass, 0 issues |
| `manage.py makemigrations --check --dry-run` | pass, no changes detected |
| `manage.py migrate` | pass — creates schema + seeds demo user and 15 FAQ entries, each with a 1536-length embedding |
| `manage.py migrate` (second run) | pass — idempotent, no duplicate rows |
| `manage.py test` (36 tests) | pass — embedding stub determinism, `similarity_search` ranking correctness against known vectors, cross-user isolation (FAQ entries, chat logs, `/api/ask/`), `/api/ask/` stub answer format + `ChatLog` creation, seed migration row/embedding counts |
| `npm install` | pass |
| `npm run build` (`tsc -b && vite build`) | pass |

**Not verified here** (pgvector is not yet installed on the local Postgres —
handled by a separate setup step, not part of this app's build):

- Running `docker compose up` end to end against real Postgres + pgvector
- The `CREATE EXTENSION IF NOT EXISTS vector;` migration guard actually
  running against Postgres
- `pgvector.django.VectorField` schema creation and `CosineDistance`-based
  ranking in `similarity_search()` against a live Postgres database
- Any ANN/ivfflat/hnsw indexing or performance characteristics on pgvector

Once pgvector is available, the recommended check is: `USE_SQLITE=False`,
run `docker compose up --build` (or point `manage.py migrate`/`test` at a
local Postgres with pgvector installed) and confirm `manage.py test` still
passes — the test suite itself is backend-agnostic since `vector_search.py`
and `embedding_field.py` both branch on `settings.USE_SQLITE`.
