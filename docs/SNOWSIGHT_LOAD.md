# Snowsight load (when Python connector auth fails)

Use this if `python scripts/load_data.py` cannot connect
(`externalbrowser` SAML error, or missing password).

## Steps

1. Open Snowsight → **Projects → Worksheets**
2. Set role `ACCOUNTADMIN`, warehouse `COMPUTE_WH`
3. Run `sql/bootstrap_ddl.sql` (creates DB / schemas / RAW tables)
4. Run `sql/load_raw_data.sql` (inserts customers / orders / products)  
   Regenerate anytime with:
   ```bash
   python -c "exec(open('scripts/prepare_data.py').read())"  # if needed
   ```
   Or from repo root after CSVs exist, regenerate inserts:
   ```bash
   # re-run the generator used in Phase 1 fallback, or:
   python scripts/prepare_data.py --generate
   ```
5. Run `sql/curated.sql`
6. Run `sql/analytics.sql`
7. Run `sql/views.sql`
8. Verify:

```sql
SELECT 'CUSTOMERS_RAW' t, COUNT(*) n FROM ANALYTICS_AI_DB.RAW.CUSTOMERS_RAW
UNION ALL SELECT 'ORDERS_RAW', COUNT(*) FROM ANALYTICS_AI_DB.RAW.ORDERS_RAW
UNION ALL SELECT 'PRODUCTS_RAW', COUNT(*) FROM ANALYTICS_AI_DB.RAW.PRODUCTS_RAW
UNION ALL SELECT 'SALES_ANALYTICS', COUNT(*) FROM ANALYTICS_AI_DB.ANALYTICS.SALES_ANALYTICS;
```

## Faster path (recommended)

Put your Snowflake **web login password** in `.env`:

```bash
SNOWFLAKE_AUTHENTICATOR=password
SNOWFLAKE_PASSWORD=your_password_here
```

Then:

```bash
python scripts/load_data.py --with-phase2
```
