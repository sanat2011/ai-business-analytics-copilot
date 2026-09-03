-- =============================================================================
-- Phase 3: AI semantic layer — glossary, table/column metadata, sample questions
-- =============================================================================

USE DATABASE ANALYTICS_AI_DB;
USE SCHEMA AI;

CREATE OR REPLACE TABLE BUSINESS_GLOSSARY (
    TERM            VARCHAR(100)  NOT NULL,
    DEFINITION_SQL  VARCHAR(1000) NOT NULL,
    DESCRIPTION     VARCHAR(2000),
    RELATED_TABLES  VARCHAR(500),
    UNIT            VARCHAR(50),
    PRIMARY KEY (TERM)
)
COMMENT = 'Canonical business metric definitions for NL→SQL';

CREATE OR REPLACE TABLE TABLE_METADATA (
    TABLE_SCHEMA    VARCHAR(100)  NOT NULL,
    TABLE_NAME      VARCHAR(100)  NOT NULL,
    COLUMN_NAME     VARCHAR(100)  NOT NULL DEFAULT '',  -- '' = table-level description
    DATA_TYPE       VARCHAR(100),
    DESCRIPTION     VARCHAR(2000) NOT NULL,
    IS_KEY          BOOLEAN DEFAULT FALSE,
    EXAMPLE_VALUES  VARCHAR(500),
    PRIMARY KEY (TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME)
)
COMMENT = 'Semantic descriptions of analytics tables and columns';

CREATE OR REPLACE TABLE SAMPLE_QUESTIONS (
    QUESTION_ID     NUMBER AUTOINCREMENT,
    CATEGORY        VARCHAR(100),
    QUESTION        VARCHAR(1000) NOT NULL,
    EXPECTED_TABLES VARCHAR(500),
    EXPECTED_METRIC VARCHAR(200),
    SORT_ORDER      NUMBER DEFAULT 0
)
COMMENT = 'Default / suggested analytics questions for the Streamlit UI';

CREATE OR REPLACE TABLE QUERY_LOG (
    LOG_ID              NUMBER AUTOINCREMENT,
    TS                  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    USER_QUESTION       VARCHAR(4000),
    GENERATED_SQL       VARCHAR(8000),
    EXECUTION_STATUS    VARCHAR(50),
    EXECUTION_TIME_MS   NUMBER,
    ROW_COUNT           NUMBER,
    ERROR_MESSAGE       VARCHAR(4000),
    VISUALIZATION_TYPE  VARCHAR(100)
)
COMMENT = 'AI query observability log';

-- ---------------------------------------------------------------------------
-- Business glossary
-- ---------------------------------------------------------------------------
TRUNCATE TABLE IF EXISTS BUSINESS_GLOSSARY;
INSERT INTO BUSINESS_GLOSSARY (TERM, DEFINITION_SQL, DESCRIPTION, RELATED_TABLES, UNIT) VALUES
('Revenue',
 'SUM(orders.sales)',
 'Total sales amount across order lines. Synonyms: sales, revenue, turnover.',
 'CURATED.ORDERS, ANALYTICS.SALES_ANALYTICS',
 'currency'),
('Profit',
 'SUM(orders.profit)',
 'Total profit across order lines.',
 'CURATED.ORDERS, ANALYTICS.SALES_ANALYTICS',
 'currency'),
('Quantity',
 'SUM(orders.quantity)',
 'Total units sold across order lines.',
 'CURATED.ORDERS, ANALYTICS.SALES_ANALYTICS',
 'units'),
('Order Count',
 'COUNT(DISTINCT orders.order_id)',
 'Number of distinct orders.',
 'CURATED.ORDERS, ANALYTICS.SALES_ANALYTICS',
 'count'),
('Customer Count',
 'COUNT(DISTINCT customers.customer_id)',
 'Number of distinct customers.',
 'CURATED.CUSTOMERS, ANALYTICS.CUSTOMER_ANALYTICS',
 'count'),
('Average Order Value',
 'SUM(orders.sales) / NULLIF(COUNT(DISTINCT orders.order_id), 0)',
 'Average revenue per distinct order (AOV).',
 'CURATED.ORDERS, ANALYTICS.SALES_ANALYTICS',
 'currency'),
('Profit Margin',
 'SUM(orders.profit) / NULLIF(SUM(orders.sales), 0)',
 'Profit as a share of revenue. Always use NULLIF to avoid divide-by-zero.',
 'CURATED.ORDERS, ANALYTICS.SALES_ANALYTICS',
 'ratio');

-- ---------------------------------------------------------------------------
-- Table + column metadata (prefer ANALYTICS marts for AI queries)
-- ---------------------------------------------------------------------------
TRUNCATE TABLE IF EXISTS TABLE_METADATA;

