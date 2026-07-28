# Consensus XI deployment and regeneration

Catalogue deployment and report regeneration are separate operational steps.

## Deployment checks

1. Confirm `src/config/player_catalogues/<season>.json` exists for every
   historical season being regenerated.
2. Validate the snapshot season, source, retrieval time, schema version,
   snapshot identifier, official player IDs, teams, and positions.
3. Deploy the API and pipeline worker from the same revision so every entry
   point uses the same season-aware catalogue provider.
4. Run one production-path smoke report and confirm the manifest records
   `catalogue.season`, `catalogue.snapshot_identifier`, and
   `catalogue.fingerprint`.

## Separate regeneration checklist

1. Run the historical regeneration CLI in dry-run mode and retain its
   contamination inventory:

   ```bash
   python -m src.app.cli.regenerate_historical_reports \
     --season 2025-26 \
     --from-gameweek 1 \
     --to-gameweek 38 \
     --deadlines-file data/gameweek_deadlines/2025-26.json \
     --dry-run \
     --output regeneration-dry-run.json
   ```

2. Identify canonical reports whose suggested team failed with
   `authoritative_player_catalogue_unavailable`, along with any legacy-only
   snapshots selected for replacement.
3. Run regeneration without `--dry-run`, using a recorded batch identifier.
   Do not use `--allow-identical-fingerprint` unless the exception is reviewed
   and an override justification is recorded.
4. Verify every successful replacement records the matching historical
   deadline, catalogue snapshot identifier, source-video fingerprint,
   generation timestamp, previous run IDs, and supersession metadata.
5. Query the public season index and report endpoints. Confirm successful
   vote-based squads expose official player IDs, player support/provenance, and
   `has_suggested_team: true`.
6. Confirm failed and legacy runs remain auditable and are not presented as
   newly generated vote-based consensus squads.
