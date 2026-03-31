# Holdings Normalization

Use this directory for normalized treasury and investment snapshots.

## Minimum Fields

- `as_of`
- `account_id`
- `bucket` (`operating`, `reserve`, `investable`, `private_manual`)
- `asset_id`
- `quantity`
- `market_value`
- `currency`
- `source_name`
- `last_verified_at`

## Rule

If liquidity buckets are missing, recommendations should stop and request clarification.
