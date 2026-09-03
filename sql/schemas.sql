-- =============================================================================
-- Phase 1: Schemas
-- =============================================================================

USE DATABASE ANALYTICS_AI_DB;

CREATE SCHEMA IF NOT EXISTS RAW
  COMMENT = 'Landing zone for source system extracts (CRM, ERP, Product Master)';

CREATE SCHEMA IF NOT EXISTS CURATED
  COMMENT = 'Cleaned, typed, deduplicated business entities';

CREATE SCHEMA IF NOT EXISTS ANALYTICS
  COMMENT = 'Curated analytics marts for BI and AI SQL generation';

CREATE SCHEMA IF NOT EXISTS AI
  COMMENT = 'Semantic metadata, business glossary, sample questions, query logs';
