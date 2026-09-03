-- =============================================================================
-- Phase 2: CURATED entity tables (typed, cleaned)
-- =============================================================================

USE DATABASE ANALYTICS_AI_DB;
USE SCHEMA CURATED;

CREATE OR REPLACE TABLE CUSTOMERS AS
SELECT
    TRIM(CUSTOMER_ID)                              AS CUSTOMER_ID,
    TRIM(CUSTOMER_NAME)                            AS CUSTOMER_NAME,
    TRIM(SEGMENT)                                  AS SEGMENT,
    TRIM(COUNTRY)                                  AS COUNTRY,
    TRIM(STATE)                                    AS STATE,
    TRIM(CITY)                                     AS CITY,
    TRIM(POSTAL_CODE)                              AS POSTAL_CODE,
    TRIM(REGION)                                   AS REGION,
    CURRENT_TIMESTAMP()                            AS _CURATED_AT
FROM ANALYTICS_AI_DB.RAW.CUSTOMERS_RAW
WHERE CUSTOMER_ID IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRIM(CUSTOMER_ID)
    ORDER BY _LOADED_AT DESC NULLS LAST
) = 1;

CREATE OR REPLACE TABLE PRODUCTS AS
SELECT
    TRIM(PRODUCT_ID)                               AS PRODUCT_ID,
    TRIM(PRODUCT_NAME)                             AS PRODUCT_NAME,
    TRIM(CATEGORY)                                 AS CATEGORY,
    TRIM(SUB_CATEGORY)                             AS SUB_CATEGORY,
    CURRENT_TIMESTAMP()                            AS _CURATED_AT
FROM ANALYTICS_AI_DB.RAW.PRODUCTS_RAW
WHERE PRODUCT_ID IS NOT NULL
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY TRIM(PRODUCT_ID)
    ORDER BY _LOADED_AT DESC NULLS LAST
) = 1;

CREATE OR REPLACE TABLE ORDERS AS
SELECT
    TRIM(ORDER_ID)                                 AS ORDER_ID,
    TRY_TO_DATE(ORDER_DATE)                        AS ORDER_DATE,
    TRY_TO_DATE(SHIP_DATE)                         AS SHIP_DATE,
    TRIM(SHIP_MODE)                                AS SHIP_MODE,
    TRIM(CUSTOMER_ID)                              AS CUSTOMER_ID,
    TRIM(PRODUCT_ID)                               AS PRODUCT_ID,
    TRY_TO_NUMBER(QUANTITY)                        AS QUANTITY,
    TRY_TO_NUMBER(SALES)                           AS SALES,
    TRY_TO_NUMBER(DISCOUNT)                        AS DISCOUNT,
    TRY_TO_NUMBER(PROFIT)                          AS PROFIT,
    CURRENT_TIMESTAMP()                            AS _CURATED_AT
FROM ANALYTICS_AI_DB.RAW.ORDERS_RAW
WHERE ORDER_ID IS NOT NULL
  AND CUSTOMER_ID IS NOT NULL
  AND PRODUCT_ID IS NOT NULL;

-- Helpful comments
ALTER TABLE CUSTOMERS SET COMMENT = 'Curated CRM customer master';
ALTER TABLE PRODUCTS  SET COMMENT = 'Curated product master';
ALTER TABLE ORDERS    SET COMMENT = 'Curated order lines with typed dates/metrics';
