# Domain Data Model — Ground Truth

Field names from `backend/shared/models.py`:

| Design Doc Term | Actual Code Field |
|---|---|
| product | `flag_program` |
| sub_product | `jenis_leads` |
| channel | `media_blasting` |
| region | `wilayah` (int 1-17) |
| customer_id | `cif` (PII) |

## Valid Enum Values

```python
VALID_MEDIA_BLASTING = {"wa", "digisales", "telesales", "email", "push notif", "sms"}
VALID_FLAG_PROGRAM = {"PROGRAM BIAYA ADMIN", "PROGRAM QRIS"}
SIMILAR_CAMPAIGN_DIMENSIONS = {"media_blasting", "jenis_leads", "flag_program"}
```
