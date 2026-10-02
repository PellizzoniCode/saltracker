# DynamoDB data model

## Table keys

| Record | PK | SK |
|---|---|---|
| Asset metadata | `ASSET#<assetId>` | `METADATA` |
| Asset-tag lock | `ASSETTAG#<assetTag>` | `UNIQUE` |
| Maintenance event | `ASSET#<assetId>` | `MAINTENANCE#<date>#<maintenanceId>` |
| Recommendation | `ASSET#<assetId>` | `RECOMMENDATION#<timestamp>` |
| Audit history | `ASSET#<assetId>` | `HISTORY#<timestamp>#<eventId>` |

The asset-tag lock record enforces `assetTag` uniqueness. It is written alongside the asset metadata item in a single `TransactWriteItems` call, each conditioned on `attribute_not_exists(PK)`, so a duplicate tag cannot slip through a race between two concurrent creates. Renaming `assetTag` on update deletes the old lock item and creates the new one in the same transaction.

Week 1 uses asset metadata records; week 3 adds maintenance events. The shared partition leaves room for immutable history without creating unrelated tables.

## Asset access patterns

| Access pattern | Implementation |
|---|---|
| Create asset | Conditional `TransactWriteItems` (asset item + asset-tag lock item) |
| View asset by ID | Strongly consistent `GetItem` |
| Administrator and Auditor listing | Paginated `Scan` |
| Employee listing | `Query` on `AssignedUserIndex` using the Cognito `sub` claim |
| Manager and Technician listing | `Query` on `DepartmentIndex` using the Cognito `custom:department` claim |
| Continue a large result set | Return and accept an encoded `nextToken` |

## Maintenance access patterns

Maintenance events share the asset's partition, so an asset's full service history is a single `Query` and never touches the global secondary indexes (maintenance items carry no `department` or `assignedUserId`).

| Access pattern | Implementation |
|---|---|
| List an asset's history (newest first) | `Query` on `PK = ASSET#<assetId>` and `begins_with(SK, "MAINTENANCE#")` with `ScanIndexForward = false`, paginated by `nextToken` |
| Record maintenance | `TransactWriteItems`: conditional `Put` of the maintenance item, plus an `Update` moving the asset's `lastMaintenanceDate` (and `lastCleaningDate` for `Cleaning`) forward when the new date is later |
| View or find one record | `Query` on the asset partition filtered by `maintenanceId` (the date is part of the sort key) |
| Correct a record (Administrator) | Conditional `Put`; when `performedDate` changes, `Delete` the old item and `Put` the new key in one transaction |
| Delete a record (Administrator) | Conditional `DeleteItem` |

`performedBy` is always the caller's Cognito `sub`. The API rejects a request that tries to set it, along with any other server-controlled field (`maintenanceId`, `assetId`, `createdAt`). Deleting or back-dating a record does not move the asset's `lastMaintenanceDate` backwards. An asset update is conditioned on `lastMaintenanceDate` and `lastCleaningDate` still holding the values it read, so it cannot overwrite a date moved forward by a concurrent maintenance record; it returns 409 instead.

Example item:

```json
{
  "PK": "ASSET#AST-0001",
  "SK": "MAINTENANCE#2026-08-15#MNT-0001",
  "maintenanceId": "MNT-0001",
  "assetId": "AST-0001",
  "performedDate": "2026-08-15",
  "maintenanceType": "Cleaning",
  "notes": "Removed external dust and inspected ventilation openings.",
  "performedBy": "example-technician-cognito-sub",
  "cost": 25.00,
  "conditionAfterService": "Good",
  "createdAt": "2026-08-15T10:00:00+00:00"
}
```

`maintenanceType` is one of `Cleaning`, `Inspection`, `Repair`, `Preventive`, `Upgrade`, `Other`. `conditionAfterService` is one of `Good`, `Fair`, `Poor`, `Unknown`.

## Global secondary indexes

| Index | Partition key | Purpose |
|---|---|---|
| `AssignedUserIndex` | `assignedUserId` | Find assets assigned to a particular employee |
| `DepartmentIndex` | `department` | Find assets belonging to a particular department |

DynamoDB returns results in pages. When more results are available, the API returns a `nextToken`, which the frontend can use to load the next page.

Optional index fields that are empty or unknown are omitted from the DynamoDB item because a global secondary index key cannot contain an empty string or `null`.

Financial values are stored as DynamoDB numbers created from Python `Decimal`. Unknown optional data is stored as `null`, never guessed.