-- SALES_ANALYTICS
INSERT INTO TABLE_METADATA (TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, DESCRIPTION, IS_KEY, EXAMPLE_VALUES) VALUES
('ANALYTICS', 'SALES_ANALYTICS', '', NULL,
 'Denormalized order-line fact table joining orders, customers, and products. Preferred source for most revenue/profit questions.',
 FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'ORDER_ID', 'VARCHAR', 'Business order identifier (may repeat across lines).', TRUE, 'CA-2024-100000'),
('ANALYTICS', 'SALES_ANALYTICS', 'ORDER_DATE', 'DATE', 'Date the order was placed.', FALSE, '2024-06-15'),
('ANALYTICS', 'SALES_ANALYTICS', 'ORDER_MONTH', 'DATE', 'Month truncated from ORDER_DATE for time-series.', FALSE, '2024-06-01'),
('ANALYTICS', 'SALES_ANALYTICS', 'ORDER_YEAR', 'NUMBER', 'Calendar year of the order.', FALSE, '2023,2024'),
('ANALYTICS', 'SALES_ANALYTICS', 'CUSTOMER_ID', 'VARCHAR', 'Customer key linking to CUSTOMER_ANALYTICS.', TRUE, 'CG-10000'),
('ANALYTICS', 'SALES_ANALYTICS', 'CUSTOMER_NAME', 'VARCHAR', 'Customer display name.', FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'SEGMENT', 'VARCHAR', 'Customer segment: Consumer, Corporate, Home Office.', FALSE, 'Consumer'),
('ANALYTICS', 'SALES_ANALYTICS', 'REGION', 'VARCHAR', 'Geographic region: West, East, Central, South.', FALSE, 'West'),
('ANALYTICS', 'SALES_ANALYTICS', 'STATE', 'VARCHAR', 'US state associated with the customer.', FALSE, 'California'),
('ANALYTICS', 'SALES_ANALYTICS', 'CITY', 'VARCHAR', 'City associated with the customer.', FALSE, 'Los Angeles'),
('ANALYTICS', 'SALES_ANALYTICS', 'PRODUCT_ID', 'VARCHAR', 'Product key linking to PRODUCT_ANALYTICS.', TRUE, 'TEC-PH-10002075'),
('ANALYTICS', 'SALES_ANALYTICS', 'PRODUCT_NAME', 'VARCHAR', 'Product display name.', FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'CATEGORY', 'VARCHAR', 'High-level product category.', FALSE, 'Furniture,Office Supplies,Technology'),
('ANALYTICS', 'SALES_ANALYTICS', 'SUB_CATEGORY', 'VARCHAR', 'Product sub-category.', FALSE, 'Phones,Chairs'),
('ANALYTICS', 'SALES_ANALYTICS', 'QUANTITY', 'NUMBER', 'Units sold on the order line.', FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'SALES', 'NUMBER', 'Sales/revenue amount for the order line.', FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'DISCOUNT', 'NUMBER', 'Discount rate applied to the order line (0–1).', FALSE, '0.0,0.2'),
('ANALYTICS', 'SALES_ANALYTICS', 'PROFIT', 'NUMBER', 'Profit for the order line (can be negative).', FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'PROFIT_MARGIN', 'NUMBER', 'Line profit / sales (NULL when sales is 0).', FALSE, NULL),
('ANALYTICS', 'SALES_ANALYTICS', 'SHIP_MODE', 'VARCHAR', 'Shipping mode.', FALSE, 'Standard Class');

-- CUSTOMER_ANALYTICS
INSERT INTO TABLE_METADATA (TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, DESCRIPTION, IS_KEY, EXAMPLE_VALUES) VALUES
('ANALYTICS', 'CUSTOMER_ANALYTICS', '', NULL,
 'One row per customer with aggregated sales, profit, and order metrics.',
 FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'CUSTOMER_ID', 'VARCHAR', 'Unique customer identifier.', TRUE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'CUSTOMER_NAME', 'VARCHAR', 'Customer name.', FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'SEGMENT', 'VARCHAR', 'Customer segment.', FALSE, 'Corporate'),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'REGION', 'VARCHAR', 'Customer region.', FALSE, 'East'),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'STATE', 'VARCHAR', 'Customer state.', FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'ORDER_COUNT', 'NUMBER', 'Distinct orders for the customer.', FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'TOTAL_SALES', 'NUMBER', 'Lifetime for Revenue at customer grain.', FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'TOTAL_PROFIT', 'NUMBER', 'Lifetime for Profit at customer grain.', FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'AVG_ORDER_VALUE', 'NUMBER', 'Average order value for the customer.', FALSE, NULL),
('ANALYTICS', 'CUSTOMER_ANALYTICS', 'PROFIT_MARGIN', 'NUMBER', 'Customer profit margin.', FALSE, NULL);

