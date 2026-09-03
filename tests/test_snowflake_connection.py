"""Unit tests for Phase 4 connection helpers (no live Snowflake required)."""

from __future__ import annotations

import src.snowflake_connection as sc


def test_running_in_snowflake_false_locally():
    assert sc.running_in_snowflake() is False


def test_connector_params_requires_password_for_password_auth():
    try:
        sc._connector_params(
            {
                "account": "x",
                "user": "u",
                "warehouse": "wh",
                "database": "db",
                "schema": "sch",
                "authenticator": "password",
                "password": "",
                "role": "ACCOUNTADMIN",
            }
        )
        assert False, "expected ConnectionError"
    except ConnectionError as exc:
        assert "PASSWORD" in str(exc).upper()


def test_connector_params_externalbrowser():
    params = sc._connector_params(
        {
            "account": "OSBBDNY-LKB20395",
            "user": "SANAT2011",
            "warehouse": "COMPUTE_WH",
            "database": "ANALYTICS_AI_DB",
            "schema": "ANALYTICS",
            "authenticator": "externalbrowser",
            "password": "",
            "role": "ACCOUNTADMIN",
        }
    )
    assert params["authenticator"] == "externalbrowser"
    assert "password" not in params
