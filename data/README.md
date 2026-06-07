# Runtime data (gitignored)

This directory holds local demo and agent runtime stores. Contents are created by seed scripts and are not committed (except this file).

Typical paths after seeding:

- `lancedb/` — domain graph and vector stores
- `bom.duckdb` — component master (DuckDB)

Do not hand-edit binary files. Refresh with:

```bash
uv run python scripts/seed_complex_bom.py --reset
```

See [seeding.md](../docs/seeding.md).
