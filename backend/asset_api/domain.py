from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation


READ_GROUPS = {"Employee", "Technician", "Manager", "Administrator", "Auditor"}
CREATE_GROUPS = {"Technician", "Administrator"}
FULL_UPDATE_GROUPS = {"Administrator"}
TECHNICIAN_UPDATE_FIELDS = {
    "condition",
    "status",
    "description",
    "location",
    "lastCleaningDate",
    "lastMaintenanceDate",
    "imageKey",
}
CREATE_RESTRICTED_FIELDS = {"assignedUserId", "department"}
SERVICE_DATE_FIELDS = ("lastMaintenanceDate", "lastCleaningDate")

REQUIRED_FIELDS = {
    "assetTag",
    "category",
    "description",
    "purchaseDate",
    "inServiceDate",
    "purchaseValue",
    "salvageValue",
    "usefulLifeMonths",
    "condition",
    "status",
}

VALID_STATUSES = {
    "Available",
    "Assigned",
    "Checked Out",
    "In Maintenance",
    "Damaged",
    "Lost",
    "Stolen",
    "Retired",
}


class ValidationError(ValueError):
    def __init__(self, message, fields=None):
        super().__init__(message)
        self.fields = fields or []


def parse_groups(raw_groups):
    if not raw_groups:
        return set()
    if isinstance(raw_groups, list):
        return set(raw_groups)
    return {group.strip().strip("[]'") for group in str(raw_groups).split(",") if group.strip()}


def validate_asset(payload, partial=False):
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    if "assetTag" in payload and (not isinstance(payload["assetTag"], str) or not payload["assetTag"].strip()):
        raise ValidationError("Asset tag must contain a value.", ["assetTag"])

    if not partial:
        missing = sorted(field for field in REQUIRED_FIELDS if payload.get(field) in (None, ""))
        if missing:
            raise ValidationError("Required asset information is missing.", missing)

    if "status" in payload and payload["status"] not in VALID_STATUSES:
        raise ValidationError("Invalid asset status.", ["status"])

    for field in ("purchaseDate", "inServiceDate"):
        if field in payload:
            try:
                date.fromisoformat(payload[field])
            except (TypeError, ValueError):
                raise ValidationError(f"{field} must use YYYY-MM-DD.", [field])

    for field in SERVICE_DATE_FIELDS:
        if payload.get(field) not in (None, ""):
            try:
                date.fromisoformat(payload[field])
            except (TypeError, ValueError):
                raise ValidationError(f"{field} must use YYYY-MM-DD.", [field])

    money_fields = ("purchaseValue", "salvageValue")
    values = {}
    for field in money_fields:
        if field in payload:
            try:
                value = Decimal(str(payload[field]))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError(f"{field} must be a valid financial value.", [field])
            if not value.is_finite() or value < 0:
                raise ValidationError(f"{field} must be finite and non-negative.", [field])
            values[field] = value

    if "purchaseValue" in values and "salvageValue" in values:
        if values["salvageValue"] > values["purchaseValue"]:
            raise ValidationError("Salvage value cannot exceed purchase value.", money_fields)

    if "usefulLifeMonths" in payload:
        value = payload["usefulLifeMonths"]
        if type(value) is not int or value <= 0:
            raise ValidationError("Useful life must be a positive integer.", ["usefulLifeMonths"])


def can_read(groups, claims, asset):
    if not groups.intersection(READ_GROUPS):
        return False
    if groups.intersection({"Administrator", "Auditor"}):
        return True

    if groups.intersection({"Manager", "Technician"}):
        department = claims.get("custom:department")
        return bool(department and department == asset.get("department"))

    if "Employee" in groups:
        return claims.get("sub") == asset.get("assignedUserId")

    return False


def can_create(groups):
    return bool(groups.intersection(CREATE_GROUPS))


