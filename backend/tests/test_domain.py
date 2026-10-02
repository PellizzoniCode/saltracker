import pathlib
import sys
import unittest
from unittest.mock import patch
from datetime import date, timedelta


sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "asset_api"))

from domain import (  # noqa: E402
    ValidationError,
    can_create,
    can_manage_maintenance,
    can_read,
    can_record_maintenance,
    parse_groups,
    validate_asset,
    validate_create_permissions,
    validate_maintenance,
    validate_update_permissions,
)


VALID_ASSET = {
    "assetTag": "TAG-0001",
    "category": "Laptop",
    "description": "Business laptop",
    "purchaseDate": "2026-09-01",
    "inServiceDate": "2026-09-01",
    "purchaseValue": "1500.00",
    "salvageValue": "100.00",
    "usefulLifeMonths": 48,
    "condition": "Good",
    "status": "Assigned",
}


class DomainTests(unittest.TestCase):
    def test_valid_asset(self):
        validate_asset(VALID_ASSET)

    def test_missing_required_field(self):
        asset = {**VALID_ASSET}
        del asset["description"]
        with self.assertRaises(ValidationError) as error:
            validate_asset(asset)
        self.assertIn("description", error.exception.fields)

    def test_salvage_cannot_exceed_purchase_value(self):
        asset = {**VALID_ASSET, "salvageValue": "2000.00"}
        with self.assertRaises(ValidationError):
            validate_asset(asset)

    def test_useful_life_must_be_positive_integer(self):
        with self.assertRaises(ValidationError):
            validate_asset({**VALID_ASSET, "usefulLifeMonths": 0})

    def test_groups_are_parsed_from_api_gateway_claim(self):
        self.assertEqual(parse_groups("[Technician, Administrator]"), {"Technician", "Administrator"})

    def test_employee_can_only_read_assigned_asset(self):
        groups = {"Employee"}
        self.assertTrue(can_read(groups, {"sub": "user-1"}, {"assignedUserId": "user-1"}))
        self.assertFalse(can_read(groups, {"sub": "user-1"}, {"assignedUserId": "user-2"}))

    def test_manager_can_only_read_department_asset(self):
        groups = {"Manager"}
        claims = {"sub": "manager-1", "custom:department": "IT"}
        self.assertTrue(can_read(groups, claims, {"department": "IT"}))
        self.assertFalse(can_read(groups, claims, {"department": "Finance"}))

    def test_auditor_is_read_only(self):
        self.assertTrue(can_read({"Auditor"}, {"sub": "a"}, {}))
        self.assertFalse(can_create({"Auditor"}))
        self.assertFalse(validate_update_permissions({"Auditor"}, {"condition"}))

    def test_technician_update_is_field_limited(self):
        self.assertTrue(validate_update_permissions({"Technician"}, {"condition", "status"}))
        self.assertFalse(validate_update_permissions({"Technician"}, {"purchaseValue"}))

    def test_technician_cannot_set_assignment_fields_on_create(self):
        self.assertFalse(validate_create_permissions({"Technician"}, {**VALID_ASSET, "assignedUserId": "user-1"}))
        self.assertFalse(validate_create_permissions({"Technician"}, {**VALID_ASSET, "department": "IT"}))
        self.assertTrue(validate_create_permissions({"Technician"}, VALID_ASSET))

    def test_administrator_can_set_assignment_fields_on_create(self):
        self.assertTrue(validate_create_permissions({"Administrator"}, {**VALID_ASSET, "assignedUserId": "user-1", "department": "IT"}))


VALID_MAINTENANCE = {
    "performedDate": "2026-08-15",
    "maintenanceType": "Cleaning",
    "notes": "Removed external dust and inspected ventilation openings.",
    "cost": "25.00",
    "conditionAfterService": "Good",
}


class MaintenanceDomainTests(unittest.TestCase):
    def test_valid_maintenance_passes(self):
        validate_maintenance(dict(VALID_MAINTENANCE))

    def test_optional_fields_may_be_omitted(self):
        validate_maintenance({"performedDate": "2026-08-15", "maintenanceType": "Repair"})

    def test_rejects_invalid_values(self):
        cases = {
            "performedDate": "15/08/2026",
            "maintenanceType": "Polishing",
            "conditionAfterService": "Shiny",
            "cost": "-1",
            "notes": "x" * 2001,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as raised:
                    validate_maintenance({**VALID_MAINTENANCE, field: value})
                self.assertEqual(raised.exception.fields, [field])

    def test_rejects_non_text_enum_values(self):
        for field, value in (("maintenanceType", ["Repair"]), ("conditionAfterService", {"value": "Good"})):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as raised:
                    validate_maintenance({**VALID_MAINTENANCE, field: value})
                self.assertEqual(raised.exception.fields, [field])

    def test_rejects_out_of_range_cost(self):
        for cost in ("1e200", "1000000000.01", "10.001"):
            with self.subTest(cost=cost):
                with self.assertRaises(ValidationError) as raised:
                    validate_maintenance({**VALID_MAINTENANCE, "cost": cost})
                self.assertEqual(raised.exception.fields, ["cost"])
        validate_maintenance({**VALID_MAINTENANCE, "cost": "1000000000"})
        validate_maintenance({**VALID_MAINTENANCE, "cost": 25.5})

    def test_accepts_latest_local_date_but_not_later(self):
        with patch("domain.latest_local_date", return_value=date(2026, 8, 15)):
            validate_maintenance({**VALID_MAINTENANCE, "performedDate": "2026-08-15"})
            with self.assertRaises(ValidationError):
                validate_maintenance({**VALID_MAINTENANCE, "performedDate": "2026-08-16"})

    def test_rejects_future_date(self):
        future = (date.today() + timedelta(days=2)).isoformat()
        with self.assertRaises(ValidationError):
            validate_maintenance({**VALID_MAINTENANCE, "performedDate": future})

    def test_rejects_server_controlled_fields(self):
        for field in ("performedBy", "maintenanceId", "assetId", "createdAt"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as raised:
                    validate_maintenance({**VALID_MAINTENANCE, field: "x"})
                self.assertEqual(raised.exception.fields, [field])

    def test_missing_required_fields(self):
        with self.assertRaises(ValidationError) as raised:
            validate_maintenance({"notes": "No date"})
        self.assertEqual(raised.exception.fields, ["maintenanceType", "performedDate"])

    def test_partial_allows_missing_required_fields(self):
        validate_maintenance({"notes": "Correction"}, partial=True)

    def test_asset_service_dates_must_be_dates(self):
        validate_asset({**VALID_ASSET, "lastMaintenanceDate": "2026-01-01", "lastCleaningDate": None})
        for field in ("lastMaintenanceDate", "lastCleaningDate"):
            with self.subTest(field=field):
                with self.assertRaises(ValidationError) as raised:
                    validate_asset({**VALID_ASSET, field: 5})
                self.assertEqual(raised.exception.fields, [field])

    def test_maintenance_permissions(self):
        self.assertTrue(can_record_maintenance({"Technician"}))
        self.assertTrue(can_record_maintenance({"Administrator"}))
        self.assertFalse(can_record_maintenance({"Manager", "Employee", "Auditor"}))
        self.assertTrue(can_manage_maintenance({"Administrator"}))
        self.assertFalse(can_manage_maintenance({"Technician"}))


if __name__ == "__main__":
    unittest.main()

