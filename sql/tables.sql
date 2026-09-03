-- =============================================================================
-- Phase 1: RAW tables (+ stub CURATED / ANALYTICS / AI for later phases)
-- Source simulation:
--   CUSTOMERS_RAW  ← CRM
--   ORDERS_RAW     ← ERP / Order Management
--   PRODUCTS_RAW   ← Product Master
-- =============================================================================

USE DATABASE ANALYTICS_AI_DB;
USE SCHEMA RAW;

-- ---------------------------------------------------------------------------
-- CRM extract
-- ---------------------------------------------------------------------------
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
)
COMMENT = 'RAW CRM customer master extract';

-- ---------------------------------------------------------------------------
-- ERP / Order Management extract
-- ---------------------------------------------------------------------------
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
)
COMMENT = 'RAW ERP order line extract (all columns as VARCHAR for safe landing)';

-- ---------------------------------------------------------------------------
-- Product Master extract
-- ---------------------------------------------------------------------------
CREATE OR REPLACE TABLE PRODUCTS_RAW (
    PRODUCT_ID      VARCHAR(50),
    PRODUCT_NAME    VARCHAR(500),
    CATEGORY        VARCHAR(100),
    SUB_CATEGORY    VARCHAR(100),
    _LOADED_AT      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    _SOURCE_FILE    VARCHAR(500)
)
COMMENT = 'RAW Product Master extract';

-- Optional internal stage for PUT/COPY (local loader may also use write_pandas)
CREATE STAGE IF NOT EXISTS SUPERSTORE_STAGE
  COMMENT = 'Stage for Superstore CSV loads';