def validate_update_permissions(groups, changed_fields):
    if groups.intersection(FULL_UPDATE_GROUPS):
        return True
    if "Technician" in groups:
        return set(changed_fields).issubset(TECHNICIAN_UPDATE_FIELDS)
    return False


def validate_create_permissions(groups, payload):
    if groups.intersection(FULL_UPDATE_GROUPS):
        return True
    restricted_present = {field for field in CREATE_RESTRICTED_FIELDS if payload.get(field)}
    return not restricted_present


MAINTENANCE_CREATE_GROUPS = {"Technician", "Administrator"}
MAINTENANCE_MANAGE_GROUPS = {"Administrator"}
VALID_MAINTENANCE_TYPES = {"Cleaning", "Inspection", "Repair", "Preventive", "Upgrade", "Other"}
VALID_CONDITIONS = {"Good", "Fair", "Poor", "Unknown"}
MAINTENANCE_FIELDS = {"performedDate", "maintenanceType", "notes", "cost", "conditionAfterService"}
MAINTENANCE_REQUIRED_FIELDS = {"performedDate", "maintenanceType"}
MAX_NOTES_LENGTH = 2000
MAX_COST = Decimal("1000000000")
# The furthest ahead of UTC any time zone runs (UTC+14).
MAX_UTC_OFFSET = timedelta(hours=14)


def can_record_maintenance(groups):
    return bool(groups.intersection(MAINTENANCE_CREATE_GROUPS))


def can_manage_maintenance(groups):
    return bool(groups.intersection(MAINTENANCE_MANAGE_GROUPS))


def latest_local_date():
    """The latest calendar date currently in use anywhere on Earth."""
    return (datetime.now(timezone.utc) + MAX_UTC_OFFSET).date()


def validate_maintenance(payload, partial=False):
    """Validate client-supplied maintenance fields.

    Server-controlled fields such as performedBy are rejected rather than
    ignored, so a client can never believe it set them.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    unknown = sorted(set(payload) - MAINTENANCE_FIELDS)
    if unknown:
        raise ValidationError("These maintenance fields cannot be set by the client.", unknown)

    if not partial:
        missing = sorted(field for field in MAINTENANCE_REQUIRED_FIELDS if payload.get(field) in (None, ""))
        if missing:
            raise ValidationError("Required maintenance information is missing.", missing)

    if "performedDate" in payload:
        try:
            performed = date.fromisoformat(payload["performedDate"])
        except (TypeError, ValueError):
            raise ValidationError("performedDate must use YYYY-MM-DD.", ["performedDate"])
        # Lambda runs in UTC, so allow the local "today" of zones ahead of UTC but nothing later.
        if performed > latest_local_date():
            raise ValidationError("performedDate cannot be in the future.", ["performedDate"])

    maintenance_type = payload.get("maintenanceType")
    if "maintenanceType" in payload and (not isinstance(maintenance_type, str)
                                         or maintenance_type not in VALID_MAINTENANCE_TYPES):
        raise ValidationError("Invalid maintenance type.", ["maintenanceType"])

    condition = payload.get("conditionAfterService")
    if condition is not None and (not isinstance(condition, str) or condition not in VALID_CONDITIONS):
        raise ValidationError("Invalid condition after service.", ["conditionAfterService"])

    notes = payload.get("notes")
    if notes is not None:
        if not isinstance(notes, str):
            raise ValidationError("notes must be text.", ["notes"])
        if len(notes) > MAX_NOTES_LENGTH:
            raise ValidationError(f"notes cannot exceed {MAX_NOTES_LENGTH} characters.", ["notes"])

    cost = payload.get("cost")
    if cost not in (None, ""):
        try:
            value = Decimal(str(cost))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("cost must be a valid financial value.", ["cost"])
        if not value.is_finite() or value < 0:
            raise ValidationError("cost must be finite and non-negative.", ["cost"])
        if value > MAX_COST or value.as_tuple().exponent < -2:
            raise ValidationError("cost must be at most 1,000,000,000 with no more than two decimal places.", ["cost"])
