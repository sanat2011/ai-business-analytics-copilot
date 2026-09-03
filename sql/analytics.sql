-- =============================================================================
-- Phase 2: ANALYTICS marts
-- =============================================================================

USE DATABASE ANALYTICS_AI_DB;
USE SCHEMA ANALYTICS;

-- Grain: one row per order line with denormalized customer + product attributes
CREATE OR REPLACE TABLE SALES_ANALYTICS AS
SELECT
    o.ORDER_ID,
    o.ORDER_DATE,
    DATE_TRUNC('MONTH', o.ORDER_DATE)              AS ORDER_MONTH,
    YEAR(o.ORDER_DATE)                             AS ORDER_YEAR,
    o.SHIP_DATE,
    o.SHIP_MODE,
    o.CUSTOMER_ID,
    c.CUSTOMER_NAME,
    c.SEGMENT,
    c.COUNTRY,
    c.STATE,
    c.CITY,
    c.REGION,
    o.PRODUCT_ID,
    p.PRODUCT_NAME,
    p.CATEGORY,
    p.SUB_CATEGORY,
    o.QUANTITY,
    o.SALES,
    o.DISCOUNT,
    o.PROFIT,
    CASE
        WHEN o.SALES IS NULL OR o.SALES = 0 THEN NULL
        ELSE o.PROFIT / NULLIF(o.SALES, 0)
    END                                            AS PROFIT_MARGIN,
    CURRENT_TIMESTAMP()                            AS _BUILT_AT
FROM ANALYTICS_AI_DB.CURATED.ORDERS o
LEFT JOIN ANALYTICS_AI_DB.CURATED.CUSTOMERS c
    ON o.CUSTOMER_ID = c.CUSTOMER_ID
LEFT JOIN ANALYTICS_AI_DB.CURATED.PRODUCTS p
    ON o.PRODUCT_ID = p.PRODUCT_ID;

-- Grain: one row per customer
CREATE OR REPLACE TABLE CUSTOMER_ANALYTICS AS
SELECT
    c.CUSTOMER_ID,
    c.CUSTOMER_NAME,
    c.SEGMENT,
    c.COUNTRY,
    c.STATE,
    c.CITY,
    c.REGION,
    COUNT(DISTINCT o.ORDER_ID)                     AS ORDER_COUNT,
    COALESCE(SUM(o.QUANTITY), 0)                   AS TOTAL_QUANTITY,
    COALESCE(SUM(o.SALES), 0)                      AS TOTAL_SALES,
    COALESCE(SUM(o.PROFIT), 0)                     AS TOTAL_PROFIT,
    CASE
        WHEN COUNT(DISTINCT o.ORDER_ID) = 0 THEN NULL
        ELSE SUM(o.SALES) / NULLIF(COUNT(DISTINCT o.ORDER_ID), 0)
    END                                            AS AVG_ORDER_VALUE,
    CASE
        WHEN COALESCE(SUM(o.SALES), 0) = 0 THEN NULL
        ELSE SUM(o.PROFIT) / NULLIF(SUM(o.SALES), 0)
    END                                            AS PROFIT_MARGIN,
    MIN(o.ORDER_DATE)                              AS FIRST_ORDER_DATE,
    MAX(o.ORDER_DATE)                              AS LAST_ORDER_DATE,
    CURRENT_TIMESTAMP()                            AS _BUILT_AT
FROM ANALYTICS_AI_DB.CURATED.CUSTOMERS c
LEFT JOIN ANALYTICS_AI_DB.CURATED.ORDERS o
    ON c.CUSTOMER_ID = o.CUSTOMER_ID
GROUP BY
    c.CUSTOMER_ID,
    c.CUSTOMER_NAME,
    c.SEGMENT,
    c.COUNTRY,
    c.STATE,
    c.CITY,
    c.REGION;

-- Grain: one row per product
CREATE OR REPLACE TABLE PRODUCT_ANALYTICS AS
SELECT
    p.PRODUCT_ID,
    p.PRODUCT_NAME,
    p.CATEGORY,
    p.SUB_CATEGORY,
    COUNT(DISTINCT o.ORDER_ID)                     AS ORDER_COUNT,
    COALESCE(SUM(o.QUANTITY), 0)                   AS TOTAL_QUANTITY,
    COALESCE(SUM(o.SALES), 0)                      AS TOTAL_SALES,
    COALESCE(SUM(o.PROFIT), 0)                     AS TOTAL_PROFIT,
    CASE
        WHEN COALESCE(SUM(o.SALES), 0) = 0 THEN NULL
        ELSE SUM(o.PROFIT) / NULLIF(SUM(o.SALES), 0)
    END                                            AS PROFIT_MARGIN,
    CURRENT_TIMESTAMP()                            AS _BUILT_AT
FROM ANALYTICS_AI_DB.CURATED.PRODUCTS p
LEFT JOIN ANALYTICS_AI_DB.CURATED.ORDERS o
    ON p.PRODUCT_ID = o.PRODUCT_ID
GROUP BY
    p.PRODUCT_ID,
    p.PRODUCT_NAME,
    p.CATEGORY,
    p.SUB_CATEGORY;

ALTER TABLE SALES_ANALYTICS    SET COMMENT = 'Denormalized order-line sales facts for AI SQL';
ALTER TABLE CUSTOMER_ANALYTICS SET COMMENT = 'Customer-level revenue and profit aggregates';
ALTER TABLE PRODUCT_ANALYTICS  SET COMMENT = 'Product-level revenue and profit aggregates';
