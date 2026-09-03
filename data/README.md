# Source extracts (generated or split from Sample Superstore)

| File | Source system simulation |
|------|--------------------------|
| `customers.csv` | CRM |
| `orders.csv` | ERP / Order Management |
| `products.csv` | Product Master |

Regenerate:

```bash
python scripts/prepare_data.py --generate
# or
python scripts/prepare_data.py --source /path/to/SampleSuperstore.csv
```
