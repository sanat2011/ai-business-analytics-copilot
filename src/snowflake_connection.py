"""
Snowflake connection helpers (Phase 4).

Supports:
  1. Snowflake-hosted Streamlit (SiS) — native active Snowpark session
  2. Local Streamlit — credentials from st.secrets["snowflake"] or .env
  3. Scripts / pytest — .env via python-dotenv

No credentials are hard-coded. Prefer read-only role for app queries.
"""

from __future__ import annotations

import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Default analytical context for the Copilot
DEFAULT_DATABASE = "ANALYTICS_AI_DB"
DEFAULT_SCHEMA = "ANALYTICS"
DEFAULT_ROLE = "ACCOUNTADMIN"  # switch to ANALYTICS_AI_READONLY after roles.sql

# Snowpark allows only one active Session per process; creating another closes the last.
_SESSION_LOCK = threading.Lock()
_LOCAL_SESSION = None


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass


def running_in_snowflake() -> bool:
    """True when code executes inside Snowflake (Streamlit / Notebook / SPCS)."""
    # SiS sets this; also detect active Snowpark session
    if os.getenv("SNOWFLAKE_ACCOUNT_LOCATOR") or os.getenv("SNOWFLAKE_HOST"):
        try:
            from snowflake.snowpark.context import get_active_session

            get_active_session()
            return True
        except Exception:
            pass
    try:
        from snowflake.snowpark.context import get_active_session

        get_active_session()
        return True
    except Exception:
        return False


def _secrets_snowflake() -> dict[str, Any]:
    """Read [snowflake] from Streamlit secrets when available."""
    try:
        import streamlit as st

        block = st.secrets.get("snowflake", None)
        if block is None:
            return {}
        return dict(block)
    except Exception:
        return {}


def _config() -> dict[str, str]:
    """Merge env + Streamlit secrets (secrets win for local Streamlit)."""
    _load_dotenv()
    secrets = _secrets_snowflake()

    def pick(*keys: str, default: str = "") -> str:
        for k in keys:
            if k in secrets and secrets[k] not in (None, ""):
                return str(secrets[k])
            env_key = k.upper() if k.startswith("snowflake") else f"SNOWFLAKE_{k.upper()}"
            # allow both SNOWFLAKE_ACCOUNT and account
            for candidate in (k, k.upper(), f"SNOWFLAKE_{k.upper()}", env_key):
                val = os.getenv(candidate)
                if val:
                    return val
        return default

    account = pick("account", default="")
    user = pick("user", default="")
    password = pick("password", default="")
    authenticator = pick("authenticator", default=os.getenv("SNOWFLAKE_AUTHENTICATOR", "password"))
    role = pick("role", default=os.getenv("SNOWFLAKE_ROLE", DEFAULT_ROLE))
    warehouse = pick("warehouse", default="")
    database = pick("database", default=os.getenv("SNOWFLAKE_DATABASE", DEFAULT_DATABASE))
    schema = pick("schema", default=os.getenv("SNOWFLAKE_SCHEMA", DEFAULT_SCHEMA))

    return {
        "account": account,
        "user": user,
        "password": password,
        "authenticator": (authenticator or "password").strip().lower(),
        "role": role,
        "warehouse": warehouse,
        "database": database,
        "schema": schema,
    }


def _connector_params(cfg: dict[str, str]) -> dict[str, Any]:
    missing = [k for k in ("account", "user", "warehouse") if not cfg.get(k)]
    if missing:
        raise ConnectionError(
            "Missing Snowflake settings: "
            + ", ".join(missing)
            + ". Set .env or .streamlit/secrets.toml [snowflake]."
        )

    params: dict[str, Any] = {
        "account": cfg["account"],
        "user": cfg["user"],
        "warehouse": cfg["warehouse"],
        "database": cfg["database"],
        "schema": cfg["schema"],
        "client_session_keep_alive": True,
    }
    if cfg.get("role"):
        params["role"] = cfg["role"]

    auth = cfg.get("authenticator") or "password"
    if auth in {"externalbrowser", "browser"}:
        params["authenticator"] = "externalbrowser"
    elif auth in {"snowflake", "password", ""}:
        if not cfg.get("password"):
            raise ConnectionError(
                "SNOWFLAKE_PASSWORD is required when authenticator=password."
            )
        params["password"] = cfg["password"]
    else:
        raise ConnectionError(
            f"Unsupported authenticator={auth!r}. Use password or externalbrowser."
        )
    return params


