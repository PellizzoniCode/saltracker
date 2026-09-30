import calendar
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CURRENCY_PLACES = Decimal("0.01")
PERCENT_PLACES = Decimal("0.01")


class DepreciationError(ValueError):
    """Raised when depreciation input is invalid."""


def _decimal(value, field_name):
    if isinstance(value, bool):
        raise DepreciationError(f"{field_name} must be a finite number.")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise DepreciationError(
            f"{field_name} must be a finite number."
        ) from exc

    if not result.is_finite():
        raise DepreciationError(f"{field_name} must be a finite number.")

    return result


def _positive_integer(value, field_name):
    if isinstance(value, bool):
        raise DepreciationError(f"{field_name} must be a positive integer.")

    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise DepreciationError(
            f"{field_name} must be a positive integer."
        ) from exc

    if result <= 0 or str(result) != str(value).strip():
        raise DepreciationError(f"{field_name} must be a positive integer.")

    return result


def _date(value, field_name):
    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise DepreciationError(f"{field_name} must use YYYY-MM-DD format.")

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DepreciationError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from exc


def _add_months(start_date, months):
    month_index = start_date.month - 1 + months
    year = start_date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def completed_months(start_date, as_of_date):
    """Return completed monthly anniversaries, never a negative value."""
    if as_of_date <= start_date:
        return 0

    months = (
        (as_of_date.year - start_date.year) * 12
        + as_of_date.month
        - start_date.month
    )

    anniversary = _add_months(start_date, months)

    if as_of_date < anniversary:
        months -= 1

    return max(0, months)


def calculate_depreciation(
    purchase_value,
    salvage_value,
    useful_life_months,
    in_service_date,
    as_of_date=None,
):
    """
    Calculate straight-line depreciation using completed monthly anniversaries.

    Bedrock must not calculate or replace these deterministic financial values.
    """
    purchase = _decimal(purchase_value, "purchaseValue")
    salvage = _decimal(salvage_value, "salvageValue")
    useful_life = _positive_integer(
        useful_life_months,
        "usefulLifeMonths",
    )
    service_date = _date(in_service_date, "inServiceDate")
    calculation_date = (
        _date(as_of_date, "asOfDate")
        if as_of_date is not None
        else date.today()
    )

    if purchase < 0:
        raise DepreciationError("purchaseValue cannot be negative.")

    if salvage < 0:
        raise DepreciationError("salvageValue cannot be negative.")

    if salvage > purchase:
        raise DepreciationError(
            "salvageValue cannot exceed purchaseValue."
        )

    elapsed_months = completed_months(service_date, calculation_date)
    depreciable_amount = purchase - salvage
    monthly_depreciation = depreciable_amount / Decimal(useful_life)
    annual_depreciation = monthly_depreciation * Decimal(12)

    depreciated_months = min(elapsed_months, useful_life)
    accumulated_depreciation = (
        monthly_depreciation * Decimal(depreciated_months)
    )
    current_book_value = max(
        salvage,
        purchase - accumulated_depreciation,
    )

    useful_life_consumed = min(
        Decimal("100"),
        Decimal(elapsed_months)
        * Decimal("100")
        / Decimal(useful_life),
    )

    replacement_date = _add_months(service_date, useful_life)

    return {
        "asOfDate": calculation_date.isoformat(),
        "inServiceDate": service_date.isoformat(),
        "estimatedReplacementDate": replacement_date.isoformat(),
        "elapsedMonths": elapsed_months,
        "usefulLifeMonths": useful_life,
        "originalPurchaseValue": purchase.quantize(
            CURRENCY_PLACES,
            rounding=ROUND_HALF_UP,
        ),
        "salvageValue": salvage.quantize(
            CURRENCY_PLACES,
            rounding=ROUND_HALF_UP,
        ),
        "annualDepreciation": annual_depreciation.quantize(
            CURRENCY_PLACES,
            rounding=ROUND_HALF_UP,
        ),
        "accumulatedDepreciation": accumulated_depreciation.quantize(
            CURRENCY_PLACES,
            rounding=ROUND_HALF_UP,
        ),
        "currentBookValue": current_book_value.quantize(
            CURRENCY_PLACES,
            rounding=ROUND_HALF_UP,
        ),
        "usefulLifeConsumedPercent": useful_life_consumed.quantize(
            PERCENT_PLACES,
            rounding=ROUND_HALF_UP,
        ),
    }