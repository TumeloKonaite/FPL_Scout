# Completed-report public lookup index validation

Validation was run on 2026-08-06 with PostgreSQL 18.3. The isolated validation
table contained 300,000 report runs distributed across five seasons, 38
gameweeks, completed and processing statuses, and nullable/non-null report
payloads. There were 957 rows matching the target season, gameweek, status, and
non-null report predicate. `ANALYZE completed_report_runs` was run before each
plan was collected.

This controlled dataset is a production-scale proxy for repeated historical and
regenerated runs; no production data was copied. Both plans used warm shared
buffers, so shared reads were zero. Deployments should repeat the comparison
against the production-equivalent staging dataset because planner decisions
depend on the deployed data distribution and statistics.

## Comparison

| Metric | Before | After |
| --- | ---: | ---: |
| Planning time | 2.835 ms | 3.667 ms |
| Execution time | 103.363 ms | 0.098 ms |
| Rows examined | 300,000 | 1 index entry |
| Matching rows visited before `LIMIT` | 957 | 1 |
| Shared buffer hits, execution | 11,352 | 4 |
| Shared buffer reads, execution | 0 | 0 |
| Shared buffer hits, planning | 70 | 105 |
| Shared buffer reads, planning | 0 | 0 |
| Access path | Parallel sequential scan | Index scan |
| Separate sort | Top-N heapsort | None |

The after plan uses `ix_completed_report_public_lookup`, applies `season` and
`gameweek` as index conditions, obtains completed rows from the partial-index
predicate, and checks `final_report IS NOT NULL` as a residual filter. The index
ordering satisfies `ORDER BY updated_at DESC`, so PostgreSQL does not perform a
separate sort.

## Query

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    run_id,
    final_report,
    updated_at
FROM completed_report_runs
WHERE season = '2025-26'
  AND gameweek = 34
  AND status = 'completed'
  AND final_report IS NOT NULL
ORDER BY updated_at DESC
LIMIT 1;
```

## Before migration

```text
Limit  (cost=14636.67..14636.67 rows=1 width=263) (actual time=94.733..103.111 rows=1.00 loops=1)
  Buffers: shared hit=11352
  ->  Sort  (cost=14636.67..14639.06 rows=954 width=263) (actual time=94.482..102.860 rows=1.00 loops=1)
        Sort Key: updated_at DESC
        Sort Method: top-N heapsort  Memory: 26kB
        Buffers: shared hit=11352
        ->  Gather  (cost=1000.00..14631.90 rows=954 width=263) (actual time=0.863..101.313 rows=957.00 loops=1)
              Workers Planned: 2
              Workers Launched: 2
              Buffers: shared hit=11349
              ->  Parallel Seq Scan on completed_report_runs  (cost=0.00..13536.50 rows=398 width=263) (actual time=0.169..65.434 rows=319.00 loops=3)
                    Filter: ((final_report IS NOT NULL) AND (season = '2025-26'::text) AND (gameweek = 34) AND (status = 'completed'::text))
                    Rows Removed by Filter: 99681
                    Buffers: shared hit=11349
Planning:
  Buffers: shared hit=70
Planning Time: 2.835 ms
Execution Time: 103.363 ms
```

The parallel scan processed 100,000 rows in each of three loops (300,000 total),
returning 319 matches per loop (957 total) to the separate top-N sort.

## After migration

```text
Limit  (cost=0.42..4.58 rows=1 width=263) (actual time=0.069..0.069 rows=1.00 loops=1)
  Buffers: shared hit=4
  ->  Index Scan using ix_completed_report_public_lookup on completed_report_runs  (cost=0.42..3934.24 rows=945 width=263) (actual time=0.066..0.066 rows=1.00 loops=1)
        Index Cond: ((season = '2025-26'::text) AND (gameweek = 34))
        Filter: (final_report IS NOT NULL)
        Index Searches: 1
        Buffers: shared hit=4
Planning:
  Buffers: shared hit=105
Planning Time: 3.667 ms
Execution Time: 0.098 ms
```

## Deployment validation

On a production-equivalent staging database, capture the before plan, apply the
Alembic migration, refresh statistics if needed, and capture the after plan:

```sql
ANALYZE completed_report_runs;
```

```bash
uv run alembic upgrade 20260806_05
```

Run the query above before and after the migration and retain both complete
plans with the deployment record. Do not assert an exact plan in automated tests:
small tables, cached pages, data distribution, and PostgreSQL settings can all
make a sequential scan legitimately cheaper.