def _is_session_alive(session) -> bool:
    if session is None:
        return False
    try:
        conn = getattr(session, "connection", None)
        if conn is not None and getattr(conn, "is_closed", lambda: False)():
            return False
        session.sql("SELECT 1 AS OK").collect()
        return True
    except Exception:
        return False


def _create_local_session():
    from snowflake.snowpark import Session

    cfg = _config()
    params = _connector_params(cfg)
    return Session.builder.configs(params).create()


def reset_local_session() -> None:
    """Drop the cached local Snowpark session so the next call opens a new one."""
    global _LOCAL_SESSION
    with _SESSION_LOCK:
        if _LOCAL_SESSION is not None:
            try:
                _LOCAL_SESSION.close()
            except Exception:
                pass
            _LOCAL_SESSION = None


def get_session():
    """
    Return a Snowpark Session.

    Inside Snowflake Streamlit: reuses the active session.
    Local / Streamlit Cloud: reuse one process session (creating a second
    Snowpark Session closes the first — error 1404).
    """
    if running_in_snowflake():
        from snowflake.snowpark.context import get_active_session

        session = get_active_session()
        try:
            cfg = _config()
            if cfg.get("database"):
                session.use_database(cfg["database"])
            if cfg.get("schema"):
                session.use_schema(cfg["schema"])
            if cfg.get("warehouse"):
                session.use_warehouse(cfg["warehouse"])
        except Exception:
            pass
        return session

    global _LOCAL_SESSION
    with _SESSION_LOCK:
        if _is_session_alive(_LOCAL_SESSION):
            return _LOCAL_SESSION
        if _LOCAL_SESSION is not None:
            try:
                _LOCAL_SESSION.close()
            except Exception:
                pass
        _LOCAL_SESSION = _create_local_session()
        return _LOCAL_SESSION


def get_connection():
    """
    Return the connector connection backing the shared Snowpark session.

    Do not close this connection — that would kill the shared session.
    """
    return get_session().connection


def run_query(sql: str):
    """Execute SQL and return a pandas DataFrame. Read-path helper for later phases."""
    import pandas as pd

    session = get_session()
    return session.sql(sql).to_pandas()


def healthcheck() -> dict[str, Any]:
    """Lightweight connectivity probe for UI / ops."""
    info: dict[str, Any] = {
        "ok": False,
        "mode": "snowflake" if running_in_snowflake() else "local",
        "database": None,
        "schema": None,
        "warehouse": None,
        "role": None,
        "sales_rows": None,
        "error": None,
    }
    try:
        session = get_session()
        row = session.sql(
            """
            SELECT
              CURRENT_DATABASE()  AS DB,
              CURRENT_SCHEMA()    AS SCH,
              CURRENT_WAREHOUSE() AS WH,
              CURRENT_ROLE()      AS ROLE
            """
        ).collect()[0]
        info["database"] = row["DB"]
        info["schema"] = row["SCH"]
        info["warehouse"] = row["WH"]
        info["role"] = row["ROLE"]

        try:
            cnt = session.sql(
                "SELECT COUNT(*) AS N FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS"
            ).collect()[0]["N"]
            info["sales_rows"] = int(cnt)
        except Exception as exc:  # mart may not exist yet
            info["sales_rows"] = None
            info["error"] = f"Connected, but SALES_ANALYTICS not readable: {exc}"

        info["ok"] = True
        return info
    except Exception as exc:
        info["error"] = str(exc)
        return info


@lru_cache(maxsize=1)
def cached_healthcheck() -> dict[str, Any]:
    return healthcheck()


def clear_connection_cache() -> None:
    cached_healthcheck.cache_clear()
    if not running_in_snowflake():
        reset_local_session()