-- PRODUCT_ANALYTICS
INSERT INTO TABLE_METADATA (TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, DESCRIPTION, IS_KEY, EXAMPLE_VALUES) VALUES
('ANALYTICS', 'PRODUCT_ANALYTICS', '', NULL,
 'One row per product with aggregated sales, profit, and quantity.',
 FALSE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'PRODUCT_ID', 'VARCHAR', 'Unique product identifier.', TRUE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'PRODUCT_NAME', 'VARCHAR', 'Product name.', FALSE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'CATEGORY', 'VARCHAR', 'Product category.', FALSE, 'Technology'),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'SUB_CATEGORY', 'VARCHAR', 'Product sub-category.', FALSE, 'Phones'),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'ORDER_COUNT', 'NUMBER', 'Distinct orders containing the product.', FALSE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'TOTAL_QUANTITY', 'NUMBER', 'Units sold.', FALSE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'TOTAL_SALES', 'NUMBER', 'Revenue for the product.', FALSE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'TOTAL_PROFIT', 'NUMBER', 'Profit for the product (may be negative).', FALSE, NULL),
('ANALYTICS', 'PRODUCT_ANALYTICS', 'PROFIT_MARGIN', 'NUMBER', 'Product profit margin.', FALSE, NULL);

-- CURATED entities (for joins / detail)
INSERT INTO TABLE_METADATA (TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, DESCRIPTION, IS_KEY, EXAMPLE_VALUES) VALUES
('CURATED', 'CUSTOMERS', '', NULL, 'Customer master information from CRM.', FALSE, NULL),
('CURATED', 'CUSTOMERS', 'CUSTOMER_ID', 'VARCHAR', 'Primary business key for customers.', TRUE, NULL),
('CURATED', 'CUSTOMERS', 'REGION', 'VARCHAR', 'Geographical region associated with the customer.', FALSE, 'West'),
('CURATED', 'ORDERS', '', NULL, 'Customer orders and financial metrics (order-line grain).', FALSE, NULL),
('CURATED', 'ORDERS', 'ORDER_ID', 'VARCHAR', 'Order identifier.', TRUE, NULL),
('CURATED', 'ORDERS', 'CUSTOMER_ID', 'VARCHAR', 'FK to CUSTOMERS.', TRUE, NULL),
('CURATED', 'ORDERS', 'PRODUCT_ID', 'VARCHAR', 'FK to PRODUCTS.', TRUE, NULL),
('CURATED', 'ORDERS', 'SALES', 'NUMBER', 'Sales/revenue amount for the order line.', FALSE, NULL),
('CURATED', 'ORDERS', 'PROFIT', 'NUMBER', 'Profit generated by the order line.', FALSE, NULL),
('CURATED', 'ORDERS', 'ORDER_DATE', 'DATE', 'Date on which the order was placed.', FALSE, NULL),
('CURATED', 'PRODUCTS', '', NULL, 'Product master data.', FALSE, NULL),
('CURATED', 'PRODUCTS', 'PRODUCT_ID', 'VARCHAR', 'Primary business key for products.', TRUE, NULL),
('CURATED', 'PRODUCTS', 'CATEGORY', 'VARCHAR', 'High-level product category.', FALSE, NULL),
('CURATED', 'PRODUCTS', 'SUB_CATEGORY', 'VARCHAR', 'Product sub-category.', FALSE, NULL);

-- ---------------------------------------------------------------------------
-- Sample / default analytics questions
-- ---------------------------------------------------------------------------
TRUNCATE TABLE IF EXISTS SAMPLE_QUESTIONS;
INSERT INTO SAMPLE_QUESTIONS (CATEGORY, QUESTION, EXPECTED_TABLES, EXPECTED_METRIC, SORT_ORDER) VALUES
('Revenue', 'What is total revenue?', 'SALES_ANALYTICS', 'Revenue', 1),
('Revenue', 'Show monthly revenue trend', 'SALES_ANALYTICS', 'Revenue', 2),
('Revenue', 'Show revenue by region', 'SALES_ANALYTICS', 'Revenue', 3),
('Revenue', 'Show revenue by category', 'SALES_ANALYTICS', 'Revenue', 4),
('Products', 'What are the top 10 products by revenue?', 'PRODUCT_ANALYTICS', 'Revenue', 5),
('Products', 'What are the top 10 products by profit?', 'PRODUCT_ANALYTICS', 'Profit', 6),
('Products', 'Which products have negative profit?', 'PRODUCT_ANALYTICS', 'Profit', 7),
('Customers', 'Who are the top 10 customers by revenue?', 'CUSTOMER_ANALYTICS', 'Revenue', 8),
('Customers', 'Show revenue by customer segment', 'SALES_ANALYTICS', 'Revenue', 9),
('Performance', 'Compare sales vs profit by category', 'SALES_ANALYTICS', 'Revenue,Profit', 10),
('Performance', 'Show profit margin by category', 'SALES_ANALYTICS', 'Profit Margin', 11),
('Performance', 'Show monthly sales growth', 'SALES_ANALYTICS', 'Revenue', 12);
