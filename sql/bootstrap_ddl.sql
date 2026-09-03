-- =============================================================================
-- Snowsight bootstrap: Phase 1 DDL + Phase 2 CURATED/ANALYTICS
-- Run this entire worksheet as ACCOUNTADMIN with warehouse COMPUTE_WH.
-- Then run sql/load_raw_data.sql to load rows (or use scripts/load_data.py).
-- =============================================================================

-- Phase 1: database + schemas + RAW tables
CREATE DATABASE IF NOT EXISTS ANALYTICS_AI_DB
  COMMENT = 'AI Business Analytics Copilot — retail Superstore demo';

USE DATABASE ANALYTICS_AI_DB;

CREATE SCHEMA IF NOT EXISTS RAW
  COMMENT = 'Landing zone for source system extracts (CRM, ERP, Product Master)';

CREATE SCHEMA IF NOT EXISTS CURATED
  COMMENT = 'Cleaned, typed, deduplicated business entities';

CREATE SCHEMA IF NOT EXISTS ANALYTICS
  COMMENT = 'Curated analytics marts for BI and AI SQL generation';

CREATE SCHEMA IF NOT EXISTS AI
  COMMENT = 'Semantic metadata, business glossary, sample questions, query logs';

USE SCHEMA RAW;

CREATE OR REPLACE TABLE CUSTOMERS_RAW (
    CUSTOMER_ID     VARCHAR(50),
    CUSTOMER_NAME   VARCHAR(200),
    SEGMENT         VARCHAR(50),
    COUNTRY         VARCHAR(100),
    STATE           VARCHAR(100),
    CITY            VARCHAR(100),
    POSTAL_CODE     VARCHAR(20),
    REGION          VARCHAR(50),
    _LOADED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _SOURCE_FILE    VARCHAR(500)
);

CREATE OR REPLACE TABLE ORDERS_RAW (
    ORDER_ID        VARCHAR(50),
    ORDER_DATE      VARCHAR(50),
    SHIP_DATE       VARCHAR(50),
    SHIP_MODE       VARCHAR(50),
    CUSTOMER_ID     VARCHAR(50),
    PRODUCT_ID      VARCHAR(50),
    QUANTITY        VARCHAR(50),
    SALES           VARCHAR(50),
    DISCOUNT        VARCHAR(50),
    PROFIT          VARCHAR(50),
    _LOADED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _SOURCE_FILE    VARCHAR(500)
);

CREATE OR REPLACE TABLE PRODUCTS_RAW (
    PRODUCT_ID      VARCHAR(50),
    PRODUCT_NAME    VARCHAR(500),
    CATEGORY        VARCHAR(100),
    SUB_CATEGORY    VARCHAR(100),
    _LOADED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _SOURCE_FILE    VARCHAR(500)
);

CREATE STAGE IF NOT EXISTS SUPERSTORE_STAGE;

-- After loading RAW data (load_raw_data.sql or Python loader), run:
--   sql/curated.sql
--   sql/analytics.sql
--   sql/views.sql
-- Or open sql/phase2_transform.sql (same content bundled below is applied separately).

SELECT 'DDL ready — next load RAW data' AS STATUS;
