# Deploy AI Business Analytics Copilot in Snowflake (Phase 14)

This app is designed to run as **Streamlit in Snowflake (SiS)** on a **warehouse** runtime,
backed by `ANALYTICS_AI_DB` and (optionally) a public GitHub repo.

GitHub repo: https://github.com/sanat2011/ai-business-analytics-copilot

---

## Prerequisites

1. Snowflake account with Streamlit enabled (Enterprise trial / student OK).
2. Warehouse: `COMPUTE_WH` (or any X-Small).
3. Database objects already created and loaded (Phases 1–3):
   - `ANALYTICS_AI_DB.RAW.*`
   - `ANALYTICS_AI_DB.CURATED.*`
   - `ANALYTICS_AI_DB.ANALYTICS.*`
   - `ANALYTICS_AI_DB.AI.*` (glossary, metadata, sample questions, query log)
4. Role that can create Streamlit apps (typically `ACCOUNTADMIN` for MVP).

If data is not loaded yet, from a local machine with credentials:

```bash
python scripts/prepare_data.py --generate
python scripts/load_data.py --with-phase2
python scripts/run_phase3.py
```

Or use the Snowsight SQL path in `docs/SNOWSIGHT_LOAD.md`.

---

## Recommended UI selections (Snowsight)

| Field | Value |
|-------|--------|
| Runtime | **Run on Warehouse** (not Container) |
| Warehouse | `COMPUTE_WH` |
| Database | `ANALYTICS_AI_DB` |
| Schema | `AI` |
| Main file | `streamlit_app.py` |
| Query warehouse | `COMPUTE_WH` |
| App name | `AI_BUSINESS_ANALYTICS_COPILOT` |

---

## Option A — Create from GitHub (preferred)

### 1. API integration (once per account)

```sql
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE API INTEGRATION GITHUB_API_INTEGRATION
  API_PROVIDER = GIT_HTTPS_API
  API_ALLOWED_PREFIXES = ('https://github.com/sanat2011')
  ENABLED = TRUE;
```

### 2. Clone the Git repository in Snowflake

Snowsight → **Projects** → **Git Repositories** → **Clone repository**

| Field | Value |
|-------|--------|
| Origin URL | `https://github.com/sanat2011/ai-business-analytics-copilot` |
| Integration | `GITHUB_API_INTEGRATION` |
| Database | `ANALYTICS_AI_DB` |
| Schema | `AI` |
| Repository name | `AI_ANALYTICS_COPILOT_REPO` |
| Branch | `main` |

Public repo usually needs no personal access token.

Fetch latest whenever you push to GitHub:

```sql
ALTER GIT REPOSITORY ANALYTICS_AI_DB.AI.AI_ANALYTICS_COPILOT_REPO FETCH;
```

### 3. Create the Streamlit app from the Git repo

Snowsight → **Projects** → **Streamlit** → **+ Streamlit App**

- Choose **from Git repository**
- Select `AI_ANALYTICS_COPILOT_REPO` / `main`
- Main file: **`streamlit_app.py`**
- Runtime: **Warehouse**
- Location: `ANALYTICS_AI_DB.AI`
- Warehouse: `COMPUTE_WH`

### 4. Packages

SiS reads `environment.yml` from the repo root:

- `snowflake-snowpark-python`
- `streamlit`
- `pandas` / `numpy` / `plotly`
- `python-dotenv` (harmless in SiS; credentials come from the active session)

---

## Option B — Upload / create without Git

1. Create an empty Streamlit app in `ANALYTICS_AI_DB.AI`.
2. Paste / sync files so the app root contains at least:
   - `streamlit_app.py`
   - `app.py`
   - `environment.yml`
   - `src/` (entire package)
3. Set main file to `streamlit_app.py`.

Git is strongly preferred so Snowflake stays in sync with GitHub.

---

## Grants (read-only app role)

Run as `ACCOUNTADMIN` after objects exist:

```sql
-- see sql/streamlit_grants.sql
```

MVP tip: you can run the Streamlit app as `ACCOUNTADMIN` first to confirm it works,
then switch the app owner/viewer role to `ANALYTICS_AI_READONLY`.

---

## Authentication inside SiS

No `.env` password is required in Snowflake.

`src/snowflake_connection.py` detects the active Snowpark session via
`get_active_session()` and runs queries as the Streamlit viewer’s role.

Local development still uses `.env` / Streamlit secrets.

---

## Cortex (optional)

For NL→SQL / insights via Cortex, set the sidebar SQL engine to **snowflake_cortex**
(or set `LLM_PROVIDER=snowflake_cortex` in local `.env`).

Ensure your role can call Cortex:

```sql
-- Account-dependent; often enabled on modern trials
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ACCOUNTADMIN;
```

If Cortex is unavailable, keep **heuristic** selected — the MVP still works.

---

## Acceptance checklist

After deploy, verify:

1. App opens without import errors.
2. Sidebar shows **Connected (snowflake)**.
3. Click **Top 10 Products by Revenue** → chart + table + insight + View SQL.
4. Ask follow-up: **Now show their profit.** → context-aware SQL.
5. Ask **What is our employee attrition?** → insufficient-data message (no hallucination).
6. Destructive SQL cannot run (validator rejects non-SELECT).
7. Optional: `SELECT * FROM ANALYTICS_AI_DB.AI.QUERY_LOG ORDER BY TS DESC LIMIT 20;`

---

## Sync workflow

```text
Local code change
  → git commit / push to GitHub main
  → ALTER GIT REPOSITORY ... FETCH;
  → Refresh / redeploy Streamlit app from Git
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: src` | Ensure `src/` is in the Git root synced to the app; `streamlit_app.py` adds project root to `sys.path`. |
| Main file not found | Select `streamlit_app.py` (not only `app.py`). |
| Plotly missing | Confirm `environment.yml` includes `plotly` and rebuild/refresh the app. |
| Password / SAML errors | Only affect **local** runs. SiS uses the active session. |
| Empty marts | Re-run Phase 2/3 load (`run_phase2.py`, `run_phase3.py`) or Snowsight SQL. |
| Cortex errors | Switch sidebar engine to `heuristic`. |

---

## User access

```sql
GRANT USAGE ON DATABASE ANALYTICS_AI_DB TO ROLE ANALYTICS_AI_READONLY;
GRANT USAGE ON SCHEMA ANALYTICS_AI_DB.AI TO ROLE ANALYTICS_AI_READONLY;
GRANT USAGE ON STREAMLIT ANALYTICS_AI_DB.AI.AI_BUSINESS_ANALYTICS_COPILOT TO ROLE ANALYTICS_AI_READONLY;
GRANT ROLE ANALYTICS_AI_READONLY TO USER <business_user>;
```

Share the Streamlit app URL from Snowsight with viewers who have the role.
