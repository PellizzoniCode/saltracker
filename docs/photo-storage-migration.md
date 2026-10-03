# Migrating existing photos out of `pending/`

New uploads land under `pending/` and are moved to `claimed/` when an asset is saved (see `_claim_photo` in `backend/asset_api/app.py`). The stack's `ExpireUnclaimedPendingUploads` lifecycle rule deletes everything under `pending/` after 7 days.

Assets saved **before** that change still reference `pending/` keys. If the lifecycle rule is deployed first, those photos expire and the assets point at deleted objects. Backfill them first with `scripts/migrate_pending_photos.py`.

For each asset whose `imageKey` starts with `pending/`, the script copies the photo to `claimed/`, updates the asset (only if `imageKey` hasn't changed in the meantime), then deletes the pending copy. It is idempotent, so it is safe to re-run. A photo whose source object is already gone is reported and the asset is left alone.

## Order of operations

Run per environment, **before** deploying the template that contains the lifecycle rule. Replace `ENVIRONMENT` with the stack you're migrating (e.g. `test`; run `dev` only once approved):

```bash
ENVIRONMENT=test
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
TABLE=smart-asset-tracker-${ENVIRONMENT}
BUCKET=smart-asset-tracker-${ENVIRONMENT}-photos-${ACCOUNT}-us-east-1   # <stack-name>-photos-<account>-<region>

# 1. Dry run: lists affected assets, changes nothing
python scripts/migrate_pending_photos.py --table "$TABLE" --bucket "$BUCKET"

# 2. Apply
python scripts/migrate_pending_photos.py --table "$TABLE" --bucket "$BUCKET" --apply
```

3. Deploy the stack.
4. Re-run the dry run. It should report `would migrate: 0`; anything listed was saved between steps 2 and 3 and can be applied the same way.

Review the "source photo already missing" and "failed" sections of the output. Missing photos had already expired or been removed and need to be re-uploaded by hand.

The stack name in `BUCKET` assumes the default `smart-asset-tracker-<environment>` naming from `samconfig.toml`; check the `AssetPhotoBucketName` stack output if yours differs.
